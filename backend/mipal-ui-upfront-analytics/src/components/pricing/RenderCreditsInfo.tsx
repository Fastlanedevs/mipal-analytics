import React, { useEffect, useState } from "react";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { CircleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { Button } from "../ui/button";
import {
  useGetSubscriptionQuery,
  useGetUserCreditsQuery,
} from "@/store/services/userApi";
import {
  planToCreditsMapping,
  subscriptionPlanLable,
} from "@/lib/utils/pricing";
import { SubscriptionPlan } from "@/constants/pricing";

interface RenderCreditsInfoProps {
  popoverOpen: boolean;
  setPopoverOpen: (value: boolean) => void;
  isOpen: boolean;
  setIsOpen: (value: boolean) => void;
}

export default function RenderCreditsInfo({
  popoverOpen,
  setPopoverOpen,
  isOpen,
  setIsOpen,
}: RenderCreditsInfoProps) {
  const {
    data: subscription,
    isLoading: isSubscriptionLoading,
    refetch: refetchSubscription,
  } = useGetSubscriptionQuery();
  const {
    data: userCredits,
    isLoading: isUserCreditsLoading,
    refetch: refetchUserCredits,
  } = useGetUserCreditsQuery({});
  const t = useTranslations("sidebar");
  const router = useRouter();

  useEffect(() => {
    refetchSubscription();
    refetchUserCredits();
  }, []);

  // inline loader spinner if subscription is loading
  if (isSubscriptionLoading || isUserCreditsLoading)
    return (
      <div className="flex items-center justify-center h-5 w-full">
        <LoadingSpinner size={14} />
      </div>
    );

  if (!userCredits && !subscription)
    return (
      <div className="flex items-start justify-between gap-2">
        <CircleAlert className="w-3 h-3 flex-shrink-0 mt-1 text-destructive" />
        <span className="text-sm font-sm text-destructive flex-1">
          {t("unableToFetchCredits")}
        </span>
      </div>
    );

  const percentage = userCredits?.current_credits
    ? Math.min(
        ((userCredits?.current_credits ?? 0) /
          (userCredits?.total_credits ?? 1)) *
          100,
        100
      )
    : 0;

  const formatCredits = (value: number) => {
    // if (value >= 1000000) {
    //   return `${(value / 1000000).toFixed(2)}M`;
    // }
    // if (value >= 1000) {
    //   return `${(value / 1000).toFixed(2)}K`;
    // }
    // Remove negative values
    // Hide values after decimal point
    return value < 0 ? "0" : Math.floor(value).toString();
  };

  return (
    <div className="space-y-3">
      {/* Credits header */}
      <div className="flex items-center justify-between">
        {/* Show the subscription info if the user has a subscription */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {t("subscription")}
          </span>
          <span
            className={cn(
              "px-2 py-1 text-xs font-medium rounded-full",
              subscription?.subscription_plan
                ? subscription?.subscription_plan === "free"
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400"
            )}
          >
            {subscription?.subscription_plan
              ? subscriptionPlanLable(subscription?.subscription_plan)
              : "Free"}
          </span>
        </div>
      </div>

      {/* Show the credits info if the user has credits and total credits */}
      {userCredits?.current_credits && userCredits?.total_credits && (
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-sm font-medium">
              {formatCredits(userCredits?.current_credits || 0)} {t("credits")}
            </span>
            {/* <span className="text-xs text-muted-foreground">
              {t("remainingToday")}
            </span> */}
          </div>
          <span className="text-xs font-medium text-muted-foreground">
            {Math.round(percentage)}%
          </span>
        </div>
      )}

      {/* Progress bar */}
      {userCredits?.current_credits && userCredits?.total_credits && (
        <div className="w-full h-1 overflow-hidden bg-gray-200 rounded-full dark:bg-gray-700">
          <div
            className="h-full transition-all duration-300 rounded-full bg-primary dark:bg-primary-foreground"
            style={{
              width: `${percentage}%`,
              backgroundColor:
                percentage < 26
                  ? "hsl(var(--destructive))"
                  : percentage < 50
                    ? "hsl(var(--warning))"
                    : "hsl(var(--primary))",
            }}
          />
        </div>
      )}

      {/* Credits details */}
      {userCredits?.current_credits && userCredits?.total_credits && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium">
            {formatCredits(userCredits.current_credits)} /{" "}
            {formatCredits(userCredits.total_credits)}
          </span>
        </div>
      )}

      {/* Add a button to upgrade */}
      <Button
        variant="outline"
        className="w-full"
        onClick={() => {
          setPopoverOpen(false);
          setIsOpen(false);
          router.push("/settings/plans");
        }}
      >
        {t("upgrade")}
      </Button>
    </div>
  );
}
