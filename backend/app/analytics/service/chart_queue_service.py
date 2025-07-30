import json
import uuid
from typing import Optional, Dict, Any, cast, List
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException

from pkg.redis.client import RedisClient
from pkg.log.logger import Logger
from app.analytics.entity.chart import ChartStatus, ChartTask, ChartVisibility


class ChartQueueService:
    """Service for managing chart generation queue"""
    
    def __init__(self, redis_client: RedisClient, logger: Logger):
        self.redis = redis_client
        self.logger = logger
        self.queue_key = "chart_generation:queue"
        self.processing_key = "chart_generation:processing"
        self.status_key_prefix = "chart_generation:status:"
        self.task_key_prefix = "chart_generation:task:"
        
    async def enqueue_chart_task(self, task: ChartTask) -> bool:
        """Add chart generation task to queue"""
        try:
            task_data = {
                "task_id": task.task_id,
                "message_id": str(task.message_id),
                "user_id": task.user_id,
                "org_id": task.org_id,
                "visibility": task.visibility.value,
                "force_create": task.force_create,
                "adjustment_query": task.adjustment_query,
                "queued_at": datetime.utcnow().isoformat()
            }
            
            # Add to queue - Redis client will handle JSON serialization
            self.redis.list_push(self.queue_key, task_data)
            
            # Store full task data
            await self._store_task_data(task)
            
            # Set initial status in Redis
            await self._update_task_status(task.task_id, ChartStatus.PENDING, 0, "queued")
            
            # Add to message index for easy lookup
            await self._add_task_to_message_index(
                str(task.message_id), 
                task.user_id, 
                task.task_id
            )
            
            self.logger.info(f"Chart task {task.task_id} enqueued")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enqueueing chart task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to queue chart task")
    
    async def dequeue_chart_task(self) -> Optional[Dict[str, Any]]:
        """Get next chart task from queue"""
        try:
            # Atomically retrieve and remove the next task from the queue.
            task_json_string = self.redis.client.lpop(self.queue_key)

            if not task_json_string:
                return None

            # The value is already a JSON string, so we can parse it directly.
            task_data = json.loads(cast(str, task_json_string))
            
            # Mark as processing
            await self._update_task_status(
                task_data["task_id"], 
                ChartStatus.PROCESSING, 
                10,
                "data_extraction"
            )
            
            return task_data
            
        except Exception as e:
            self.logger.error(f"Error dequeuing chart task: {str(e)}")
            return None
    
    async def _store_task_data(self, task: ChartTask):
        """Store full task data in Redis"""
        try:
            # Convert task to dict using model_dump with JSON mode to respect encoders
            task_dict = task.model_dump(mode="json")

            self.redis.set_value(
                f"{self.task_key_prefix}{task.task_id}",
                task_dict,
                expiry=86400  # 24 hours TTL
            )
        except Exception as e:
            self.logger.error(f"Error storing task data: {str(e)}")
            raise
    
    async def get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get raw task data from Redis without reconstruction"""
        try:
            task_key = f"{self.task_key_prefix}{task_id}"
            self.logger.info(f"Reading raw task data from key: {task_key}")
            
            task_data = self.redis.get_value(task_key, bypass_cache=True)
            if task_data:
                self.logger.info(f"Raw task data for {task_id}: status={task_data.get('status')}, chart_id={task_data.get('chart_id')}")
            else:
                self.logger.error(f"No raw task data found for {task_id}")
            
            return task_data
        except Exception as e:
            self.logger.error(f"Error getting raw task data: {str(e)}")
            return None

    async def _update_task_status(self, task_id: str, status: ChartStatus, 
                                progress: int, current_step: Optional[str] = None,
                                error_message: Optional[str] = None):
        """Update task status in Redis"""
        try:
            status_data = {
                "status": status.value,
                "progress": progress,
                "current_step": current_step or "unknown",
                "error_message": error_message or "",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Update status - Redis client will handle JSON serialization
            self.redis.set_value(
                f"{self.status_key_prefix}{task_id}",
                status_data,
                expiry=3600  # 1 hour TTL
            )
            
            # Publish status update - Redis client will handle JSON serialization
            self.redis.publish(
                f"chart_generation:updates:{task_id}",
                status_data
            )
            
        except Exception as e:
            self.logger.error(f"Error updating task status: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status"""
        try:
            status_data = self.redis.get_value(f"{self.status_key_prefix}{task_id}", bypass_cache=True)
            if status_data:
                # Redis client already deserializes JSON, so status_data is already a dict
                return status_data
            return None
        except Exception as e:
            self.logger.error(f"Error getting task status: {str(e)}")
            return None
    
    async def update_task_progress(self, task_id: str, progress: int, 
                                 current_step: str, step_progress: Optional[Dict[str, int]] = None):
        """Update task progress"""
        try:
            status_data = await self.get_task_status(task_id)
            if status_data:
                status_data["progress"] = progress
                status_data["current_step"] = current_step
                if step_progress:
                    status_data["step_progress"] = step_progress
                status_data["updated_at"] = datetime.utcnow().isoformat()
                
                # Update status - Redis client will handle JSON serialization
                self.redis.set_value(
                    f"{self.status_key_prefix}{task_id}",
                    status_data,
                    expiry=3600
                )
                
                # Publish update - Redis client will handle JSON serialization
                self.redis.publish(
                    f"chart_generation:updates:{task_id}",
                    status_data
                )
                
        except Exception as e:
            self.logger.error(f"Error updating task progress: {str(e)}")
    
    async def complete_task(self, task_id: str, chart_id: Optional[str] = None, 
                          error_message: Optional[str] = None):
        """Mark task as completed or failed"""
        try:
            if error_message:
                status = ChartStatus.FAILED
                progress = 0
                current_step = "failed"
            else:
                status = ChartStatus.COMPLETED
                progress = 100
                current_step = "completed"
            
            self.logger.info(f"Completing task {task_id} with status {status.value}, chart_id: {chart_id}")
            
            await self._update_task_status(
                task_id, status, progress, current_step, error_message or ""
            )
            
            # Update task data with completion info - avoid calling get_task_data to prevent corruption
            task_key = f"{self.task_key_prefix}{task_id}"
            self.logger.info(f"Reading task data from key: {task_key}")
            
            task_data = self.redis.get_value(task_key, bypass_cache=True)
            if task_data:
                self.logger.info(f"Updating task data for {task_id}, current status: {task_data.get('status')}")
                
                # Update the task data directly without reconstruction
                task_data["status"] = status.value
                task_data["completed_at"] = datetime.utcnow().isoformat()
                if chart_id:
                    task_data["chart_id"] = chart_id
                if error_message:
                    task_data["error_message"] = error_message
                
                # Store the updated task data
                self.redis.set_value(
                    task_key,
                    task_data,
                    expiry=86400  # 24 hours TTL
                )
                
                self.logger.info(f"Task {task_id} data updated successfully, new status: {task_data['status']}, chart_id: {task_data.get('chart_id')}")
                
                # Clear the cache for this key to ensure fresh data is read
                self.redis.clear_cache()
                self.logger.info(f"Cleared Redis cache after updating task {task_id}")
                
                # Verify the data was actually stored
                verification_data = self.redis.get_value(task_key, bypass_cache=True)
                self.logger.info(f"Verification - stored data for {task_id}: status={verification_data.get('status')}, chart_id={verification_data.get('chart_id')}")
            else:
                self.logger.error(f"No task data found for {task_id}")
            
        except Exception as e:
            self.logger.error(f"Error completing task: {str(e)}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        try:
            status_data = await self.get_task_status(task_id)
            if not status_data or status_data["status"] not in ["PENDING", "PROCESSING"]:
                return False
            
            await self._update_task_status(
                task_id, ChartStatus.CANCELLED, 0, "cancelled"
            )
            
            # Update task data - avoid calling get_task_data to prevent corruption
            task_data = self.redis.get_value(f"{self.task_key_prefix}{task_id}", bypass_cache=True)
            if task_data:
                # Update the task data directly without reconstruction
                task_data["status"] = ChartStatus.CANCELLED.value
                task_data["completed_at"] = datetime.utcnow().isoformat()
                
                # Store the updated task data
                self.redis.set_value(
                    f"{self.task_key_prefix}{task_id}",
                    task_data,
                    expiry=86400  # 24 hours TTL
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling task: {str(e)}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            queue_length = self.redis.client.llen(self.queue_key)
            processing_count = self.redis.client.hlen(self.processing_key)
            
            return {
                "queue_length": queue_length,
                "processing_count": processing_count,
                "updated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting queue stats: {str(e)}")
            return {"error": str(e)}
    
    async def _add_task_to_message_index(self, message_id: str, user_id: str, task_id: str):
        """Add task to message index for easy lookup"""
        try:
            index_key = f"message_tasks:{message_id}:{user_id}"
            self.redis.set_add(index_key, task_id)
            # Set expiry for the index
            self.redis.expire(index_key, 86400)  # 24 hours
        except Exception as e:
            self.logger.error(f"Error adding task to message index: {str(e)}")
    
    async def get_active_tasks_by_message_id(self, message_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all active chart tasks for a specific message"""
        try:
            index_key = f"message_tasks:{message_id}:{user_id}"
            
            # Get task IDs from the index
            task_ids = self.redis.set_members(index_key, bypass_cache=True)
            if not task_ids:
                return []
            
            active_tasks = []
            
            for task_id in task_ids:
                # Get task data
                task_data = self.redis.get_value(f"{self.task_key_prefix}{task_id}", bypass_cache=True)
                if task_data:
                    # Check if task is still active (not completed/failed/cancelled)
                    status = task_data.get("status")
                    if status in ["PENDING", "PROCESSING"]:
                        # Get current status data
                        status_data = await self.get_task_status(task_id)
                        if status_data:
                            active_tasks.append({
                                "task_id": task_data["task_id"],
                                "message_id": task_data["message_id"],
                                "status": status_data["status"],
                                "progress": status_data["progress"],
                                "current_step": status_data["current_step"],
                                "created_at": task_data.get("created_at"),
                                "started_at": task_data.get("started_at")
                            })
            
            return active_tasks
            
        except Exception as e:
            self.logger.error(f"Error getting active tasks by message_id: {str(e)}")
            return []
    
    async def cleanup_expired_tasks(self, max_age_hours: int = 24):
        """Clean up expired task data"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # This would require scanning Redis keys, which is expensive
            # In production, consider using Redis TTL or a separate cleanup job
            self.logger.info("Task cleanup would run here in production")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired tasks: {str(e)}") 