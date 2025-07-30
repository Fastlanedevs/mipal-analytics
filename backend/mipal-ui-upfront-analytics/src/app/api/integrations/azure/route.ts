import { NextRequest, NextResponse } from "next/server";
import { AuthorizationUrlRequest } from "@azure/msal-node";
import { getMsalInstance } from "@/lib/azure-config";
import { INTEGRATION_TYPES } from "@/store/services/integrationApi";

export const dynamic = "force-dynamic";

const SCOPE_MAP = {
  [INTEGRATION_TYPES.MICROSOFT_ONEDRIVE]: [
    "Files.Read",
    "Files.ReadWrite.All",
    "offline_access",
  ],
  [INTEGRATION_TYPES.MICROSOFT_OUTLOOK]: [
    "Mail.ReadWrite",
    "Mail.Send",
    "offline_access",
  ],
  [INTEGRATION_TYPES.MICROSOFT_CALENDER]: [
    "Calendars.ReadWrite",
    "offline_access",
  ],
  [INTEGRATION_TYPES.MICROSOFT_TEAMS]: [
    "Team.ReadBasic.All",
    "TeamSettings.Read.All",
    "Channel.ReadBasic.All",
    "ChannelMessage.Read.All",
    "Chat.Read",
    "offline_access",
  ],
};

export async function GET(request: NextRequest) {
  try {
    const msalInstance = getMsalInstance();
    const searchParams = request.nextUrl.searchParams;
    const service = searchParams.get("service");

    if (!service || !SCOPE_MAP[service as keyof typeof SCOPE_MAP]) {
      return NextResponse.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=invalid_service`
      );
    }

    const scopes = [
      "User.Read",
      ...SCOPE_MAP[service as keyof typeof SCOPE_MAP],
    ];

    const authUrlRequest: AuthorizationUrlRequest = {
      scopes: scopes,
      redirectUri: `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/azure/callback`,
      responseMode: "query",
      state: service, // Pass the service type to the callback
    };

    const authUrl = await msalInstance.getAuthCodeUrl(authUrlRequest);
    return NextResponse.redirect(authUrl);
  } catch (error) {
    console.error("Error generating Azure auth URL:", error);
    return NextResponse.redirect(
      `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=auth_url_failed`
    );
  }
}
