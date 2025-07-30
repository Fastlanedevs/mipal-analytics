import { jwtDecode } from "jwt-decode";
import { getSession, useSession } from "next-auth/react";

interface TokenPayload {
  exp: number;
}

export async function refreshAccessToken(refreshToken: string) {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }
    );

    if (!response.ok) {
      throw new Error("Failed to refresh token");
    }

    const data = await response.json();
    return data.access_token;
  } catch (error) {
    console.error("Error refreshing token: auth helpers page se", error);
    throw error;
  }
}

export function isTokenExpired(token: string): boolean {
  try {
    const decoded = jwtDecode<TokenPayload>(token);
    const currentTime = Math.floor(Date.now() / 1000);
    return decoded.exp < currentTime;
  } catch {
    return true;
  }
}

// Client-side cookie management
export function getTokenFromCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
  return null;
}

export function setTokenCookie(name: string, value: string, days = 7) {
  const date = new Date();
  date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value}; expires=${date.toUTCString()}; path=/`;
}

export interface AuthResponse {
  id: string;
  joined_org: boolean;
  role: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export async function parseAuthResponse(response: Response) {
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "Authentication failed");
  }

  const data = await response.json();
  return {
    id: data.user_id || data.id,
    joined_org: data.joined_org,
    role: data.role,
    access_token: data.access_token,
    refresh_token: data.refresh_token,
  };
}

export async function updateSessionTokens(
  access_token: string,
  refresh_token: string
) {
  try {
    // Update the session
    const response = await fetch("/api/auth/session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        accessToken: access_token,
        refreshToken: refresh_token,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to update session");
    }

    // Force a session refresh
    const event = new Event("visibilitychange");
    document.dispatchEvent(event);
  } catch (error) {
    console.error("Error updating session tokens:", error);
    throw error;
  }
}
