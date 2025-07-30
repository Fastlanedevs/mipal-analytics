import { PricingPlanLookupKeys, SubscriptionPlan } from "@/constants/pricing";

const stripeToSubscriptionMapping = (stripePlanLookupKey: string) => {
  switch (stripePlanLookupKey) {
    case PricingPlanLookupKeys.FREE_PLAN:
      return SubscriptionPlan.FREE;
    case PricingPlanLookupKeys.PLUS_PLAN:
      return SubscriptionPlan.PLUS;
    case PricingPlanLookupKeys.PLUS_PLAN_MONTHLY:
      return SubscriptionPlan.PLUS_MONTHLY;
    case PricingPlanLookupKeys.PLUS_PLAN_YEARLY:
      return SubscriptionPlan.PLUS_YEARLY;
    case PricingPlanLookupKeys.PRO_PLAN:
      return SubscriptionPlan.PRO;
    case PricingPlanLookupKeys.PRO_PLAN_MONTHLY:
      return SubscriptionPlan.PRO_MONTHLY;
    case PricingPlanLookupKeys.PRO_PLAN_YEARLY:
      return SubscriptionPlan.PRO_YEARLY;
    case PricingPlanLookupKeys.ENTERPRISE_PLAN:
      return SubscriptionPlan.ENTERPRISE;
    default:
      return SubscriptionPlan.FREE;
  }
};

const planToCreditsMapping = (plan: SubscriptionPlan) => {
  switch (plan) {
    case SubscriptionPlan.FREE:
      return 1000; // Starting credits + daily refill
    case SubscriptionPlan.PLUS:
      return 3000; // Monthly credits
    case SubscriptionPlan.PRO:
      return 6000; // Monthly credits
    case SubscriptionPlan.ENTERPRISE:
      return 50000; // Custom amount
    default:
      return 1000;
  }
};

const handleIsCurrentPlan = (subscriptionPlan: string, lookupKey: string) => {
  if (subscriptionPlan === SubscriptionPlan.FREE) {
    if (lookupKey === PricingPlanLookupKeys.FREE_PLAN) {
      return true;
    }
  } else if (
    subscriptionPlan === SubscriptionPlan.PLUS_MONTHLY ||
    subscriptionPlan === SubscriptionPlan.PLUS_YEARLY
  ) {
    if (
      lookupKey === PricingPlanLookupKeys.PLUS_PLAN ||
      lookupKey === PricingPlanLookupKeys.PLUS_PLAN_MONTHLY ||
      lookupKey === PricingPlanLookupKeys.PLUS_PLAN_YEARLY
    ) {
      return true;
    }
  } else if (
    subscriptionPlan === SubscriptionPlan.PRO_MONTHLY ||
    subscriptionPlan === SubscriptionPlan.PRO_YEARLY
  ) {
    if (
      lookupKey === PricingPlanLookupKeys.PRO_PLAN ||
      lookupKey === PricingPlanLookupKeys.PRO_PLAN_MONTHLY ||
      lookupKey === PricingPlanLookupKeys.PRO_PLAN_YEARLY
    ) {
      return true;
    }
  } else if (subscriptionPlan === SubscriptionPlan.ENTERPRISE) {
    if (lookupKey === PricingPlanLookupKeys.ENTERPRISE_PLAN) {
      return true;
    }
  }
  return false;
};

const subscriptionPlanLable = (subscriptionPlan: string) => {
  if (subscriptionPlan === SubscriptionPlan.FREE) {
    return "FREE";
  } else if (
    subscriptionPlan === SubscriptionPlan.PLUS_MONTHLY ||
    subscriptionPlan === SubscriptionPlan.PLUS_YEARLY
  ) {
    return "PLUS";
  } else if (
    subscriptionPlan === SubscriptionPlan.PRO_MONTHLY ||
    subscriptionPlan === SubscriptionPlan.PRO_YEARLY
  ) {
    return "PRO";
  } else if (subscriptionPlan === SubscriptionPlan.ENTERPRISE) {
    return "ENTERPRISE";
  }
  return "FREE";
};

export {
  stripeToSubscriptionMapping,
  planToCreditsMapping,
  handleIsCurrentPlan,
  subscriptionPlanLable,
};
