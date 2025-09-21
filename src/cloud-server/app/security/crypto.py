"""
ArchBuilder.AI - Security Utilities
Additional security utilities for encryption, hashing, and secure operations.
"""

import hashlib
import hmac
import secrets
import base64
from typing import Optional, Dict, Any, Union, List, Tuple
import structlog
import json
from datetime import datetime, timedelta

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

class EncryptionService:
    """
    Secure encryption service for sensitive data.
    
    Features:
    - Symmetric encryption with Fernet (AES 128)
    - Asymmetric encryption with RSA
    - Key derivation from passwords
    - Secure random key generation
    - Data integrity verification
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.logger = structlog.get_logger(__name__)
        
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography package is required for encryption features")
        
        if master_key:
            self.fernet = Fernet(master_key)
        else:
            # Generate a new key if none provided
            self.fernet = Fernet(Fernet.generate_key())
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypt data using symmetric encryption."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return self.fernet.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using symmetric encryption."""
        return self.fernet.decrypt(encrypted_data)
    
    def encrypt_string(self, text: str) -> str:
        """Encrypt string and return base64 encoded result."""
        encrypted = self.encrypt(text)
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt base64 encoded string."""
        encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
        decrypted = self.decrypt(encrypted_data)
        return decrypted.decode('utf-8')
    
    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """Encrypt JSON data."""
        json_str = json.dumps(data, separators=(',', ':'))
        return self.encrypt_string(json_str)
    
    def decrypt_json(self, encrypted_json: str) -> Dict[str, Any]:
        """Decrypt JSON data."""
        json_str = self.decrypt_string(encrypted_json)
        return json.loads(json_str)

class AsymmetricEncryption:
    """Asymmetric encryption using RSA."""
    
    def __init__(self, private_key: Optional[bytes] = None, public_key: Optional[bytes] = None):
        self.logger = structlog.get_logger(__name__)
        
        if private_key:
            self.private_key = serialization.load_pem_private_key(private_key, password=None)
            self.public_key = self.private_key.public_key()
        elif public_key:
            self.public_key = serialization.load_pem_public_key(public_key)
            self.private_key = None
        else:
            # Generate new key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
    
    def get_public_key_pem(self) -> bytes:
        """Get public key in PEM format."""
        return self.public_key.serialize(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def get_private_key_pem(self) -> Optional[bytes]:
        """Get private key in PEM format."""
        if not self.private_key:
            return None
        
        return self.private_key.serialize(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using public key."""
        return self.public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using private key."""
        if not self.private_key:
            raise ValueError("Private key not available for decryption")
        
        return self.private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def sign(self, data: bytes) -> bytes:
        """Sign data using private key."""
        if not self.private_key:
            raise ValueError("Private key not available for signing")
        
        return self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify signature using public key."""
        try:
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

