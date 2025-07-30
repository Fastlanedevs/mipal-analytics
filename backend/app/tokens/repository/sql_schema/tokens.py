from sqlalchemy import Column, String, Integer, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
import uuid

from pkg.db_util.sql_alchemy.declarative_base import Base
from app.tokens.entities.value_objects import TokenTransactionType
from sqlalchemy import Column, String, Enum as SQLAlchemyEnum


class UserTokensModel(Base):
    __tablename__ = "user_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True, unique=True)
    current_credits = Column(Integer, nullable=False, default=0)
    total_credits = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def to_entity(self):
        from app.tokens.entities.entity import UserTokens
        
        return UserTokens(
            id=self.id,
            user_id=self.user_id,
            current_credits=self.current_credits,
            total_credits=self.total_credits,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
        
    @staticmethod
    def from_entity(entity):
        return UserTokensModel(
            id=entity.id,
            user_id=entity.user_id,
            current_credits=entity.current_credits,
            total_credits=entity.total_credits,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


class TokenTransactionModel(Base):
    __tablename__ = "user_token_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(
        SQLAlchemyEnum(TokenTransactionType, native_enum=False),  # Store as VARCHAR
        nullable=False
    )
    balance_after = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    
    def to_entity(self):
        from app.tokens.entities.entity import TokenTransaction
        
        return TokenTransaction(
            id=self.id,
            user_id=self.user_id,
            amount=self.amount,
            transaction_type=self.transaction_type,
            balance_after=self.balance_after,
            description=self.description,
            created_at=self.created_at
        )
        
    @staticmethod
    def from_entity(entity):
        return TokenTransactionModel(
            id=entity.id,
            user_id=entity.user_id,
            amount=entity.amount,
            transaction_type=entity.transaction_type,
            balance_after=entity.balance_after,
            description=entity.description,
            created_at=entity.created_at
        )
