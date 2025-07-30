from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class IntegrationInfo(BaseModel):
    integration_id: Optional[UUID] = None
    integration_name: Optional[str] = Field(default_factory=str)
    integration_type: str
    is_active: bool


class GetUserIntegrationListResponseDTO(BaseModel):
    integration_list: list[IntegrationInfo]


class CreateIntegrationRequestDTO(BaseModel):
    integration_type: str
    credential: dict[str, Any] | None = None
    expires_at: datetime | None = None
    settings: dict[str, Any] | None = None


class CreateIntegrationResponseDTO(BaseModel):
    user_id: str
    integration_id: UUID
    integration_name: str
    integration_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class IntegrationUpdateRequestDTO(BaseModel):
    integration_type: str
    credential: dict[str, Any] | None = None
    expires_at: datetime | None = None
    settings: dict[str, Any] | None = None
    is_active: bool | None = None


class IntegrationUpdateResponseDTO(BaseModel):
    user_id: str
    integration_id: UUID
    integration_type: str
    integration_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateIntegrationSyncResponseDTO(BaseModel):
    sync_process_id: UUID
    integration_type: str
    integration_id: UUID
    sync_status: str
    sync_start_time: datetime
    sync_end_time: Optional[datetime]


class GetIntegrationSyncRequestDTO(BaseModel):
    last_sync_process_id: UUID
    integration_id: UUID
    integration_type: str
    last_sync_status: str
    last_sync_start_time: datetime
    last_sync_end_time: Optional[datetime]

    last_successful_sync: datetime | None = None
