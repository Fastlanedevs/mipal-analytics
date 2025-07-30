export interface PricingPlan {
  tier: string;
  name: string;
  alias?: string;
  description: string;
  price: number | string;
  billingPeriod?: string;
  isPopular?: boolean;
  features: string[];
  buttonText: string;
  lookupKey?: string;
  lookupKeyYearly?: string;
  hidePlan?: boolean;
}

export enum PricingPlanLookupKeys {
  FREE_PLAN = "MIPAL_FREE_PLAN",
  PLUS_PLAN = "MIPAL_PLUS_PLAN", // Not used in stripe
  PLUS_PLAN_MONTHLY = "MIPAL_PLUS_MONTHLY",
  PLUS_PLAN_YEARLY = "MIPAL_PLUS_YEARLY",
  PRO_PLAN = "MIPAL_PRO_PLAN", // Not used in stripe
  PRO_PLAN_MONTHLY = "MIPAL_PRO_MONTHLY",
  PRO_PLAN_YEARLY = "MIPAL_PRO_YEARLY",
  ENTERPRISE_PLAN = "MIPAL_ENTERPRISE_PLAN",
}

export enum SubscriptionPlan {
  FREE = "FREE",
  PLUS = "PLUS",
  PLUS_MONTHLY = "PLUS_MONTHLY",
  PLUS_YEARLY = "PLUS_YEARLY",
  PRO = "PRO",
  PRO_MONTHLY = "PRO_MONTHLY",
  PRO_YEARLY = "PRO_YEARLY",
  ENTERPRISE = "ENTERPRISE",
}

export const pricingPlans: PricingPlan[] = [
  {
    tier: "free",
    name: "Free",
    alias: "FREE",
    description:
      "A starter plan for individuals or teams to test MiPal's core value.",
    price: 0,
    billingPeriod: "forever",
    features: [],
    buttonText: "GET STARTED",
    lookupKey: PricingPlanLookupKeys.FREE_PLAN,
    lookupKeyYearly: PricingPlanLookupKeys.FREE_PLAN,
    hidePlan: false,
  },
  {
    tier: "plus",
    name: "Plus",
    alias: "PLUS",
    description: "Unlock the power of deeper research and real-time analytics.",
    price: 20,
    billingPeriod: "per month",
    isPopular: true,
    features: [],
    buttonText: "UPGRADE",
    lookupKey: PricingPlanLookupKeys.PLUS_PLAN_MONTHLY,
    lookupKeyYearly: PricingPlanLookupKeys.PLUS_PLAN_YEARLY,
    hidePlan: false,
  },
  {
    tier: "pro",
    name: "Pro",
    alias: "PRO",
    description:
      "Scale your operations with document automation and powerful assistants.",
    price: 50,
    billingPeriod: "per month",
    features: [],
    buttonText: "UPGRADE",
    lookupKey: PricingPlanLookupKeys.PRO_PLAN_MONTHLY,
    lookupKeyYearly: PricingPlanLookupKeys.PRO_PLAN_YEARLY,
    hidePlan: true,
  },
  {
    tier: "enterprise",
    name: "Enterprise",
    alias: "ENTERPRISE",
    description: "For large teams and advanced automation pipelines.",
    price: "Custom",
    features: [],
    buttonText: "LET'S TALK",
    lookupKey: PricingPlanLookupKeys.ENTERPRISE_PLAN,
    hidePlan: true,
  },
];

export const tokenLimitsReached = `Not enough tokens available for this operation`;
