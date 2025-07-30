import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

export async function middleware(request: NextRequest) {
  // Skip health check requests
  if (request.headers.get("user-agent")?.includes("ELB-HealthChecker")) {
    return NextResponse.next();
  }

  // Get the protocol and host from the request
  const protocol = request.headers.get("x-forwarded-proto") || "http";
  const host = request.headers.get("host") || "";
  const baseUrl = `${protocol}://${host}`;

  console.log("=== Middleware Start ===", {
    timestamp: new Date().toISOString(),
    requestInfo: {
      url: request.url,
      host,
      protocol,
      baseUrl,
      pathname: request.nextUrl.pathname,
    },
  });

  // Skip middleware for these paths
  if (
    request.nextUrl.pathname.startsWith("/_next") ||
    request.nextUrl.pathname.startsWith("/api/auth") ||
    request.nextUrl.pathname.startsWith("/videos") ||
    request.nextUrl.pathname.startsWith("/images") ||
    request.nextUrl.pathname === "/favicon.ico" ||
    request.nextUrl.pathname === "/privacy-policy" ||
    request.nextUrl.pathname === "/terms-of-service" ||
    request.nextUrl.pathname.startsWith("/api/proxy/auth/password-reset") ||
    request.nextUrl.pathname === "/api/proxy/auth/password-reset-request" ||
    request.nextUrl.pathname ===
      "/.well-known/microsoft-identity-association.json"
  ) {
    return NextResponse.next();
  }

  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  });

  // If on auth page and authenticated, redirect to home
  if (request.nextUrl.pathname.startsWith("/auth") && token) {
    const redirectUrl = request.nextUrl.searchParams.get("callbackUrl") || "/";
    console.log("Redirecting authenticated user:");
    return NextResponse.redirect(new URL(redirectUrl, baseUrl));
  }

  // If accessing protected route without auth, redirect to login
  if (!token && !request.nextUrl.pathname.startsWith("/auth")) {
    const callbackUrl = request.url;
    const authUrl = new URL("/auth", baseUrl);
    authUrl.searchParams.set("callbackUrl", callbackUrl);

    console.log("Redirecting to auth:");

    return NextResponse.redirect(authUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|favicon.png|privacy-policy|terms-of-service|.well-known).*)",
  ],
};
