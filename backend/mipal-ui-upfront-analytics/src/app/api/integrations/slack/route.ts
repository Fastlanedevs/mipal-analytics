import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    if (!process.env.SLACK_CLIENT_ID) {
      console.error("Slack client ID is missing");
      return NextResponse.redirect(
        `${
          process.env.NEXT_PUBLIC_APP_URL || ""
        }/integration?error=missing_client_id`
      );
    }

    if (!process.env.NEXT_PUBLIC_APP_URL) {
      console.error("App URL is missing");
      return NextResponse.redirect(`/integration?error=missing_app_url`);
    }

    const scopes = [
      "channels:read",
      "channels:history",
      "chat:write",
      "groups:read",
      "im:read",
      "mpim:read",
      "users:read",
      "users:read.email",
      "team:read",
    ].join(",");

    // const redirectUri = `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/slack/callback`;
    const redirectUri = `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/slack/callback`;

    const slackAuthUrl = new URL("https://slack.com/oauth/v2/authorize");
    slackAuthUrl.searchParams.append("client_id", process.env.SLACK_CLIENT_ID);
    slackAuthUrl.searchParams.append("user_scope", scopes);
    slackAuthUrl.searchParams.append("redirect_uri", redirectUri);

    return NextResponse.redirect(slackAuthUrl.toString());
  } catch (error) {
    console.error("Error in Slack OAuth route:", error);
    return NextResponse.redirect(
      `${process.env.NEXT_PUBLIC_APP_URL || ""}/integration?error=oauth_error`
    );
  }
}
