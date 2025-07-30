from app.integrations.service.integration_service import IntegrationService
from app.integrations.entity.entity import SyncIntegration
from app.knowledge_base.entity.entity import SyncIntegration, UserIntegration, IntegrationType
from app.knowledge_base.service.service import IIntegrationAdapter
from pkg.log.logger import Logger
from uuid import UUID
from typing import Optional


class IntegrationAdapter(IIntegrationAdapter):
    def __init__(self, integration_service: IntegrationService, logger: Logger):
        self.integration_service = integration_service
        self.logger = logger

    async def get_sync_integration(self, user_id: str, sync_id: UUID) -> SyncIntegration:
        """Get sync integration details"""
        try:
            integration_sync = await self.integration_service.get_integration_sync_by_id(user_id, sync_id)
            if not integration_sync:
                self.logger.error(f"Sync integration not found for user {user_id} and sync {sync_id}")
                raise ValueError(f"Sync integration not found for user {user_id} and sync {sync_id}")
            
            # Map from integration domain entity to knowledge base domain entity
            return SyncIntegration(
                user_id=integration_sync.user_id,
                sync_id=integration_sync.sync_id,
                integration_id=integration_sync.integration_id,
                integration_type=integration_sync.integration_type,
                status=integration_sync.status,
                created_at=integration_sync.created_at,
                completed_at=integration_sync.completed_at,
                updated_at=integration_sync.updated_at,
                error_message=integration_sync.error_message,
            )
        except ValueError as e:
            # Re-raise ValueError for clearer error handling
            raise e
        except Exception as e:
            self.logger.error(f"Error getting sync integration: {e!s}")
            raise e

    async def update_sync_status(
            self, user_id: str, sync_id: UUID, status: str, error_message: Optional[str] = None) -> None:
        try:
            # Map to integration domain entity format if needed
            await self.integration_service.update_integration_sync_status(
                user_id=user_id,
                sync_id=sync_id,
                sync_status=status,
                error_message=error_message,
            )
        except Exception as e:
            self.logger.error(f"Error updating sync status for {sync_id}: {e!s}")
            raise e

    async def get_integration(self, user_id: str, integration_id: UUID) -> UserIntegration:
        """Get integration details by ID"""
        try:
            integration = await self.integration_service.get_user_integration(
                user_id, integration_id
            )
            if not integration:
                raise Exception(
                    f"Integration not found for user {user_id} and integration {integration_id}"
                )

            # Map from integration domain entity to knowledge base domain entity
            return UserIntegration(
                integration_id=integration.integration_id,
                user_id=integration.user_id,
                integration_type=IntegrationType(integration.integration_metadata.type),
                credential=integration.credential,
                expires_at=integration.expires_at,
                created_at=integration.created_at,
                updated_at=integration.updated_at,
                settings=integration.settings,
                is_active=integration.is_active,
            )
        except Exception as e:
            self.logger.error(f"Error getting integration: {e!s}")
            raise e

    async def get_latest_checkpoint_integration(self, user_id: str, integration_id: UUID) -> Optional[str]:
        """Get the latest checkpoint for a given integration"""
        try:
            checkpoint = await self.integration_service.get_latest_checkpoint_integration(user_id, integration_id)
            return checkpoint
        except Exception as e:
            self.logger.error(f"Error getting latest checkpoint: {e!s}")
            raise e

    async def update_latest_checkpoint_integration(self, user_id: str, integration_id: UUID,
                                                   checkpoint: str) -> bool:
        """Update the latest checkpoint for a given integration"""
        try:
            updated = await self.integration_service.update_latest_checkpoint_integration(
                user_id, integration_id, checkpoint
            )
            return updated
        except Exception as e:
            self.logger.error(f"Error updating latest checkpoint: {e!s}")
            raise e
