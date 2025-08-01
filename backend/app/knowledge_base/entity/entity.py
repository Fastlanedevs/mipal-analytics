import uuid
from uuid import UUID
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict






class IntegrationType(str, Enum):
    """Enum representing different integration services"""

    POSTGRESQL = "POSTGRESQL"

    @classmethod
    def get_all_integration_types(cls) -> list:
        return [integration_type for integration_type in cls]


class UserIntegration(BaseModel):
    """Entity representing a user's integration"""

    integration_id: UUID
    user_id: str
    integration_type: IntegrationType
    credential: Dict[str, Any] | None = None
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settings: Dict[str, Any] | None = None
    is_active: bool = True


class SyncIntegration(BaseModel):
    """Entity for tracking integration synchronization status"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True
    )

    user_id: str
    integration_id: UUID
    status: str
    integration_type: str
    sync_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
