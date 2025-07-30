import { NextRequest } from "next/server";
import { google } from "googleapis";
import { cookies } from "next/headers";
import { revalidateTag } from "next/cache";
import { getValidAccessToken } from "@/lib/auth-helper";
import {
  INTEGRATION_TYPES,
  IntegrationType,
} from "@/store/services/integrationApi";

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/google-workspace/callback`
);

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const service = searchParams.get("state");

  if (!code) {
    return Response.redirect(
      `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=no_code`
    );
  }

  try {
    const validAccessToken = await getValidAccessToken();
    if (!validAccessToken) {
      console.error("No valid access token found");
      return Response.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=no_access_token`
      );
    }

    const { tokens } = await oauth2Client.getToken(code);

    const requestBody = {
      integration_type: INTEGRATION_TYPES[service as IntegrationType],
      credential: tokens,
      expires_at: tokens.expiry_date
        ? new Date(tokens.expiry_date).toISOString()
        : new Date().toISOString(),
      settings: {
        service: service || "all",
      },
    };

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/integrations`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${validAccessToken}`,
          },
          body: JSON.stringify(requestBody),
        }
      );

      if (!response.ok) {
        console.error("Failed to store integration:", await response.text());
        return Response.redirect(
          `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=store_failed`
        );
      }

      // Wait a short moment to ensure the integration is properly stored
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Revalidate the integrations data
      revalidateTag("integrations");

      return Response.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?success=true`
      );
    } catch (error) {
      console.error("Failed to store integration:", error);
      return Response.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=store_failed`
      );
    }
  } catch (error) {
    console.error("Error during Google Workspace authentication:", error);
    return Response.redirect(
      `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=auth_failed`
    );
  }
}
