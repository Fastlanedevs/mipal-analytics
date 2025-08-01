// src/lib/auth.config.ts
import { NextAuthOptions } from "next-auth";
// Google and Azure providers removed
// Slack provider removed
import CredentialsProvider from "next-auth/providers/credentials";
import { parseAuthResponse } from "@/lib/auth-helpers";
import type { User } from "next-auth";
import { BackendAuthData } from "@/types/next-auth";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        name: { label: "Name", type: "text" },
        isSignUp: { label: "Is Sign Up", type: "text" },
        otp: { label: "OTP", type: "text" },
        access_token: { label: "Access Token", type: "text" },
        refresh_token: { label: "Refresh Token", type: "text" },
      },
      async authorize(credentials) {
        try {
          if (credentials?.access_token && credentials?.refresh_token) {
            const tokenData = JSON.parse(
              atob(credentials.access_token.split(".")[1])
            );
            return {
              id: tokenData.user_id,
              email: tokenData.email || "",
              name: tokenData.name || "",
              role: tokenData.role,
              joined_org: tokenData.joined_org,
              access_token: credentials.access_token,
              refresh_token: credentials.refresh_token,
            };
          }

          if (!credentials?.email || !credentials?.password) {
            throw new Error("Email and password are required");
          }

          const isSignUp = credentials.isSignUp === "true";

          if (credentials.otp) {
            const verifyResponse = await fetch(
              `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/verify-email`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  email: credentials.email,
                  otp: credentials.otp,
                }),
              }
            );

            if (!verifyResponse.ok) {
              const verifyData = await verifyResponse.json();
              throw new Error(verifyData.error || "OTP verification failed");
            }

            const loginResponse = await fetch(
              `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/login`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  email: credentials.email,
                  password: credentials.password,
                }),
              }
            );

            const authData = await parseAuthResponse(loginResponse);
            return {
              id: authData.id,
              email: credentials.email,
              name: credentials.name || "",
              role: authData.role,
              joined_org: authData.joined_org,
              access_token: authData.access_token,
              refresh_token: authData.refresh_token,
            };
          }

          const endpoint = isSignUp
            ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/register`
            : `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/login`;

          const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
              name: credentials.name,
            }),
          });

          if (isSignUp) {
            const data = await response.json();
            if (!response.ok) {
              throw new Error(data.message || "Registration failed");
            }
            throw new Error("OTP_REQUIRED");
          }

          const authData = await parseAuthResponse(response);
          return {
            id: authData.id,
            email: credentials.email,
            name: credentials.name || "",
            role: authData.role,
            joined_org: authData.joined_org,
            access_token: authData.access_token,
            refresh_token: authData.refresh_token,
          };
        } catch (error: any) {
          console.error("Authorization error:", error);
          throw new Error(error.message || "Authentication failed");
        }
      },
    }),
    // Slack provider removed
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      // Google and Azure sign-in callbacks removed
      return true;
    },

    async jwt({ token, user, account }) {
      // Check if token needs refresh
      if (token.access_token) {
        try {
          const tokenData = JSON.parse(atob(token.access_token.split(".")[1]));
          const expiresAt = tokenData.exp * 1000; // Convert to milliseconds
          const now = Date.now();

          // If token is expired or close to expiry (within 5 minutes)
          if (now >= expiresAt - 5 * 60 * 1000) {
            if (token.refresh_token) {
              try {
                const response = await fetch(
                  `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/refresh`,
                  {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      refresh_token: token.refresh_token,
                    }),
                  }
                );

                const data = await response.json();
                if (response.ok && data.access_token) {
                  token.access_token = data.access_token;
                  token.accessToken = data.access_token;
                  if (data.refresh_token) {
                    token.refresh_token = data.refresh_token;
                  }
                } else {
                  console.error("Failed to refresh token:", data);
                  // Clear tokens to force re-authentication
                  delete token.access_token;
                  delete token.accessToken;
                  delete token.refresh_token;
                }
              } catch (error) {
                console.error("Error refreshing token:", error);
                // Clear tokens on error
                delete token.access_token;
                delete token.accessToken;
                delete token.refresh_token;
              }
            }
          }
        } catch (error) {
          console.error("Error parsing token for expiry check:", error);
        }
      }

      // Handle initial sign in
      if (account?.access_token) {
        token.access_token = account.access_token;
        token.accessToken = account.access_token;
        token.refresh_token = account.refresh_token;

        // Use type assertion with the backend data interface
        const accountData = account as unknown as {
          role?: string;
          joined_org?: boolean;
        };

        if (accountData.role) {
          token.role = accountData.role;
        }
        if (accountData.joined_org !== undefined) {
          token.joined_org = accountData.joined_org;
        }
      }

      // Handle credentials/custom login
      if (user?.access_token) {
        token.access_token = user.access_token;
        token.accessToken = user.access_token;
        token.refresh_token = user.refresh_token;

        // Use type assertion for user data
        const userData = user as unknown as {
          role?: string;
          joined_org?: boolean;
        };

        if (userData.role) {
          token.role = userData.role;
        }
        if (userData.joined_org !== undefined) {
          token.joined_org = userData.joined_org;
        }
      }

      // Preserve existing tokens if new ones aren't provided
      if (!token.access_token && token.accessToken) {
        token.access_token = token.accessToken;
      }

      if (user) {
        token.user = {
          id: (user as User).id,
          name: (user as User).name || "Anonymous",
          email: (user as User).email || "no-email",
          role: ((user as User).role || token.role) as string | undefined,
          joined_org: ((user as User).joined_org || token.joined_org) as
            | boolean
            | undefined,
          access_token: (user as User).access_token,
          refresh_token: (user as User).refresh_token,
        };
      }

      return token;
    },

    async session({ session, token }) {
      // Set both token formats in session
      if (token.access_token || token.accessToken) {
        const accessToken = token.access_token || token.accessToken;
        session.access_token = accessToken;
        session.accessToken = accessToken;
      }

      if (token.refresh_token || token.refreshToken) {
        const refreshToken = token.refresh_token || token.refreshToken;
        session.refresh_token = refreshToken as string;
        session.refreshToken = refreshToken as string;
      }

      if (token.user) {
        session.user = {
          ...session.user,
          ...(token.user as {
            id: string;
            name: string;
            email: string;
            role?: string;
            joined_org?: boolean;
          }),
        };
      }

      return session;
    },

    async redirect({ url, baseUrl }) {
      // Normalize the URLs
      const normalizedUrl = url.startsWith("http") ? url : `${baseUrl}${url}`;
      const normalizedBaseUrl = baseUrl.endsWith("/")
        ? baseUrl.slice(0, -1)
        : baseUrl;

      // If it's the default auth page redirect
      if (url === `${normalizedBaseUrl}/auth`) {
        return normalizedBaseUrl;
      }

      // If the URL starts with the base URL, allow it
      if (normalizedUrl.startsWith(normalizedBaseUrl)) {
        return normalizedUrl;
      }

      // If it's a relative URL, make it absolute
      if (url.startsWith("/")) {
        return `${normalizedBaseUrl}${url}`;
      }

      // For OAuth callbacks, allow the URL
      if (url.startsWith(`${normalizedBaseUrl}/api/auth/callback`)) {
        return url;
      }

      // Handle malformed URLs that might contain duplicate protocols
      if (
        url.includes("https://") &&
        url.indexOf("https://") !== url.lastIndexOf("https://")
      ) {
        const cleanUrl = url.substring(url.lastIndexOf("https://"));
        return cleanUrl;
      }

      // Default fallback
      return normalizedBaseUrl;
    },
  },
  events: {
    async signOut() {
      // Clear all stored data
      if (typeof window !== "undefined") {
        // Clear session storage
        window.sessionStorage.clear();

        // Clear local storage
        window.localStorage.clear();

        // Clear specific redux persist data
        window.localStorage.removeItem("persist:root");

        // Clear any other auth related items
        window.localStorage.removeItem("next-auth.session-token");
        window.localStorage.removeItem("next-auth.callback-url");
        window.localStorage.removeItem("next-auth.csrf-token");

        // Force reload to clear any in-memory state
        window.location.reload();
      }
    },
  },
  pages: {
    signIn: "/auth",
    error: "/auth/error",
    signOut: "/auth/signout",
    verifyRequest: "/auth/verify-request",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60, // 24 hours
  },
  debug: process.env.NODE_ENV === "development",
};
