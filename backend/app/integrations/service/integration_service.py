import uuid
from uuid import UUID
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Any

from fastapi import HTTPException, status

from app.integrations.entity.entity import SyncIntegration, UserIntegration
from app.integrations.entity.value_object import (
    IntegrationConfig,
    IntegrationMetadata,
    IntegrationProvider,
    IntegrationType,
    SyncStatus,
    CommunicationIntegrations
)
from pkg.log.logger import Logger


class IIntegrationRepository(ABC):
    @abstractmethod
    async def create_user_integration(self, user_id: str,
                                      user_integration: UserIntegration) -> Optional[UserIntegration]:
        pass

    @abstractmethod
    async def get_user_integration(self, user_id: str, integration_id: UUID) -> Optional[UserIntegration]:
        pass

    @abstractmethod
    async def get_all_active_user_integration(self, user_id: str,
                                              integration_type: Optional[IntegrationType] = None) -> List[
        UserIntegration]:
        pass

    @abstractmethod
    async def update_user_integration(self, user_id: str,
                                      user_integration: UserIntegration) -> Optional[UserIntegration]:
        pass

    @abstractmethod
    async def delete_user_integration(self, user_id: str, integration_id: UUID) -> bool:
        pass

    @abstractmethod
    async def get_latest_checkpoint_integration(self, user_id: str, integration_id: UUID) -> Optional[str]:
        pass

    @abstractmethod
    async def update_latest_checkpoint_integration(self, user_id: str, integration_id: UUID, checkpoint: str) -> bool:
        pass


    @abstractmethod
    async def get_last_sync(self, user_id: str, integration_id: UUID) -> Optional[SyncIntegration]:
        pass

    @abstractmethod
    async def create_sync(self, sync_integration: SyncIntegration) -> SyncIntegration:
        pass

    @abstractmethod
    async def update_sync(self, sync_integration: SyncIntegration) -> SyncIntegration:
        pass

    @abstractmethod
    async def get_last_successful_sync(self, user_id: str, integration_id: UUID) -> Optional[SyncIntegration]:
        pass

    @abstractmethod
    async def get_sync_by_id(self, user_id: str, sync_id: UUID) -> Optional[SyncIntegration]:
        pass


class IIntegrationClient(ABC):

    @abstractmethod
    async def validate_postgres_credentials(self, integration_credentials: dict) -> bool:
        pass


