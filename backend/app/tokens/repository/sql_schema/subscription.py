from sqlalchemy import Column, String, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
import uuid

from pkg.db_util.sql_alchemy.declarative_base import Base
from app.tokens.entities.value_objects import SubscriptionPlan
from sqlalchemy import Column, String, Enum as SQLAlchemyEnum


class UserSubscriptionModel(Base):
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    subscription_plan = Column(
        SQLAlchemyEnum(SubscriptionPlan, native_enum=False, length=20),  # Store as VARCHAR(20)
        nullable=False
    )
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=False, default=func.now())
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def to_entity(self):
        from app.tokens.entities.entity import UserSubscription

        return UserSubscription(
            id=self.id,
            user_id=self.user_id,
            subscription_plan=self.subscription_plan,
            stripe_customer_id=self.stripe_customer_id,
            stripe_subscription_id=self.stripe_subscription_id,
            start_date=self.start_date,
            end_date=self.end_date,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_entity(entity):
        return UserSubscriptionModel(
            id=entity.id,
            user_id=entity.user_id,
            subscription_plan=entity.subscription_plan,
            stripe_customer_id=entity.stripe_customer_id,
            stripe_subscription_id=entity.stripe_subscription_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
