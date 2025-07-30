import { NextRequest } from "next/server";
import { getMsalInstance } from "@/lib/azure-config";
import { getValidAccessToken } from "@/lib/auth-helper";
import { revalidateTag } from "next/cache";
import {
  INTEGRATION_TYPES,
  IntegrationType,
} from "@/store/services/integrationApi";

export const dynamic = "force-dynamic";

const INTEGRATION_TO_SERVICE = {
  [INTEGRATION_TYPES.MICROSOFT_ONEDRIVE]: "onedrive",
  [INTEGRATION_TYPES.MICROSOFT_OUTLOOK]: "outlook",
  [INTEGRATION_TYPES.MICROSOFT_CALENDER]: "calendar",
  [INTEGRATION_TYPES.MICROSOFT_TEAMS]: "teams",
  [INTEGRATION_TYPES.MICROSOFT_SHAREPOINT]: "sharepoint",
};

export async function GET(request: NextRequest) {
  try {
    const msalInstance = getMsalInstance();

    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    // const serviceType = state;
    const mappedService =
      INTEGRATION_TO_SERVICE[state as keyof typeof INTEGRATION_TO_SERVICE];

    if (!code || !state) {
      console.error("Missing required parameters:", {
        code: code ? "present" : "missing",
        state: state ? "present" : "missing",
      });
      return Response.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=no_code`
      );
    }

    const validAccessToken = await getValidAccessToken();
    if (!validAccessToken) {
      console.error("No valid access token found");
      return Response.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=no_access_token`
      );
    }

    const baseScopes = ["User.Read"];
    const serviceScopes =
      mappedService === "onedrive"
        ? ["Files.Read", "Files.ReadWrite.All"]
        : mappedService === "outlook"
          ? ["Mail.ReadWrite", "Mail.Send"]
          : mappedService === "teams"
            ? ["Team.ReadBasic", "Team.ReadWriteBasic"]
            : mappedService === "calendar"
              ? ["Calendars.ReadWrite"]
              : [];

    const tokenRequest = {
      code,
      scopes: [...baseScopes, ...serviceScopes],
      redirectUri: `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/azure/callback`,
    };

    const response = await msalInstance.acquireTokenByCode(tokenRequest);

    // Calculate expiration time in seconds (default to 1 hour if not provided)
    const expiresIn = response.expiresOn
      ? Math.floor((response.expiresOn.getTime() - Date.now()) / 1000)
      : 3600;

    const requestBody = {
      integration_type: INTEGRATION_TYPES[state as IntegrationType],
      credential: {
        access_token: response.accessToken,
        id_token: response.idToken, // Include id_token instead of refresh_token
        expires_in: expiresIn,
        token_type: response.tokenType,
      },
      expires_at: response.expiresOn
        ? response.expiresOn.toISOString()
        : new Date(Date.now() + expiresIn * 1000).toISOString(),
      settings: {
        service: mappedService,
      },
    };

    try {
      const storeResponse = await fetch(
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

      if (!storeResponse.ok) {
        console.error(
          "Failed to store integration:",
          await storeResponse.text()
        );
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
    console.error("Error during Azure authentication:", error);
    return Response.redirect(
      `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=auth_failed`
    );
  }
}