class IntegrationService:
    def __init__(
            self,
            integrations_client: IIntegrationClient,
            integration_repository: IIntegrationRepository,
            logger: Logger,
    ):
        self.integrations_client = integrations_client
        self.integration_repository = integration_repository
        self.logger = logger

    async def create_integration(self, user_id: str, integration_type: IntegrationType,
                                 credential: Optional[dict[str, Any]] = None,
                                 expires_at: Optional[datetime] = None,
                                 settings: Optional[dict[str, Any]] = None
                                 ) -> Optional[UserIntegration]:

        integration_config = IntegrationConfig()
        integration_metadata = integration_config.get_integration_metadata(integration_type)

        # Construct UserIntegration internally
        user_integration = UserIntegration(
            user_id=user_id,
            integration_metadata=integration_metadata,
            credential=credential,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            settings=settings,
            is_active=True
        )
        print( "user integration id ", user_integration.integration_id)

        # Validate credentials based on provider
            # POSTGRESQL
        if integration_metadata.integration_provider == IntegrationProvider.POSTGRESQL:
            if not await self.integrations_client.validate_postgres_credentials(
                    user_integration.credential
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PostgreSQL credentials",
                )
            user_integration.integration_name = user_integration.credential.get("database_name")

            integration = await self.integration_repository.create_user_integration(
                user_id, user_integration
            )
            # Automatically trigger sync upon creation for relevant types (like PostgreSQL)
            sync = await self.create_integration_sync(user_id, integration.integration_id)

            print(f"integration created: {integration}")

            return integration
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid integration provider",
            )

    async def update_integration(self, user_id: str, integration_id: UUID, credential: Optional[dict[str, Any]] = None,
                                 expires_at: Optional[datetime] = None,
                                 settings: Optional[dict[str, Any]] = None,
                                 is_active: Optional[bool] = None) -> Optional[UserIntegration]:

        try:
            # Get existing integration
            current_integration = await self.get_user_integration(user_id, integration_id)
            if not current_integration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Integration not found",
                )

            # Validate credentials based on provider )
            if current_integration.integration_metadata.integration_provider == IntegrationProvider.POSTGRESQL:
                if credential and not await self.integrations_client.validate_postgres_credentials(credential):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid PostgreSQL credentials",
                    )

            # Create updated integration
            updated_integration = UserIntegration(
                user_id=current_integration.user_id,
                integration_id=current_integration.integration_id,
                integration_metadata=current_integration.integration_metadata,
                # Update fields only if they are provided in the request
                credential=credential if update_data.credential is not None else current_integration.credential,
                expires_at=expires_at if update_data.expires_at is not None else current_integration.expires_at,
                created_at=current_integration.created_at,
                updated_at=datetime.utcnow(),
                settings=settings if update_data.settings is not None else current_integration.settings,
                is_active=is_active if update_data.is_active is not None else current_integration.is_active,
            )

            return await self.integration_repository.update_user_integration(
                user_id, updated_integration
            )
        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            self.logger.error(f"Error updating integration for user {user_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update integration: {str(e)}"
            )

    async def delete_integration(self, user_id: str, integration_id: UUID) -> bool:

        try:
            return await self.integration_repository.delete_user_integration(user_id, integration_id)
        except Exception as e:
            self.logger.error(f"Error deleting integration for user {user_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete integration: {str(e)}"
            )

    async def get_user_integration(self, user_id: str, integration_id: UUID) -> Optional[UserIntegration]:
        """Gets a specific user integration by its ID."""
        integration = await self.integration_repository.get_user_integration(user_id, integration_id)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration with ID {integration_id} not found for user {user_id}"
            )
        return integration

    async def get_user_integration_list(self, user_id: str,
                                        integration_type: Optional[IntegrationType] = None) -> List[UserIntegration]:

        try:
            # Get active integrations
            active_integrations = await self.integration_repository.get_all_active_user_integration(user_id,
                                                                                                    integration_type)
            if integration_type and len(active_integrations) > 0:
                return active_integrations
            elif integration_type:
                return []

            # Get all possible integration types
            all_integration_types = IntegrationType.get_all_integration_types()
            integration_config = IntegrationConfig()

            # make active integrations set for quick lookup
            active_integration_types = {integration.integration_metadata.type for integration in active_integrations}

            # Check if all integration types are present in active integrations

            for integration_type in all_integration_types:
                if integration_type not in active_integration_types:
                    # Create inactive integration placeholder
                    integration_metadata = integration_config.get_integration_metadata(integration_type)
                    active_integrations.append(
                        UserIntegration(
                            user_id=user_id,
                            integration_metadata=integration_metadata,
                            is_active=False,
                        )
                    )

            return active_integrations
        except Exception as e:
            self.logger.error(f"Error fetching integrations for user {user_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get integration list: {str(e)}"
            )

    async def create_integration_sync(self, user_id: str, integration_id: UUID) -> SyncIntegration:
        try:
            # Check if there's any ongoing sync
            last_sync = await self.integration_repository.get_last_sync(
                user_id, integration_id
            )
            if last_sync and last_sync.status in [SyncStatus.STARTED, SyncStatus.PROCESSING]:
                self.logger.warning(
                    f"Sync already in progress for user {user_id} and integration {integration_id}"
                )

                return last_sync

            # Get integration details to associate with the sync
            integration = await self.get_user_integration(user_id, integration_id)
            if not integration:
                # This case should ideally not happen if integration_id is valid
                # but added for robustness
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found, cannot start sync."
                )

            current_time = datetime.utcnow()
            # Create new sync record with the correct integration_id
            sync_integration = SyncIntegration(
                user_id=user_id,
                integration_type=integration.integration_metadata.type,
                status=SyncStatus.STARTED,
                created_at=current_time,
                updated_at=current_time,
                integration_id=integration_id  # Use the passed integration_id
            )

            self.logger.info(f"Creating new sync integration with ID {sync_integration.sync_id} for user {user_id}")

            # Save to repository
            created_sync = await self.integration_repository.create_sync(sync_integration)
            return created_sync
        except Exception as e:
            self.logger.error(f"Error creating sync for user {user_id}: {e!s}")
            raise e



    async def get_integration_sync(self, user_id: str, integration_id: UUID) -> Optional[SyncIntegration]:

        try:
            # Check if the integration itself exists
            integration = await self.get_user_integration(user_id, integration_id)
            if not integration:
                # Handled by get_user_integration raising 404, but keeping explicit check
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found."
                )

            last_sync = await self.integration_repository.get_last_sync(
                user_id, integration_id
            )

            # If no sync exists at all, return 404
            if not last_sync:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No sync found for this integration"
                )

            # For completed syncs, return as is
            if last_sync.status == SyncStatus.COMPLETED:
                return last_sync

            # For other statuses, get last successful sync
            last_successful_sync = await self.integration_repository.get_last_successful_sync(
                user_id, integration_id
            )

            # Update completed_at from last successful sync if it exists
            if last_successful_sync:
                last_sync.completed_at = last_successful_sync.completed_at
            else:
                last_sync.completed_at = None

            return last_sync

        except HTTPException:
            # Re-raise HTTP exceptions directly
            raise
        except Exception as e:
            self.logger.error(
                f"Error fetching sync status for user {user_id}, integration {integration_id}: {e!s}"
            )
            raise e

    async def get_integration_sync_by_id(self, user_id: str, sync_id: UUID) -> Optional[SyncIntegration]:

        return await self.integration_repository.get_sync_by_id(user_id, sync_id)

    async def update_integration_sync_status(self, user_id: str, sync_id: UUID, sync_status: str,
                                             error_message: Optional[str] = None) -> Optional[SyncIntegration]:

        try:
            # Get existing sync
            sync = await self.integration_repository.get_sync_by_id(user_id, sync_id)
            if not sync:
                self.logger.error(f"Sync integration not found: {sync_id}")
                return None

            # Update sync status
            sync.status = SyncStatus(sync_status)
            sync.error_message = error_message

            # Set completed_at if status is terminal (Completed or Failed)
            if sync_status in [SyncStatus.COMPLETED.value, SyncStatus.FAILED.value]:
                sync.completed_at = datetime.utcnow()

            # Update sync in repository
            return await self.integration_repository.update_sync(sync)

        except Exception as e:
            self.logger.error(f"Error updating sync status for sync {sync_id}: {e!s}")
            raise e

    async def get_communication_channels(self, user_id: str) -> list[str]:

        try:
            return [channel.value for channel in CommunicationIntegrations]
        except Exception as e:
            self.logger.error(f"Error getting communication channels for user {user_id}: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get communication channels: {str(e)}"
            )

    async def get_latest_checkpoint_integration(self, user_id: str, integration_id: UUID) -> Optional[str]:
        try:
            return await self.integration_repository.get_latest_checkpoint_integration(user_id, integration_id)
        except Exception as e:
            self.logger.error(f"Error fetching latest checkpoint for user {user_id}: {e!s}")
            raise e

    async def update_latest_checkpoint_integration(self, user_id: str, integration_id: UUID, checkpoint: str) -> bool:
        try:
            return await self.integration_repository.update_latest_checkpoint_integration(user_id, integration_id, checkpoint)
        except Exception as e:
            self.logger.error(f"Error updating latest checkpoint for user {user_id}: {e!s}")
            raise e
