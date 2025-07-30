import asyncio
import json
import time
import traceback
from typing import Any, Dict, Optional
from uuid import UUID

from app.integrations.entity.entity import SyncIntegrationEvent
from app.knowledge_base.service.service import IKnowledgeIngestionService
from pkg.log.logger import Logger


class KnowledgeBaseEventHandler:
    def __init__(self, service: IKnowledgeIngestionService, logger: Logger, worker=None,  max_retries: int = 3,
            enable_detailed_logging: bool = True):
        self.service = service
        self.logger = logger
        self.worker = worker
        self.max_retries = max_retries
        self.enable_detailed_logging = enable_detailed_logging

        # Performance tracking
        self.processing_times = []
        self.max_processing_time = 0
        self.total_processed = 0
        self.total_errors = 0

        # Semaphore to limit concurrent service calls if needed
        self._service_semaphore = asyncio.Semaphore(20)  # Adjust based on service capacity

    async def handle_integration_document_sync(self, message: Dict[str, Any]) -> None:
        """
        Handle document sync events from the queue

        Args:
            message: The message payload containing sync information
        """
        message_id = message.get("message_id", "unknown")
        start_time = time.time()

        if self.enable_detailed_logging:
            self.logger.info(f"Received message in handler (ID: {message_id})")

        # Update worker metrics if available
        if self.worker:
            self.worker.update_activity()

        try:
            # Perform schema validation
            await self._validate_message(message)

            # Extract data from the message
            user_id = message["user_id"]
            sync_id = UUID(message.get("sync_id"))
            retry_count = message.get("retry_count", 0)

            if retry_count >= self.max_retries:
                self.logger.warning(
                    f"Message exceeded retry limit: user_id={user_id}, sync_id={sync_id}, "
                    f"retries={retry_count}/{self.max_retries}"
                )
                # We could choose to still process but log, or skip processing
                # Here we continue with processing but with a warning

            # Check if this is a high priority message
            is_priority = message.get("priority", "normal") == "high"
            log_prefix = "[PRIORITY] " if is_priority else ""

            # Log processing start
            self.logger.info(
                f"{log_prefix}Processing document sync for user_id={user_id}, sync_id={sync_id}"
            )

            # Use semaphore to prevent overwhelming the service with too many concurrent calls
            async with self._service_semaphore:
                # Run the document service synchronization with timeout protection
                try:
                    # We could add a timeout here if needed
                    await self.service.sync_integration(user_id, sync_id)
                except asyncio.TimeoutError:
                    self.logger.error(f"Service timeout for user_id={user_id}, sync_id={sync_id}")
                    raise

            # Track successful completion
            self.total_processed += 1
            process_time = time.time() - start_time
            self.processing_times.append(process_time)
            self.max_processing_time = max(self.max_processing_time, process_time)

            # Log successful completion
            self.logger.info(
                f"Successfully processed document sync for user_id={user_id} in {process_time:.2f}s"
            )

            # Periodically log performance metrics
            if self.total_processed % 100 == 0:
                self._log_performance_metrics()

        except ValidationError as ve:
            # Validation errors shouldn't trigger retries - log and return
            self.logger.error(f"Validation error in message {message_id}: {ve}")
            if self.worker:
                self.worker.error_count += 1
            return

        except Exception as e:
            # Track error
            self.total_errors += 1
            if self.worker:
                self.worker.error_count += 1

            # Enhanced error reporting
            error_msg = f"Error handling document sync message: {e!s}"
            if self.enable_detailed_logging:
                error_msg += f"\nMessage: {json.dumps(message)}"
                error_msg += f"\nStack trace: {traceback.format_exc()}"

            self.logger.error(error_msg)

            # Re-raise to trigger SQS retry
            raise

        finally:
            # Always log the total processing time for monitoring
            if self.enable_detailed_logging:
                total_time = time.time() - start_time
                self.logger.debug(f"Message {message_id} processing took {total_time:.3f}s")

    async def _validate_message(self, message: Dict[str, Any]) -> None:
        """
        Validate message schema and required fields

        Args:
            message: The message to validate

        Raises:
            ValidationError: If the message fails validation
        """
        if not isinstance(message, dict):
            raise ValidationError(f"Expected dictionary, got {type(message).__name__}")

        # Check required fields
        required_fields = ["user_id", "sync_id"]
        for field in required_fields:
            if field not in message:
                raise ValidationError(f"Missing required field '{field}'")

        # Validate field types
        if not isinstance(message.get("user_id"), str):
            raise ValidationError("Field 'user_id' must be a string")

        # Validate UUID format for sync_id
        sync_id = message.get("sync_id")
        try:
            UUID(sync_id)
        except (ValueError, AttributeError, TypeError):
            raise ValidationError(f"Invalid sync_id format: {sync_id}")

        # Additional validations can be added here as needed

    def _log_performance_metrics(self):
        """Log handler performance metrics"""
        if not self.processing_times:
            return

        avg_time = sum(self.processing_times) / len(self.processing_times)
        self.processing_times = self.processing_times[-100:]  # Keep only last 100 for rolling average

        self.logger.info(
            f"Handler performance: avg={avg_time:.2f}s, max={self.max_processing_time:.2f}s, "
            f"processed={self.total_processed}, errors={self.total_errors}"
        )


class ValidationError(Exception):
    """Exception raised for message validation errors"""
    pass