import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, Dict, List, Optional, Set

from pkg.log.logger import Logger
from pkg.sqs.client import SQSClient


class Subscriber:
    def __init__(
            self,
            sqs_client: SQSClient,
            logger: Logger,
            batch_size: int = 10,
            wait_time: int = 20,
            max_concurrent_tasks: int = 50,
            visibility_timeout: int = 300,
            visibility_timeout_buffer: int = 30,
            visibility_extension_interval: int = 60,
            max_retries: int = 3,
            backoff_min: float = 0.1,
            backoff_max: float = 10.0,
            backoff_factor: float = 1.5,
    ):
        """
        Initialize a subscriber for SQS message processing

        Args:
            sqs_client: The SQS client for queue operations
            logger: Logger for subscriber events
            batch_size: Maximum number of messages to receive at once
            wait_time: SQS long polling wait time in seconds
            max_concurrent_tasks: Maximum number of concurrent processing tasks
            visibility_timeout: Default message visibility timeout
            visibility_timeout_buffer: Buffer for visibility extension
            visibility_extension_interval: How often to extend message visibility
            max_retries: Maximum number of retry attempts for a message
            backoff_min: Minimum backoff time for empty polls (seconds)
            backoff_max: Maximum backoff time for empty polls (seconds)
            backoff_factor: Exponential backoff multiplier
        """
        self.sqs_client = sqs_client
        self.logger = logger
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.visibility_timeout = visibility_timeout
        self.visibility_timeout_buffer = visibility_timeout_buffer
        self.visibility_extension_interval = visibility_extension_interval
        self.max_retries = max_retries

        # Backoff strategy for empty polls
        self.backoff_min = backoff_min
        self.backoff_max = backoff_max
        self.backoff_factor = backoff_factor
        self._current_backoff = backoff_min

        # Concurrency control
        self.max_concurrent_tasks = max_concurrent_tasks
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)

        # Performance metrics
        self.message_count = 0
        self.error_count = 0
        self.last_metrics_time = time.time()
        self.processed_messages = 0
        self.processing_times = []

        # Runtime state
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        self.active_message_tasks: Dict[str, asyncio.Task] = {}
        self.extension_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    async def start(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Start processing messages

        Args:
            handler: Async callback function to handle each message
        """
        if self.running:
            self.logger.warning("Subscriber is already running")
            return

        self.running = True
        self._shutdown_event.clear()
        self.last_metrics_time = time.time()

        # Start the main processing loop
        self.processing_task = asyncio.create_task(
            self._process_messages_loop(handler),
            name="sqs_processing_loop"
        )

        # Start metrics reporting
        self.metrics_task = asyncio.create_task(
            self._report_metrics_periodically(),
            name="metrics_reporting"
        )

        self.logger.info(f"Started subscriber for queue: {self.sqs_client.queue_name}")

    async def stop(self, timeout: int = 30):
        """
        Stop processing messages and wait for active tasks to complete

        Args:
            timeout: Maximum time to wait for active tasks to complete
        """
        if not self.running:
            self.logger.info("Subscriber is not running")
            return

        # Signal shutdown
        self.logger.info("Stopping subscriber...")
        self.running = False
        self._shutdown_event.set()

        # Cancel the main processing and metrics tasks
        for task_name, task in [
            ("processing", self.processing_task),
            ("metrics", self.metrics_task)
        ]:
            if task and not task.done():
                self.logger.debug(f"Cancelling {task_name} task")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.error(f"Error cancelling {task_name} task: {e!s}")

        self.processing_task = None
        self.metrics_task = None

        # Wait for active message tasks with timeout
        if self.active_message_tasks:
            task_count = len(self.active_message_tasks)
            self.logger.info(f"Waiting for {task_count} active tasks to complete (max {timeout}s)")

            try:
                # Wait for tasks with timeout
                active_tasks = list(self.active_message_tasks.values())
                done, pending = await asyncio.wait(
                    active_tasks,
                    timeout=timeout,
                    return_when=asyncio.ALL_COMPLETED
                )

                # Cancel any remaining tasks
                if pending:
                    self.logger.warning(f"Forcibly cancelling {len(pending)} tasks that didn't complete")
                    for task in pending:
                        task.cancel()

                    # Wait for cancellations to process
                    await asyncio.gather(*pending, return_exceptions=True)
            except Exception as e:
                self.logger.error(f"Error waiting for tasks to complete: {e!s}")

        # Cancel all visibility extension tasks
        for message_id, task in list(self.extension_tasks.items()):
            if not task.done():
                self.logger.debug(f"Cancelling visibility extension task for message {message_id}")
                task.cancel()

        # Wait for all extension tasks to complete
        if self.extension_tasks:
            try:
                extension_tasks = list(self.extension_tasks.values())
                await asyncio.gather(*extension_tasks, return_exceptions=True)
            except Exception as e:
                self.logger.error(f"Error cancelling extension tasks: {e!s}")

        # Clear all task tracking
        self.active_message_tasks.clear()
        self.extension_tasks.clear()

        self.logger.info("Subscriber stopped")

    async def _process_messages_loop(
            self, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Main loop for receiving and processing messages

        Args:
            handler: Async callback function to handle each message
        """
        # Reset backoff on starting
        self._current_backoff = self.backoff_min

        while self.running:
            try:
                # Calculate available capacity for new messages
                available_capacity = self.max_concurrent_tasks - len(self.active_message_tasks)

                if available_capacity <= 0:
                    # No capacity - wait briefly
                    await asyncio.sleep(0.01)
                    continue

                # Calculate batch size - dynamically adjust based on capacity
                messages_to_request = min(self.batch_size, available_capacity)

                # Receive messages
                messages = await self.sqs_client.receive_messages(
                    max_messages=messages_to_request,
                    wait_time=self.wait_time,
                    visibility_timeout=self.visibility_timeout
                )

                # Apply adaptive backoff for empty polls
                if not messages:
                    await asyncio.sleep(self._current_backoff)
                    # Increase backoff time exponentially with jitter
                    jitter = self._current_backoff * 0.1 * (0.5 - (time.time() % 1.0))
                    self._current_backoff = min(
                        self._current_backoff * self.backoff_factor + jitter,
                        self.backoff_max
                    )
                    continue
                else:
                    # Reset backoff on successful message receipt
                    self._current_backoff = self.backoff_min
                    self.logger.debug(f"Received {len(messages)} messages")

                # Process all messages in parallel
                await self._process_message_batch(messages, handler)

            except asyncio.CancelledError:
                # Normal cancellation
                self.logger.info("Message processing loop cancelled")
                break

            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e!s}")
                self.error_count += 1
                # Brief sleep to avoid tight loop in case of persistent errors
                await asyncio.sleep(1)

    async def _process_message_batch(
            self,
            messages: List[Dict[str, Any]],
            handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Process a batch of messages in parallel

        Args:
            messages: List of SQS messages from aioboto3
            handler: Async callback function to handle the message body
        """
        # Create tasks for all messages
        for message in messages:
            if not self.running:
                break

            # Skip messages without a receipt handle
            if 'ReceiptHandle' not in message:
                self.logger.warning(f"Skipping message without receipt handle: {message.get('MessageId', 'unknown')}")
                continue

            # Create task and track it
            message_id = message.get('MessageId', f"msg-{id(message)}")

            task = asyncio.create_task(
                self._process_single_message(message, handler),
                name=f"process-{message_id}"
            )

            # Track the task
            self.active_message_tasks[message_id] = task

            # Set cleanup callback
            task.add_done_callback(
                lambda t, mid=message_id: self._cleanup_message_task(mid, t)
            )

            # Increment message counter for metrics
            self.message_count += 1

    def _cleanup_message_task(self, message_id: str, task: asyncio.Task):
        """
        Clean up a completed message task

        Args:
            message_id: ID of the message
            task: The completed task
        """
        # Remove from active tasks dict
        self.active_message_tasks.pop(message_id, None)

        # Check for exceptions
        if not task.cancelled() and task.exception():
            self.logger.error(f"Message task {message_id} failed with exception: {task.exception()!s}")
            self.error_count += 1

    async def _process_single_message(
            self, message: Dict[str, Any], handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Process a single message with retry logic and concurrency control

        Args:
            message: The SQS message (dict) from aioboto3
            handler: Async callback function to handle the message body
        """
        # Extract message details
        message_id = message.get('MessageId', 'unknown')
        receipt_handle = message.get('ReceiptHandle')
        start_time = time.time()

        if not receipt_handle:
            self.logger.error(f"Message {message_id} missing receipt handle")
            return

        # Start the visibility extension task
        extension_task = asyncio.create_task(
            self._extend_visibility_timeout_periodically(message_id, receipt_handle),
            name=f"visibility-{message_id}"
        )
        self.extension_tasks[message_id] = extension_task

        # Apply concurrency control with semaphore
        async with self._semaphore:
            try:
                # Parse message body
                try:
                    message_body = json.loads(message.get('Body', '{}'))
                except (json.JSONDecodeError, AttributeError) as e:
                    self.logger.error(f"Failed to parse message {message_id}: {e!s}")
                    # Delete malformed messages to avoid poison pills
                    await self.sqs_client.delete_message(receipt_handle)
                    return

                # Get retry count from message attributes
                retry_count = 0
                if 'Attributes' in message and 'ApproximateReceiveCount' in message['Attributes']:
                    try:
                        retry_count = int(message['Attributes']['ApproximateReceiveCount']) - 1
                    except (ValueError, TypeError):
                        pass

                self.logger.debug(f"Processing message: {message_id} (attempt {retry_count + 1})")

                # Check if max retries exceeded
                if retry_count >= self.max_retries:
                    self.logger.warning(
                        f"Message {message_id} exceeded max retries ({self.max_retries}), sending to DLQ or deleting"
                    )
                    # Either send to DLQ or delete to prevent infinite retries
                    await self.sqs_client.delete_message(receipt_handle)
                    return

                # Process the message
                try:
                    # Add message_id to the message body for tracing if it doesn't exist
                    if isinstance(message_body, dict) and 'message_id' not in message_body:
                        message_body['message_id'] = message_id

                    # Call the handler
                    await handler(message_body)

                    # Track successful processing
                    self.processed_messages += 1
                    process_time = time.time() - start_time
                    self.processing_times.append(process_time)
                    # Keep only the last 100 times for rolling average
                    if len(self.processing_times) > 100:
                        self.processing_times = self.processing_times[-100:]

                    # Delete the message after successful processing
                    delete_result = await self.sqs_client.delete_message(receipt_handle)
                    if delete_result:
                        self.logger.info(
                            f"Successfully processed and deleted message: {message_id} in {process_time:.3f}s")
                    else:
                        self.logger.warning(f"Failed to delete message {message_id} after processing")

                except Exception as e:
                    self.logger.error(f"Error processing message {message_id} (attempt {retry_count + 1}): {e!s}")
                    self.error_count += 1
                    # Don't delete on error - let the message return to the queue with backoff

            except asyncio.CancelledError:
                self.logger.info(f"Message processing cancelled for {message_id}")
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error processing message {message_id}: {e!s}")
                self.error_count += 1

            finally:
                # Always clean up the extension task
                if extension_task and not extension_task.done():
                    extension_task.cancel()
                    try:
                        await extension_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        self.logger.error(f"Error cancelling extension task for {message_id}: {e!s}")

                # Remove from tracking
                self.extension_tasks.pop(message_id, None)

    async def _extend_visibility_timeout_periodically(self, message_id: str, receipt_handle: str):
        """
        Periodically extend the visibility timeout of a message while it's being processed

        Args:
            message_id: The ID of the message
            receipt_handle: The receipt handle of the message
        """
        interval = self.visibility_extension_interval

        try:
            while self.running:
                # Sleep first to allow quick processing without extra extensions
                await asyncio.sleep(interval)

                # Check if we should exit
                if not self.running:
                    break

                # Extend timeout
                self.logger.debug(f"Extending visibility timeout for message {message_id}")

                try:
                    await self.sqs_client.change_message_visibility(
                        receipt_handle=receipt_handle,
                        visibility_timeout=self.visibility_timeout
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to extend visibility timeout for message {message_id}: {e!s}")
                    # Continue trying even if an extension fails

        except asyncio.CancelledError:
            # Normal cancellation when message is complete
            pass

        except Exception as e:
            self.logger.error(f"Error in visibility timeout extension for {message_id}: {e!s}")

    async def _report_metrics_periodically(self, interval: int = 60):
        """
        Report performance metrics periodically

        Args:
            interval: How often to report metrics in seconds
        """
        try:
            while self.running:
                await asyncio.sleep(interval)

                if not self.running:
                    break

                now = time.time()
                elapsed = now - self.last_metrics_time

                if elapsed > 0:
                    msg_rate = self.message_count / elapsed
                    active_tasks = len(self.active_message_tasks)
                    avg_processing_time = 0

                    if self.processing_times:
                        avg_processing_time = sum(self.processing_times) / len(self.processing_times)

                    self.logger.info(
                        f"Performance: {msg_rate:.2f} msgs/sec, {self.processed_messages} processed, "
                        f"{self.error_count} errors, {active_tasks}/{self.max_concurrent_tasks} active, "
                        f"avg_time={avg_processing_time:.3f}s"
                    )

                    # Reset counters
                    self.message_count = 0
                    self.last_metrics_time = now

        except asyncio.CancelledError:
            self.logger.debug("Metrics reporting cancelled")

        except Exception as e:
            self.logger.error(f"Error reporting metrics: {e!s}")