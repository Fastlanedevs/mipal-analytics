import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from app.integrations.entity.entity import SyncIntegration, UserIntegration
from app.integrations.entity.value_object import (
    IntegrationMetadata,
    IntegrationProvider,
    IntegrationType,
    SyncStatus,
)
from pkg.db_util.sql_alchemy.declarative_base import Base


class IntegrationModel(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_type = Column(String, nullable=False, index=True)
    credential = Column(JSON, nullable=True)  # Encrypt sensitive data in practice
    integration_provider = Column(String, nullable=True)
    integration_name = Column(String, nullable=True)
    scopes = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    expires_at = Column(DateTime, nullable=True)
    user_id = Column(String, nullable=False, index=True)
    settings = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    def to_entity(self) -> UserIntegration:
        integration_metadata = IntegrationMetadata(
            type=IntegrationType(self.integration_type),
            integration_provider=(
                IntegrationProvider(self.integration_provider)
                if self.integration_provider
                else None
            ),
            scopes=self.scopes or [],
        )
        return UserIntegration(
            integration_id=self.id,  # Convert UUID to string for entity
            user_id=self.user_id,
            integration_metadata=integration_metadata,
            integration_name=self.integration_name,
            credential=self.credential or {},
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
            settings=self.settings or {},
            is_active=self.is_active,
        )

    @staticmethod
    def from_entity(entity: UserIntegration) -> "IntegrationModel":
        # Handle both string and UUID types for integration_id

        # Convert timezone-aware datetimes to naive if they exist
        expires_at = entity.expires_at.replace(tzinfo=None) if entity.expires_at and entity.expires_at.tzinfo else entity.expires_at
        created_at = entity.created_at.replace(tzinfo=None) if entity.created_at and entity.created_at.tzinfo else entity.created_at
        updated_at = entity.updated_at.replace(tzinfo=None) if entity.updated_at and entity.updated_at.tzinfo else entity.updated_at

        return IntegrationModel(
            id=entity.integration_id,
            user_id=entity.user_id,
            integration_type=entity.integration_metadata.type.value,
            integration_provider=(
                entity.integration_metadata.integration_provider.value
                if entity.integration_metadata.integration_provider
                else None
            ),
            integration_name=entity.integration_name,
            scopes=entity.integration_metadata.scopes,
            credential=entity.credential,
            expires_at=expires_at,
            created_at=created_at,
            updated_at=updated_at,
            settings=entity.settings,
            is_active=entity.is_active,
        )


class IntegrationSyncModel(Base):
    __tablename__ = "integration_syncs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    # Assuming integration_id refers to the uid of IntegrationModel
    integration_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    integration_type = Column(String, nullable=False, index=True)
    status = Column(
        SQLAlchemyEnum(SyncStatus, native_enum=False, name="sync_status_enum"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    is_active = Column(Boolean, nullable=False, default=True)  # Kept for consistency?
    error_message = Column(Text, nullable=True)

    def to_entity(self) -> SyncIntegration:
        return SyncIntegration(
            sync_id=self.id,  # Convert UUID to string
            user_id=self.user_id,
            integration_id=self.integration_id,  # Keep as UUID
            integration_type=self.integration_type,
            status=self.status, # Enum value is already correct type
            created_at=self.created_at,
            completed_at=self.completed_at,
            updated_at=self.updated_at,
            error_message=self.error_message,
        )

    @classmethod
    def from_entity(cls, entity):

        return cls(
            integration_id=entity.integration_id,
            id=entity.sync_id,
            user_id=entity.user_id,
            integration_type=entity.integration_type,
            status=entity.status, # Pass the Enum member directly
            created_at=entity.created_at, # Let DB handle default?
            completed_at=entity.completed_at,
            updated_at=entity.updated_at, # Let DB handle default/onupdate?
            error_message=entity.error_message,
        )

