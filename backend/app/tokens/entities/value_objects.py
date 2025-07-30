from enum import Enum
from datetime import datetime
from dataclasses import dataclass


class SubscriptionPlan(str, Enum):
    FREE = "FREE"
    PRO = "PRO" # Not used in Stripe
    PRO_MONTHLY = "PRO_MONTHLY"
    PRO_YEARLY = "PRO_YEARLY"
    PLUS = "PLUS" # Not used in Stripe
    PLUS_MONTHLY = "PLUS_MONTHLY"
    PLUS_YEARLY = "PLUS_YEARLY"
    ENTERPRISE = "ENTERPRISE"


class TokenTransactionType(str, Enum):
    CONSUMPTION = "CONSUMPTION"
    REFILL = "REFILL"
    ADJUSTMENT = "ADJUSTMENT"


@dataclass
class TokenAllocation:
    FREE = 1000000  # 1000 Credits = 1,000,000 Monthly tokens for free tier
    PLUS = 3000000  # 3000 Credits = 3,000,000 Monthly tokens for plus tier
    PRO = 6000000  # 6000 Credits = 6,000,000 Monthly tokens for pro tier
    ENTERPRISE = 10000000  # 10000 Credits = 10,000,000 Monthly tokens for enterprise tier
