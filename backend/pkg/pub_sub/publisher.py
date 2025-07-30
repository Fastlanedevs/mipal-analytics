import asyncio
import time
from functools import wraps
from typing import Any, Dict, List, Optional

from pkg.log.logger import Logger
from pkg.sqs.client import SQSClient


def retry_operation(retries=3, base_delay=0.1, max_delay=1.0):
    """
    Retry decorator for publisher operations
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == retries - 1:
                        # On last attempt, re-raise the exception
                        raise

                    # Calculate backoff with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * 0.2 * (0.5 - (time.time() % 1.0))
                    backoff = delay + jitter

                    # Log the retry attempt
                    instance = args[0]  # 'self' is the first argument
                    if hasattr(instance, 'logger'):
                        instance.logger.warning(
                            f"Attempt {attempt + 1} failed: {e!s}. Retrying in {backoff:.2f}s"
                        )

                    await asyncio.sleep(backoff)

            # Should never reach here, but just in case
            raise last_exception if last_exception else RuntimeError("Unknown retry error")

        return wrapper

    return decorator


class Publisher:
    def __init__(
            self,
            sqs_client: SQSClient,
            logger: Logger,
            batch_size: int = 10,
            flush_interval: int = 5,
            enable_retries: bool = True,
            retry_count: int = 3,
    ):
        """
        Initialize a publisher for SQS message publishing

        Args:
            sqs_client: The SQS client for queue operations
            logger: Logger for publisher events
            batch_size: Maximum number of messages to send in a batch
            flush_interval: How often to automatically flush the message buffer
            enable_retries: Whether to enable automatic retries
            retry_count: Number of times to retry failed operations
        """
        self.sqs_client = sqs_client
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.logger = logger
        self.enable_retries = enable_retries
        self.retry_count = retry_count

        # Lock to prevent concurrent batch sends
        self._lock = asyncio.Lock()

        # Performance metrics
        self.total_published = 0
        self.total_failed = 0
        self.last_metrics_time = time.time()
        self.publish_times = []  # Store recent publish times for average calculation

        # Optional buffer for async batching
        self._message_buffer = []
        self._flush_task = None
        self._shutdown_event = asyncio.Event()

    @retry_operation(retries=3)
    async def publish(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a single message immediately

        Args:
            message: The message payload to publish

        Returns:
            Dict with success status and message ID
        """
        start_time = time.time()

        try:
            result = await self.sqs_client.send_message(message)

            # Track metrics
            publish_time = time.time() - start_time
            self.publish_times.append(publish_time)
            if len(self.publish_times) > 100:
                self.publish_times = self.publish_times[-100:]  # Keep last 100 only

            self.total_published += 1

            # Log at appropriate level based on timing
            if publish_time > 1.0:
                self.logger.warning(f"Published message with slow response: {publish_time:.3f}s")
            else:
                self.logger.debug(f"Published message successfully in {publish_time:.3f}s")

            return result

        except Exception as e:
            self.total_failed += 1
            self.logger.error(f"Error publishing message: {e!s}")
            # If retries enabled, the decorator will handle retries
            # Otherwise, we'll reach here and raise the exception
            raise

    @retry_operation(retries=3)
    async def publish_batch(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Publish multiple messages in batches

        Args:
            messages: List of message payloads to publish

        Returns:
            Dict with overall status and batch results
        """
        if not messages:
            return {"success": True, "published": 0, "failed": 0}

        start_time = time.time()
        total_published = 0
        total_failed = 0
        batch_results = []

        async with self._lock:  # Prevent concurrent batch sends
            for i in range(0, len(messages), self.batch_size):
                batch = messages[i: i + self.batch_size]
                try:
                    result = await self.sqs_client.send_message_batch(batch)

                    # Track results
                    successful_count = len(result.get("successful", []))
                    failed_count = len(result.get("failed", []))

                    total_published += successful_count
                    total_failed += failed_count

                    batch_results.append(result)

                    # Log batch result
                    if failed_count > 0:
                        self.logger.warning(
                            f"Published batch with partial success: {successful_count} sent, "
                            f"{failed_count} failed"
                        )
                    else:
                        self.logger.info(f"Published batch of {len(batch)} messages successfully")

                except Exception as e:
                    # Count all messages in this batch as failed
                    total_failed += len(batch)
                    self.logger.error(f"Error publishing batch: {e!s}")
                    # If retries enabled, the decorator will handle retries
                    # Otherwise, we'll reach here and raise the exception
                    raise

        # Track overall metrics
        self.total_published += total_published
        self.total_failed += total_failed

        publish_time = time.time() - start_time
        avg_msg_time = publish_time / len(messages) if messages else 0
        self.publish_times.append(avg_msg_time)

        # Log overall result
        self.logger.info(
            f"Batch publishing completed: {total_published} sent, {total_failed} failed "
            f"in {publish_time:.3f}s ({avg_msg_time:.3f}s per message)"
        )

        return {
            "success": total_failed == 0,
            "published": total_published,
            "failed": total_failed,
            "batch_results": batch_results
        }

    async def start_async_batching(self):
        """
        Start async batching mode to automatically collect and send messages
        """
        if self._flush_task is not None:
            self.logger.warning("Async batching is already running")
            return

        self._shutdown_event.clear()
        self._flush_task = asyncio.create_task(
            self._flush_loop(),
            name="publisher_flush_loop"
        )
        self.logger.info(f"Started async batching with interval {self.flush_interval}s")

    async def buffer_message(self, message: Dict[str, Any]):
        """
        Add a message to the buffer for batch sending

        Args:
            message: The message payload to buffer
        """
        if self._flush_task is None:
            self.logger.warning("Async batching not started, sending message immediately")
            await self.publish(message)
            return

        async with self._lock:
            self._message_buffer.append(message)

            # If we've reached batch size, trigger an immediate flush
            if len(self._message_buffer) >= self.batch_size:
                # Create a separate task to avoid blocking
                asyncio.create_task(self._flush_buffer())

    async def _flush_loop(self):
        """Background task to periodically flush the message buffer"""
        try:
            while not self._shutdown_event.is_set():
                # Wait for the flush interval
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.flush_interval
                    )
                except asyncio.TimeoutError:
                    # Normal timeout - flush the buffer
                    await self._flush_buffer()

        except asyncio.CancelledError:
            self.logger.debug("Flush loop cancelled")
            # Ensure one final flush
            await self._flush_buffer()

        except Exception as e:
            self.logger.error(f"Error in flush loop: {e!s}")
            # Ensure one final flush
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush any buffered messages"""
        async with self._lock:
            if not self._message_buffer:
                return

            messages_to_send = self._message_buffer.copy()
            self._message_buffer.clear()

        # Send outside the lock to avoid blocking new messages
        if messages_to_send:
            try:
                await self.publish_batch(messages_to_send)
            except Exception as e:
                self.logger.error(f"Error during buffer flush: {e!s}")

    async def log_metrics(self):
        """Log current performance metrics"""
        now = time.time()
        elapsed = now - self.last_metrics_time

        if elapsed > 0 and (self.total_published > 0 or self.total_failed > 0):
            msg_rate = self.total_published / elapsed

            avg_time = 0
            if self.publish_times:
                avg_time = sum(self.publish_times) / len(self.publish_times)

            self.logger.info(
                f"Publisher metrics: {msg_rate:.2f} msgs/sec, {self.total_published} published, "
                f"{self.total_failed} failed, avg_time={avg_time:.3f}s"
            )

            # Reset counters
            self.total_published = 0
            self.total_failed = 0
            self.last_metrics_time = now

    async def shutdown(self):
        """
        Clean shutdown of publisher with flushing of any buffered messages
        """
        self.logger.info("Publisher shutting down...")

        # Signal the flush loop to stop
        self._shutdown_event.set()

        # Cancel and wait for the flush task
        if self._flush_task:
            try:
                # Wait briefly for the task to complete
                await asyncio.wait_for(self._flush_task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Force cancel if it's taking too long
                self._flush_task.cancel()
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass

            self._flush_task = None

        # Ensure any remaining messages are sent
        await self._flush_buffer()

        # Log final metrics
        await self.log_metrics()

        # Close the SQS client
        await self.sqs_client.close()

        self.logger.info("Publisher shutdown complete")