import { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const apiHost = process.env.NEXT_PUBLIC_API_URL;
    if (!apiHost) {
      throw new Error("API_URL environment variable is not defined");
    }

    const backendResponse = await fetch(`${apiHost}/api/auth/verify-email`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: body.email,
        otp: body.otp,
      }),
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      return Response.json(
        { error: data.detail || "Verification failed" },
        { status: backendResponse.status }
      );
    }

    // Get the Set-Cookie header
    const setCookieHeader = backendResponse.headers.get("set-cookie");

    // Create the response
    const response = Response.json(
      { message: "Email verified successfully", user: data.user },
      { status: 200 }
    );

    // If we have cookies from the backend, set them in our response
    if (setCookieHeader) {
      const cookies = setCookieHeader.split(",").map((cookie) => cookie.trim());
      cookies.forEach((cookie) => {
        response.headers.append("Set-Cookie", cookie);
      });
    }

    return response;
  } catch (error) {
    console.error("Verification error:", error);
    return Response.json(
      {
        error: error instanceof Error ? error.message : "Internal server error",
      },
      { status: 500 }
    );
  }
}
