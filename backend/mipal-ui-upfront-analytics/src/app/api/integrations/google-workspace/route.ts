import { NextRequest, NextResponse } from "next/server";
import { google } from "googleapis";

// OAuth client configuration
const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/google-workspace/callback`
);

// Define scopes for each service
const SCOPES = {
  DRIVE: [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
  ],
  GMAIL: [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
  ],
  CALENDAR: [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.settings.readonly",
  ],
};

export async function GET(request: NextRequest) {
  // Get the service type from query parameters
  const searchParams = request.nextUrl.searchParams;
  const service = searchParams.get("service");

  // Select scopes based on service type
  let scopes: string[] = [];
  switch (service) {
    case "GOOGLE_DRIVE":
      scopes = SCOPES.DRIVE;
      break;
    case "GOOGLE_GMAIL":
      scopes = SCOPES.GMAIL;
      break;
    case "GOOGLE_CALENDAR":
      scopes = SCOPES.CALENDAR;
      break;
    case "all":
      scopes = [...SCOPES.DRIVE, ...SCOPES.GMAIL, ...SCOPES.CALENDAR];
      break;
    // default:
    //   // If no specific service is specified, include all scopes
    //   scopes = [...SCOPES.DRIVE, ...SCOPES.GMAIL, ...SCOPES.CALENDAR];
  }

  const authUrl = oauth2Client.generateAuthUrl({
    access_type: "offline",
    scope: scopes,
    prompt: "consent",
    redirect_uri: `${process.env.NEXT_PUBLIC_APP_URL}/api/integrations/google-workspace/callback`,
    state: service || "all", // Pass the service type to the callback
  });

  return NextResponse.redirect(authUrl);
}
