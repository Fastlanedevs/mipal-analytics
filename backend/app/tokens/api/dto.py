from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from uuid import UUID
from app.tokens.entities.value_objects import SubscriptionPlan, TokenTransactionType


class GetUserTokensDTO(BaseModel):
    user_id: str
    current_credits: float
    total_credits: float
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE


class GetUserSubscriptionDTO(BaseModel):
    id: str
    user_id: str
    subscription_plan: SubscriptionPlan
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None


class TokenTransactionDTO(BaseModel):
    id: UUID
    amount: float
    transaction_type: TokenTransactionType
    balance_after: float
    description: Optional[str] = None
    created_at: datetime


class TokenTransactionListDTO(BaseModel):
    transactions: List[TokenTransactionDTO]


class CheckoutSessionDTO(BaseModel):
    """DTO for creating a checkout session"""
    lookup_key: str
    success_url: str
    cancel_url: str
    email: Optional[str] = None
    subscription_data: Optional[dict] = None

class CustomerPortalDTO(BaseModel):
    """DTO for creating a customer portal session"""
    customer_id: str
    return_url: str

class WebhookEventDTO(BaseModel):
    """DTO for webhook events"""
    type: str
    data: dict

class SessionRetrieveDTO(BaseModel):
    """DTO for retrieving a checkout session"""
    session_id: str 