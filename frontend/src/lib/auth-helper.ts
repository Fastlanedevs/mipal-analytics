import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth.config";
import { tokenManager } from "@/lib/token-manager";

function parseJwt(token: string) {
  try {
    return JSON.parse(Buffer.from(token.split(".")[1], "base64").toString());
  } catch (e) {
    return null;
  }
}

export async function getValidAccessToken(): Promise<string | null> {
  try {
    const session = await getServerSession(authOptions);
    if (!session) {
      return null;
    }
    const accessToken = session.accessToken ?? session.user?.access_token;
    if (!accessToken) {
      return null;
    }

    // Use the centralized token manager to handle token validation and refresh
    const refreshToken = session.refreshToken;
    if (!refreshToken) {
      console.error("No refresh token available");
      return null;
    }

    return await tokenManager.getValidAccessToken(accessToken, refreshToken);
  } catch (error) {
    console.error("Error getting valid access token:", error);
    return null;
  }
}
