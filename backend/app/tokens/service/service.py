from datetime import datetime
from typing import List, Optional, Tuple
from abc import ABC, abstractmethod

from app.tokens.entities.entity import UserTokens, UserSubscription, TokenTransaction
from app.tokens.entities.value_objects import SubscriptionPlan, TokenTransactionType, TokenAllocation
from uuid import UUID
from pkg.log.logger import Logger


class ITokensRepository(ABC):
    @abstractmethod
    async def get_user_tokens(self, user_id: str) -> Optional[UserTokens]:
        pass

    @abstractmethod
    async def create_user_tokens(self, user_id: str, initial_credits: int = 0) -> UserTokens:
        pass

    @abstractmethod
    async def update_user_tokens(self, user_id: str, current_credits: int, total_credits: int) -> Optional[UserTokens]:
        pass

    @abstractmethod
    async def record_token_transaction(self, user_id: str, amount: int, transaction_type: TokenTransactionType, balance_after: int, description: Optional[str] = None) -> TokenTransaction:
        pass




class TokensService:
    def __init__(self, tokens_repository: ITokensRepository, logger: Logger):
        self.repository = tokens_repository
        self.logger = logger

    async def get_or_create_user_tokens(self, user_id: str) -> UserTokens:
        user_tokens = await self.repository.get_user_tokens(user_id)
        if not user_tokens:
            # New user gets 1,000,000 initial tokens = 1000 Credits (FREE tier)
            user_tokens = await self.repository.create_user_tokens(user_id, initial_credits=TokenAllocation.FREE)
            # Record the initial credit transaction
            await self.repository.record_token_transaction(
                user_id=user_id,
                amount=TokenAllocation.FREE,
                transaction_type=TokenTransactionType.REFILL,
                balance_after=TokenAllocation.FREE,
                description="Initial token allocation for new user"
            )
        return user_tokens

    async def get_user_subscription(self, user_id: str, email: str) -> UserSubscription:
        subscription = await self.repository.get_user_subscription(user_id)
        if not subscription:
            # Create default FREE subscription
            subscription = await self.repository.create_user_subscription(
                user_id=user_id,
                subscription_plan=SubscriptionPlan.FREE
            )
        
        return subscription


    async def consume_tokens(self, user_id: str, amount: int, description: Optional[str] = None) -> Tuple[
        bool, UserTokens]:
        """
        Consume tokens for a user. Returns (success, updated_tokens)
        """
        user_tokens = await self.get_or_create_user_tokens(user_id)

        # Check if user has enough tokens
        if user_tokens.current_credits < amount:
            return False, user_tokens

        # Update token balance
        new_balance = user_tokens.current_credits - amount
        updated_tokens = await self.repository.update_user_tokens(
            user_id=user_id,
            current_credits=new_balance,
            total_credits=user_tokens.total_credits
        )

        # Record transaction
        await self.repository.record_token_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=TokenTransactionType.CONSUMPTION,
            balance_after=new_balance,
            description=description
        )

        return True, updated_tokens

    async def check_token_limit(self, user_id: str, consume_amount: int) -> bool:
        """
        Check if a user has enough tokens to consume a certain amount.
        """
        user_tokens = await self.get_or_create_user_tokens(user_id)
        return user_tokens.current_credits >= consume_amount

    async def refill_tokens(self, user_id: str, amount: int, description: Optional[str] = None) -> UserTokens:
        """
        Refill tokens for a user. Also updates the total credits.
        """
        user_tokens = await self.get_or_create_user_tokens(user_id)

        # Update token balance
        new_current = user_tokens.current_credits + amount
        new_total = user_tokens.total_credits + amount

        updated_tokens = await self.repository.update_user_tokens(
            user_id=user_id,
            current_credits=new_current,
            total_credits=new_total
        )

        # Record transaction
        await self.repository.record_token_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=TokenTransactionType.REFILL,
            balance_after=new_current,
            description=description
        )

        return updated_tokens

        """
        Update user's subscription and refill tokens according to the new plan
        """
        current_subscription = await self.get_user_subscription(user_id)
        self.logger.debug(f"Updating subscription for user_id: {user_id}, plan: {subscription_plan}")

        # End current subscription if it exists
        if current_subscription and current_subscription.subscription_plan != subscription_plan:
            await self.repository.update_user_subscription(
                subscription_id=current_subscription.id,
                end_date=datetime.utcnow()
            )

        # Create new subscription
        new_subscription = await self.repository.create_user_subscription(
            user_id=user_id,
            subscription_plan=subscription_plan,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            end_date=end_date
        )

        if(current_subscription.subscription_plan != subscription_plan):
            # Refill tokens based on the subscription plan
            token_amount = 0
            if subscription_plan == SubscriptionPlan.FREE:
                token_amount = TokenAllocation.FREE
            elif subscription_plan == SubscriptionPlan.PRO:
                token_amount = TokenAllocation.PRO
            elif subscription_plan == SubscriptionPlan.ENTERPRISE:
                token_amount = TokenAllocation.ENTERPRISE

            if token_amount > 0:
                await self.refill_tokens(
                    user_id=user_id,
                    amount=token_amount,
                    description=f"Token refill for {subscription_plan} subscription"
                )

        return new_subscription

    async def daily_refill_for_free_users(self) -> int:
        """
        Daily automated task to refill tokens for FREE tier users
        Returns the number of users processed
        """
        # This would be implemented as part of a scheduled task
        # For now, we'll just define the interface
        # In a real implementation, you would query all free users and refill their tokens
        refill_all_free_users = await self.repository.refill_free_users()
        return refill_all_free_users

    async def get_token_transactions(self, user_id: str, limit: int = 50) -> List[TokenTransaction]:
        """Get recent token transactions for a user"""
        return await self.repository.get_token_transactions(user_id, limit)
