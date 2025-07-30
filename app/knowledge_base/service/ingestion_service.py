import uuid
from datetime import datetime, timezone
from uuid import UUID
from app.knowledge_base.service.service import (IKnowledgeIngestionService, ILLMAdapter, IKnowledgeBaseRepository,
                                                IGSuiteAdapter, IIntegrationAdapter)
from app.knowledge_base.service.process_document import ProcessDocumentService

from app.analytics.service.postgres_service import PostgresService, CreatePostgresDatabaseRequestDTO
from pkg.log.logger import Logger
from app.knowledge_base.entity.entity import ( UserDocument, UserIntegration, SyncIntegration,
                                              IntegrationType, ProcessingStatus, DocumentStatus)
from app.knowledge_base.entity.gsuite_entity import GoogleFileMetadata

from app.integrations.entity.value_object import SyncStatus


class KnowledgeIngestionService(IKnowledgeIngestionService):
    """Enhanced knowledge ingestion service with LightRAG technique support"""


    def __init__(self, logger: Logger, repository: IKnowledgeBaseRepository, integration_adapter: IIntegrationAdapter,
                  postgres_service: PostgresService):

        self.IMAGE_SIZE_LIMIT = 5 * 1024 * 1024  # 5MB limit for images

        self.logger: Logger = logger
        self.repository: IKnowledgeBaseRepository = repository
        self.integration_adapter: IIntegrationAdapter = integration_adapter
        self.postgres_service: PostgresService = postgres_service
        self.logger.info("Initializing Knowledge Ingestion Service")




    async def sync_integration(self, user_id: str, sync_id: UUID) -> None:
        """
        Synchronize integration data from external sources.
        This is the main entry point for importing documents from integrations.

        """
        sync_start_time: datetime = datetime.now(timezone.utc)
        self.logger.info("Starting integration sync", extra={"user_id": user_id, "sync_id": str(sync_id),
                                                             "start_time": sync_start_time, })
        try:
            # Try to get the sync integration, but handle missing case
            try:
                integration_sync: SyncIntegration = await self.integration_adapter.get_sync_integration(user_id, sync_id)
            except ValueError as e:
                # Sync doesn't exist, log error and exit gracefully
                self.logger.error(f"Sync integration not found: {e}")
                return
                
            # Get integration details
            user_integration: UserIntegration = await self.integration_adapter.get_integration(user_id,
                                                                                               integration_sync.integration_id)


            # Check integration status
            if integration_sync.status == "COMPLETED":
                self.logger.info("Integration sync already completed", extra={"user_id": user_id, "sync_id": sync_id})
                return
            elif integration_sync.status == "FAILED":
                self.logger.info("Integration sync failed previously, starting again",
                                 extra={"user_id": user_id, "sync_id": sync_id})

                await self.integration_adapter.update_sync_status(user_id, sync_id, SyncStatus.PROCESSING.value)
            elif integration_sync.status == "PROCESSING":
                self.logger.info("Integration sync already in progress, continuing",
                                 extra={"user_id": user_id, "sync_id": sync_id})
            # Process integration based on its type
            if user_integration.integration_type == IntegrationType.POSTGRESQL:
                await self.process_postgres_integration(user_id, sync_id, user_integration)
            else:
                self.logger.info(f"{user_integration.integration_type} integration sync not implemented yet")
                await self.integration_adapter.update_sync_status(user_id, sync_id, SyncStatus.COMPLETED.value)
                return

            self.logger.info("Sync completed successfully", extra={"user_id": user_id, "sync_id": sync_id})
            await self.integration_adapter.update_sync_status(user_id, sync_id, SyncStatus.COMPLETED.value)
            return

        except Exception as e:
            self.logger.error("Sync failed" + str(e))
            await self.integration_adapter.update_sync_status(user_id, sync_id, SyncStatus.FAILED.value, str(e))
            raise e

    async def process_postgres_integration(self, user_id: str, sync_id: UUID, integration: UserIntegration) -> None:
        """Process PostgreSQL integration"""
        try:
            # Create database in analytics module
            self.logger.info("Making request to postgres service")
            # Map integration credentials to PostgreSQL request
            request = CreatePostgresDatabaseRequestDTO(
                database_name=integration.credential.get('database_name'),
                host=integration.credential.get('host'),
                port=integration.credential.get('port', 5432),
                user=integration.credential.get('username'),
                password=integration.credential.get('password') or '',
                description=integration.credential.get('description') or '',
                user_id=user_id,
                integration_id=str(integration.integration_id)
            )

            database = await self.postgres_service.create_database(request)
            self.logger.info(f"Database created: {database}")

            return

        except Exception as e:
            self.logger.error(
                f"Failed to process PostgreSQL integration: {e}",
                extra={"error": str(e), "user_id": user_id, "sync_id": str(sync_id)},
            )
            raise e



