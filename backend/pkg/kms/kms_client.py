import os
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode

import boto3
from botocore.exceptions import ClientError

from pkg.log.logger import Logger


class KMSError(Exception):
    """Custom exception for KMS operations"""

    pass


class IKMSClient(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        raise NotImplementedError



class KMSClient(IKMSClient):
    def __init__( self, kms_key_id: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        logger: Logger,
    ) -> None:
        self.kms_key_id = kms_key_id
        self.aws_key = aws_access_key_id
        self.aws_secret = aws_secret_access_key
        self.logger = logger
        try:
            self.kms_client = boto3.client(
                "kms",
                aws_access_key_id=self.aws_key,
                aws_secret_access_key=self.aws_secret,
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize KMS client: {e!s}")
            raise KMSError(f"KMS client initialization failed: {e!s}")

    def encrypt(self, plaintext: str) -> str:
        try:
            response = self.kms_client.encrypt(
                KeyId=self.kms_key_id, Plaintext=plaintext.encode("utf-8")
            )
            encrypted_data = b64encode(response["CiphertextBlob"]).decode("utf-8")
            self.logger.info("Data encrypted successfully")
            return encrypted_data

        except ClientError as e:
            error_msg = f"KMS encryption failed: {e!s}"
            self.logger.error(error_msg)
            raise KMSError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error during encryption: {e!s}"
            self.logger.error(error_msg)
            raise KMSError(error_msg)

    def decrypt(self, ciphertext: str) -> str:
        try:
            # Decode base64 string to bytes
            decoded_ciphertext = b64decode(ciphertext.encode("utf-8"))

            response = self.kms_client.decrypt(
                KeyId=self.kms_key_arn, CiphertextBlob=decoded_ciphertext
            )
            decrypted_data = response["Plaintext"].decode("utf-8")
            self.logger.info("Data decrypted successfully")
            return decrypted_data

        except ClientError as e:
            error_msg = f"KMS decryption failed: {e!s}"
            self.logger.error(error_msg)
            raise KMSError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error during decryption: {e!s}"
            self.logger.error(error_msg)
            raise KMSError(error_msg)


if __name__ == "__main__":
    logger = Logger()

    c = KMSClient(
        os.getenv("KMS_KEY_ID"),
        os.getenv("AWS_ACCESS_KEY_ID"),
        os.getenv("AWS_SECRET_ACCESS_KEY"),
        logger,
    )
    print(c.encrypt("dcnj"))
