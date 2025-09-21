"""
ArchBuilder.AI - Authentication Service
OAuth2 + JWT authentication with secure token management, rate limiting, and multi-factor authentication.
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import bcrypt
import structlog
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import redis.asyncio as redis
import json
import time
from pydantic import BaseModel

class UserRole(Enum):
    """User roles for authorization."""
    ADMIN = "admin"
    ARCHITECT = "architect"
    VIEWER = "viewer"
    API_CLIENT = "api_client"

class TokenType(Enum):
    """Token types for different purposes."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    RESET_PASSWORD = "reset_password"

@dataclass
class UserClaims:
    """User claims for JWT tokens."""
    user_id: str
    email: str
    role: UserRole
    tenant_id: str
    permissions: List[str]
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role.value,
            "tenant_id": self.tenant_id,
            "permissions": self.permissions,
            "is_active": self.is_active
        }

@dataclass
class AuthResult:
    """Authentication result."""
    success: bool
    user_claims: Optional[UserClaims] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None

@dataclass
class LoginAttempt:
    """Track login attempts for rate limiting."""
    ip_address: str
    email: str
    timestamp: datetime
    success: bool
    user_agent: Optional[str] = None

class SecurityConfig(BaseModel):
    """Security configuration."""
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    password_hash_rounds: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    api_key_length: int = 32
    require_mfa: bool = False
    allowed_origins: List[str] = []

