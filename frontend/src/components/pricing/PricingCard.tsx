"use client";
import {
  PricingPlan,
  PricingPlanLookupKeys,
  SubscriptionPlan,
} from "@/constants/pricing";
import {
  CircleCheck,
  Headset,
  MessageSquareMore,
  PhoneCall,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import { Button } from "../ui/button";
import { useCreateCheckoutSessionMutation } from "@/store/services/stripeApi";
import { toast } from "@/hooks/use-toast";
import { useSession } from "next-auth/react";
import {
  useGetSubscriptionQuery,
  useGetUserProfileQuery,
} from "@/store/services/userApi";
import {
  handleIsCurrentPlan,
  stripeToSubscriptionMapping,
} from "@/lib/utils/pricing";
import { cn } from "@/lib/utils/cn";
import useManageSubscription from "@/hooks/useManageSubscription";
import { LEMCAL_URL } from "@/constants";
import { useTranslations } from "next-intl";
import TrialPeriod from "./TrialPeriod";

interface SubscriptionParams {
  tier: string;
  lookupKey?: string;
  subscription_data?: SubscriptionData;
}

interface SubscriptionData {
  trial_period_days: number;
}

interface DecodedToken {
  user_id: string;
  joined_org: boolean;
  role: string;
  org_id?: string;
  exp: number;
}

// Typings for feature sections
type FeatureKey = string;

const PricingCard: React.FC<{
  plan: PricingPlan;
  planPriceDuration: string;
}> = ({ plan, planPriceDuration }) => {
  const t = useTranslations("settings.pricing");
  const { data: session } = useSession();
  const { data: subscription, isLoading: isLoadingSubscription } =
    useGetSubscriptionQuery();
  const [createCheckoutSession, { isLoading }] =
    useCreateCheckoutSessionMutation();
  const { isLoading: isLoadingManageSubscription } = useManageSubscription();
  const { data: userProfile } = useGetUserProfileQuery({});
  const [animatePrice, setAnimatePrice] = useState(false);

  // Track price duration changes to trigger animation
  useEffect(() => {
    setAnimatePrice(true);
    const timer = setTimeout(() => {
      setAnimatePrice(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [planPriceDuration]);

  const isCurrentPlan = handleIsCurrentPlan(
    subscription?.subscription_plan ?? "",
    planPriceDuration === "month"
      ? (plan.lookupKey ?? "")
      : (plan.lookupKeyYearly ?? "")
  );

  const handleSubscription = async ({
    lookupKey,
    subscription_data,
  }: SubscriptionParams) => {
    const accessToken = session?.accessToken ?? session?.user?.access_token;

    if (!lookupKey || !accessToken) return;

    if (lookupKey === PricingPlanLookupKeys.ENTERPRISE_PLAN) {
      window.open(LEMCAL_URL, "_blank");
      return;
    }

    if (lookupKey === PricingPlanLookupKeys.FREE_PLAN) {
      toast({
        title: "Free plan is not available for purchase",
      });
      return;
    }

    const { data } = await createCheckoutSession({
      lookup_key: lookupKey,
      success_url: `${window.location.origin}/settings/plans`,
      cancel_url: `${window.location.origin}/settings/plans`,
      email: userProfile?.email,
      ...(subscription_data && { subscription_data }),
    });

    if (data?.url) {
      window.open(data.url);
    }
  };

  // Define feature sections per tier
  const freeTierFeatures: FeatureKey[] = [
    "freePlanCreditsSignup",
    "freePlanBusinessIntelligence",
    "freePlanAnalytics",
    "freePlanCsvExcelPostgresMySQL",
    // "freePlanCreditsRefill",
    // "freePlanDeepResearch",
    // "freePlanKnowledgePal",
    // "freePlanWebSearchAgent",
    // "freePlanAnalyticsPal",
    // "freePlanBIDashboards",
    // "freePlanIntegrations",
    // "freePlanLimitedDocs",
  ];

  const plusTierFeatures: FeatureKey[] = [
    // "plusPlanCreditsSignup",
    "plusPlanCreditsPerMonth",
    "plusPlanAdvancedAnalytics",
    "plusPlanPrioritySupport",
    // "plusPlanDeepResearch",
    // "plusPlanSupport",
    // "plusPlanIntegrations",
    // "plusPlanAnalyticsPalUpgrade",
    // "plusPlanUnlimitedBIDashboards",
    // "plusPlanAccessAIAgentsBeta",
  ];

  const proTierFeatures: FeatureKey[] = [
    "proPlanCreditsSignup",
    "proPlanCreditsPerMonth",
    "proPlanDeepResearch",
    "proPlanComplexDocs",
    "proPlanMeetingPal",
    "proPlanSourcingPal",
    "proPlanWorkflowAutomations",
    "proPlanIntegrations",
  ];

  const enterpriseTierFeatures: FeatureKey[] = [
    "enterprisePlanDeepResearch",
    "enterprisePlanProjectAgent",
    "enterprisePlanPersonaPal",
    "enterprisePlanAPIAccess",
    "enterprisePlanCustomOnboarding",
    "enterprisePlanUnlimitedAutomations",
    "enterprisePlanUnlimitedIntegrations",
    "enterprisePlanSupport",
    "enterprisePlanAccountManager",
    // "addonDeepResearchCredits",
    // "addonAIAssistantAPI",
    // "addonManagedServices",
  ];

  // Determine which features to use based on the plan tier
  let features: FeatureKey[] = freeTierFeatures;
  let everythingInText = "";
  let planTitle = "";
  let planPrice = "";
  let planPriceMonth = "";
  let planDescription = "";
  let planPriceYear = "";
  let supportText = "";
  if (plan.tier === "free") {
    features = freeTierFeatures;
    planTitle = t("freePlanTitle");
    planPrice = t("freePlanPrice");
    planPriceYear = t("freePlanPriceYear");
    planPriceMonth = t("freePlanPriceMonth");
    planDescription = t("freePlanDescription");
  } else if (plan.tier === "plus") {
    features = plusTierFeatures;
    planTitle = t("plusPlanTitle");
    planPrice = t("plusPlanPriceYear");
    planPriceYear = t("plusPlanPriceYear");
    planPriceMonth = t("plusPlanPriceMonth");
    planDescription = t("plusPlanDescription");
    everythingInText = t("plusPlanEverythingInFree");
    supportText = t("plusPlanSupport");
  } else if (plan.tier === "pro") {
    features = proTierFeatures;
    planTitle = t("proPlanTitle");
    planPrice = t("proPlanPrice");
    planPriceYear = t("proPlanPriceYear");
    planPriceMonth = t("proPlanPriceMonth");
    planDescription = t("proPlanDescription");
    everythingInText = t("proPlanEverythingInPlus");
  } else if (plan.tier === "enterprise") {
    features = enterpriseTierFeatures;
    planTitle = t("enterprisePlanTitle");
    planPrice = t("enterprisePlanPrice");
    planDescription = t("enterprisePlanDescription");
    everythingInText = t("enterprisePlanEverythingInPro");
  }

  // Helper function to get button text
  const getButtonText = (): string => {
    if (isLoading || isLoadingManageSubscription) {
      return t("loading");
    }

    if (!session) {
      return t("pleaseSignIn");
    }

    if (isCurrentPlan) {
      return t("currentPlan");
    }

    switch (plan.tier) {
      case "enterprise":
        return t("letsTalk");
      case "free":
        return t("downgrade");
      case "plus":
      case "pro":
        return t("upgrade");
      default:
        return t("upgrade");
    }
  };

  if (plan.hidePlan) {
    return null;
  }

  return (
    <div className="border shadow-sm card-foreground relative flex flex-col justify-between rounded-2xl p-0 bg-card w-full max-w-[320px] overflow-hidden">
      <div className="relative h-full rounded-2xl p-6">
        <div className="flex flex-col gap-6">
          {/* Plan title and badges */}
          <div className="flex flex-col space-y-1.5 p-0">
            <h3 className="text-2xl leading-none tracking-tight flex flex-row items-center flex-wrap gap-2 font-medium">
              <span className="text-2xl">{planTitle}</span>
              {plan.isPopular && <PopularBadge />}
              {!isLoadingManageSubscription && isCurrentPlan && (
                <CurrentPlanBadge />
              )}
            </h3>
            {/* Plan description */}
            <p className="text-sm text-muted-foreground mt-2 line-clamp-3">
              {planDescription}
            </p>
          </div>

          <div className="flex flex-col gap-6 p-0">
            {/* Plan price */}
            <div className="flex w-full flex-col items-center gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex flex-row flex-wrap items-center gap-2">
                  <span
                    className={cn(
                      "flex font-semibold text-4xl tabular-nums items-end gap-1 transition-all duration-300 h-[48px]",
                      plan.tier !== "free" &&
                        plan.tier !== "enterprise" &&
                        animatePrice &&
                        "animate-price-change"
                    )}
                  >
                    {plan.tier === "enterprise" ? (
                      <MessageSquareMore className="w-9 h-9" />
                    ) : planPriceMonth &&
                      planPriceYear &&
                      planPriceDuration === "month" ? (
                      planPriceMonth
                    ) : (
                      planPriceYear
                    )}
                  </span>
                </div>
              </div>

              {/* Action buttons */}
              <div className="w-full flex flex-col gap-4">
                <Button
                  disabled={
                    isLoading ||
                    !session ||
                    isCurrentPlan ||
                    isLoadingManageSubscription
                  }
                  onClick={() => {
                    handleSubscription({
                      lookupKey:
                        planPriceDuration === "month"
                          ? plan.lookupKey
                          : plan.lookupKeyYearly,
                      tier: plan.tier,
                    });
                  }}
                  variant="outline"
                  size={"lg"}
                  className={cn("w-full rounded-xl cursor-pointer")}
                >
                  {getButtonText()}
                </Button>
                {/* <TrialPeriod
                  enable={
                    (plan.alias === SubscriptionPlan.PRO ||
                      plan.alias === SubscriptionPlan.PLUS) &&
                    subscription?.subscription_plan === SubscriptionPlan.FREE
                  }
                  onClick={() => {
                    handleSubscription({
                      lookupKey:
                        planPriceDuration === "month"
                          ? plan.lookupKey
                          : plan.lookupKeyYearly,
                      tier: plan.tier,
                      subscription_data: {
                        trial_period_days: 14,
                      },
                    });
                  }}
                  disabled={
                    isLoading ||
                    !session ||
                    isCurrentPlan ||
                    isLoadingManageSubscription
                  }
                  loading={isLoading || isLoadingManageSubscription}
                /> */}
              </div>
            </div>

            {/* Divider */}
            <div
              data-orientation="horizontal"
              role="none"
              className="shrink-0 dark:bg-zinc-700 h-[1px] w-full mt-2 bg-zinc-200"
            ></div>

            {/* Features */}
            <div className="mt-4 space-y-4">
              {/* Everything in X, plus: text */}
              {everythingInText && (
                <p className="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-2">
                  {everythingInText}
                </p>
              )}

              {/* Render features as a single list */}
              <ul className="space-y-3">
                {features.map((featureKey: string) => (
                  <li
                    key={`${plan.tier}-${featureKey}`}
                    className="flex flex-row items-start gap-3 font-normal text-sm text-card-foreground"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <CircleCheck height={16} width={16} />
                    </div>
                    <p className="flex-1">{t(featureKey)}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingCard;

const PopularBadge = () => {
  const t = useTranslations("settings.pricing");
  return (
    <div className="inline-flex items-center border transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-950 focus:ring-offset-2 dark:border-zinc-800 dark:focus:ring-zinc-300 border-transparent bg-zinc-900 text-zinc-50 shadow hover:bg-zinc-900/80 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-50/80 fade-in animate-in select-none rounded-xl px-2 py-1 font-semibold text-xs">
      {t("popular")}
    </div>
  );
};

const CurrentPlanBadge = () => {
  const t = useTranslations("settings.pricing");
  return (
    <div className="inline-flex items-center border transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-950 focus:ring-offset-2 dark:border-zinc-800 dark:focus:ring-zinc-300 border-transparent bg-green-600 text-zinc-50 shadow hover:bg-green-600/80 dark:bg-green-500 dark:text-zinc-900 dark:hover:bg-green-500/80 fade-in animate-in select-none rounded-xl px-2 py-1 font-semibold text-xs">
      {t("currentPlan")}
    </div>
  );
};
