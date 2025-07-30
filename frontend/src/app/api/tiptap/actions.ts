"use server";

import jwt from "jsonwebtoken";

export async function generateTiptapToken() {
  try {
    const secret = process.env.NEXT_PUBLIC_TIPTAP_JWT_SECRET;

    if (!secret) {
      throw new Error("Tiptap service not configured");
    }

    const payload = {
      userId: "user123",
    };

    const token = jwt.sign(payload, secret);
    return { token };
  } catch (error) {
    console.error("Error generating token:", error);
    throw error;
  }
}
