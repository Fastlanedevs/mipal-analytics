"use client";
import React from "react";
import { useGetUserCreditsQuery } from "@/store/services/userApi";
import { useSession } from "next-auth/react";
import { CircleCheck } from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

const TokenSection = ({ maxWidthOfCards }: { maxWidthOfCards: string }) => {
  const t = useTranslations("settings.profile.tokenSection");
  const { data: userCredits } = useGetUserCreditsQuery({});

  const progressPercentage = userCredits?.total_credits
    ? (userCredits.current_credits / userCredits.total_credits) * 100
    : 0;

  return (
    <Card className={cn("shadow-sm h-fit", maxWidthOfCards)}>
      <CardHeader className="p-6">
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="p-6 pt-0">
        <div className="flex flex-col gap-6">
          <div className="flex w-full flex-col items-start gap-4">
            <div className="w-full">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-card-foreground">
                  {t("currentCredits")}
                </span>
                <span className="text-sm font-medium text-card-foreground">
                  {Math.floor(userCredits?.current_credits || 0)} /{" "}
                  {Math.floor(userCredits?.total_credits || 0)}
                </span>
              </div>
              <div className="w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-2.5 max-w-full">
                <div
                  className="bg-zinc-900 dark:bg-zinc-50 h-2.5 rounded-full transition-all duration-300"
                  style={{
                    width: `${
                      progressPercentage > 100 ? 100 : progressPercentage
                    }%`,
                  }}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2 w-full">
              <div className="flex justify-between items-center">
                <span className="text-sm text-zinc-500">
                  {t("subscriptionPlan")}
                </span>
                <span className="text-sm font-medium text-card-foreground">
                  {userCredits?.subscription_plan || "FREE"}
                </span>
              </div>
            </div>
          </div>
          {/* 
          <div className="mt-4">
            <p className="text-sm text-zinc-500">
              Tokens are used to power the AI models. You can purchase
              additional tokens in the pricing section.
            </p>
          </div> */}
        </div>
      </CardContent>
    </Card>
  );
};

export default TokenSection;
