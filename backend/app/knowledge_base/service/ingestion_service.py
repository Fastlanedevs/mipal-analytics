import uuid
from datetime import datetime, timezone
from uuid import UUID
from app.knowledge_base.service.service import (IKnowledgeIngestionService, ILLMAdapter, IKnowledgeBaseRepository,
                                                 IIntegrationAdapter)


from app.analytics.service.postgres_service import PostgresService, CreatePostgresDatabaseRequestDTO
from pkg.log.logger import Logger
from app.knowledge_base.entity.entity import ( UserDocument, UserIntegration, SyncIntegration,
                                              IntegrationType, ProcessingStatus, DocumentStatus)

from app.integrations.entity.value_object import SyncStatus


class KnowledgeIngestionService(IKnowledgeIngestionService):
    """Enhanced knowledge ingestion service with  technique support"""


    def __init__(self, logger: Logger, repository: IKnowledgeBaseRepository, integration_adapter: IIntegrationAdapter,
                 llm_adapter: ILLMAdapter, postgres_service: PostgresService, process_document_service: ProcessDocumentService):

        self.IMAGE_SIZE_LIMIT = 5 * 1024 * 1024  # 5MB limit for images

        self.logger: Logger = logger
        self.repository: IKnowledgeBaseRepository = repository
        self.integration_adapter: IIntegrationAdapter = integration_adapter
        self.llm_adapter: ILLMAdapter = llm_adapter
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

    async def process_gsuite_integration(self, user_id: str, sync_id: UUID, integration: UserIntegration) -> None:
        """Process Google Suite integration with incremental sync and failure retry."""
        self.logger.info("Processing GSuite integration", extra={"user_id": user_id, "sync_id": str(sync_id),
                                                                 "integration_id": str(integration.integration_id)})
        try:
            # 1. Prepare OAuth Token
            try:
                oauth_token = self.gsuite_adapter.make_oauth_token(integration.credential)
            except Exception as e:
                self.logger.error(f"Failed to prepare GSuite credential: {e}", exc_info=True)
                # Mark sync as failed if token creation fails
                await self.integration_adapter.update_sync_status(user_id, sync_id, SyncStatus.FAILED.value, f"Credential error: {e}")
                return  # Stop processing if token fails

            # 2. Get all files from Google Drive
            all_files = await self.gsuite_adapter.get_all_documents(oauth_token, modified_after=None)
            self.logger.info(f"Found {len(all_files)} files in Google Drive", extra={"user_id": user_id, "file_count": len(all_files)})
            all_files = all_files
            # 3. Process each file based on its type
            processed_count = 0
            failed_count = 0

            for file in all_files:
                try:
                    # print(file)
                    if file.mime_type in self.DOCUMENT_TYPES:
                        existing_doc = await self.repository.get_document_by_original_id(
                            user_id=user_id,
                            original_file_id=file.id,
                        )

                        if existing_doc:
                            if existing_doc.processing_status == ProcessingStatus.SUCCESS:
                                self.logger.info(f"Skipping already processed document: {file.name} (ID: {file.id})",
                                                 extra={"user_id": user_id, "file_id": file.id})
                                continue # Skip to the next file

                            elif existing_doc.processing_status == ProcessingStatus.FAILED or \
                                 existing_doc.processing_status == ProcessingStatus.PROCESSING:
                                
                                self.logger.info(f"Retrying document: {file.name} (ID: {file.id}), Current ProcessingStatus: {existing_doc.processing_status}, DocumentStatus: {existing_doc.status}",
                                                 extra={"user_id": user_id, "file_id": file.id})

                                # Reset status for retry and clear error if it was FAILED
                                if existing_doc.processing_status == ProcessingStatus.FAILED:
                                    existing_doc.error = None
                                existing_doc.processing_status = ProcessingStatus.PROCESSING # Set to PROCESSING for the attempt
                                # Persist this change immediately so _process_document sees the correct state
                                await self.repository.update_document(existing_doc)
                                
                                if existing_doc.status == DocumentStatus.META_DATA_FETCHED:
                                    try:
                                        extracted_content = await self.gsuite_adapter.extract_document_content(oauth_token, file)
                                        doc_content = extracted_content.extracted_text if hasattr(extracted_content, 'extracted_text') else str(extracted_content.raw_content)
                                        doc_content = doc_content.replace('\x00', '')

                                        existing_doc.content = doc_content
                                        existing_doc.status = DocumentStatus.CONTENT_FETCHED
                                        # processing_status is already PROCESSING due to the update above
                                        await self.repository.update_document(existing_doc)
                                        
                                        await self._process_document(user_id, doc_content, file, existing_doc)
                                        processed_count += 1
                                    except Exception as e:
                                        self.logger.error(f"Failed to reprocess document content for {file.name} during retry: {e}", exc_info=True)
                                        existing_doc.processing_status = ProcessingStatus.FAILED
                                        existing_doc.error = str(e)
                                        await self.repository.update_document(existing_doc)
                                        failed_count += 1
                                    continue # Whether success or failure in this try-except, continue to the next file
                                elif existing_doc.status == DocumentStatus.CONTENT_FETCHED:
                                    try:
                                        # Content already fetched, just reprocess
                                        # processing_status should already be PROCESSING from the update above
                                        await self._process_document(user_id, existing_doc.content, file, existing_doc)
                                        processed_count += 1
                                    except Exception as e:
                                        self.logger.error(f"Failed to reprocess document {file.name} during retry: {e}", exc_info=True)
                                        existing_doc.processing_status = ProcessingStatus.FAILED
                                        existing_doc.error = str(e)
                                        await self.repository.update_document(existing_doc)
                                        failed_count += 1
                                    continue # Whether success or failure in this try-except, continue to the next file
                                elif existing_doc.status  == DocumentStatus.CHUNKING_SUCCEEDED:
                                    # Document was chunked but entity extraction (or later steps in _process_document) failed, retrying that part.
                                    self.logger.info(f"Retrying document {file.name} (ID: {file.id}) from CHUNKING_SUCCEEDED state.")
                                    # Ensure processing_status is PROCESSING and error is cleared (already done by the parent if block, but good for clarity)
                                    # existing_doc.processing_status = ProcessingStatus.PROCESSING 
                                    # existing_doc.error = None
                                    # await self.repository.update_document(existing_doc) # Already updated before this if/elif cascade
                                    try:
                                        # Content must exist if chunking succeeded.
                                        # _process_document will attempt to re-process from where it likely failed (entity extraction onwards).
                                        if not existing_doc.content:
                                            self.logger.error(f"Content missing for document {file.name} (ID: {file.id}) in CHUNKING_SUCCEEDED state. Cannot retry. Marking FAILED.")
                                            existing_doc.processing_status = ProcessingStatus.FAILED
                                            existing_doc.error = "Content missing for retry from CHUNKING_SUCCEEDED state"
                                        else:
                                            await self._process_document(user_id, existing_doc.content, file, existing_doc)
                                            processed_count += 1 # Assumes _process_document updates status to SUCCESS if fully completed
                                    except Exception as e:
                                        self.logger.error(f"Failed to reprocess document {file.name} from CHUNKING_SUCCEEDED state: {e}", exc_info=True)
                                        existing_doc.processing_status = ProcessingStatus.FAILED
                                        existing_doc.error = str(e)
                                    # Update the document regardless of _process_document outcome, as its status might have changed internally
                                    await self.repository.update_document(existing_doc)
                                    if existing_doc.processing_status == ProcessingStatus.FAILED:
                                         failed_count +=1
                                    continue # Important: continue to next file after attempt
                                else:
                                    # Document was FAILED/PROCESSING, but status is not META_DATA_FETCHED or CONTENT_FETCHED or CHUNKING_SUCCEEDED.
                                    # This is an unexpected state for standard retry. Log and mark as FAILED.
                                    self.logger.warning(f"Document {file.name} (ID: {file.id}) has an unexpected status ({existing_doc.status}) for FAILED/PROCESSING retry. Marking as FAILED.")
                                    existing_doc.processing_status = ProcessingStatus.FAILED
                                    existing_doc.error = existing_doc.error or f"Unexpected status for retry: {existing_doc.status}"
                                    await self.repository.update_document(existing_doc)
                                    failed_count += 1
                                    continue # Ensure we skip to next file.
                            
                            else: # existing_doc found, but status is not SUCCESS, FAILED, or PROCESSING
                                self.logger.warning(f"Document {file.name} (ID: {file.id}) exists with unhandled processing status: {existing_doc.processing_status}. Skipping.")
                                continue # Critical: skip to next file to prevent duplicate creation

                        else: # existing_doc is None. Create a new document.
                            # Create document metadata in database
                            doc = UserDocument(
                                id=uuid.uuid4(),
                                user_id=user_id,
                                address=file.web_view_link,
                                original_file_id=file.id,
                                source_type="GOOGLE_DRIVE",
                                integration_id=integration.integration_id,
                                file_name=file.name,
                                file_type=file.mime_type,
                                size=file.size,
                                created_at=file.created_time,
                                updated_at=file.modified_time,
                                status=DocumentStatus.META_DATA_FETCHED,
                                processing_status=ProcessingStatus.PROCESSING,
                                error=None,
                            )

                            await self.repository.create_document(doc)
                            
                            try:
                                # Extract document content
                                extracted_content = await self.gsuite_adapter.extract_document_content(oauth_token, file)
                                # print("extracted_content:", extracted_content)
                                doc_content = extracted_content.extracted_text if hasattr(extracted_content, 'extracted_text') else str(extracted_content.raw_content)
                                doc_content = doc_content.replace('\x00', '') # Remove null bytes
                                
                                doc.status = DocumentStatus.CONTENT_FETCHED
                                doc.content = doc_content
                                await self.repository.update_document(doc)
                                
                                # Process document (chunking and entity extraction)
                                await self._process_document(user_id, doc_content, file, doc)
                                processed_count += 1
                                
                            except Exception as e:
                                self.logger.error(f"Failed to extract/process document content for {file.name}: {e}", exc_info=True)
                                doc.processing_status = ProcessingStatus.FAILED
                                doc.error = str(e)
                                await self.repository.update_document(doc)
                                failed_count += 1
                                continue # Continue to the next file if processing of new doc fails

                    elif file.mime_type in self.SPREADSHEET_TYPES:
                        # Process spreadsheet (placeholder for now)
                        await self._process_spreadsheet(user_id, file)
                        
                    elif file.mime_type in self.IMAGE_TYPES:
                        # Process image (placeholder for now)
                        await self._process_image(user_id, file)
                        
                    else:
                        self.logger.debug(f"Skipping unsupported file type: {file.mime_type} for file {file.name}")

                except Exception as e:
                    self.logger.error(f"Failed to process file {file.name}: {e}", exc_info=True)
                    failed_count += 1
                    continue

            self.logger.info(f"GSuite integration processing completed", extra={
                "user_id": user_id,
                "sync_id": str(sync_id),
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_files": len(all_files)
            })

        except Exception as e:
            self.logger.error(f"Unhandled error during GSuite integration processing: {e}", exc_info=True,
                              extra={"user_id": user_id, "sync_id": str(sync_id)})
            # Re-raise to be caught by the main sync_integration handler, which will mark sync as FAILED
            raise e


    async def _process_document(self, user_id: str, text_content: str, file: GoogleFileMetadata, doc: UserDocument) -> None:
        try:
            self.logger.info(f"Starting document processing for {doc.id} ({file.name})")
            
            chunking_status, entity_status = await self.process_document_service.process_document(
                user_id, doc.id, text_content, self.MAX_TOKENS, self.OVERLAP_TOKENS
            )
            
            self.logger.info(f"Document processing completed for {doc.id}: chunking={chunking_status}, entities={entity_status}")
            
            if chunking_status and entity_status:
                doc.status = DocumentStatus.COMPLETED
                doc.processing_status = ProcessingStatus.SUCCESS
                self.logger.info(f"Document {doc.id} fully processed successfully")
            elif chunking_status:
                doc.status = DocumentStatus.CHUNKING_SUCCEEDED
                doc.processing_status = ProcessingStatus.FAILED
                self.logger.info(f"Document {doc.id} chunking succeeded, but entity extraction failed")
            else:
                doc.status = DocumentStatus.CONTENT_FETCHED
                doc.processing_status = ProcessingStatus.FAILED
                doc.error = "Failed to process document chunks"
                self.logger.warning(f"Document {doc.id} processing failed at chunking stage")
                
        except Exception as e:
            self.logger.error(f"Failed to process document {doc.id}: {e}", exc_info=True)
            doc.status = DocumentStatus.CONTENT_FETCHED
            doc.processing_status = ProcessingStatus.FAILED
            doc.error = str(e)
        
        self.logger.info(f"Updating document {doc.id} with final status: {doc.status}, processing_status: {doc.processing_status}")
        await self.repository.update_document(doc)
        return None

    async def _process_spreadsheet(self, user_id: str, file: GoogleFileMetadata) -> None:
        """Process spreadsheet files - placeholder implementation"""
        pass
       

    async def _process_image(self, user_id: str, file: GoogleFileMetadata) -> None:
        """Process image files - placeholder implementation"""
        pass


