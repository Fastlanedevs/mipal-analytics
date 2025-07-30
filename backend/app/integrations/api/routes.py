from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends

from app.integrations.api.dependency import IntegrationHandlerDep
from app.integrations.api.dto import (
    CreateIntegrationRequestDTO,
    CreateIntegrationResponseDTO,
    CreateIntegrationSyncResponseDTO,
    GetIntegrationSyncRequestDTO,
    GetUserIntegrationListResponseDTO,
)
from app.middleware import get_token_detail

integration_router = APIRouter(tags=["Integrations"])


# Organisation Management Routes
@integration_router.get("/integrations")
async def get_user_integration_list(
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep,
        integration_type: str = None
) -> GetUserIntegrationListResponseDTO:
    """Create a new organisation"""
    return await handler.get_user_integration_list(token_detail.user_id, integration_type)


@integration_router.get("/integrations/{integration_id}")
async def get_user_integration(
        integration_id: UUID,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep,
) -> GetUserIntegrationListResponseDTO:
    """Create a new organisation"""
    return await handler.get_user_integration(token_detail.user_id, integration_id)


@integration_router.post("/integrations")
async def create_user_integration(
        create_user_integration_request: CreateIntegrationRequestDTO,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep,
) -> CreateIntegrationResponseDTO:
    """Create a new organisation"""
    return await handler.create_user_integration(
        token_detail.user_id, create_user_integration_request
    )


@integration_router.post("/integrations/{integration_id}/sync")
async def create_sync_integration(
        integration_id: str,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep,
) -> CreateIntegrationSyncResponseDTO:
    return await handler.create_sync_integration(token_detail.user_id, integration_id)


@integration_router.get("/integrations/{integration_id}/sync")
async def get_sync_integration(integration_id: UUID, token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep) -> GetIntegrationSyncRequestDTO:
    return await handler.get_sync_integration(token_detail.user_id, integration_id)


@integration_router.put("/integrations/{integration_id}")
async def update_user_integration(
        integration_id: UUID,
        update_user_integration_request: CreateIntegrationRequestDTO,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep,
) -> CreateIntegrationResponseDTO:
    """Create a new organisation"""
    return await handler.update_user_integration(
        token_detail.user_id, integration_id, update_user_integration_request
    )


@integration_router.delete("/integrations/{integration_id}")
async def delete_user_integration(
        integration_id: UUID,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: IntegrationHandlerDep,
) -> dict:
    """Create a new organisation"""
    return await handler.delete_user_integration(token_detail.user_id, integration_id)
