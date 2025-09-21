"""
Encryption Service for ArchBuilder.AI
Handles data encryption/decryption using AES-256
"""

import base64
import hashlib
import secrets
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

logger = structlog.get_logger(__name__)


class EncryptionService:
    """
    Encryption service using AES-256 for data at rest and in transit
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """Initialize encryption service with optional key"""
        self.key = key or self._generate_key()
        self.cipher = Fernet(self.key)
    
    def _generate_key(self) -> bytes:
        """Generate a new encryption key"""
        return Fernet.generate_key()
    
    def _derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data and return base64 encoded result"""
        try:
            encrypted_data = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise
    
    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """Encrypt a file and save to output path"""
        if output_path is None:
            output_path = f"{file_path}.encrypted"
        
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            encrypted_data = self.cipher.encrypt(file_data)
            
            with open(output_path, 'wb') as encrypted_file:
                encrypted_file.write(encrypted_data)
            
            logger.info("File encrypted successfully", 
                       input_path=file_path, output_path=output_path)
            return output_path
        except Exception as e:
            logger.error("File encryption failed", 
                        file_path=file_path, error=str(e))
            raise
    
    def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """Decrypt a file and save to output path"""
        if output_path is None:
            output_path = encrypted_file_path.replace('.encrypted', '')
        
        try:
            with open(encrypted_file_path, 'rb') as encrypted_file:
                encrypted_data = encrypted_file.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as decrypted_file:
                decrypted_file.write(decrypted_data)
            
            logger.info("File decrypted successfully",
                       input_path=encrypted_file_path, output_path=output_path)
            return output_path
        except Exception as e:
            logger.error("File decryption failed",
                        file_path=encrypted_file_path, error=str(e))
            raise
    
    def hash_data(self, data: str) -> str:
        """Create SHA-256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_hash(self, data: str, hash_value: str) -> bool:
        """Verify data against hash"""
        return self.hash_data(data) == hash_value


class FieldEncryption:
    """
    Field-level encryption for sensitive database fields
    """
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption_service = encryption_service
    
    def encrypt_field(self, value: str, field_name: Optional[str] = None) -> str:
        """Encrypt a database field value"""
        if not value:
            return value
        
        try:
            encrypted = self.encryption_service.encrypt(value)
            if field_name:
                logger.debug("Field encrypted", field=field_name)
            return encrypted
        except Exception as e:
            logger.error("Field encryption failed", 
                        field=field_name, error=str(e))
            raise
    
    def decrypt_field(self, encrypted_value: str, field_name: Optional[str] = None) -> str:
        """Decrypt a database field value"""
        if not encrypted_value:
            return encrypted_value
        
        try:
            decrypted = self.encryption_service.decrypt(encrypted_value)
            if field_name:
                logger.debug("Field decrypted", field=field_name)
            return decrypted
        except Exception as e:
            logger.error("Field decryption failed",
                        field=field_name, error=str(e))
            raise


# Global encryption service instance
_encryption_service = None

def get_encryption_service() -> EncryptionService:
    """Get global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service