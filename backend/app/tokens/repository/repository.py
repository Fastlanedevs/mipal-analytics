import uuid
from typing import List, Optional, Any
from datetime import datetime

from sqlalchemy import select, insert, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tokens.entities.entity import (UserTokens as UserTokensEntity, UserSubscription as UserSubscriptionEntity,
                                        TokenTransaction as TokenTransactionEntity)
from app.tokens.entities.value_objects import SubscriptionPlan, TokenTransactionType, TokenAllocation
from app.tokens.repository.sql_schema.tokens import UserTokensModel, TokenTransactionModel
from app.tokens.repository.sql_schema.subscription import UserSubscriptionModel
from app.tokens.service.service import ITokensRepository
from pkg.log.logger import Logger
from pkg.db_util.postgres_conn import PostgresConnection


class TokensRepository(ITokensRepository):
    def __init__(self, sql_db_conn: PostgresConnection, logger: Logger):
        self.db_conn = sql_db_conn
        self.logger = logger

    async def get_user_tokens(self, user_id: str) -> Optional[UserTokensEntity]:
        """Get user tokens by user ID using SQLAlchemy ORM"""
        async with self.db_conn.get_session() as session:
            stmt = select(UserTokensModel).where(UserTokensModel.user_id == user_id)

            try:
                result = await session.execute(stmt)
                user_tokens = result.scalars().first()

                if not user_tokens:
                    return None

                return user_tokens.to_entity()
            except Exception as e:
                self.logger.error(f"Error getting user tokens for {user_id}: {str(e)}")
                raise

    async def create_user_tokens(self, user_id: str, initial_credits: int = 0) -> UserTokensEntity:
        """Create user tokens using SQLAlchemy ORM"""
        async with self.db_conn.get_session() as session:
            # Create the model instance
            user_tokens = UserTokensModel(
                user_id=user_id,
                current_credits=initial_credits,
                total_credits=initial_credits
            )

            try:
                session.add(user_tokens)
                await session.commit()
                # Refresh to get generated values (id, timestamps, etc.)
                await session.refresh(user_tokens)

                return user_tokens.to_entity()
            except Exception as e:
                self.logger.error(f"Error creating user tokens for {user_id}: {str(e)}")
                raise

    async def update_user_tokens(self, user_id: str, current_credits: int, total_credits: int) -> Optional[
        UserTokensEntity]:
        """Update user tokens using SQLAlchemy ORM"""
        async with self.db_conn.get_session() as session:
            stmt = (
                update(UserTokensModel)
                .where(UserTokensModel.user_id == user_id)
                .values(
                    current_credits=current_credits,
                    total_credits=total_credits,
                    updated_at=func.now()
                )
                .returning(UserTokensModel)
            )

            try:
                result = await session.execute(stmt)
                await session.commit()

                updated_tokens = result.scalars().first()
                if not updated_tokens:
                    return None

                return updated_tokens.to_entity()
            except Exception as e:
                self.logger.error(f"Error updating user tokens for {user_id}: {str(e)}")
                raise


    async def record_token_transaction(
            self,
            user_id: str,
            amount: int,
            transaction_type: TokenTransactionType,
            balance_after: int,
            description: Optional[str] = None
    ) -> TokenTransactionEntity:
        """Record token transaction using SQLAlchemy ORM"""
        async with self.db_conn.get_session() as session:
            # Create the model instance
            transaction = TokenTransactionModel(
                user_id=user_id,
                amount=amount,
                transaction_type=transaction_type,
                balance_after=balance_after,
                description=description
            )

            try:
                session.add(transaction)
                await session.commit()
                # Refresh to get generated values (id, timestamp, etc.)
                await session.refresh(transaction)

                return transaction.to_entity()
            except Exception as e:
                self.logger.error(f"Error recording token transaction for {user_id}: {str(e)}")
                raise

    async def get_token_transactions(self, user_id: str, limit: int = 50) -> List[TokenTransactionEntity]:
        """Get user token transactions using SQLAlchemy ORM"""
        async with self.db_conn.get_session() as session:
            stmt = (
                select(TokenTransactionModel)
                .where(TokenTransactionModel.user_id == user_id)
                .order_by(TokenTransactionModel.created_at.desc())
                .limit(limit)
            )

            try:
                result = await session.execute(stmt)
                transactions = result.scalars().all()

                return [transaction.to_entity() for transaction in transactions]
            except Exception as e:
                self.logger.error(f"Error getting token transactions for {user_id}: {str(e)}")
                raise

    async def refill_free_users(self, batch_size: int = 100) -> int:
        """Refills tokens for active users on the FREE plan who are below the limit using SQLAlchemy ORM"""
        total_refilled = 0
        now = datetime.utcnow()
        refill_amount = TokenAllocation.FREE

        try:
            # First, identify all users who need refilling
            async with self.db_conn.get_session() as session:
                # 1. Find active FREE user IDs
                free_users_stmt = (
                    select(UserSubscriptionModel.user_id)
                    .where(
                        UserSubscriptionModel.subscription_plan == SubscriptionPlan.FREE,
                        or_(
                            UserSubscriptionModel.end_date == None,
                            UserSubscriptionModel.end_date > now
                        )
                    )
                    .distinct()
                )

                result = await session.execute(free_users_stmt)
                free_user_ids = [row.user_id for row in result.all()]

                if not free_user_ids:
                    self.logger.info("No active FREE users found to check for refill.")
                    return 0

                # 2. Find which of these users need refilling
                users_to_refill_stmt = (
                    select(UserTokensModel.user_id)
                    .where(
                        UserTokensModel.user_id.in_(free_user_ids),
                        UserTokensModel.current_credits < refill_amount
                    )
                )

                result = await session.execute(users_to_refill_stmt)
                users_to_refill_ids = [row.user_id for row in result.all()]

            # Process users in batches to avoid long transactions
            for i in range(0, len(users_to_refill_ids), batch_size):
                batch_users = users_to_refill_ids[i:i + batch_size]
                if not batch_users:
                    continue

                async with self.db_conn.get_session() as session:
                    async with session.begin():
                        update_stmt = (
                            update(UserTokensModel)
                            .where(UserTokensModel.user_id.in_(batch_users))
                            .values(
                                current_credits=refill_amount,
                                total_credits=UserTokensModel.total_credits + refill_amount,
                                updated_at=func.now()
                            )
                        )

                        result = await session.execute(update_stmt)
                        await session.commit()
                        total_refilled += len(batch_users)

                # Add a small delay between batches to reduce load
                await asyncio.sleep(0.1)

            self.logger.info(f"Successfully updated tokens for {total_refilled} users.")
            return total_refilled

        except Exception as e:
            self.logger.error(f"Failed to update tokens during refill: {e}", exc_info=True)
            return 0

