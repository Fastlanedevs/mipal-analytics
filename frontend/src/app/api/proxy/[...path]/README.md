# Proxy API Route

This directory contains a Next.js API route that acts as a proxy to a backend service. It handles various HTTP methods (GET, POST, PUT, PATCH, DELETE) and forwards requests to the corresponding backend endpoints.

## Functionality

- **Authentication Handling:**

  - Retrieves an access token from the user's session.
  - Implements a mechanism to refresh the access token if it's expired or nearing expiration using a refresh token.
  - Includes the access token in the `Authorization` header (as a Bearer token) for requests to the backend, except for specific unauthenticated paths like password reset.

- **Request Forwarding:**

  - Captures the dynamic path segments (`[...path]`) from the incoming request URL.
  - Joins the path segments to form the specific API endpoint to be called on the backend.
  - Forwards query parameters from the original request to the backend.

- **HTTP Method Handling:**

  - Exports asynchronous functions for `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` HTTP methods.
  - Each function constructs the appropriate request to the backend service defined by `process.env.NEXT_PUBLIC_BACKEND_URL`.

- **Request Body Handling:**

  - For `POST`, `PUT`, and `PATCH` requests, it typically expects a JSON body, which is parsed and forwarded to the backend.
  - **Special File Upload Handling:** For specific POST and PUT paths (e.g., `/chat/extract`, `/analytics/csv/databases`, `/analytics/excel/database`), it processes `FormData` for file uploads and sends it to the backend.

- **Response Handling:**

  - Returns the backend's response (including status code and body) to the client.
  - For successful JSON responses, it ensures the `Content-Type` header is set to `application/json`.
  - **Streaming Support:** For paths containing "completion" (likely for services like AI chat completions), it streams the response body directly from the backend to the client with `Content-Type: text/event-stream`.

- **Error Handling:**
  - Catches errors during the proxying process (e.g., network issues, errors from the backend).
  - Returns appropriate error responses to the client, typically with a 500 status code for internal server errors or the backend's error status code if available.
  - Logs errors to the console for debugging purposes.
  - Handles unauthorized access by returning a 401 status if no access token is available for protected routes.

## Key Helper Functions

- **`getAccessToken()`:**
  - Retrieves the session token from cookies.
  - Uses `next-auth/jwt`'s `getToken` to decode the session token and extract the access token.
  - Checks for token expiration and attempts to refresh it using `refreshAccessToken()` if necessary.
- **`refreshAccessToken(refreshToken)`:**
  - Makes a POST request to the backend's `/auth/refresh` endpoint to obtain a new access token.
  - Updates the session with the new tokens if successful (commented out in the provided code, but intended functionality).

## Environment Variables

- `NEXT_PUBLIC_BACKEND_URL`: The base URL of the backend service.
- `NEXTAUTH_SECRET`: The secret used for signing NextAuth.js JWTs.
- `NODE_ENV`: Used to determine the correct cookie name for the session token (`__Secure-next-auth.session-token` for production, `next-auth.session-token` otherwise).

This proxy route is crucial for securely and consistently communicating with the backend service from the Next.js frontend, abstracting away the direct backend URL and managing authentication tokens.
