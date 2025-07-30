import os
from abc import ABC, abstractmethod
from typing import Any, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from pkg.log.logger import Logger


class S3Error(Exception):
    """Custom exception for S3 operations"""

    pass


class IS3Client(ABC):
    @abstractmethod
    def upload_file(
        self,
        file_obj: BinaryIO,
        object_path: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 3600,
        method: str = "GET",
        content_type: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, object_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_file_metadata(self, object_path: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_object(self, bucket_name: str, object_path: str) -> bytes:
        raise NotImplementedError


class S3Client(IS3Client):
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region: str,
        kms_key_id: str,
        logger: Logger,
    ) -> None:
        self.bucket_name = bucket_name
        self.kms_key_id = kms_key_id
        self.logger = logger

        # Configure S3 client with addressing style
        self.s3_config = Config(
            region_name=region,
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            retries={"max_attempts": 3, "mode": "standard"},
        )

        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                config=self.s3_config,
            )
            self.logger.info("S3 client initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize S3 client: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)

    def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 604800,  # Default to 7 days (maximum allowed by AWS)
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL for accessing a file"""
        try:
            # Map HTTP methods to S3 client methods
            method_mapping = {
                "GET": "get_object",
                "PUT": "put_object",
                "DELETE": "delete_object"
            }
            
            client_method = method_mapping.get(method.upper())
            if not client_method:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Log the details for better debugging
            self.logger.info(f"Generating presigned URL for bucket={self.bucket_name}, key={object_path}, method={method}, expiration={expiration}s")

            url = self.s3_client.generate_presigned_url(
                ClientMethod=client_method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_path
                },
                ExpiresIn=expiration
            )
            
            # Log URL generation success (without exposing the full URL for security)
            url_parts = url.split('?')
            base_url = url_parts[0] if len(url_parts) > 0 else 'unknown'
            self.logger.info(f"Successfully generated presigned URL with base: {base_url}")
            
            return url
        except Exception as e:
            error_msg = f"Failed to generate presigned URL for {object_path}: {str(e)}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)

    def upload_file(
        self,
        file_obj: BinaryIO,
        object_path: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            # Prepare extra arguments
            extra_args = {
                "ContentType": content_type,
            }

            # Add encryption parameters
            if self.kms_key_id:
                extra_args.update(
                    {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": self.kms_key_id}
                )

            # Add metadata if provided
            if metadata:
                extra_args["Metadata"] = metadata

            # Perform upload - this is synchronous
            self.s3_client.upload_fileobj(
                file_obj, self.bucket_name, object_path, ExtraArgs=extra_args
            )

            # Generate presigned URL with max allowed expiration (7 days)
            presigned_url = self.generate_presigned_url(
                object_path=object_path,
                expiration=604800,  # 7 days in seconds (max allowed by AWS)
                method="GET",
            )

            # Generate response with file details
            response = {
                "object_path": object_path,
                "bucket": self.bucket_name,
                "content_type": content_type,
                "encryption": "aws:kms" if self.kms_key_id else "AES256",
                "metadata": metadata,
                "presigned_url": presigned_url,
                "url_expiration": 604800,
            }

            self.logger.info(f"File uploaded successfully: {object_path}")
            return response

        except ClientError as e:
            error_msg = f"S3 upload failed for path {object_path}: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during upload for path {object_path}: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)

    def delete_file(self, object_path: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_path)
            self.logger.info(f"File deleted successfully: {object_path}")
            return True

        except ClientError as e:
            error_msg = f"Failed to delete file {object_path}: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)

    def get_file_metadata(self, object_path: str) -> dict[str, Any]:
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=object_path
            )

            metadata = {
                "key": object_path,
                "size": response.get("ContentLength", 0),
                "last_modified": response.get("LastModified"),
                "content_type": response.get("ContentType"),
                "encryption": response.get("ServerSideEncryption"),
                "metadata": response.get("Metadata", {}),
                "etag": response.get("ETag"),
            }

            self.logger.info(f"Retrieved metadata for key: {object_path}")
            return metadata

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                error_msg = f"File not found: {object_path}"
            else:
                error_msg = f"Failed to get metadata for {object_path}: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)

    def get_object(self, bucket_name: str, object_path: str) -> bytes:
        """
        Get an object from S3.
        
        Args:
            bucket_name: The name of the bucket (will use self.bucket_name if this is None)
            object_path: The object key/path in the bucket
            
        Returns:
            The object content as bytes
        """
        try:
            # Use the provided bucket name or default to self.bucket_name
            bucket = bucket_name or self.bucket_name
            response = self.s3_client.get_object(Bucket=bucket, Key=object_path)
            return response['Body'].read()
        except ClientError as e:
            self.logger.error(f"Failed to get object {object_path} from bucket {bucket}: {str(e)}")
            raise S3Error(f"Failed to get object {object_path} from bucket {bucket}: {str(e)}")

    def update_cors(self, allowed_origins: list[str]) -> bool:
        try:
            cors_config = {
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                        "AllowedOrigins": allowed_origins,
                        "ExposeHeaders": [
                            "ETag",
                            "x-amz-server-side-encryption",
                            "x-amz-request-id",
                            "x-amz-id-2",
                        ],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            }

            self.s3_client.put_bucket_cors(
                Bucket=self.bucket_name, CORSConfiguration=cors_config
            )
            self.logger.info("CORS configuration updated successfully")
            return True

        except ClientError as e:
            error_msg = f"Failed to update CORS configuration: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)

    def create_multipart_upload(
        self,
        object_path: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Initialize a multipart upload
        """
        try:
            upload_args = {
                "Bucket": self.bucket_name,
                "Key": object_path,
                "ContentType": content_type,
            }

            if self.kms_key_id:
                upload_args.update(
                    {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": self.kms_key_id}
                )

            if metadata:
                upload_args["Metadata"] = metadata

            response = self.s3_client.create_multipart_upload(**upload_args)
            return response["UploadId"]

        except ClientError as e:
            error_msg = f"Failed to create multipart upload for {object_path}: {e!s}"
            self.logger.error(error_msg)
            raise S3Error(error_msg)


if __name__ == "__main__":
    import requests

    logger = Logger()
    # Initialize S3 client
    s3_client = S3Client(
        bucket_name=os.getenv("S3_BUCKET_NAME"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region=os.getenv("AWS_REGION"),
        kms_key_id=os.getenv("KMS_KEY_ID"),
        logger=logger,
    )
    # Test file content
    test_content = b"This is a test file content"
    object_path = "test/upload_test.txt"
    content_type = "text/plain"

    # Generate PUT URL
    # Generate PUT URL
    put_url = s3_client.generate_presigned_url(
        object_path=object_path,
        method="PUT",
        content_type=content_type,
        expiration=3600,
    )
    print(f"Generated PUT URL: {put_url}")

    # Make the PUT request with minimal headers
    response = requests.put(
        put_url, data=test_content, headers={"Content-Type": content_type}
    )

    if response.status_code == 200:
        print("File uploaded successfully!")

        # Verify by generating a GET URL and retrieving the content
        get_url = s3_client.generate_presigned_url(
            object_path=object_path, method="GET"
        )

        get_response = requests.get(get_url)
        if get_response.status_code == 200:
            print("Retrieved content:", get_response.text)
            assert get_response.text == test_content.decode(), (
                "Content verification failed"
            )
            print("Content verified successfully!")
        else:
            print(f"Failed to retrieve content: {get_response.status_code}")
    else:
        print(f"Upload failed with status code: {response.status_code}")
        print("Response:", response.text)
