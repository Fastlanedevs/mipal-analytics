import asyncio
import json
from functools import wraps
from typing import Any, Dict, List, Optional, Union

import aioboto3
from botocore.exceptions import ClientError

from pkg.log.logger import Logger


def retry_decorator(retries=3, base_delay=1, max_delay=10):
    """
    Enhanced retry decorator with exponential backoff for async functions
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except ClientError as e:
                    last_exception = e
                    if attempt == retries - 1:
                        # On last attempt, re-raise the exception
                        raise

                    # Calculate backoff with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * 0.2 * (0.5 - (asyncio.get_event_loop().time() % 1.0))
                    backoff = delay + jitter

                    print(f"Attempt {attempt + 1} failed: {e!s}. Retrying in {backoff:.2f}s")
                    await asyncio.sleep(backoff)

            # Should never reach here, but just in case
            raise last_exception if last_exception else RuntimeError("Unknown retry error")

        return wrapper

    return decorator


class SQSClient:
    def __init__(
            self,
            queue_name: str,
            region: str,
            aws_access_key: str,
            aws_secret_key: str,
            logger: Logger,
    ):
        self.logger = logger
        self.queue_name = queue_name
        self.region = region
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key

        # Store credentials for session creation
        self.queue_url = None

        # Connection pool management
        self._connection_lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_connection(self):
        """Ensure connection is initialized (with connection pooling)"""
        if self._initialized:
            return

        async with self._connection_lock:
            if self._initialized:  # Double-check after acquiring lock
                return

            # Create a temporary session to get the queue URL
            session = aioboto3.Session(
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.region
            )

            # Get the queue URL
            async with session.client("sqs") as client:
                response = await client.get_queue_url(QueueName=self.queue_name)
                self.queue_url = response['QueueUrl']

            self._initialized = True

    def _get_session(self):
        """Get a fresh session for each operation"""
        return aioboto3.Session(
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region
        )

    @retry_decorator()
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a single message to the SQS queue using native async

        Args:
            message: Dictionary containing the message payload

        Returns:
            Dict with success status and message ID
        """
        await self._ensure_connection()

        try:
            # Create a fresh session and client for each operation
            session = self._get_session()
            async with session.client("sqs") as client:
                response = await client.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(message),
                    MessageAttributes={
                        "MessageType": {
                            "DataType": "String",
                            "StringValue": "DriveSync",
                        }
                    },
                )

            message_id = response.get('MessageId')
            self.logger.info(f"Message sent: {message_id}")
            return {"success": True, "message_id": message_id}
        except ClientError as e:
            self.logger.error(f"Error sending message: {e!s}")
            raise

    @retry_decorator()
    async def send_message_batch(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple messages in a batch to the SQS queue

        Args:
            messages: List of dictionaries containing message payloads

        Returns:
            Dict with success status and details about successful/failed messages
        """
        if not messages:
            return {"success": False, "successful": [], "failed": []}

        await self._ensure_connection()

        # Prepare message entries
        entries = [
            {
                "Id": str(idx),
                "MessageBody": json.dumps(msg),
                "MessageAttributes": {
                    "MessageType": {"DataType": "String", "StringValue": "DriveSync"}
                },
            }
            for idx, msg in enumerate(messages)
        ]

        try:
            # Create a fresh session and client for each operation
            session = self._get_session()
            async with session.client("sqs") as client:
                response = await client.send_message_batch(
                    QueueUrl=self.queue_url,
                    Entries=entries
                )

            successful = response.get("Successful", [])
            failed = response.get("Failed", [])

            if failed:
                self.logger.warning(f"Some messages failed to send: {failed}")

            return {
                "success": len(successful) > 0,
                "successful": successful,
                "failed": failed,
            }
        except ClientError as e:
            self.logger.error(f"Error sending batch messages: {e!s}")
            raise

    @retry_decorator()
    async def receive_messages(
            self, max_messages: int = 10, wait_time: int = 20, visibility_timeout: int = 300
    ) -> List[Any]:
        """
        Receive messages from the SQS queue using native async

        Args:
            max_messages: Maximum number of messages to receive
            wait_time: Long polling wait time in seconds
            visibility_timeout: Visibility timeout for received messages

        Returns:
            List of SQS Message dictionaries
        """
        await self._ensure_connection()

        try:
            # Create a fresh session and client for each operation
            session = self._get_session()
            async with session.client("sqs") as client:
                response = await client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=max_messages,
                    WaitTimeSeconds=wait_time,
                    VisibilityTimeout=visibility_timeout,
                    AttributeNames=["All"],
                    MessageAttributeNames=["All"],
                )

            # Convert response to list of messages
            messages = response.get('Messages', [])
            return messages
        except ClientError as e:
            self.logger.error(f"Error receiving messages: {e!s}")
            raise

    @retry_decorator()
    async def change_message_visibility(
            self, receipt_handle: str, visibility_timeout: int
    ) -> bool:
        """
        Change the visibility timeout of a message

        Args:
            receipt_handle: The receipt handle of the message
            visibility_timeout: The new visibility timeout in seconds

        Returns:
            bool: True if successful
        """
        await self._ensure_connection()

        try:
            # Create a fresh session and client for each operation
            session = self._get_session()
            async with session.client("sqs") as client:
                await client.change_message_visibility(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=visibility_timeout
                )
            self.logger.debug(f"Changed message visibility timeout to {visibility_timeout} seconds")
            return True
        except ClientError as e:
            self.logger.error(f"Error changing message visibility: {e!s}")
            raise

    @retry_decorator()
    async def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the queue

        Args:
            receipt_handle: The receipt handle of the message to delete

        Returns:
            bool: True if successful
        """
        if not receipt_handle:
            self.logger.error("Cannot delete message: receipt_handle is empty")
            return False

        await self._ensure_connection()

        try:
            # Create a fresh session and client for each operation
            session = self._get_session()
            async with session.client("sqs") as client:
                await client.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=receipt_handle
                )
            return True
        except ClientError as e:
            self.logger.error(f"Error deleting message: {e!s}")
            raise

    @retry_decorator()
    async def delete_message_batch(
            self, receipt_handles: List[str]
    ) -> Dict[str, Any]:
        """
        Delete multiple messages in a batch

        Args:
            receipt_handles: List of receipt handles to delete

        Returns:
            Dict with success status and details about successful/failed deletions
        """
        if not receipt_handles:
            return {"success": False, "successful": [], "failed": []}

        await self._ensure_connection()

        entries = [
            {"Id": str(idx), "ReceiptHandle": handle}
            for idx, handle in enumerate(receipt_handles)
        ]

        try:
            # Create a fresh session and client for each operation
            session = self._get_session()
            async with session.client("sqs") as client:
                response = await client.delete_message_batch(
                    QueueUrl=self.queue_url,
                    Entries=entries
                )

            successful = response.get("Successful", [])
            failed = response.get("Failed", [])

            if failed:
                self.logger.warning(f"Some messages failed to delete: {failed}")

            return {
                "success": len(successful) > 0,
                "successful": successful,
                "failed": failed,
            }
        except ClientError as e:
            self.logger.error(f"Error batch deleting messages: {e!s}")
            raise

    async def close(self):
        """Nothing to close with this implementation"""
        pass

    async def __aenter__(self):
        """Allow usage with async context manager"""
        await self._ensure_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting context"""
        await self.close()


async def main():
    import os

    logger = Logger()
    queue_name = "mipal-sync-documents-queue"
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION")

    # Using as context manager for proper resource cleanup
    client = SQSClient(
        queue_name=queue_name,
        region=region,
        logger=logger,
        aws_access_key=aws_access_key_id,
        aws_secret_key=aws_secret_access_key,
    )

    try:
        # Send test message
        val = await client.send_message({"message": "Hello World"})
        print(val)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())