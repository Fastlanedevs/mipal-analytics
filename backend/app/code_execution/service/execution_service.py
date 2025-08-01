import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import io
import traceback
import contextlib
import re
import warnings
from app.code_execution.entity.code_execution_entity import CodeExecution
from app.code_execution.entity.value_objects import ExecutionStatus, ExecutionResult
from app.code_execution.repository.execution_repository import IExecutionRepository
from app.code_execution.service.service import IExecutionService
from pkg.log.logger import Logger
from pkg.redis.client import RedisClient

import pandas as pd
import numpy as np
import sklearn
import statsmodels
import time


class ExecutionService(IExecutionService):

    def __init__(
            self,
            execution_repository: IExecutionRepository,
            redis_client: RedisClient,
            logger: Logger
    ):
        self.repository = execution_repository
        self.redis_client = redis_client
        self.logger = logger

    def _filter_warnings_from_stderr(self, stderr_output: str) -> str:
        """
        Filter out warning messages from stderr output.
        
        Args:
            stderr_output: The stderr output string
            
        Returns:
            Filtered stderr output with warnings removed
        """
        if not stderr_output:
            return stderr_output
            
        # Split into lines and filter out warning lines
        lines = stderr_output.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that are warnings
            if any(warning_pattern in line.lower() for warning_pattern in [
                'warning:', 'warnings.warn', 'deprecationwarning', 'futurewarning',
                'userwarning', 'runtimewarning', 'importwarning', 'pendingdeprecationwarning',
                'settingwithcopywarning', 'dataframe.append', 'series.append', 'pandas.errors',
                'numpy.visible_deprecationwarning', 'sklearn.exceptions', 'matplotlib',
                'the following argument', 'this will change', 'this is deprecated',
                'future versions', 'deprecated since', 'will be removed'
            ]):
                continue
            # Skip lines that match common warning patterns
            if re.match(r'.*:\d+:\s*warning:', line, re.IGNORECASE):
                continue
            if re.match(r'.*:\d+:\s*deprecationwarning:', line, re.IGNORECASE):
                continue
            if re.match(r'.*:\d+:\s*futurewarning:', line, re.IGNORECASE):
                continue
            if re.match(r'.*:\d+:\s*userwarning:', line, re.IGNORECASE):
                continue
            if re.match(r'.*:\d+:\s*runtimewarning:', line, re.IGNORECASE):
                continue
            filtered_lines.append(line)
            
        return '\n'.join(filtered_lines).strip()

    @contextlib.contextmanager
    def _suppress_warnings_context(self):
        """
        Context manager to suppress warnings during code execution.
        This prevents warnings from being generated in the first place.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            yield

    async def execute_code_sync(self, code: str,
                                input_data: Optional[Dict[str, Any]] = None) -> Tuple[CodeExecution, bool, Optional[str]]:
        """
        This provides immediate execution and response.
        
        Returns:
            Tuple containing:
            - The code execution entity
            - Success flag
            - Error message (if any)
        """
        
        try:
            execution = await self.repository.create_execution_with_status(
                code=code,
                input_data=input_data,
                status=ExecutionStatus.PROCESSING
            )

            self.logger.info(f"Code execution successful for ID: {execution.id}")
            self.logger.info(f"Created execution record with ID: {execution.id}")

            
            # 3. Filter warnings from stderr before checking for errors
            filtered_stderr = self._filter_warnings_from_stderr(result.stderr)
            
            # 4. Check for execution error (using filtered stderr)
            if result.exit_code != 0:
                error_msg = f"Execution failed with exit code {result.exit_code}. {filtered_stderr}"
                self.logger.warning(f"Execution {execution.id} failed: {error_msg}")
                await self.repository.fail_execution(
                    execution_id=execution.id,
                    error_message=error_msg
                )
                return execution, False, error_msg

            # 5. Create filtered result object
            filtered_result = ExecutionResult(
                stdout=result.stdout,
                stderr=filtered_stderr,
                exit_code=result.exit_code,
                execution_time_ms=result.execution_time_ms,
                memory_usage_kb=result.memory_usage_kb,
                output_files=result.output_files
            )

            # 6. Complete execution with filtered result
            self.logger.info(f"Execution {execution.id} completed successfully")
            execution = await self.repository.complete_execution(
                execution_id=execution.id,
                result=filtered_result,
                metrics=metrics
            )
            
            return execution, True, None

        except Exception as e:
            error_message = f"Error in synchronous code execution: {str(e)}"
            self.logger.error(error_message)

            # If we created an execution record, mark it as failed
            if execution and execution.id:
                await self.repository.fail_execution(
                    execution_id=execution.id,
                    error_message=error_message
                )

            return execution, False, error_message

    async def execute_code_local(self, code: str,
                                 input_data: Optional[Dict[str, Any]] = None) -> Tuple[
        CodeExecution, bool, Optional[str]]:
        """
        Execute code synchronously in the local environment.
        This provides immediate execution and response using local Python.

        Returns:
            Tuple containing:
            - The code execution entity
            - Success flag
            - Error message (if any)
        """
        self.logger.info("Executing code synchronously in local environment")

        try:
            execution = await self.repository.create_execution_with_status(
                code=code,
                input_data=input_data,
                status=ExecutionStatus.PROCESSING
            )

            self.logger.info(f"Created execution record with ID: {execution.id}")

            # 2. Create a namespace with available libraries and input data
            output_files = {}  # For potential file outputs
            namespace = {
                'pd': pd,
                'pandas': pd,
                'np': np,
                'numpy': np,
                'sklearn': sklearn,
                'statsmodels':statsmodels,
                'input_data': input_data,  # Make input_data directly available
                'output_files': output_files,  # For file outputs like Lambda
                '__builtins__': __builtins__,
            }

            # 3. Capture stdout and stderr and measure execution time
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            start_time = time.time()

            try:
                with contextlib.redirect_stdout(stdout_capture), \
                        contextlib.redirect_stderr(stderr_capture), \
                        self._suppress_warnings_context():

                    # Execute the code
                    exec(code, namespace)

                # Calculate execution time
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Get output
                output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()

                if stderr_output:
                    output += f"\nStderr: {self._filter_warnings_from_stderr(stderr_output)}"

            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()

                if output or stderr_output:
                    error_message = f"Output: {output}\nStderr: {self._filter_warnings_from_stderr(stderr_output)}\nError: {error_message}"

                self.logger.warning(f"Execution {execution.id} failed: {error_message}")
                await self.repository.fail_execution(
                    execution_id=execution.id,
                    error_message=error_message
                )
                return execution, False, error_message

            # 4. Complete execution with result
            self.logger.info(f"Execution {execution.id} completed successfully")

            # Create ExecutionResult object matching Lambda adapter pattern
            execution_result = ExecutionResult(
                stdout=output,
                stderr=self._filter_warnings_from_stderr(stderr_output),
                exit_code=0,
                execution_time_ms=execution_time_ms,
                memory_usage_kb=0,  # Local execution - no easy memory tracking
                output_files=output_files
            )

            # Create metrics matching what repository expects
            metrics = {
                "execution_time_ms": execution_time_ms,
                "memory_usage_kb": 0,
                "success": True,
                "lambda_cold_start": False  # Local execution is never a cold start
            }

            execution = await self.repository.complete_execution(
                execution_id=execution.id,
                result=execution_result,
                metrics=metrics
            )

            return execution, True, None

        except Exception as e:
            error_message = f"Error in local code execution: {str(e)}"
            self.logger.error(error_message)

            # If we created an execution record, mark it as failed
            if 'execution' in locals() and execution and execution.id:
                await self.repository.fail_execution(
                    execution_id=execution.id,
                    error_message=error_message
                )

            return execution if 'execution' in locals() else None, False, error_message

    async def get_execution(self, execution_id: uuid.UUID) -> Optional[CodeExecution]:
        """
        Get execution by ID.
        Tries to fetch from Redis cache first for status updates, falls back to database.
        """
        try:
            # Get execution from database
            execution = await self.repository.get_execution(execution_id)

            if not execution:
                return None

            # Check if there's a more recent status in Redis
            cached_status = await self._get_execution_status_cache(execution_id)
            if cached_status and cached_status != execution.status:
                execution.status = cached_status

            return execution

        except Exception as e:
            self.logger.error(f"Error getting execution {execution_id}: {str(e)}")
            raise


    async def get_processing_executions(self, limit: int = 10) -> List[CodeExecution]:
        """Get processing executions"""
        return await self.repository.get_executions_by_status(ExecutionStatus.PROCESSING, limit)

    async def _update_execution_status_cache(self, execution_id: uuid.UUID, status: ExecutionStatus) -> None:
        """Update execution status in Redis cache"""
        key = f"execution:{execution_id}:status"
        self.redis_client.set_value(key, status.value, expiry=3600)  # 1 hour expiration

    async def _get_execution_status_cache(self, execution_id: uuid.UUID) -> Optional[ExecutionStatus]:
        """Get execution status from Redis cache"""
        key = f"execution:{execution_id}:status"
        status_value = self.redis_client.get_value(key)

        if not status_value:
            return None

        try:
            return ExecutionStatus(status_value)
        except ValueError:
            return None
