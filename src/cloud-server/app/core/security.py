"""
ArchBuilder.AI - Security Utilities
STRIDE Threat Model Implementation with comprehensive security features
"""

import hashlib
import hmac
import secrets
import time
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Request, Response
import bcrypt
import structlog

logger = structlog.get_logger(__name__)

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    try:
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
        
    except Exception as e:
        logger.error("Failed to hash password", error=str(e))
        raise

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
        
    except Exception as e:
        logger.error("Failed to verify password", error=str(e))
        return False

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        Hex-encoded secure token
    """
    return secrets.token_hex(length)

def generate_salt() -> str:
    """Generate a cryptographic salt."""
    return secrets.token_hex(16)

def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    return secrets.compare_digest(a, b)


class SecurityManager:
    """
    Central security manager implementing STRIDE threat model
    """
    
    def __init__(self):
        self.secret_key = secrets.token_urlsafe(32)
    
    def generate_request_signature(self, request_data: Dict[str, Any]) -> str:
        """Generate HMAC signature for request data (Anti-Tampering)"""
        # Serialize request data consistently
        serialized_data = self._serialize_data(request_data)
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            serialized_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug("Request signature generated")
        return signature
    
    def validate_request_signature(self, request_data: Dict[str, Any], signature: str) -> bool:
        """Validate request signature (Anti-Tampering)"""
        expected_signature = self.generate_request_signature(request_data)
        
        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning("Invalid request signature detected", 
                          expected=expected_signature[:8] + "...",
                          received=signature[:8] + "...")
        
        return is_valid
    
    def sign_operation(self, operation_data: Dict[str, Any]) -> str:
        """Generate digital signature for critical operations (Non-Repudiation)"""
        # Add timestamp for freshness
        operation_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Generate signature
        signature = self.generate_request_signature(operation_data)
        
        logger.info("Operation signed", operation_type=operation_data.get("type"))
        return signature
    
    def verify_operation_signature(self, operation_data: Dict[str, Any], signature: str) -> bool:
        """Verify operation signature (Non-Repudiation)"""
        return self.validate_request_signature(operation_data, signature)
    
    def _serialize_data(self, data: Dict[str, Any]) -> str:
        """Serialize data consistently for signing"""
        import json
        return json.dumps(data, sort_keys=True, separators=(',', ':'))


class TokenManager:
    """
    JWT Token Management (Anti-Spoofing)
    """
    
    def __init__(self):
        self.secret_key = secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug("Access token created", user_id=data.get("user_id"))
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug("Refresh token created", user_id=data.get("user_id"))
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                raise HTTPException(status_code=401, detail="Invalid token type")
            
            return payload
        
        except ExpiredSignatureError:
            logger.warning("Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        
        except InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def get_current_user_id(self, token: str) -> int:
        """Extract user ID from token"""
        payload = self.verify_token(token)
        user_id = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        return user_id


class HTTPSRedirectMiddleware:
    """
    HTTPS Enforcement Middleware (Information Disclosure Prevention)
    """
    
    def __init__(self, force_https: bool = True):
        self.force_https = force_https
    
    async def process_request(self, request: Request) -> Optional[Response]:
        """Process request and enforce HTTPS if required"""
        if not self.force_https:
            return None
        
        # Check if request is HTTPS
        if request.url.scheme != "https":
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            
            logger.warning("HTTP request redirected to HTTPS", 
                          original_url=str(request.url),
                          https_url=str(https_url))
            
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=str(https_url), status_code=307)
        
        return None


class InputValidator:
    """
    Input validation and sanitization
    """
    
    @staticmethod
    def sanitize_html_input(input_string: str) -> str:
        """Remove HTML tags and potentially dangerous content"""
        import re
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', input_string)
        
        # Remove potential script content
        clean = re.sub(r'javascript:', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'on\w+\s*=', '', clean, flags=re.IGNORECASE)
        
        return clean.strip()


# Global security instances
security_manager = SecurityManager()
token_manager = TokenManager()
input_validator = InputValidator()