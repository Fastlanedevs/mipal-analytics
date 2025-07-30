import { NextResponse } from "next/server";

export async function GET() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace("/api", "");

  try {
    const response = await fetch(`${API_URL}/auth/test`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.text();

    return NextResponse.json({
      status: "success",
      message: "Backend connection successful",
      response: data,
    });
  } catch (error) {
    console.error("Backend connection error:", error);
    return NextResponse.json(
      {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
