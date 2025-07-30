from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import uuid
from app.tokens.entities.value_objects import SubscriptionPlan, TokenTransactionType


class UserTokens(BaseModel):
    id: uuid.UUID
    user_id: str
    current_credits: int
    total_credits: int
    created_at: datetime
    updated_at: datetime


class UserSubscription(BaseModel):
    id: uuid.UUID
    user_id: str
    subscription_plan: SubscriptionPlan
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str = "active"
    start_date: datetime
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TokenTransaction(BaseModel):
    id: uuid.UUID
    user_id: str
    amount: int
    transaction_type: TokenTransactionType
    balance_after: int
    description: Optional[str] = None
    created_at: datetime

class StripePlan(BaseModel):
    price: int
    duration: str
    name: str
    lookup_key: str
    
    