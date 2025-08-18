import os
import json
import base64
import secrets
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from pkg.log.logger import Logger

class LocalKMSError(Exception):
    """
    Custom exception for local KMS client errors.
    """
    pass

class IKMSClient():
    """
    Interface for KMS client.
    """

    def encrypt(self, plaintext: str) -> str:
        raise NotImplementedError

    def decrypt(self, ciphertext: str) -> str:
        raise NotImplementedError


class LocalKMSClient(IKMSClient):
    """
    Replacement for AWS KMS client.
    """

    def __init__(
        self,
        encryption_password: str,
        key_storage_path: Optional[str] = None,
        logger: Optional[Logger] = None,
        key_size: int = 32,
    ):
        self.logger = logger or Logger()
        self.encryption_password = encryption_password
        self.key_size = key_size

        if key_storage_path:
            self.key_storage_path = key_storage_path
        else:
            import tempfile
            self.key_storage_path = Path(tempfile.gettempdir()) / ".mipal_kms"

        # Ensure key storage directory exists with secure permissions.
        self.key_storage_path.mkdir(mode=0o700, exist_ok=True)
        
        # Initialize encryption components.
        self._initialize_encryption()

        self.logger.info("Local KMS client initialized successfully")

    def _initialize_encryption(self):
        """
        Initialize encryption components and derive keys.
        """
        try:
            #Generate or load salt for key derivation.
            salt_file = self.key_storage_path / "key.salt"

            if salt_file.exists():
                with open(salt_file, "rb") as f:
                    self.salt = f.read()
                    self.logger.debug("Loaded existing salt from file for key derivation.")
            else:
                self.salt = os.urandom(32)
                with open(salt_file, "wb") as f:
                    f.write(self.salt)
                salt_file.chmod(0o600)
                self.logger.info("Generated new salt for key derivation.")

            # Derive encryption key using PBKDF2.
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.key_size,
                salt=self.salt,
                iterations=100000,
                backend=default_backend()
            )

            self.encryption_key = kdf.derive(self.encryption_password.encode('utf-8'))

            # Create metadata about the key.
            self.key_metadata = {
                "algorithm": "AES-GCM",
                "Key_size_bits": self.key_size * 8,
                "iterations": 100000,
                "created_at": self._get_timestamp(),
                "version": "1.0"
            }
            self.logger.info(f"Encryption key derived successfully (AES - {self.key_size * 8} bits)")

        except Exception as e:
            error_msg = f"Failed to initialize encryption: {str(e)}"
            self.logger.error(error_msg)
            raise LocalKMSError(error_msg)
        

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string using AES-GCM.

        Args:
            plaintext: The plaintext string to encrypt.

        Returns:
            str: Base64-encoded string compatible with AWS KMS format.
        """
        try:
            if not isinstance(plaintext, str):
                raise LocalKMSError("Plaintext must be a string.")
            
            if not plaintext:
                raise LocalKMSError("Cannot encrypt empty string.")
            
            # Generate a random 96-bit (12-byte) nonce for GCM.
            nonce = os.urandom(12)

            # Create AES-GCM cipher with nonce.
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Encrypt the plaintext.
            ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()

            # Get the authentication tag.
            tag = encryptor.tag

            # Create encrypyted payload structure
            encrypted_payload = {
                "version": "1.0",
                "algorithm": "AES-256-GCM",
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "tag": base64.b64encode(tag).decode('utf-8'),
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
            }

            # Serialize and encode the entire payload
            payload_json = json.dumps(encrypted_payload, separators=(',',':'))
            result = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')

            self.logger.debug("Data encrypted successfully.")
            return result
        
        except Exception as e:
            error_msg = f"Local KMS Encryption failed"
            self.logger.error(error_msg)
            raise LocalKMSError(error_msg)
        
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string using AES-GCM

        Args:
        ciphertext : Base64encoded enrypted string from encrypt

        Returns:
        Decrypted plaintext string
        """

        try:
            if not isinstance(ciphertext, str):
                raise LocalKMSError("Ciphertext must be a string")
            
            if not ciphertext:
                raise LocalKMSError("Cannot decrypt empty ciphertext")
            
            try:
                payload_json = base64.b64decode(ciphertext.encode('utf-8')).decode('utf-8')
                encrypted_payload = json.loads(payload_json)
            except Exception as e:
                raise LocalKMSError(f"Invalid ciphertext format: {e}")
            
            # Validate payload sructure
            required_fields = ["version", "algorithm", "nonce", "tag", "ciphertext"]
            missing_fields = [ field for field in required_fields if field not in encrypted_payload]
            if missing_fields:
                raise LocalKMSError(f"Invalid payload structure, missing fields: {missing_fields}")
            
            if encrypted_payload["version"] != 1:
                raise LocalKMSError(f"Unsupported payload version:{encrypted_payload["version"]}")
            
            # Extract components
            nonce = base64.b64decode(encrypted_payload["nonce"].encode('utf-8'))
            tag = base64.b64decode(encrypted_payload["tag"].encode('utf-8'))
            actual_ciphertext = base64.b64decode(encrypted_payload["ciphertext"].encode('utf-8'))

            # Validate nonce and tag
            if len(nonce) != 12:
                raise LocalKMSError(f"Invalid nonce size")
            if len(tag) != 16:
                raise LocalKMSError(f"Invalid authentication tag size")
            
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt the data
            plaintext_bytes = decryptor.update(actual_ciphertext) + decryptor.finalize()
            result = plaintext_bytes.decode('utf-8')

            self.logger.debug("Data decrypted successfully")
            return result
        
        except Exception as e:
            error_msg = f"Local decryption failed : {e}"
            self.logger.error(error_msg)
            raise LocalKMSError(error_msg)
    

    def rotate_password(self, new_password : str) -> None:
        """
        Rotate to a new encryption password

        Note: This will generate a new salt and key.
        Existing encrypted data will need to be re-encrypted with the new key

        """
        try:
            self.logger.info("Starting passord rotation")

            # Backup current salt
            salt_file = self.key_storage_path / "key.salt"
            backup_file = self.key_storage_path / f"key.salt.backup{self._get_timestamp()}"

            if salt_file.exists():
                salt_file.rename(backup_file)
                self.logger.info(f"Backed up old salt to {backup_file}")

            # Update password and re-initialize
            self.encryption_password = new_password
            self._initialize_encryption()

            self.logger.info("Password rotation completed successfully")
        except Exception as e:
            error_msg = f"Password rotation failed : {e}"
            self.logger.error(error_msg)
            raise LocalKMSError(error_msg)
        
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now(datetime.UTC).isoformat() + "Z"
    
# Backward compatability
KMSError = LocalKMSError
KMSClient = LocalKMSClient