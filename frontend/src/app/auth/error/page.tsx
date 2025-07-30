"use client";

import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

export default function AuthError() {
  const searchParams = useSearchParams();
  const error = searchParams?.get("error");
  const router = useRouter();

  const getErrorMessage = (error: string) => {
    switch (error) {
      case "AccessDenied":
        return "Access was denied. Please ensure you're using a valid Google account and try again.";
      case "Verification":
        return "Email verification is required. Please check your inbox.";
      default:
        return "An error occurred during authentication. Please try again.";
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <h1 className="text-2xl font-semibold mb-4">Authentication Error</h1>
      <p className="text-gray-600 mb-6 text-center">
        {getErrorMessage(error || "")}
      </p>
      <Button onClick={() => router.push("/auth")} className="w-full max-w-sm">
        Back to Sign In
      </Button>
    </div>
  );
}
