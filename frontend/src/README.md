# Middleware (`src/middleware.ts`)

This middleware handles request processing, authentication, and redirection for the Next.js application.

## Functionality

1.  **Health Check Skip**: Ignores requests from AWS Elastic Load Balancer health checks (identified by the `ELB-HealthChecker` user-agent).

2.  **Request Logging**: Logs detailed information for incoming requests, including timestamp, URL, host, protocol, base URL, and pathname. This is helpful for debugging and monitoring.

3.  **Path Exclusion**: The middleware bypasses processing for specific paths to improve performance and avoid unnecessary checks. These paths include:

    - `/_next/*` (Next.js internal assets)
    - `/api/auth/*` (Authentication API routes)
    - `/videos/*` (Video assets)
    - `/images/*` (Image assets)
    - `/favicon.ico`
    - `/privacy-policy`
    - `/terms-of-service`
    - `/api/proxy/auth/password-reset`
    - `/api/proxy/auth/password-reset-request`
    - `/.well-known/microsoft-identity-association.json` (Microsoft identity verification)

4.  **Authentication Handling**:

    - It retrieves the JWT token for the user using `next-auth/jwt`.
    - **Authenticated Users on Auth Pages**: If an authenticated user tries to access an authentication page (e.g., `/auth/login`), they are redirected to the home page (`/`) or to the `callbackUrl` specified in the query parameters.
    - **Unauthenticated Users on Protected Routes**: If an unauthenticated user attempts to access any route not explicitly excluded or under `/auth`, they are redirected to the login page (`/auth`). The original requested URL is passed as a `callbackUrl` query parameter, so the user is redirected back to their intended page after successful authentication.

5.  **Base URL Construction**: Dynamically constructs the `baseUrl` using `x-forwarded-proto` and `host` headers to ensure correct redirection URLs, especially when operating behind a proxy or load balancer.

## Configuration (`config`)

The `matcher` configuration specifies the paths on which this middleware will run. It's configured to run on all paths _except_ for:

- `/api/auth/*`
- `/_next/static/*`
- `/_next/image/*`
- `favicon.ico`
- `favicon.png`
- `/privacy-policy`
- `/terms-of-service`
- `/.well-known/*`

This ensures that the middleware only processes relevant application routes and avoids interfering with static assets or specific API endpoints that don't require this level of request handling.
