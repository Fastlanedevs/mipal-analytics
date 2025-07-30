import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, insert, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.code_execution.entity.code_execution_entity import CodeExecution
from app.code_execution.entity.value_objects import ExecutionStatus, ExecutionResult
from app.code_execution.repository.sql_schema.execution_status import CodeExecutionModel
from app.code_execution.repository.sql_schema.execution_result import ExecutionResultModel
from pkg.log.logger import Logger
from pkg.db_util.postgres_conn import PostgresConnection
from app.code_execution.service.service import IExecutionRepository


class ExecutionRepository(IExecutionRepository):
    """Repository for code executions"""

    def __init__(self, sql_db_conn: PostgresConnection, logger: Logger):
        self.db_conn = sql_db_conn
        self.logger = logger
        # Results cache to reduce database reads
        self._result_cache = {}
        # Maximum cache size
        self._max_cache_entries = 100
        # Execution status cache
        self._status_cache = {}

    async def get_execution(self, execution_id: uuid.UUID) -> Optional[CodeExecution]:
        """Get execution by ID"""
        async with self.db_conn.get_session() as session:
            # Query execution
            exec_stmt = select(CodeExecutionModel).where(CodeExecutionModel.id == execution_id)

            try:
                result = await session.execute(exec_stmt)
                execution_model = result.scalars().first()

                if not execution_model:
                    return None

                # Convert to entity
                execution = execution_model.to_entity()

                # Check if status is in cache and is more recent than the DB status
                cached_status = self._status_cache.get(str(execution_id))
                if cached_status:
                    # Use cache only if newer than model
                    if execution_model.updated_at and cached_status.get('timestamp',
                                                                        datetime.min) > execution_model.updated_at:
                        execution.status = ExecutionStatus(cached_status.get('status'))

                # Get result from cache or database
                if execution.status == ExecutionStatus.COMPLETED:
                    # Check cache first
                    cached_result = self._result_cache.get(str(execution_id))
                    if cached_result:
                        execution.result = cached_result
                    else:
                        # Query result from database
                        result_stmt = select(ExecutionResultModel).where(
                            ExecutionResultModel.execution_id == execution_id
                        )
                        result = await session.execute(result_stmt)
                        result_model = result.scalars().first()

                        if result_model:
                            execution.result = result_model.to_entity()
                            # Cache the result
                            self._cache_result(execution_id, execution.result)

                return execution

            except Exception as e:
                self.logger.error(f"Error getting execution {execution_id}: {str(e)}")
                raise

    async def get_executions_batch(self, execution_ids: List[uuid.UUID]) -> Dict[uuid.UUID, CodeExecution]:
        """Get multiple executions by their IDs in a single query"""
        if not execution_ids:
            return {}

        result_dict = {}

        async with self.db_conn.get_session() as session:
            # Query executions in a single statement
            exec_stmt = select(CodeExecutionModel).where(CodeExecutionModel.id.in_(execution_ids))

            try:
                exec_result = await session.execute(exec_stmt)
                execution_models = exec_result.scalars().all()

                # Create mapping of ID -> model
                execution_dict = {str(model.id): model.to_entity() for model in execution_models}

                # Collect IDs of completed executions that need results
                completed_ids = [
                    model.id for model in execution_models
                    if model.status == ExecutionStatus.COMPLETED.value
                ]

                # Query results for completed executions in a single statement
                if completed_ids:
                    result_stmt = select(ExecutionResultModel).where(
                        ExecutionResultModel.execution_id.in_(completed_ids)
                    )
                    result_models = await session.execute(result_stmt)
                    results = result_models.scalars().all()

                    # Create mapping of execution_id -> result
                    results_dict = {str(result.execution_id): result.to_entity() for result in results}

                    # Add results to executions
                    for exec_id, result in results_dict.items():
                        if exec_id in execution_dict:
                            execution_dict[exec_id].result = result
                            # Cache the result
                            self._cache_result(uuid.UUID(exec_id), result)

                # Convert string keys back to UUID for return value
                for exec_id, execution in execution_dict.items():
                    result_dict[uuid.UUID(exec_id)] = execution

                return result_dict

            except Exception as e:
                self.logger.error(f"Error getting executions batch: {str(e)}")
                raise

    async def create_execution(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> CodeExecution:
        """Create a new code execution with QUEUED status"""
        async with self.db_conn.get_session() as session:
            # Create execution entity
            execution = CodeExecution(
                code=code,
                input_data=input_data,
                status=ExecutionStatus.QUEUED
            )

            # Create model from entity
            execution_model = CodeExecutionModel.from_entity(execution)

            try:
                session.add(execution_model)
                await session.commit()
                await session.refresh(execution_model)

                # Cache the status
                self._cache_status(execution_model.id, ExecutionStatus.QUEUED)

                return execution_model.to_entity()

            except Exception as e:
                self.logger.error(f"Error creating execution: {str(e)}")
                raise

    async def create_execution_with_status(self, code: str, input_data: Optional[Dict[str, Any]] = None,
                                           status: ExecutionStatus = ExecutionStatus.QUEUED) -> CodeExecution:
        """
        Create a new code execution with a specified status.
        This allows direct creation of executions in PROCESSING state for sync APIs.
        """
        async with self.db_conn.get_session() as session:
            # Create execution entity with specified status
            execution = CodeExecution(
                code=code,
                input_data=input_data,
                status=status
            )

            # Set started_at timestamp if status is PROCESSING
            if status == ExecutionStatus.PROCESSING:
                execution.started_at = datetime.utcnow()

            # Create model from entity
            execution_model = CodeExecutionModel.from_entity(execution)

            try:
                session.add(execution_model)
                await session.commit()
                await session.refresh(execution_model)

                # Cache the status
                self._cache_status(execution_model.id, status)

                return execution_model.to_entity()

            except Exception as e:
                self.logger.error(f"Error creating execution with status {status}: {str(e)}")
                raise

    async def update_execution_status(self, execution_id: uuid.UUID, status: ExecutionStatus) -> Optional[CodeExecution]:
        """Update execution status"""
        async with self.db_conn.get_session() as session:
            values = {
                "status": status
            }

            if status == ExecutionStatus.PROCESSING:
                values["started_at"] = func.now()

            stmt = (
                update(CodeExecutionModel)
                .where(CodeExecutionModel.id == execution_id)
                .values(**values)
                .returning(CodeExecutionModel)
            )

            try:
                result = await session.execute(stmt)
                await session.commit()

                updated_execution = result.scalars().first()
                if not updated_execution:
                    return None

                # Update cache
                self._cache_status(execution_id, status)

                return updated_execution.to_entity()

            except Exception as e:
                self.logger.error(f"Error updating execution {execution_id} status: {str(e)}")
                raise

    async def complete_execution(self, execution_id: uuid.UUID, result: ExecutionResult,
                                metrics: Optional[Dict[str, Any]] = None) -> Optional[CodeExecution]:
        """Mark execution as completed with results"""
        async with self.db_conn.get_session() as session:
            async with session.begin():
                # Update execution status
                exec_values = {
                    "status": ExecutionStatus.COMPLETED,
                    "completed_at": func.now()
                }

                if metrics:
                    if "execution_time_ms" in metrics:
                        exec_values["execution_time_ms"] = metrics["execution_time_ms"]
                    if "memory_usage_kb" in metrics:
                        exec_values["memory_usage_kb"] = metrics["memory_usage_kb"]

                exec_stmt = (
                    update(CodeExecutionModel)
                    .where(CodeExecutionModel.id == execution_id)
                    .values(**exec_values)
                    .returning(CodeExecutionModel)
                )

                # Save execution result
                result_model = ExecutionResultModel.from_entity(result, execution_id=execution_id)

                try:
                    # Update execution
                    exec_result = await session.execute(exec_stmt)
                    updated_execution = exec_result.scalars().first()

                    if not updated_execution:
                        await session.rollback()
                        return None

                    # Save result
                    session.add(result_model)
                    await session.commit()

                    # Update caches
                    self._cache_status(execution_id, ExecutionStatus.COMPLETED)
                    self._cache_result(execution_id, result)

                    # Return updated entity with result
                    execution = updated_execution.to_entity()
                    execution.result = result
                    return execution

                except Exception as e:
                    self.logger.error(f"Error completing execution {execution_id}: {str(e)}")
                    await session.rollback()
                    raise

    async def fail_execution(self, execution_id: uuid.UUID, error_message: str) -> Optional[CodeExecution]:
        """Mark execution as failed with error message"""
        async with self.db_conn.get_session() as session:
            values = {
                "status": ExecutionStatus.FAILED,
                "error_message": error_message,
                "completed_at": func.now()
            }

            stmt = (
                update(CodeExecutionModel)
                .where(CodeExecutionModel.id == execution_id)
                .values(**values)
                .returning(CodeExecutionModel)
            )

            try:
                result = await session.execute(stmt)
                await session.commit()

                updated_execution = result.scalars().first()
                if not updated_execution:
                    return None

                # Update cache
                self._cache_status(execution_id, ExecutionStatus.FAILED)

                return updated_execution.to_entity()

            except Exception as e:
                self.logger.error(f"Error failing execution {execution_id}: {str(e)}")
                raise

    async def get_executions_by_status(self, status: ExecutionStatus, limit: int = 10) -> List[CodeExecution]:
        """Get executions by status"""
        async with self.db_conn.get_session() as session:
            stmt = (
                select(CodeExecutionModel)
                .where(CodeExecutionModel.status == status)
                .order_by(CodeExecutionModel.created_at)
                .limit(limit)
            )

            try:
                result = await session.execute(stmt)
                executions = result.scalars().all()

                return [execution.to_entity() for execution in executions]

            except Exception as e:
                self.logger.error(f"Error getting executions by status {status}: {str(e)}")
                raise

    def _cache_result(self, execution_id: uuid.UUID, result: ExecutionResult) -> None:
        """Cache an execution result"""
        # Enforce maximum cache size
        if len(self._result_cache) >= self._max_cache_entries:
            # Remove oldest entry (we don't track insertion order, so just remove any one)
            if self._result_cache:
                self._result_cache.pop(next(iter(self._result_cache)))

        # Add to cache
        self._result_cache[str(execution_id)] = result

    def _cache_status(self, execution_id: uuid.UUID, status: ExecutionStatus) -> None:
        """Cache an execution status with timestamp"""
        # Enforce maximum cache size
        if len(self._status_cache) >= self._max_cache_entries:
            # Remove oldest entry
            if self._status_cache:
                self._status_cache.pop(next(iter(self._status_cache)))

        # Add to cache with current timestamp
        self._status_cache[str(execution_id)] = {
            'status': status.value,
            'timestamp': datetime.utcnow()
        }

    def invalidate_cache(self, execution_id: uuid.UUID) -> None:
        """Invalidate caches for an execution ID"""
        str_id = str(execution_id)
        if str_id in self._result_cache:
            del self._result_cache[str_id]
        if str_id in self._status_cache:
            del self._status_cache[str_id]

    def clear_caches(self) -> None:
        """Clear all caches"""
        self._result_cache.clear()
        self._status_cache.clear()