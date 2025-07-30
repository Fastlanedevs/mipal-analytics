from enum import Enum

class SubscriptionPlan(str, Enum):
    FREE_PLAN = "MIPAL_FREE_PLAN"
    PRO_PLAN = "MIPAL_PRO_PLAN" # Not used in Stripe
    PRO_PLAN_MONTHLY = "MIPAL_PRO_MONTHLY"
    PRO_PLAN_YEARLY = "MIPAL_PRO_YEARLY"
    PLUS_PLAN = "MIPAL_PLUS_PLAN" # Not used in Stripe
    PLUS_PLAN_MONTHLY = "MIPAL_PLUS_MONTHLY"
    PLUS_PLAN_YEARLY = "MIPAL_PLUS_YEARLY"
    ENTERPRISE_PLAN = "MIPAL_ENTERPRISE_PLAN"

    @classmethod
    def get_all_plans(cls) -> list[str]:
        """Returns a list of all possible subscription plans."""
        return [plan.value for plan in cls]
