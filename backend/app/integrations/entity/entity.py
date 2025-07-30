import uuid
from uuid import UUID
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.integrations.entity.value_object import (
    IntegrationMetadata,
    IntegrationProvider,
    IntegrationType,
    SyncStatus,
)


class UserIntegration(BaseModel):
    user_id: str
    integration_id: UUID = Field(default_factory=uuid.uuid4)
    is_active: bool = True
    integration_name: Optional[str] = Field(default_factory=str)
    integration_metadata: IntegrationMetadata | None = None
    credential: dict[str, Any] | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)
    settings: dict[str, Any] | None = Field(default_factory=dict)


class UserIntegrationCreateRequest(BaseModel):
    user_id: str
    is_active: bool = True
    integration_metadata: IntegrationMetadata | None = None
    credential: dict[str, Any] | None = None
    expires_at: datetime | None = None
    settings: dict[str, Any] | None = Field(default_factory=dict)


class SyncIntegration(BaseModel):
    sync_id: UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    integration_type: IntegrationType
    status: SyncStatus
    integration_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = None


class SyncIntegrationEvent(BaseModel):
    user_id: str
    sync_id: str