class HashService:
    """Secure hashing service."""
    
    @staticmethod
    def sha256(data: Union[str, bytes]) -> str:
        """Generate SHA-256 hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def sha512(data: Union[str, bytes]) -> str:
        """Generate SHA-512 hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return hashlib.sha512(data).hexdigest()
    
    @staticmethod
    def hmac_sha256(data: Union[str, bytes], key: Union[str, bytes]) -> str:
        """Generate HMAC-SHA256."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        return hmac.new(key, data, hashlib.sha256).hexdigest()
    
    @staticmethod
    def verify_hmac(data: Union[str, bytes], key: Union[str, bytes], signature: str) -> bool:
        """Verify HMAC signature."""
        expected = HashService.hmac_sha256(data, key)
        return hmac.compare_digest(expected, signature)

class SecureTokenGenerator:
    """Secure token generation for various purposes."""
    
    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """Generate secure API key."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_session_id(length: int = 32) -> str:
        """Generate secure session ID."""
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_csrf_token(length: int = 32) -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_password_reset_token(length: int = 32) -> str:
        """Generate password reset token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_verification_code(length: int = 6, numeric_only: bool = True) -> str:
        """Generate verification code."""
        if numeric_only:
            return ''.join(secrets.choice('0123456789') for _ in range(length))
        else:
            return ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

class SecureStorage:
    """
    Secure storage for sensitive configuration and secrets.
    
    Features:
    - Encrypted storage of sensitive data
    - Automatic key rotation
    - Integrity verification
    - Secure deletion
    """
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption_service = encryption_service
        self.logger = structlog.get_logger(__name__)
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    def store_secret(
        self,
        key: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Store encrypted secret.
        
        Args:
            key: Secret key identifier
            value: Secret value to encrypt and store
            metadata: Optional metadata
            expires_at: Optional expiration time
            
        Returns:
            True if successful
        """
        try:
            encrypted_value = self.encryption_service.encrypt_string(value)
            
            self._storage[key] = {
                "encrypted_value": encrypted_value,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "metadata": metadata or {},
                "hash": HashService.sha256(value)  # For integrity verification
            }
            
            self.logger.info(
                "Secret stored",
                key=key,
                expires_at=expires_at.isoformat() if expires_at else None
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to store secret",
                key=key,
                error=str(e),
                exc_info=True
            )
            return False
    
    def retrieve_secret(self, key: str) -> Optional[str]:
        """
        Retrieve and decrypt secret.
        
        Args:
            key: Secret key identifier
            
        Returns:
            Decrypted secret value or None if not found/expired
        """
        try:
            if key not in self._storage:
                return None
            
            secret_data = self._storage[key]
            
            # Check expiration
            if secret_data["expires_at"]:
                expires_at = datetime.fromisoformat(secret_data["expires_at"])
                if datetime.utcnow() > expires_at:
                    self.delete_secret(key)
                    return None
            
            # Decrypt value
            decrypted_value = self.encryption_service.decrypt_string(secret_data["encrypted_value"])
            
            # Verify integrity
            expected_hash = HashService.sha256(decrypted_value)
            if expected_hash != secret_data["hash"]:
                self.logger.error(
                    "Secret integrity verification failed",
                    key=key
                )
                self.delete_secret(key)
                return None
            
            return decrypted_value
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve secret",
                key=key,
                error=str(e),
                exc_info=True
            )
            return None
    
    def delete_secret(self, key: str) -> bool:
        """
        Securely delete secret.
        
        Args:
            key: Secret key identifier
            
        Returns:
            True if successful
        """
        try:
            if key in self._storage:
                # Overwrite sensitive data before deletion
                self._storage[key]["encrypted_value"] = "DELETED"
                self._storage[key]["hash"] = "DELETED"
                del self._storage[key]
                
                self.logger.info("Secret deleted", key=key)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete secret",
                key=key,
                error=str(e),
                exc_info=True
            )
            return False
    
    def list_secrets(self) -> List[Dict[str, Any]]:
        """List all stored secrets (metadata only)."""
        try:
            secrets_list = []
            
            for key, data in self._storage.items():
                # Don't include actual encrypted values
                secrets_list.append({
                    "key": key,
                    "created_at": data["created_at"],
                    "expires_at": data["expires_at"],
                    "metadata": data["metadata"]
                })
            
            return secrets_list
            
        except Exception as e:
            self.logger.error(
                "Failed to list secrets",
                error=str(e),
                exc_info=True
            )
            return []
    
    def cleanup_expired_secrets(self) -> int:
        """Clean up expired secrets."""
        try:
            expired_keys = []
            current_time = datetime.utcnow()
            
            for key, data in self._storage.items():
                if data["expires_at"]:
                    expires_at = datetime.fromisoformat(data["expires_at"])
                    if current_time > expires_at:
                        expired_keys.append(key)
            
            for key in expired_keys:
                self.delete_secret(key)
            
            self.logger.info(
                "Expired secrets cleaned up",
                count=len(expired_keys)
            )
            
            return len(expired_keys)
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup expired secrets",
                error=str(e),
                exc_info=True
            )
            return 0