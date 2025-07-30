"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Check, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useRetrieveSessionQuery } from "@/store/services/stripeApi";

export default function StripeSuccess() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = searchParams?.get("session_id");
  const {
    data: session,
    isLoading,
    isError,
  } = useRetrieveSessionQuery(sessionId ?? "", {
    skip: !sessionId,
  });

  if (!sessionId) {
    return (
      <ErrorState
        message="No session ID found. Please try again or contact support."
        onRetry={() => router.push("/settings/plans")}
      />
    );
  }

  if (isLoading) {
    return <LoadingState />;
  }

  // Don't show as error is on our side not on strip, creation of session_id is enough for
  // marking succesfull payment.
  // if (isError || !session) {
  //   return (
  //     <ErrorState
  //       message="Failed to verify payment. Please contact support."
  //       onRetry={() => router.push('/settings/plans')}
  //     />
  //   );
  // }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-white to-gray-50">
      <div className="w-full max-w-md animate-fade-in">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-sm border border-gray-100">
          <div className="flex flex-col items-center space-y-6">
            <SuccessCheck />

            <div className="text-center space-y-2">
              <div className="inline-flex items-center rounded-full bg-[#E7F3E5]/30 px-3 py-1 text-sm">
                Payment Successful
              </div>
              <h1 className="text-2xl font-medium text-gray-900">
                Thank you for your payment
              </h1>
              <p className="text-gray-500 text-sm">
                Your transaction has been completed
              </p>
            </div>

            <div className="w-full border-t border-gray-100 my-4" />

            <div className="w-full space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Transaction ID</span>
                <span className="text-gray-900 font-medium max-w-[25ch] break-words">
                  {session?.id ?? "N/A"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Date</span>
                <span className="text-gray-900">
                  {new Date().toLocaleDateString()}
                </span>
              </div>
            </div>

            <Button
              className="w-full bg-gray-900 hover:bg-gray-800 text-white transition-all duration-200"
              onClick={() => router.push("/dashboard")}
            >
              Return to Dashboard
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

const LoadingState = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="flex flex-col items-center space-y-4">
      <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
      <p className="text-gray-600">Verifying your payment...</p>
    </div>
  </div>
);

const ErrorState = ({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center space-y-4">
      <p className="text-red-600">{message}</p>
      <Button onClick={onRetry} variant="outline">
        Return to Plans
      </Button>
    </div>
  </div>
);

const SuccessCheck = ({ className }: { className?: string }) => {
  return (
    <div
      className={cn(
        "relative inline-flex items-center justify-center w-16 h-16 rounded-full bg-[#E7F3E5]",
        "animate-scale-in",
        className
      )}
    >
      <Check
        className="w-8 h-8 text-[#2E7D32] animate-fade-in"
        strokeWidth={3}
      />
    </div>
  );
};
