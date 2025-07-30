from typing import Dict, Any, Optional, Tuple

from app.code_execution.entity.value_objects import ExecutionResult
from app.code_execution.service.service import ILambdaAdapter
from pkg.lambda_service.lambda_client import LambdaClient
from pkg.log.logger import Logger


class LambdaAdapter(ILambdaAdapter):
    """Adapter for executing code via AWS Lambda"""

    def __init__(self, lambda_client: LambdaClient, logger: Logger):
        """
        Initialize the Lambda adapter
        
        Args:
            lambda_client: Lambda client for AWS interactions
            logger: Logger instance
        """
        self.lambda_client = lambda_client
        self.logger = logger

    async def execute_code(self, 
                           code: str, 
                           input_data: Optional[Dict[str, Any]] = None,
                           timeout_seconds: int = 30) -> Tuple[ExecutionResult, Dict[str, Any]]:
        """
        Execute code using AWS Lambda
        
        Args:
            code: Python code to execute
            input_data: Optional data to provide to the code
            timeout_seconds: Maximum execution time in seconds
            
        Returns:
            Tuple of (ExecutionResult, metrics)
        """
        self.logger.info(f"Executing code via Lambda (timeout: {timeout_seconds}s)")
        
        result, success = await self.lambda_client.invoke_function(
            code=code,
            input_data=input_data,
            timeout_seconds=timeout_seconds
        )
        
        # Extract values from the Lambda response
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", 1 if not success else 0)
        execution_time_ms = result.get("execution_time_ms", 0)
        memory_usage_kb = result.get("memory_usage_kb", 0)
        output_files = result.get("output_files", {})
        
        # Create execution result object
        execution_result = ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time_ms=execution_time_ms,
            memory_usage_kb=memory_usage_kb,
            output_files=output_files
        )
        
        # Metrics for monitoring and analytics
        metrics = {
            "execution_time_ms": execution_time_ms,
            "memory_usage_kb": memory_usage_kb,
            "success": success,
            "lambda_cold_start": result.get("cold_start", False)
        }
        
        return execution_result, metrics
        