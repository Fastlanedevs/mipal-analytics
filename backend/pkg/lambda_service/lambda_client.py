import json
import base64
import aioboto3
import inspect
from typing import Dict, Any, Optional, Tuple, Awaitable
from botocore.exceptions import ClientError

from pkg.log.logger import Logger


class LambdaClient:
    """Client for AWS Lambda service operations"""

    def __init__(self, logger: Logger, region_name: str, function_name: str, aws_access_key_id: str,
                 aws_secret_access_key: str):
        """
        Initialize Lambda client

        Args:
            logger: Logger instance
            region_name: AWS region
            function_name: Name of the Lambda function for code execution
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
        """
        self.logger = logger
        self.region_name = region_name
        self.function_name = function_name
        self.session = aioboto3.Session(region_name=region_name,
                                        aws_access_key_id=aws_access_key_id,
                                        aws_secret_access_key=aws_secret_access_key,
                                        )

    async def invoke_function(self,
                              code: str,
                              input_data: Optional[Dict[str, Any]] = None,
                              timeout_seconds: int = 30) -> Tuple[Dict[str, Any], bool]:
        """
        Invoke Lambda function to execute code

        Args:
            code: Python code to execute
            input_data: Optional data to provide to the code
            timeout_seconds: Maximum execution time in seconds

        Returns:
            Tuple containing (response data, success flag)
        """
        try:
            # Prepare serializable input data
            serializable_input_data = await self._ensure_serializable(input_data)

            payload = {
                "code": code,
                "input_data": serializable_input_data or {},
                "timeout_seconds": timeout_seconds
            }

            # For debugging
            self.logger.info("Checking payload for serialize issues before invoking Lambda")
            try:
                json_payload = json.dumps(payload).encode('utf-8')
                self.logger.info(f"Payload successfully serialized, size: {len(json_payload)} bytes")
            except TypeError as e:
                self.logger.error(f"Serialization error: {e}")
                # Try to identify problematic keys
                for k, v in payload.items():
                    try:
                        json.dumps({k: v})
                    except Exception as e2:
                        self.logger.error(f"Problem with key '{k}': {e2}, type: {type(v)}")
                return {
                    "stdout": "",
                    "stderr": f"Payload serialization error: {str(e)}",
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "memory_usage_kb": 0
                }, False

            async with self.session.client("lambda") as lambda_client:
                self.logger.info(f"Invoking Lambda function: {self.function_name}")

                response = await lambda_client.invoke(
                    FunctionName=self.function_name,
                    InvocationType="RequestResponse",  # Synchronous execution
                    Payload=json_payload
                )

                # Process response
                if response.get("StatusCode") != 200:
                    self.logger.error(f"Lambda invocation error: {response}")
                    return {
                        "stdout": "",
                        "stderr": f"Lambda error: Status code {response.get('StatusCode')}",
                        "exit_code": 1,
                        "execution_time_ms": 0,
                        "memory_usage_kb": 0
                    }, False

                # Read payload from response - this is the key fix
                # In aioboto3, this is an awaitable that must be awaited
                payload_stream = response.get("Payload")
                if payload_stream:
                    # Must await the read operation
                    payload_bytes = await payload_stream.read()
                    try:
                        result = json.loads(payload_bytes)
                    except json.JSONDecodeError as json_error:
                        self.logger.error(f"Failed to parse Lambda response: {json_error}")
                        payload_str = payload_bytes.decode('utf-8', errors='replace')[:500]
                        self.logger.error(f"Raw response (truncated): {payload_str}")
                        return {
                            "stdout": "",
                            "stderr": f"Failed to parse Lambda response: {str(json_error)}. Raw: {payload_str}",
                            "exit_code": 1,
                            "execution_time_ms": 0,
                            "memory_usage_kb": 0
                        }, False
                else:
                    self.logger.error("Lambda response missing Payload")
                    return {
                        "stdout": "",
                        "stderr": "Lambda response missing Payload",
                        "exit_code": 1,
                        "execution_time_ms": 0,
                        "memory_usage_kb": 0
                    }, False

                # Check for function errors
                if "FunctionError" in response:
                    error_msg = result.get("errorMessage", "Unknown Lambda execution error")
                    self.logger.error(f"Lambda function error: {error_msg}")
                    return {
                        "stdout": "",
                        "stderr": f"Lambda execution error: {error_msg}",
                        "exit_code": 1,
                        "execution_time_ms": 0,
                        "memory_usage_kb": 0
                    }, False

                return result, True

        except ClientError as e:
            self.logger.error(f"AWS client error invoking Lambda: {e}")
            return {
                "stdout": "",
                "stderr": f"AWS client error: {str(e)}",
                "exit_code": 1,
                "execution_time_ms": 0,
                "memory_usage_kb": 0
            }, False

        except Exception as e:
            self.logger.error(f"Unexpected error invoking Lambda: {e}")
            return {
                "stdout": "",
                "stderr": f"Unexpected error: {str(e)}",
                "exit_code": 1,
                "execution_time_ms": 0,
                "memory_usage_kb": 0
            }, False

    async def _ensure_serializable(self, data: Any) -> Any:
        """
        Recursively process data to ensure it's JSON serializable.
        Awaits coroutines and processes nested dictionaries and lists.

        Args:
            data: The data to process

        Returns:
            Serializable version of the data
        """
        if data is None:
            return None

        # Handle coroutines/awaitables
        if inspect.iscoroutine(data) or isinstance(data, Awaitable):
            try:
                self.logger.info(f"Awaiting coroutine in input data")
                return await data
            except Exception as e:
                self.logger.error(f"Error awaiting coroutine in input data: {e}")
                return str(e)  # Return error as string instead of failing

        # Handle dictionaries
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = await self._ensure_serializable(value)
            return result

        # Handle lists/tuples
        if isinstance(data, (list, tuple)):
            return [await self._ensure_serializable(item) for item in data]

        # Return other types as is
        return data