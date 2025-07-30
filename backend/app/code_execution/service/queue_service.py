import uuid
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from pkg.log.logger import Logger
from pkg.redis.client import RedisClient
from app.code_execution.service.service import IQueueService


class QueueService(IQueueService):
    """Service for managing code execution queue using Redis"""

    def __init__(self, redis_client: RedisClient, logger: Logger):
        self.redis = redis_client
        self.logger = logger

        # Queue settings
        self.queue_key = "code_execution:queue"
        self.processing_key = "code_execution:processing"
        self.queue_stats_key = "code_execution:stats"

        # Queue operation lock to prevent race conditions
        self._queue_lock = asyncio.Lock()

    async def enqueue_execution(self, execution_id: uuid.UUID) -> bool:
        """
        Add an execution to the queue
        Returns True if successfully queued
        """
        try:
            # Convert UUID to string for Redis
            exec_id_str = str(execution_id)

            async with self._queue_lock:
                # Add to queue with timestamp
                timestamp = datetime.utcnow().timestamp()
                queue_item = json.dumps({
                    "execution_id": exec_id_str,
                    "queued_at": timestamp
                })

                # Use list_push instead of rpush (no await - it's synchronous)
                self.redis.list_push(self.queue_key, queue_item)

                # Update queue stats - don't fail the enqueue if stats fail
                try:
                    await self._update_queue_stats()
                except Exception as stats_error:
                    self.logger.error(f"Error updating queue stats during enqueue: {str(stats_error)}")

            self.logger.info(f"Execution {exec_id_str} enqueued")
            return True

        except Exception as e:
            self.logger.error(f"Error enqueueing execution {execution_id}: {str(e)}")
            return False

    async def dequeue_execution(self) -> Optional[uuid.UUID]:
        """
        Remove and return the next execution from the queue
        Returns None if queue is empty
        """
        try:
            self.logger.info(f"Attempting to dequeue execution from queue '{self.queue_key}'")
            
            async with self._queue_lock:
                # Since RedisClient doesn't have a direct blpop method, we'll use a work-around
                # First check if there's anything in the queue
                queue_length = self.redis.client.llen(self.queue_key)
                self.logger.info(f"Current queue length: {queue_length}")
                
                items = self.redis.list_range(self.queue_key, 0, 0)
                if not items:
                    self.logger.info("Queue is empty, nothing to dequeue")
                    return None
                
                # If there's an item, get it and remove it
                queue_item_str = items[0]
                self.logger.info(f"Found queue item: {queue_item_str}")
                
                # Remove the first item
                result = self.redis.client.lpop(self.queue_key)
                self.logger.info(f"Removed item from queue: {result}")

                # Parse the item and extract execution ID
                # Ensure we have a string
                if isinstance(queue_item_str, bytes):
                    queue_item_str = queue_item_str.decode('utf-8')
                    
                queue_item = json.loads(queue_item_str)
                execution_id_str = queue_item.get("execution_id")

                if not execution_id_str:
                    self.logger.warning("Queue item missing execution_id")
                    return None

                # Convert string back to UUID
                execution_id = uuid.UUID(execution_id_str)

                # Track in processing set with timestamp
                timestamp = datetime.utcnow().timestamp()
                processing_item = json.dumps({
                    "execution_id": execution_id_str,
                    "dequeued_at": timestamp
                })
                self.logger.info(f"Adding execution {execution_id_str} to processing set")
                
                # Make sure the key and value are both strings for hash_set
                self.redis.hash_set(self.processing_key, {execution_id_str: processing_item})

                try:
                    # Update queue stats
                    await self._update_queue_stats()
                except Exception as stats_error:
                    # Don't fail the dequeue operation if stats update fails
                    self.logger.error(f"Error updating queue stats during dequeue: {str(stats_error)}")

                self.logger.info(f"Execution {execution_id_str} dequeued successfully")
                return execution_id

        except Exception as e:
            self.logger.error(f"Error dequeuing execution: {str(e)}")
            return None

    async def complete_processing(self, execution_id: uuid.UUID) -> None:
        """Mark an execution as no longer processing"""
        try:
            exec_id_str = str(execution_id)

            # Remove from processing set - use client for hdel
            self.redis.client.hdel(self.processing_key, exec_id_str)

            # Update queue stats
            await self._update_queue_stats()

        except Exception as e:
            self.logger.error(f"Error completing processing for {execution_id}: {str(e)}")

    async def peek_queue(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Peek at the next items in the queue without dequeuing
        Returns list of execution items
        """
        try:
            # Get items from queue without removing using list_range
            items = self.redis.list_range(self.queue_key, 0, count - 1)

            result = []
            for item_bytes in items:
                try:
                    item = json.loads(item_bytes)
                    result.append(item)
                except Exception:
                    continue

            return result

        except Exception as e:
            self.logger.error(f"Error peeking queue: {str(e)}")
            return []

    async def get_queue_length(self) -> int:
        """Get the current queue length"""
        try:
            return self.redis.client.llen(self.queue_key)
        except Exception as e:
            self.logger.error(f"Error getting queue length: {str(e)}")
            return 0

    async def get_processing_count(self) -> int:
        """Get the number of currently processing executions"""
        try:
            return self.redis.client.hlen(self.processing_key)
        except Exception as e:
            self.logger.error(f"Error getting processing count: {str(e)}")
            return 0

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the queue"""
        try:
            stats_json = self.redis.get_value(self.queue_stats_key)
            if not stats_json:
                stats = {
                    "queue_length": 0,
                    "processing_count": 0,
                    "enqueued_count": 0,
                    "dequeued_count": 0,
                    "updated_at": datetime.utcnow().timestamp()
                }
            else:
                stats = json.loads(stats_json)

            # Update current counts
            stats["queue_length"] = await self.get_queue_length()
            stats["processing_count"] = await self.get_processing_count()

            return stats

        except Exception as e:
            self.logger.error(f"Error getting queue stats: {str(e)}")
            return {
                "error": str(e)
            }

    async def clear_queue(self) -> int:
        """
        Clear the queue (for maintenance/testing only)
        Returns the number of items cleared
        """
        try:
            async with self._queue_lock:
                # Get queue length
                queue_length = self.redis.client.llen(self.queue_key)

                # Delete queue
                self.redis.delete(self.queue_key)

                # Update queue stats
                await self._update_queue_stats()

                return queue_length

        except Exception as e:
            self.logger.error(f"Error clearing queue: {str(e)}")
            return 0

    async def _update_queue_stats(self) -> None:
        """Update queue statistics"""
        try:
            # Get current stats - initialize with defaults
            stats = {
                "queue_length": 0,
                "processing_count": 0,
                "enqueued_count": 0,
                "dequeued_count": 0,
                "updated_at": datetime.utcnow().timestamp()
            }
            
            # Try to get existing stats from Redis
            try:
                stats_json = self.redis.get_value(self.queue_stats_key)
                if stats_json:
                    # Make sure we have a string before parsing JSON
                    if isinstance(stats_json, bytes):
                        stats_json = stats_json.decode('utf-8')
                    elif isinstance(stats_json, dict):
                        # If somehow we already got a dict, use it directly
                        for key in stats:
                            if key in stats_json:
                                stats[key] = stats_json[key]
                        # Skip the JSON parsing below
                        stats_json = None
                    
                    # Parse JSON if we have a string
                    if stats_json:
                        try:
                            parsed_stats = json.loads(stats_json)
                            # Update our default stats with parsed values
                            if isinstance(parsed_stats, dict):
                                for key in stats:
                                    if key in parsed_stats:
                                        stats[key] = parsed_stats[key]
                        except json.JSONDecodeError as json_error:
                            self.logger.error(f"Failed to parse stats JSON: {str(json_error)}")
            except Exception as get_error:
                self.logger.error(f"Error getting queue stats: {str(get_error)}")

            # Update stats with current values (these will be integers, not awaitable)
            stats["queue_length"] = self.redis.client.llen(self.queue_key)
            stats["processing_count"] = self.redis.client.hlen(self.processing_key)
            stats["updated_at"] = datetime.utcnow().timestamp()

            # Convert dict to JSON string before saving
            try:
                stats_json_str = json.dumps(stats)
                
                # Save updated stats - make sure we're passing a string
                self.redis.set_value(self.queue_stats_key, stats_json_str)
            except Exception as set_error:
                self.logger.error(f"Error saving queue stats: {str(set_error)}")

        except Exception as e:
            self.logger.error(f"Error updating queue stats: {str(e)}")
            # Don't re-raise the exception to avoid breaking the calling methods
