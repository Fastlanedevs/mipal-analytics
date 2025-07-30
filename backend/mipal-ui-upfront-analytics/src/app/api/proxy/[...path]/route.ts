import { NextRequest } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth.config";
import { tokenManager } from "@/lib/token-manager";

/**
 * Retrieves and validates access token from the current NextAuth session
 * @param forceRefresh - If true, forces a token refresh even if current token is valid
 * @returns Valid access token or null if authentication fails
 */
async function getAccessToken(forceRefresh = false) {
  try {
    // Use getServerSession to get the session data directly
    // This properly decrypts the NextAuth session token and extracts the JWT tokens
    const session = await getServerSession(authOptions);

    if (!session) {
      console.error("No session found");
      return null;
    }

    // Get access token from session - NextAuth stores it in multiple possible locations
    let accessToken =
      (session as any).access_token || (session as any).accessToken;
    const refreshToken =
      (session as any).refresh_token || (session as any).refreshToken;

    // Handle token refresh scenarios
    if (forceRefresh && refreshToken) {
      // Force refresh the token (used when we get 401 responses)
      accessToken = await tokenManager.refreshAccessToken(refreshToken);
    } else if (!accessToken && refreshToken) {
      // No access token available, try to refresh using refresh token
      accessToken = await tokenManager.refreshAccessToken(refreshToken);
    } else if (accessToken && refreshToken) {
      // We have an access token, check if it needs refreshing based on expiration
      accessToken = await tokenManager.getValidAccessToken(
        accessToken,
        refreshToken
      );
    }

    if (!accessToken) {
      console.error("No valid access token available");
      return null;
    }

    return accessToken;
  } catch (error) {
    console.error("Error in getAccessToken:", error);
    return null;
  }
}

/**
 * Makes authenticated requests to the backend with automatic token refresh on 401 errors
 * @param url - The backend URL to call
 * @param options - Fetch options (method, headers, body, etc.)
 * @returns Response from the backend
 */
async function makeBackendRequest(url: string, options: RequestInit) {
  // Get the current access token
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return new Response("Unauthorized", { status: 401 });
  }

  // Make the initial request with the access token
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${accessToken}`,
    },
  });

  // If we get a 401 Unauthorized, try refreshing the token once
  if (response.status === 401) {
    console.log("Got 401, attempting token refresh...");
    const refreshedToken = await getAccessToken(true);

    if (refreshedToken) {
      console.log("Token refreshed, retrying request...");
      // Retry the request with the refreshed token
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${refreshedToken}`,
        },
      });
    }
  }

  return response;
}

