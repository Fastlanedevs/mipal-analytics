"use client";

import { pricingPlans } from "@/constants/pricing";
import PricingCard from "./PricingCard";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "@/hooks/use-toast";
import { useTranslations } from "next-intl";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";

export default function PricingSection() {
  const t = useTranslations("settings.pricing");
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const searchParams = useSearchParams();
  const [planPriceDuration, setPlanPriceDuration] = useState<"year" | "month">(
    "month"
  );

  useEffect(() => {
    // Check to see if this is a redirect back from Checkout
    if (searchParams?.get("success")) {
      setSuccess(true);
      setSessionId(searchParams?.get("session_id") || "");
      toast({
        title: t("success"),
        description: t("paymentSuccess"),
      });
    }

    if (searchParams?.get("canceled")) {
      setSuccess(false);
      setMessage(t("paymentCanceled"));
      toast({
        title: t("canceled"),
        description: t("paymentCanceled"),
        variant: "destructive",
      });
    }
  }, [searchParams]);

  const handleMonthClick = () => {
    if (planPriceDuration !== "month") {
      setPlanPriceDuration("month");
    }
  };

  const handleYearClick = () => {
    if (planPriceDuration !== "year") {
      setPlanPriceDuration("year");
    }
  };

  return (
    <div className="flex flex-col gap-6 items-center">
      {success && (
        <div className="w-full">
          <PaymentSuccess />
        </div>
      )}
      <div className="relative flex items-center rounded-full p-1 bg-foreground/10 border border-foreground/40 w-fit">
        <div
          className={cn(
            "absolute h-[85%] w-24 bg-primary rounded-full transition-all duration-300 ease-in-out z-0",
            planPriceDuration === "month" ? "left-[4px]" : "left-[calc(50%)]"
          )}
        />
        <button
          onClick={handleMonthClick}
          className={cn(
            "relative z-10 rounded-full w-24 py-2 text-sm font-medium transition-colors duration-200",
            planPriceDuration === "month"
              ? "text-primary-foreground"
              : "text-foreground"
          )}
        >
          {t("month")}
        </button>
        <button
          onClick={handleYearClick}
          className={cn(
            "relative z-10 rounded-full w-24 py-2 text-sm font-medium transition-colors duration-200",
            planPriceDuration === "year"
              ? "text-primary-foreground"
              : "text-foreground"
          )}
        >
          {t("year")}
        </button>
      </div>
      <div className="flex flex-row flex-wrap justify-center gap-6">
        {pricingPlans.map((plan, index) => (
          <PricingCard
            key={index}
            plan={plan}
            planPriceDuration={planPriceDuration}
          />
        ))}
      </div>
    </div>
  );
}

function PaymentSuccess() {
  const t = useTranslations("settings.pricing");
  return (
    <div
      className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative"
      role="alert"
    >
      <strong className="font-bold">{t("success")}</strong>
      <span className="block sm:inline"> {t("paymentSuccess")}</span>
    </div>
  );
}