class AuthenticationService:
    """
    Comprehensive authentication service with security best practices.
    
    Features:
    - JWT token-based authentication
    - Secure password hashing with bcrypt
    - Rate limiting for login attempts
    - Account lockout protection
    - API key authentication
    - Multi-factor authentication (optional)
    - Token refresh and rotation
    - Audit logging for security events
    """
    
    def __init__(
        self,
        config: SecurityConfig,
        redis_client: redis.Redis,
        correlation_id: str = None
    ):
        self.config = config
        self.redis_client = redis_client
        self.logger = structlog.get_logger(__name__)
        self.correlation_id = correlation_id or secrets.token_hex(16)
        
        # Password hashing
        self.password_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=config.password_hash_rounds
        )
        
        # OAuth2 scheme for FastAPI
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
        self.bearer_scheme = HTTPBearer()
        
        # Cache keys
        self.LOGIN_ATTEMPTS_KEY = "login_attempts"
        self.BLACKLISTED_TOKENS_KEY = "blacklisted_tokens"
        self.ACTIVE_SESSIONS_KEY = "active_sessions"
        self.API_KEYS_KEY = "api_keys"
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str = None,
        require_mfa: bool = None
    ) -> AuthResult:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email address
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            require_mfa: Override MFA requirement
            
        Returns:
            Authentication result
        """
        try:
            # Check rate limiting
            if await self._is_rate_limited(email, ip_address):
                await self._log_security_event(
                    "authentication_rate_limited",
                    {
                        "email": email,
                        "ip_address": ip_address,
                        "user_agent": user_agent
                    }
                )
                
                return AuthResult(
                    success=False,
                    error_message="Too many failed login attempts. Please try again later.",
                    correlation_id=self.correlation_id
                )
            
            # Validate input
            if not email or not password:
                await self._record_login_attempt(email, ip_address, False, user_agent)
                return AuthResult(
                    success=False,
                    error_message="Email and password are required",
                    correlation_id=self.correlation_id
                )
            
            # Get user from database (placeholder - would integrate with actual user store)
            user_data = await self._get_user_by_email(email)
            if not user_data:
                await self._record_login_attempt(email, ip_address, False, user_agent)
                return AuthResult(
                    success=False,
                    error_message="Invalid email or password",
                    correlation_id=self.correlation_id
                )
            
            # Verify password
            if not self.password_context.verify(password, user_data["password_hash"]):
                await self._record_login_attempt(email, ip_address, False, user_agent)
                
                await self._log_security_event(
                    "authentication_failed",
                    {
                        "email": email,
                        "ip_address": ip_address,
                        "reason": "invalid_password"
                    }
                )
                
                return AuthResult(
                    success=False,
                    error_message="Invalid email or password",
                    correlation_id=self.correlation_id
                )
            
            # Check if user is active
            if not user_data.get("is_active", True):
                await self._record_login_attempt(email, ip_address, False, user_agent)
                return AuthResult(
                    success=False,
                    error_message="Account is disabled",
                    correlation_id=self.correlation_id
                )
            
            # Create user claims
            user_claims = UserClaims(
                user_id=user_data["id"],
                email=user_data["email"],
                role=UserRole(user_data["role"]),
                tenant_id=user_data["tenant_id"],
                permissions=user_data.get("permissions", []),
                is_active=user_data.get("is_active", True)
            )
            
            # Check MFA if required
            require_mfa = require_mfa or self.config.require_mfa
            if require_mfa and user_data.get("mfa_enabled", False):
                # For now, return a special token that requires MFA completion
                mfa_token = await self._create_mfa_token(user_claims)
                return AuthResult(
                    success=False,
                    error_message="MFA required",
                    access_token=mfa_token,
                    correlation_id=self.correlation_id
                )
            
            # Generate tokens
            access_token = await self._create_access_token(user_claims)
            refresh_token = await self._create_refresh_token(user_claims)
            
            # Record successful login
            await self._record_login_attempt(email, ip_address, True, user_agent)
            
            # Store active session
            await self._store_active_session(user_claims.user_id, access_token, ip_address)
            
            await self._log_security_event(
                "authentication_success",
                {
                    "user_id": user_claims.user_id,
                    "email": email,
                    "ip_address": ip_address,
                    "role": user_claims.role.value
                }
            )
            
            return AuthResult(
                success=True,
                user_claims=user_claims,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.config.access_token_expire_minutes * 60,
                correlation_id=self.correlation_id
            )
            
        except Exception as e:
            self.logger.error(
                "Authentication error",
                error=str(e),
                email=email,
                correlation_id=self.correlation_id,
                exc_info=True
            )
            
            return AuthResult(
                success=False,
                error_message="Authentication failed due to internal error",
                correlation_id=self.correlation_id
            )
    
    async def authenticate_api_key(
        self,
        api_key: str,
        ip_address: str
    ) -> AuthResult:
        """
        Authenticate using API key.
        
        Args:
            api_key: API key
            ip_address: Client IP address
            
        Returns:
            Authentication result
        """
        try:
            # Validate API key format
            if not api_key or len(api_key) != self.config.api_key_length:
                return AuthResult(
                    success=False,
                    error_message="Invalid API key format",
                    correlation_id=self.correlation_id
                )
            
            # Get API key data from cache/database
            api_key_data = await self._get_api_key_data(api_key)
            if not api_key_data:
                await self._log_security_event(
                    "api_key_authentication_failed",
                    {
                        "api_key_prefix": api_key[:8] + "...",
                        "ip_address": ip_address,
                        "reason": "invalid_key"
                    }
                )
                
                return AuthResult(
                    success=False,
                    error_message="Invalid API key",
                    correlation_id=self.correlation_id
                )
            
            # Check if API key is active
            if not api_key_data.get("is_active", True):
                return AuthResult(
                    success=False,
                    error_message="API key is disabled",
                    correlation_id=self.correlation_id
                )
            
            # Check expiration
            expires_at = api_key_data.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
                return AuthResult(
                    success=False,
                    error_message="API key has expired",
                    correlation_id=self.correlation_id
                )
            
            # Create user claims for API client
            user_claims = UserClaims(
                user_id=api_key_data["user_id"],
                email=api_key_data.get("email", f"api-{api_key_data['user_id']}"),
                role=UserRole.API_CLIENT,
                tenant_id=api_key_data["tenant_id"],
                permissions=api_key_data.get("permissions", []),
                is_active=True
            )
            
            # Update last used timestamp
            await self._update_api_key_usage(api_key, ip_address)
            
            await self._log_security_event(
                "api_key_authentication_success",
                {
                    "user_id": user_claims.user_id,
                    "api_key_id": api_key_data["id"],
                    "ip_address": ip_address
                }
            )
            
            return AuthResult(
                success=True,
                user_claims=user_claims,
                correlation_id=self.correlation_id
            )
            
        except Exception as e:
            self.logger.error(
                "API key authentication error",
                error=str(e),
                api_key_prefix=api_key[:8] + "..." if api_key else None,
                correlation_id=self.correlation_id,
                exc_info=True
            )
            
            return AuthResult(
                success=False,
                error_message="API key authentication failed",
                correlation_id=self.correlation_id
            )
    
    async def verify_jwt_token(
        self,
        token: str,
        token_type: TokenType = TokenType.ACCESS
    ) -> AuthResult:
        """
        Verify JWT token and extract user claims.
        
        Args:
            token: JWT token
            token_type: Type of token to verify
            
        Returns:
            Authentication result with user claims
        """
        try:
            # Check if token is blacklisted
            if await self._is_token_blacklisted(token):
                return AuthResult(
                    success=False,
                    error_message="Token has been revoked",
                    correlation_id=self.correlation_id
                )
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            
            # Verify token type
            if payload.get("type") != token_type.value:
                return AuthResult(
                    success=False,
                    error_message="Invalid token type",
                    correlation_id=self.correlation_id
                )
            
            # Extract user claims
            user_claims = UserClaims(
                user_id=payload["user_id"],
                email=payload["email"],
                role=UserRole(payload["role"]),
                tenant_id=payload["tenant_id"],
                permissions=payload.get("permissions", []),
                is_active=payload.get("is_active", True)
            )
            
            # Verify user is still active (could check database)
            if not user_claims.is_active:
                return AuthResult(
                    success=False,
                    error_message="User account is disabled",
                    correlation_id=self.correlation_id
                )
            
            return AuthResult(
                success=True,
                user_claims=user_claims,
                correlation_id=self.correlation_id
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                error_message="Token has expired",
                correlation_id=self.correlation_id
            )
        except jwt.InvalidTokenError:
            return AuthResult(
                success=False,
                error_message="Invalid token",
                correlation_id=self.correlation_id
            )
        except Exception as e:
            self.logger.error(
                "Token verification error",
                error=str(e),
                correlation_id=self.correlation_id,
                exc_info=True
            )
            
            return AuthResult(
                success=False,
                error_message="Token verification failed",
                correlation_id=self.correlation_id
            )
    
    async def refresh_token(
        self,
        refresh_token: str,
        ip_address: str
    ) -> AuthResult:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            ip_address: Client IP address
            
        Returns:
            New authentication result with fresh tokens
        """
        # Verify refresh token
        auth_result = await self.verify_jwt_token(refresh_token, TokenType.REFRESH)
        if not auth_result.success or not auth_result.user_claims:
            return auth_result
        
        # Generate new tokens
        access_token = await self._create_access_token(auth_result.user_claims)
        new_refresh_token = await self._create_refresh_token(auth_result.user_claims)
        
        # Invalidate old refresh token
        await self._blacklist_token(refresh_token)
        
        # Store new active session
        await self._store_active_session(
            auth_result.user_claims.user_id, 
            access_token, 
            ip_address
        )
        
        await self._log_security_event(
            "token_refreshed",
            {
                "user_id": auth_result.user_claims.user_id,
                "ip_address": ip_address
            }
        )
        
        return AuthResult(
            success=True,
            user_claims=auth_result.user_claims,
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60,
            correlation_id=self.correlation_id
        )
    
    async def logout(
        self,
        access_token: str,
        refresh_token: str = None,
        user_id: str = None
    ) -> bool:
        """
        Logout user and invalidate tokens.
        
        Args:
            access_token: Access token to invalidate
            refresh_token: Refresh token to invalidate (optional)
            user_id: User ID for session cleanup
            
        Returns:
            True if successful
        """
        try:
            # Blacklist tokens
            await self._blacklist_token(access_token)
            if refresh_token:
                await self._blacklist_token(refresh_token)
            
            # Remove active session
            if user_id:
                await self._remove_active_session(user_id, access_token)
            
            await self._log_security_event(
                "user_logout",
                {
                    "user_id": user_id,
                    "tokens_invalidated": 2 if refresh_token else 1
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Logout error",
                error=str(e),
                user_id=user_id,
                correlation_id=self.correlation_id,
                exc_info=True
            )
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.password_context.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return self.password_context.verify(password, password_hash)
    
    async def create_api_key(
        self,
        user_id: str,
        tenant_id: str,
        name: str,
        permissions: List[str] = None,
        expires_days: int = None
    ) -> Dict[str, str]:
        """
        Create new API key for user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            name: API key name/description
            permissions: List of permissions (optional)
            expires_days: Expiration in days (optional)
            
        Returns:
            Dictionary with API key and metadata
        """
        # Generate secure API key
        api_key = secrets.token_urlsafe(self.config.api_key_length)
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Store API key data
        api_key_data = {
            "id": secrets.token_hex(16),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "name": name,
            "permissions": permissions or [],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_active": True,
            "last_used": None
        }
        
        # Store in Redis (in production, also store in database)
        await self.redis_client.hset(
            f"{self.API_KEYS_KEY}:{api_key}",
            mapping={k: json.dumps(v) if isinstance(v, (list, dict)) else str(v) 
                    for k, v in api_key_data.items()}
        )
        
        # Set expiration on Redis key if needed
        if expires_at:
            await self.redis_client.expireat(
                f"{self.API_KEYS_KEY}:{api_key}",
                expires_at
            )
        
        await self._log_security_event(
            "api_key_created",
            {
                "user_id": user_id,
                "api_key_id": api_key_data["id"],
                "name": name,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
        )
        
        return {
            "api_key": api_key,
            "id": api_key_data["id"],
            "name": name,
            "created_at": api_key_data["created_at"],
            "expires_at": api_key_data["expires_at"]
        }
    
    async def _create_access_token(self, user_claims: UserClaims) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
        
        payload = {
            **user_claims.to_dict(),
            "type": TokenType.ACCESS.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)  # JWT ID for tracking
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
    
    async def _create_refresh_token(self, user_claims: UserClaims) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        
        payload = {
            **user_claims.to_dict(),
            "type": TokenType.REFRESH.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
    
    async def _create_mfa_token(self, user_claims: UserClaims) -> str:
        """Create temporary MFA token."""
        expire = datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry
        
        payload = {
            **user_claims.to_dict(),
            "type": "mfa_pending",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
    
    async def _is_rate_limited(self, email: str, ip_address: str) -> bool:
        """Check if login attempts are rate limited."""
        try:
            # Check attempts by email
            email_key = f"{self.LOGIN_ATTEMPTS_KEY}:email:{email}"
            email_attempts = await self.redis_client.get(email_key)
            
            if email_attempts and int(email_attempts) >= self.config.max_login_attempts:
                return True
            
            # Check attempts by IP
            ip_key = f"{self.LOGIN_ATTEMPTS_KEY}:ip:{ip_address}"
            ip_attempts = await self.redis_client.get(ip_key)
            
            if ip_attempts and int(ip_attempts) >= self.config.max_login_attempts * 3:  # Higher limit for IP
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(
                "Rate limit check failed",
                error=str(e),
                correlation_id=self.correlation_id
            )
            return False
    
    async def _record_login_attempt(
        self,
        email: str,
        ip_address: str,
        success: bool,
        user_agent: str = None
    ):
        """Record login attempt for rate limiting."""
        try:
            if not success:
                # Increment failed attempts
                email_key = f"{self.LOGIN_ATTEMPTS_KEY}:email:{email}"
                ip_key = f"{self.LOGIN_ATTEMPTS_KEY}:ip:{ip_address}"
                
                # Increment and set expiry
                await self.redis_client.incr(email_key)
                await self.redis_client.expire(email_key, self.config.lockout_duration_minutes * 60)
                
                await self.redis_client.incr(ip_key)
                await self.redis_client.expire(ip_key, self.config.lockout_duration_minutes * 60)
            else:
                # Reset failed attempts on success
                email_key = f"{self.LOGIN_ATTEMPTS_KEY}:email:{email}"
                ip_key = f"{self.LOGIN_ATTEMPTS_KEY}:ip:{ip_address}"
                
                await self.redis_client.delete(email_key, ip_key)
            
            # Store login attempt for audit
            attempt = LoginAttempt(
                ip_address=ip_address,
                email=email,
                timestamp=datetime.utcnow(),
                success=success,
                user_agent=user_agent
            )
            
            # Store in audit log (Redis list with expiration)
            audit_key = f"audit:login_attempts:{datetime.utcnow().strftime('%Y%m%d')}"
            await self.redis_client.lpush(audit_key, json.dumps({
                "ip_address": attempt.ip_address,
                "email": attempt.email,
                "timestamp": attempt.timestamp.isoformat(),
                "success": attempt.success,
                "user_agent": attempt.user_agent
            }))
            await self.redis_client.expire(audit_key, 86400 * 30)  # Keep for 30 days
            
        except Exception as e:
            self.logger.warning(
                "Failed to record login attempt",
                error=str(e),
                correlation_id=self.correlation_id
            )
    
    async def _blacklist_token(self, token: str):
        """Add token to blacklist."""
        try:
            # Extract expiration from token
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm],
                options={"verify_exp": False}
            )
            
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # Store until token naturally expires
                expire_time = datetime.fromtimestamp(exp)
                ttl = int((expire_time - datetime.utcnow()).total_seconds())
                
                if ttl > 0:
                    await self.redis_client.setex(
                        f"{self.BLACKLISTED_TOKENS_KEY}:{jti}",
                        ttl,
                        "blacklisted"
                    )
                    
        except Exception as e:
            self.logger.warning(
                "Failed to blacklist token",
                error=str(e),
                correlation_id=self.correlation_id
            )
    
    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm],
                options={"verify_exp": False}
            )
            
            jti = payload.get("jti")
            if jti:
                result = await self.redis_client.get(f"{self.BLACKLISTED_TOKENS_KEY}:{jti}")
                return result is not None
            
            return False
            
        except Exception:
            return False
    
    async def _store_active_session(self, user_id: str, token: str, ip_address: str):
        """Store active session information."""
        try:
            session_data = {
                "token": token,
                "ip_address": ip_address,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.hset(
                f"{self.ACTIVE_SESSIONS_KEY}:{user_id}",
                token,
                json.dumps(session_data)
            )
            
            # Set expiration
            await self.redis_client.expire(
                f"{self.ACTIVE_SESSIONS_KEY}:{user_id}",
                self.config.access_token_expire_minutes * 60
            )
            
        except Exception as e:
            self.logger.warning(
                "Failed to store active session",
                error=str(e),
                user_id=user_id,
                correlation_id=self.correlation_id
            )
    
    async def _remove_active_session(self, user_id: str, token: str):
        """Remove active session."""
        try:
            await self.redis_client.hdel(
                f"{self.ACTIVE_SESSIONS_KEY}:{user_id}",
                token
            )
        except Exception as e:
            self.logger.warning(
                "Failed to remove active session",
                error=str(e),
                user_id=user_id,
                correlation_id=self.correlation_id
            )
    
    async def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user data by email (placeholder for database integration)."""
        # This would integrate with your user database
        # For demo purposes, return a mock user
        if email == "admin@archbuilder.ai":
            return {
                "id": "admin-001",
                "email": email,
                "password_hash": self.hash_password("admin123"),  # In real app, this would be pre-hashed
                "role": "admin",
                "tenant_id": "default",
                "permissions": ["*"],
                "is_active": True,
                "mfa_enabled": False
            }
        return None
    
    async def _get_api_key_data(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get API key data from storage."""
        try:
            key_data = await self.redis_client.hgetall(f"{self.API_KEYS_KEY}:{api_key}")
            if key_data:
                # Convert back from Redis string values
                result = {}
                for k, v in key_data.items():
                    if k in ["permissions"]:
                        result[k] = json.loads(v) if v else []
                    elif k in ["is_active"]:
                        result[k] = v.lower() == "true"
                    else:
                        result[k] = v
                return result
            return None
        except Exception as e:
            self.logger.warning(
                "Failed to get API key data",
                error=str(e),
                correlation_id=self.correlation_id
            )
            return None
    
    async def _update_api_key_usage(self, api_key: str, ip_address: str):
        """Update API key last used timestamp."""
        try:
            await self.redis_client.hset(
                f"{self.API_KEYS_KEY}:{api_key}",
                "last_used",
                datetime.utcnow().isoformat()
            )
        except Exception as e:
            self.logger.warning(
                "Failed to update API key usage",
                error=str(e),
                correlation_id=self.correlation_id
            )
    
    async def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event for audit trail."""
        try:
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": self.correlation_id,
                "details": details
            }
            
            # Store in audit log
            audit_key = f"audit:security_events:{datetime.utcnow().strftime('%Y%m%d')}"
            await self.redis_client.lpush(audit_key, json.dumps(event))
            await self.redis_client.expire(audit_key, 86400 * 90)  # Keep for 90 days
            
            # Log to structured logger
            self.logger.info(
                "Security event",
                event_type=event_type,
                correlation_id=self.correlation_id,
                **details
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log security event",
                error=str(e),
                correlation_id=self.correlation_id,
                exc_info=True
            )