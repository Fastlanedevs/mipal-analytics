import { NextRequest } from "next/server";
import { revalidateTag } from "next/cache";
import { getValidAccessToken } from "@/lib/auth-helper";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");

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

    // Exchange the code for access token
    const params = new URLSearchParams({
      client_id: process.env.SLACK_CLIENT_ID!,
      client_secret: process.env.SLACK_CLIENT_SECRET!,
      code: code,
      redirect_uri: `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/slack/callback`,
    });

    const slackResponse = await fetch(
      `https://slack.com/api/oauth.v2.access?${params.toString()}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      }
    );

    const slackData = await slackResponse.json();

    if (!slackData.ok) {
      console.error("Slack OAuth error:", slackData.error);
      return Response.redirect(
        `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=auth_failed`
      );
    }
    const requestBody = {
      integration_type: "SLACK_CHAT",
      credential: {
        access_token: slackData.authed_user.access_token,
        team_id: slackData.team.id,
        team_name: slackData.team.name,
        scope: slackData.authed_user.scope,
        token_type: slackData.authed_user.token_type,
        id: slackData.authed_user.id,
      },
      expires_at: new Date(
        Date.now() + 365 * 24 * 60 * 60 * 1000
      ).toISOString(), // Set to 1 year
      settings: {},
    };

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
    console.error("Error during Slack authentication:", error);
    return Response.redirect(
      `${process.env.NEXT_PUBLIC_APP_URL}/integration?error=auth_failed`
    );
  }
}
