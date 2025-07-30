import uuid
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from typing import Optional
from app.integrations.api.dto import (
    CreateIntegrationRequestDTO,
    CreateIntegrationResponseDTO,
    CreateIntegrationSyncResponseDTO,
    GetIntegrationSyncRequestDTO,
    GetUserIntegrationListResponseDTO,
    IntegrationInfo,
    IntegrationUpdateRequestDTO,
    IntegrationUpdateResponseDTO,
)
from app.integrations.entity.entity import SyncIntegration, UserIntegration
from app.integrations.entity.value_object import IntegrationType
from app.integrations.service.integration_service import IntegrationService
from pkg.log.logger import Logger


class IntegrationHandler:
    def __init__(self, integration_service: IntegrationService, logger: Logger):
        self.integration_service = integration_service
        self.logger = logger

    async def get_user_integration_list(self, user_id: str, integration_type_str: Optional[str] = None):
        integration_type: Optional[IntegrationType] = None
        if integration_type_str:
            try:
                integration_type = IntegrationType(integration_type_str)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid integration type: {integration_type_str}")

        result: list[UserIntegration] = await self.integration_service.get_user_integration_list(user_id, integration_type)
        return model_list_integration_entity_to_get_user_integration_list_response_dto(
            result
        )

    async def get_user_integration(self, user_id: str, integration_id: UUID):
        result = await self.integration_service.get_user_integration(user_id, integration_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
        return model_integration_entity_to_integration_info(result)

    async def create_user_integration(
        self, user_id: str, user_data: CreateIntegrationRequestDTO
    ) -> CreateIntegrationResponseDTO:
        try:
            integration_type = IntegrationType(user_data.integration_type)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid integration type: {user_data.integration_type}")

        result = await self.integration_service.create_integration(
            user_id=user_id,
            integration_type=integration_type,
            credential=user_data.credential,
            expires_at=user_data.expires_at,
            settings=user_data.settings,
        )

        if not result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create integration")

        return model_integration_entity_to_create_integration_response_dto(
            result
        )

    async def create_sync_integration(
        self, user_id: str, integration_id: UUID
    ) -> CreateIntegrationSyncResponseDTO:
        result = await self.integration_service.create_integration_sync(
            user_id, integration_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create integration sync")
        return model_integration_sync_to_create_sync_response_dto(result)

    async def get_sync_integration(
        self, user_id: str, integration_id: UUID
    ) -> GetIntegrationSyncRequestDTO:
        result = await self.integration_service.get_integration_sync(
            user_id, integration_id
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration sync status not found")
        return model_integration_sync_to_get_sync_request_dto(result)

    async def update_user_integration(
        self, user_id: str, integration_id: UUID, update_data: IntegrationUpdateRequestDTO
    ) -> IntegrationUpdateResponseDTO:

        result = await self.integration_service.update_integration(
            user_id=user_id,
            integration_id=integration_id,
            credential=update_data.credential,
            expires_at=update_data.expires_at,
            settings=update_data.settings,
            is_active=update_data.is_active,
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found for update")
        return model_integration_entity_to_update_integration_response_dto(result)

    async def delete_user_integration(
        self, user_id: str, integration_id: UUID
    ) -> dict:
        deleted = await self.integration_service.delete_integration(user_id, integration_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration with ID {integration_id} not found or could not be deleted"
            )
        return {"ok": True, "detail": "Integration deleted successfully"}


def model_integration_entity_to_integration_info(integration_entity: UserIntegration) -> IntegrationInfo:
    if integration_entity.is_active:

        return IntegrationInfo(
            integration_id=integration_entity.integration_id,
            integration_name=integration_entity.integration_name,
            integration_type=integration_entity.integration_metadata.type.value if integration_entity.integration_metadata else "Unknown",
            is_active=integration_entity.is_active
        )
    else:
        return IntegrationInfo(
            integration_type=integration_entity.integration_metadata.type.value if integration_entity.integration_metadata else "Unknown",
            is_active=integration_entity.is_active
        )


def model_list_integration_entity_to_get_user_integration_list_response_dto(
    integration_entity_list: list[UserIntegration],
) -> GetUserIntegrationListResponseDTO:
    return GetUserIntegrationListResponseDTO(
        integration_list=[
            model_integration_entity_to_integration_info(integration_entity)
            for integration_entity in integration_entity_list
        ]
    )


def model_integration_entity_to_create_integration_response_dto(
    integration_entity: UserIntegration
) -> CreateIntegrationResponseDTO:
    integration_type_str = integration_entity.integration_metadata.type.value if integration_entity.integration_metadata else "Unknown"
    return CreateIntegrationResponseDTO(
        user_id=integration_entity.user_id,
        integration_id=integration_entity.integration_id,
        integration_name=integration_entity.integration_name,
        integration_type=integration_type_str,
        is_active=integration_entity.is_active,
        created_at=integration_entity.created_at,
        updated_at=integration_entity.updated_at,
    )


def model_integration_entity_to_update_integration_response_dto(
    integration_entity: UserIntegration
) -> IntegrationUpdateResponseDTO:
    integration_type_str = integration_entity.integration_metadata.type.value if integration_entity.integration_metadata else "Unknown"
    return IntegrationUpdateResponseDTO(
        user_id=integration_entity.user_id,
        integration_id=integration_entity.integration_id,
        integration_name=integration_entity.integration_name,
        integration_type=integration_type_str,
        is_active=integration_entity.is_active,
        created_at=integration_entity.created_at,
        updated_at=integration_entity.updated_at,
    )


def model_integration_sync_to_create_sync_response_dto(
    sync_result: SyncIntegration,
) -> CreateIntegrationSyncResponseDTO:
    return CreateIntegrationSyncResponseDTO(
        sync_process_id=sync_result.sync_id,
        integration_id=sync_result.integration_id,
        integration_type=sync_result.integration_type.value,
        sync_status=sync_result.status.value,
        sync_start_time=sync_result.created_at,
        sync_end_time=sync_result.completed_at,
    )


def model_integration_sync_to_get_sync_request_dto(
    sync_result: SyncIntegration,
) -> GetIntegrationSyncRequestDTO:
    return GetIntegrationSyncRequestDTO(
        last_sync_process_id=sync_result.sync_id,
        integration_id=sync_result.integration_id,
        integration_type=sync_result.integration_type.value,
        last_sync_status=sync_result.status.value,
        last_sync_start_time=sync_result.created_at,
        last_sync_end_time=sync_result.completed_at,
        last_successful_sync=sync_result.completed_at,
    )
