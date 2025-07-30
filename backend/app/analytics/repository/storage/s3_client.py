import os
from typing import Any, BinaryIO, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import io

from pkg.log.logger import Logger
from pkg.s3.s3_client import S3Client

class SchemaS3Client:
    """A simplified S3 client specifically for handling CSV schema uploads"""
    
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,  # Keep this as region_name to match container
        bucket_name: str,
        logger: Logger,
        kms_key_id: str = None  # Add this parameter
    ):
        self.bucket_name = bucket_name
        self.logger = logger
        # Initialize base S3 client with all required parameters
        self.s3_client = S3Client(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region=region_name,  # Convert region_name to region here
            bucket_name=bucket_name,
            logger=logger,
            kms_key_id=kms_key_id  # Pass the KMS key ID
        )

    async def upload_file(self, file_obj, object_path: str, content_type: str = "text/csv"):
        """Upload file to S3"""
        try:
            # The base method is synchronous, no need to await
            storage_info = self.s3_client.upload_file(
                file_obj=file_obj,
                object_path=object_path,
                content_type=content_type
            )

            return storage_info  # This already includes presigned_url, bucket, and object_path

        except Exception as e:
            self.logger.error(f"Failed to upload file: {str(e)}")
            raise

    def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 604800,  # Default to 7 days (maximum allowed by AWS)
    ) -> str:
        """Generate a presigned URL for accessing a file"""
        try:
            url = self.s3_client.generate_presigned_url(
                object_path=object_path,
                expiration=expiration,
                method="GET"  # Use GET as default for CSV files
            )
            return url
        except Exception as e:
            error_msg = f"Failed to generate presigned URL for {object_path}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
    async def get_fresh_presigned_url(self, bucket: str, object_path: str, expiration: int = 604800) -> str:
        """
        Generate a fresh presigned URL for an object with specified expiration.
        This is useful for generating URLs on-demand rather than storing potentially expired ones.
        
        Args:
            bucket: The S3 bucket name
            object_path: The object path within the bucket
            expiration: Expiration time in seconds (default: 7 days)
            
        Returns:
            A presigned URL for accessing the object
        """
        try:
            # If the provided object path already includes the bucket or s3:// prefix, extract just the path
            if object_path.startswith(f"s3://{bucket}/"):
                object_path = object_path.replace(f"s3://{bucket}/", "")
            elif object_path.startswith("s3://"):
                # This is a full S3 URI, extract just the path part after the bucket
                parts = object_path[5:].split('/', 1)  # Remove "s3://" and split on first '/'
                if len(parts) == 2 and parts[0] == bucket:
                    object_path = parts[1]
            
            # Get the AWS region from environment variables for consistency
            aws_region = os.environ.get('AWS_REGION')
            self.logger.info(f"Using AWS region from environment: {aws_region}")
            
            # Create a boto3 client with the explicit region
            s3_config = Config(
                region_name=aws_region,
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
                retries={"max_attempts": 3, "mode": "standard"},
            )
            
            temp_client = boto3.client(
                "s3",
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                config=s3_config,
            )
            
            self.logger.info(f"Generating presigned URL for bucket={bucket}, object_path={object_path} with region={aws_region}")
            
            # Generate URL using environment-configured client
            url = temp_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': bucket,
                    'Key': object_path
                },
                ExpiresIn=expiration
            )
            
            self.logger.info(f"Generated fresh presigned URL with {expiration}s expiration")
            return url
        except Exception as e:
            error_msg = f"Failed to generate fresh presigned URL for {object_path} in bucket {bucket}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def get_object(self, bucket_name: str, object_path: str) -> bytes:
        """
        Get an object from S3.
        
        Args:
            bucket_name: The name of the bucket
            object_path: The path of the object within the bucket
            
        Returns:
            The object content as bytes
        """
        try:
            # Check if we're accessing a different bucket than the configured one
            if bucket_name != self.bucket_name:
                self.logger.info(f"Accessing bucket {bucket_name} which is different from configured bucket {self.bucket_name}")
                
            # Get the AWS region from environment variables for consistency
            aws_region = os.environ.get('AWS_REGION')
            self.logger.info(f"Using AWS region from environment: {aws_region}")
            
            # Create a boto3 client with the explicit region
            s3_config = Config(
                region_name=aws_region,
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
                retries={"max_attempts": 3, "mode": "standard"},
            )
            
            temp_client = boto3.client(
                "s3",
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                config=s3_config,
            )
            
            # Get object using the environment-configured client
            response = temp_client.get_object(Bucket=bucket_name, Key=object_path)
            return response['Body'].read()
        except Exception as e:
            self.logger.error(f"Failed to get object {object_path} from bucket {bucket_name}: {str(e)}")
            raise

    async def get_file(self, storage_path: str) -> io.BytesIO:
        """
        Get a file from S3 and return it as a BytesIO object.
        
        Args:
            storage_path: The path of the file in S3
            
        Returns:
            A BytesIO object containing the file content
        """
        try:
            # If the path is in s3:// format, parse it to get bucket and key
            if storage_path.startswith("s3://"):
                parts = storage_path[5:].split('/', 1)  # Remove "s3://" and split on first '/'
                if len(parts) < 2:
                    raise ValueError(f"Invalid S3 URI format: {storage_path}")
                    
                bucket = parts[0]
                key = parts[1]
                
                self.logger.info(f"Parsed S3 URI: bucket={bucket}, key={key}")
            else:
                # Assume the path is relative to the bucket
                bucket = self.bucket_name
                key = storage_path
                
            # Get the file content directly from S3 (now with region-aware get_object)
            file_content = self.get_object(bucket, key)
            return io.BytesIO(file_content)
            
        except Exception as e:
            self.logger.error(f"Error getting file from S3: {str(e)}")
            raise 