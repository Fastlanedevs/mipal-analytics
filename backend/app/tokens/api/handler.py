from typing import List, Tuple, Optional

from app.tokens.api.dto import (
    GetUserTokensDTO,
    GetUserSubscriptionDTO,
    TokenTransactionDTO,
    TokenTransactionListDTO
)
from pkg.log.logger import Logger
from app.tokens.entities.value_objects import SubscriptionPlan
from app.tokens.service.service import TokensService

CREDIT_TO_TOKEN = 0.001


class TokensHandler:
    def __init__(self, tokens_service: TokensService, logger: Logger):
        self.service = tokens_service
        self.logger = logger

    async def get_user_tokens(self, user_id: str, email: str) -> GetUserTokensDTO:
        tokens = await self.service.get_or_create_user_tokens(user_id)
        subscription = await self.service.get_user_subscription(user_id, email)
        
        return GetUserTokensDTO(
            user_id=tokens.user_id,
            current_credits=round(tokens.current_credits * CREDIT_TO_TOKEN * 2) / 2,
            total_credits=round(tokens.total_credits * CREDIT_TO_TOKEN *2 ) / 2,
            subscription_plan=subscription.subscription_plan
        )

    async def get_user_subscription(self, user_id: str, email: str) -> GetUserSubscriptionDTO:
        subscription = await self.service.get_user_subscription(user_id, email)
        
        return GetUserSubscriptionDTO(
            id=subscription.id.__str__(),
            user_id=subscription.user_id,
            subscription_plan=subscription.subscription_plan,
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_subscription_id=subscription.stripe_subscription_id,
            start_date=subscription.start_date,
            end_date=subscription.end_date
        )

    async def get_token_transactions(self, user_id: str, limit: int = 50) -> TokenTransactionListDTO:
        transactions = await self.service.get_token_transactions(user_id, limit)

        return TokenTransactionListDTO(
            transactions=[
                TokenTransactionDTO(
                    id=tx.id,
                    amount=tx.amount * CREDIT_TO_TOKEN,
                    transaction_type=tx.transaction_type,
                    balance_after=tx.balance_after * CREDIT_TO_TOKEN,
                    description=tx.description,
                    created_at=tx.created_at
                ) for tx in transactions
            ]
        )
