import uuid
import asyncio
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import HTTPException, status, BackgroundTasks

from app.code_execution.service.execution_service import ExecutionService
from app.code_execution.entity.value_objects import ExecutionStatus, ExecutionResult
from app.code_execution.api.dto import (
    CodeExecutionRequestDTO,
    CodeExecutionResponseDTO,
    CodeExecutionResultDTO,
    CodeExecutionStatusDTO,
)
from pkg.log.logger import Logger


class CodeExecutionHandler:
    """Handles API requests related to code execution."""

    def __init__(self, execution_service: ExecutionService, logger: Logger):
        self.execution_service = execution_service
        self.logger = logger


    async def execute_code_sync(
            self,
            user_id: str,
            code: str,
            input_data: Optional[Dict[str, Any]],
            timeout_seconds: int
    ) -> CodeExecutionResultDTO:
        """
        Execute code synchronously using optimized direct execution path.
        This bypasses the queue system for better performance.
        """
        self.logger.info(f"User {user_id} submitting code for synchronous execution.")

        try:
            # Use the optimized direct execution path
            execution, success, error_message = await self.execution_service.execute_code_sync(
                code=code,
                input_data=input_data
            )

            if not success:
                self.logger.error(f"Synchronous execution failed: {error_message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Execution failed: {error_message}"
                )

            if not execution or not execution.result:
                self.logger.error(f"Execution result not available after processing")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Execution result not available"
                )

            # Return the result directly
            return CodeExecutionResultDTO(
                execution_id=execution.id,
                status=execution.status.value,
                stdout=execution.result.stdout,
                stderr=execution.result.stderr,
                exit_code=execution.result.exit_code,
                execution_time_ms=execution.result.execution_time_ms,
                memory_usage_kb=execution.result.memory_usage_kb,
                output_files=execution.result.output_files or {}
            )

        except HTTPException:
            # Re-raise HTTP exceptions
            raise

        except Exception as e:
            self.logger.error(f"Error during synchronous execution for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during synchronous execution: {str(e)}"
            )

    async def execute_ml_run_sync(self, user_id: str, code: str,
                                  input_data: Optional[Dict[str, Any]] = None,
                                  timeout_seconds: int = 30) -> CodeExecutionResultDTO:

        try:
            # Use the optimized direct execution path
            execution, success, error_message = await self.execution_service.execute_code_local(
                code=code,
                input_data=input_data
            )

            if not success:
                self.logger.error(f"Synchronous execution failed: {error_message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Execution failed: {error_message}"
                )

            if not execution or not execution.result:
                self.logger.error(f"Execution result not available after processing")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Execution result not available"
                )

            # Return the result directly
            return CodeExecutionResultDTO(
                execution_id=execution.id,
                status=execution.status.value,
                stdout=execution.result.stdout,
                stderr=execution.result.stderr,
                exit_code=execution.result.exit_code,
                execution_time_ms=execution.result.execution_time_ms,
                memory_usage_kb=execution.result.memory_usage_kb,
                output_files=execution.result.output_files or {}
            )

        except HTTPException:
            # Re-raise HTTP exceptions
            raise

        except Exception as e:
            self.logger.error(f"Error during synchronous execution for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during synchronous execution: {str(e)}"
            )
    async def get_execution_status(
            self, user_id: str, execution_id: UUID
    ) -> CodeExecutionStatusDTO:
        """Get the status of an asynchronous execution."""
        self.logger.debug(f"User {user_id} checking status for execution {execution_id}")
        execution = await self.execution_service.get_execution(execution_id)

        if not execution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        # Map CodeExecution entity to DTO
        result_dict = None
        if execution.status == ExecutionStatus.COMPLETED and execution.result:
            result_dict = execution.result.model_dump()

        return CodeExecutionStatusDTO(
            execution_id=execution.id,
            status=execution.status.value,
            created_at=execution.created_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            execution_time_ms=execution.execution_time_ms,
            result=result_dict,
            error=execution.error_message
        )

    async def get_execution_result(
            self, user_id: str, execution_id: UUID
    ) -> Optional[CodeExecutionResultDTO]:
        """Get the result of a completed execution."""
        self.logger.debug(f"User {user_id} fetching result for execution {execution_id}")
        execution = await self.execution_service.get_execution(execution_id)

        if not execution or execution.status != ExecutionStatus.COMPLETED or not execution.result:
            # Return None as per route definition, which will cause a 404 in the route
            return None

        # Map ExecutionResult entity to DTO
        return CodeExecutionResultDTO(
            execution_id=execution_id,
            status=execution.status.value,
            stdout=execution.result.stdout,
            stderr=execution.result.stderr,
            exit_code=execution.result.exit_code,
            execution_time_ms=execution.result.execution_time_ms,
            memory_usage_kb=execution.result.memory_usage_kb,
            output_files=execution.result.output_files
        )
