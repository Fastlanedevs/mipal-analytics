import asyncio
import signal
import time
from contextlib import AsyncExitStack
from typing import Optional, Set, Dict, Any

from app.knowledge_base.event_handler.handler import KnowledgeBaseEventHandler
from pkg.log.logger import Logger
from pkg.pub_sub.subscriber import Subscriber


class KnowledgeBaseWorker:
    def __init__(self,
                 knowledge_handler: KnowledgeBaseEventHandler,
                 subscriber: Subscriber,
                 logger: Logger,
                 shutdown_timeout: int = 30,
                 health_check_interval: int = 60):
        self.logger = logger
        self.subscriber = subscriber
        self.handler = knowledge_handler
        self.shutdown_timeout = shutdown_timeout
        self.health_check_interval = health_check_interval

        # State tracking
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.shutdown_complete = asyncio.Event()
        self.main_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.start_time = 0

        # Resource management
        self.exit_stack = AsyncExitStack()

        # Metrics
        self.processed_count = 0
        self.error_count = 0
        self.last_activity_time = 0

    async def start(self):
        """Start the knowledge base worker with proper resource management"""
        if self.running:
            self.logger.warning("Worker is already running")
            return

        try:
            # Record start time for uptime reporting
            self.start_time = time.time()
            self.last_activity_time = self.start_time

            # Setup signal handlers
            self._setup_signal_handlers()

            # Set state
            self.running = True
            self.shutdown_event.clear()
            self.shutdown_complete.clear()

            self.logger.info("Knowledge base worker starting")

            # Use AsyncExitStack for proper resource cleanup
            async with self.exit_stack:
                # Start health check task
                self.health_check_task = asyncio.create_task(
                    self._health_check_loop(),
                    name="health_check_loop"
                )

                # Register cleanup
                self.exit_stack.push_async_callback(self._cancel_task, self.health_check_task)

                # Start the subscriber - will be cleaned up by exit_stack
                await self.subscriber.start(self.handler.handle_integration_document_sync)
                self.exit_stack.push_async_callback(self.subscriber.stop, self.shutdown_timeout)

                # Wait for shutdown signal
                self.logger.info("Worker running, waiting for shutdown signal")
                await self.shutdown_event.wait()
                self.logger.info("Shutdown event received, stopping worker...")

        except Exception as e:
            self.logger.error(f"Error starting knowledge base worker: {e!s}")
            self.error_count += 1
            raise
        finally:
            # Ensure we clean up even if there was an error
            if self.running:
                await self._cleanup()
                self.shutdown_complete.set()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        loop = asyncio.get_running_loop()

        # Use more robust signal handling with error recovery
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(
                        self._handle_signal(s),
                        name=f"signal_handler_{s.name}"
                    )
                )
                self.logger.debug(f"Registered signal handler for {sig.name}")
            except Exception as e:
                self.logger.error(f"Failed to set up signal handler for {sig.name}: {e!s}")

    async def _handle_signal(self, sig: signal.Signals):
        """Handle termination signals"""
        self.logger.info(f"Received exit signal {sig.name}")
        try:
            await self.stop()
        except Exception as e:
            self.logger.error(f"Error during signal-triggered shutdown: {e!s}")
            # Force shutdown in case of error
            self.running = False
            self.shutdown_event.set()

    async def stop(self):
        """Stop the worker and wait for shutdown to complete"""
        if not self.running:
            self.logger.info("Worker is not running")
            return

        self.logger.info("Stopping knowledge base worker...")
        self.running = False
        self.shutdown_event.set()

        # Wait for shutdown to complete with timeout
        try:
            await asyncio.wait_for(
                self.shutdown_complete.wait(),
                timeout=self.shutdown_timeout
            )
            self.logger.info("Worker shutdown completed successfully")
        except asyncio.TimeoutError:
            self.logger.warning(f"Worker shutdown timed out after {self.shutdown_timeout}s")

    async def _cleanup(self):
        """Clean up resources during shutdown using AsyncExitStack"""
        self.logger.info("Cleaning up resources...")

        # AsyncExitStack will handle all registered cleanup operations
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            self.logger.error(f"Error during exit stack cleanup: {e!s}")

        # Cancel health check if still running
        if self.health_check_task and not self.health_check_task.done():
            await self._cancel_task(self.health_check_task)
            self.health_check_task = None

        # Additional cleanup for any directly managed tasks
        try:
            # Find any remaining tasks (excluding this one)
            current_task = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks()
                       if t is not current_task
                       and not t.done()
                       and not t.cancelled()
                       and "knowledge_base_worker" in getattr(t, 'name', '')]

            if pending:
                self.logger.info(f"Waiting for {len(pending)} remaining worker tasks to complete...")

                # Wait with timeout
                done, pending = await asyncio.wait(
                    pending,
                    timeout=self.shutdown_timeout / 2,
                    return_when=asyncio.ALL_COMPLETED
                )

                # Cancel any remaining tasks
                if pending:
                    self.logger.warning(f"Forcibly cancelling {len(pending)} outstanding worker tasks")
                    for task in pending:
                        if not task.done():
                            task.cancel()

                    # Wait briefly for cancellations to process
                    await asyncio.gather(*pending, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Error during task cleanup: {e!s}")

        self.logger.info("Knowledge base worker shutdown complete")

    async def _health_check_loop(self):
        """Periodic health check and metrics reporting"""
        try:
            while self.running:
                current_time = time.time()
                uptime = current_time - self.start_time
                idle_time = current_time - self.last_activity_time

                # Report health metrics
                self.logger.info(
                    f"Health check: Uptime={int(uptime)}s, "
                    f"Messages processed={self.processed_count}, "
                    f"Errors={self.error_count}, "
                    f"Idle time={int(idle_time)}s"
                )

                # Wait for next check interval
                await asyncio.sleep(self.health_check_interval)

        except asyncio.CancelledError:
            self.logger.debug("Health check loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in health check loop: {e!s}")

    async def _cancel_task(self, task):
        """Helper to properly cancel and await a task"""
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error cancelling task {task.get_name()}: {e!s}")

    def update_activity(self):
        """Update last activity time and message count"""
        self.last_activity_time = time.time()
        self.processed_count += 1