/**
 * Handles GET requests to the backend API
 * Proxies requests with authentication and automatic token refresh
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  // Reconstruct the backend path from the dynamic route segments
  const path = params.path.join("/");

  // Get query parameters from the request URL
  const searchParams = request.nextUrl.searchParams;
  const queryString = searchParams.toString();

  // Construct the full backend URL with query parameters
  let url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
    queryString ? `?${queryString}` : ""
  }`;

  try {
    // Make authenticated request to backend
    const response = await makeBackendRequest(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    });

    // Handle error responses from backend
    if (!response.ok) {
      const text = await response.text();
      console.error("Error response from backend:", text);
      return new Response(text, { status: response.status });
    }

    // Special handling for downloadTemplate endpoint (blob response)
    if (path.includes("sourcing/rfp/download-sample-template")) {
      const blob = await response.blob();
      return new Response(blob, {
        headers: {
          "Content-Type":
            response.headers.get("Content-Type") || "application/octet-stream",
          "Content-Disposition":
            response.headers.get("Content-Disposition") || "attachment",
        },
      });
    }

    // Parse and return successful response
    const data = await response.json();

    return new Response(JSON.stringify(data), {
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    console.error("Fetch error:", error);
    return new Response(
      JSON.stringify({
        error: "Internal Server Error",
        details: error instanceof Error ? error.message : "Unknown error",
        path: path,
        url: url,
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
}

/**
 * Handles POST requests to the backend API
 * Supports both JSON and file upload (FormData) requests
 * Some endpoints (password reset) don't require authentication
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const searchParams = request.nextUrl.searchParams;
  const queryString = searchParams.toString();

  // Check if this is a public endpoint that doesn't need authentication
  const isPublicEndpoint =
    path.includes("auth/password-reset") ||
    path.includes("auth/password-reset-request");

  // For protected endpoints, verify we have authentication
  if (!isPublicEndpoint) {
    const accessToken = await getAccessToken();
    if (!accessToken) {
      console.error("No access token available");
      return new Response("Unauthorized", { status: 401 });
    }
  }

  try {
    // Handle form data uploads
    if (
      path.includes("chat/extract") ||
      path.includes("analytics/csv/databases") ||
      path.includes("analytics/excel/database") ||
      path.includes("sourcing/rfp/upload-document") ||
      path.includes("sourcing/rfp/upload-template")
    ) {
      const formData = await request.formData();

      const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
        queryString ? `?${queryString}` : ""
      }`;

      // Use makeBackendRequest for authenticated file uploads
      console.log(`Processing form data upload to ${url}`);

      // For debugging - log form data entries
      if (path.includes("upload-template")) {
        console.log("Form data for template upload:");
        Array.from(formData.entries()).forEach(([key, value]) => {
          if (value instanceof File) {
            console.log(
              `${key}: File name=${value.name}, size=${value.size}, type=${value.type}`
            );
          } else {
            console.log(`${key}: ${value}`);
          }
        });
      }

      try {
        const response = await makeBackendRequest(url, {
          method: "POST",
          headers: {
            Accept: "application/json",
            // Note: Don't set Content-Type for FormData - browser sets it with boundary
          },
          body: formData,
        });

        console.log(
          `Form upload response status: ${response.status} ${response.statusText}`
        );

        const responseText = await response.text();
        console.log(`Response body length: ${responseText.length}`);

        if (!response.ok) {
          console.error("Error response:", responseText);
          try {
            const errorJson = JSON.parse(responseText);
            return new Response(JSON.stringify(errorJson), {
              status: response.status,
              headers: { "Content-Type": "application/json" },
            });
          } catch (e) {
            return new Response(responseText, {
              status: response.status,
              headers: { "Content-Type": "text/plain" },
            });
          }
        }

        return new Response(responseText, {
          status: response.status,
          headers: {
            "Content-Type": "application/json",
          },
        });
      } catch (error) {
        console.error(`Error during form upload to ${url}:`, error);
        return new Response(
          JSON.stringify({
            error: "Form upload failed",
            details: error instanceof Error ? error.message : "Unknown error",
            path: path,
          }),
          {
            status: 500,
            headers: { "Content-Type": "application/json" },
          }
        );
      }
    }

    // Handle requests without body
    if (
      (path.includes("sourcing/rfp/sections") &&
        path.includes("templates") &&
        path.includes("answer")) ||
      (path.includes("sourcing/rfp/subsections") &&
        path.includes("questions") &&
        !path.includes("prompt-questions") &&
        !path.includes("accept-questions"))
    ) {
      const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}`;

      const response = await makeBackendRequest(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });

      const responseText = await response.text();

      if (!response.ok) {
        console.error("Error response:", responseText);
        return new Response(responseText, { status: response.status });
      }

      return new Response(responseText, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    // Special handling for question answer endpoint with query params
    if (path.includes("sourcing/rfp/questions") && path.includes("answer")) {
      // Get query parameters
      const searchParams = request.nextUrl.searchParams;
      const sectionId = searchParams.get("section_id");
      const templateId = searchParams.get("template_id");

      // Construct URL with query parameters
      const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}?section_id=${sectionId}&template_id=${templateId}`;

      console.log("Calling question answer endpoint:", url);

      const response = await makeBackendRequest(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      });

      const responseText = await response.text();
      console.log("Question answer response:", responseText);

      if (!response.ok) {
        console.error("Error response:", responseText);
        return new Response(responseText, { status: response.status });
      }

      return new Response(responseText, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    // Handle normal JSON requests
    const body = await request.json();

    let url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
      queryString ? `?${queryString}` : ""
    }`;

    let response;
    if (isPublicEndpoint) {
      // For public endpoints, make request without authentication
      response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
      });
    } else {
      // For protected endpoints, use makeBackendRequest for authentication
      response = await makeBackendRequest(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
      });
    }

    // Handle streaming responses
    if (path.includes("completion") || path.includes("generate-stream")) {
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Streaming error response:", errorText);
        return new Response(errorText, { status: response.status });
      }

      // Return streaming response with appropriate headers
      return new Response(response.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    // Handle regular responses
    const responseText = await response.text();

    if (!response.ok) {
      console.error("Error response:", responseText);
      return new Response(responseText, { status: response.status });
    }

    return new Response(responseText, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    console.error("POST request error:", error);
    return new Response(
      JSON.stringify({
        error: "Internal Server Error",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500 }
    );
  }
}

/**
 * Handles PUT requests to the backend API
 * Supports both JSON and file upload (FormData) requests
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const searchParams = request.nextUrl.searchParams;
  const queryString = searchParams.toString();

  try {
    // Special handling for file upload endpoints (FormData)
    if (path.includes("analytics/csv/databases")) {
      const formData = await request.formData();

      const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
        queryString ? `?${queryString}` : ""
      }`;

      // Use makeBackendRequest for authenticated file uploads
      const response = await makeBackendRequest(url, {
        method: "PUT",
        headers: {
          Accept: "application/json",
          // Note: Don't set Content-Type for FormData
        },
        body: formData,
      });

      const responseText = await response.text();

      if (!response.ok) {
        console.error("Error response:", responseText);

        // Try to parse error response as JSON for better error handling
        try {
          const errorJson = JSON.parse(responseText);
          return new Response(JSON.stringify(errorJson), {
            status: response.status,
            headers: { "Content-Type": "application/json" },
          });
        } catch (e) {
          // If the error response isn't valid JSON, return it as is
          return new Response(responseText, { status: response.status });
        }
      }

      return new Response(responseText, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    // Handle regular JSON requests
    const body = await request.json();

    let url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
      queryString ? `?${queryString}` : ""
    }`;

    // Make authenticated request to backend
    const response = await makeBackendRequest(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });

    // Get the response body
    const responseText = await response.text();

    // Try to parse as JSON if possible, otherwise return as text
    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }

    // Return the response with the same status code from backend
    return new Response(
      typeof responseData === "string"
        ? responseData
        : JSON.stringify(responseData),
      {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  } catch (error) {
    console.error("PUT request error:", error);
    return new Response(
      JSON.stringify({
        error: "Internal Server Error",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
}

/**
 * Handles PATCH requests to the backend API
 * Used for partial updates of resources
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const searchParams = request.nextUrl.searchParams;
  const queryString = searchParams.toString();

  try {
    // Parse the JSON body
    const body = await request.json();

    // Construct the backend URL
    let url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
      queryString ? `?${queryString}` : ""
    }`;

    // Make authenticated request to backend
    const response = await makeBackendRequest(url, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });

    // Get the response body
    const responseText = await response.text();

    // Try to parse as JSON if possible, otherwise return as text
    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }

    // Return the response with the same status code from backend
    return new Response(
      typeof responseData === "string"
        ? responseData
        : JSON.stringify(responseData),
      {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  } catch (error) {
    console.error("PATCH request error:", error);
    return new Response(
      JSON.stringify({
        error: "Internal Server Error",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
}

/**
 * Handles DELETE requests to the backend API
 * Used for deleting resources
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  // Get query parameters from the request URL
  const searchParams = request.nextUrl.searchParams;
  const queryString = searchParams.toString();

  try {
    // Construct the backend URL with query parameters
    let url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/${path}${
      queryString ? `?${queryString}` : ""
    }`;

    // Make authenticated request to backend
    console.log("🚀 ~ DELETE ~ url:", url);

    // Check if deleteQuestions endpoint (has request body)
    if (
      path.includes("sourcing/rfp/subsections") &&
      path.includes("questions")
    ) {
      try {
        const body = await request.json();

        const response = await makeBackendRequest(url, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(body),
        });

        const responseText = await response.text();

        if (!response.ok) {
          console.error("Error response:", responseText);
          return new Response(responseText, { status: response.status });
        }

        // Try to parse as JSON if possible
        let responseData;
        try {
          responseData = JSON.parse(responseText);
        } catch {
          responseData = responseText;
        }

        return new Response(
          typeof responseData === "string"
            ? responseData
            : JSON.stringify(responseData),
          {
            status: response.status,
            headers: {
              "Content-Type": "application/json",
            },
          }
        );
      } catch (error) {
        console.error("Error parsing JSON in DELETE request:", error);
      }
    }

    // Default handling for DELETE requests without body
    const response = await makeBackendRequest(url, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    });

    // Get the response body
    const responseText = await response.text();

    if (!response.ok) {
      console.error("Error response:", responseText);
      return new Response(responseText, { status: response.status });
    }

    // Try to parse as JSON if possible, otherwise return as text
    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }

    return new Response(
      typeof responseData === "string"
        ? responseData
        : JSON.stringify(responseData),
      {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  } catch (error) {
    console.error("DELETE request error:", error);
    return new Response(
      JSON.stringify({
        error: "Internal Server Error",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
}
