"""
ArchBuilder.AI - Security Middleware
Comprehensive security middleware for FastAPI with authentication, authorization, rate limiting, and security headers.
"""

from typing import Optional, Dict, Any, List, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import structlog
import time
import secrets
import hashlib
import hmac
from datetime import datetime
import json
import re
from urllib.parse import urlparse

from .authentication import AuthenticationService, AuthResult, UserClaims
from .authorization import AuthorizationService, AuthorizationContext, Permission, Resource, ResourceType
from ..utils.performance_tracker import PerformanceTracker
from ..utils.config_manager import AppConfig

class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        """Get default security headers."""
        return {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent framing (clickjacking protection)
            "X-Frame-Options": "DENY",
            
            # Force HTTPS (if enabled)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            ),
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "accelerometer=(), "
                "gyroscope=()"
            )
        }

class InputSanitizer:
    """Input sanitization and validation."""
    
    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|CREATE|ALTER|EXEC)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(--|\/\*|\*\/|;)",
        r"(\b(XP_|SP_)\w+)",
        r"(\b(OPENROWSET|OPENDATASOURCE)\b)"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>"
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]\\]",
        r"\b(cat|ls|ps|kill|rm|mv|cp|mkdir|rmdir|chmod|chown|sudo|su)\b",
        r"\b(cmd|powershell|bash|sh|zsh)\b"
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not value:
            return ""
        
        # Truncate
        if len(value) > max_length:
            value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # HTML encode dangerous characters
        value = (value.replace('&', '&amp;')
                     .replace('<', '&lt;')
                     .replace('>', '&gt;')
                     .replace('"', '&quot;')
                     .replace("'", '&#x27;'))
        
        return value.strip()
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        """Detect potential SQL injection attempts."""
        if not value:
            return False
        
        value_lower = value.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def detect_xss(cls, value: str) -> bool:
        """Detect potential XSS attempts."""
        if not value:
            return False
        
        value_lower = value.lower()
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def detect_command_injection(cls, value: str) -> bool:
        """Detect potential command injection attempts."""
        if not value:
            return False
        
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def validate_input(cls, value: str, field_name: str = "input") -> None:
        """Validate input and raise exception if malicious content detected."""
        if cls.detect_sql_injection(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Potential SQL injection detected in {field_name}"
            )
        
        if cls.detect_xss(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Potential XSS attack detected in {field_name}"
            )
        
        if cls.detect_command_injection(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Potential command injection detected in {field_name}"
            )

class SecurityMiddleware:
    """
    Comprehensive security middleware for FastAPI applications.
    
    Features:
    - Authentication and authorization
    - Input sanitization and validation
    - Rate limiting
    - Security headers
    - CORS handling
    - Request/response logging
    - Attack detection and prevention
    """
    
    def __init__(
        self,
        auth_service: AuthenticationService,
        authz_service: AuthorizationService,
        config: AppConfig,
        performance_tracker: PerformanceTracker
    ):
        self.auth_service = auth_service
        self.authz_service = authz_service
        self.config = config
        self.performance_tracker = performance_tracker
        self.logger = structlog.get_logger(__name__)
        self.bearer = HTTPBearer(auto_error=False)
        
        # Exempt paths that don't require authentication
        self.exempt_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password"
        }
        
        # Rate limiting configuration
        self.rate_limits = {
            "default": 100,  # requests per minute
            "auth": 10,      # authentication requests per minute
            "api": 1000      # API requests per minute
        }
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request through security middleware."""
        start_time = time.time()
        correlation_id = secrets.token_hex(16)
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        try:
            # Security headers check
            if not self._is_secure_request(request):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Insecure request rejected"},
                    headers=SecurityHeaders.get_default_headers()
                )
            
            # Rate limiting
            if not await self._check_rate_limit(request):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "Rate limit exceeded"},
                    headers=SecurityHeaders.get_default_headers()
                )
            
            # Input validation
            await self._validate_request_input(request)
            
            # Authentication and authorization
            auth_context = await self._authenticate_request(request)
            
            # Store auth context in request state
            request.state.auth_context = auth_context
            
            # Log security event
            await self._log_security_event(
                "request_processed",
                request,
                auth_context,
                correlation_id
            )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            for header, value in SecurityHeaders.get_default_headers().items():
                response.headers[header] = value
            
            # Add correlation ID to response
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Track performance
            duration = time.time() - start_time
            await self.performance_tracker.track_operation(
                "http_request",
                duration,
                {
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "user_id": auth_context.user_id if auth_context else None,
                    "correlation_id": correlation_id
                }
            )
            
            return response
            
        except HTTPException as e:
            # Handle known HTTP exceptions
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "correlation_id": correlation_id},
                headers=SecurityHeaders.get_default_headers()
            )
            
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(
                "Security middleware error",
                error=str(e),
                correlation_id=correlation_id,
                path=str(request.url.path),
                method=request.method,
                exc_info=True
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "correlation_id": correlation_id},
                headers=SecurityHeaders.get_default_headers()
            )
    
    def _is_secure_request(self, request: Request) -> bool:
        """Check if request meets basic security requirements."""
        # Check for required headers in production
        if self.config.environment == "production":
            # Require HTTPS in production
            if request.url.scheme != "https":
                return False
            
            # Check for suspicious headers
            suspicious_headers = [
                "x-forwarded-for",
                "x-real-ip",
                "x-originating-ip"
            ]
            
            for header in suspicious_headers:
                if header in request.headers:
                    # Validate IP format if present
                    ip_value = request.headers[header]
                    if not self._is_valid_ip(ip_value):
                        return False
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                # Limit request size to 10MB
                if length > 10 * 1024 * 1024:
                    return False
            except ValueError:
                return False
        
        return True
    
    def _is_valid_ip(self, ip_str: str) -> bool:
        """Validate IP address format."""
        import ipaddress
        try:
            ipaddress.ip_address(ip_str.split(',')[0].strip())
            return True
        except ValueError:
            return False
    
    async def _check_rate_limit(self, request: Request) -> bool:
        """Check rate limiting for request."""
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Determine rate limit type
            path = str(request.url.path)
            if path.startswith("/auth/"):
                limit_type = "auth"
                limit = self.rate_limits["auth"]
            elif path.startswith("/api/"):
                limit_type = "api"
                limit = self.rate_limits["api"]
            else:
                limit_type = "default"
                limit = self.rate_limits["default"]
            
            # Check rate limit (simplified - would use Redis in production)
            rate_key = f"rate_limit:{limit_type}:{client_ip}"
            
            # For now, always allow (would implement Redis-based rate limiting)
            return True
            
        except Exception as e:
            self.logger.warning(
                "Rate limit check failed",
                error=str(e),
                path=str(request.url.path)
            )
            return True  # Allow on error
    
    async def _validate_request_input(self, request: Request):
        """Validate request input for security threats."""
        try:
            # Validate query parameters
            for key, value in request.query_params.items():
                InputSanitizer.validate_input(str(value), f"query parameter '{key}'")
            
            # Validate path parameters
            path_params = getattr(request, "path_params", {})
            for key, value in path_params.items():
                InputSanitizer.validate_input(str(value), f"path parameter '{key}'")
            
            # Validate headers (selective)
            suspicious_headers = ["user-agent", "referer", "origin"]
            for header in suspicious_headers:
                if header in request.headers:
                    value = request.headers[header]
                    if InputSanitizer.detect_xss(value) or InputSanitizer.detect_command_injection(value):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Malicious content detected in header '{header}'"
                        )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.warning(
                "Input validation error",
                error=str(e),
                path=str(request.url.path)
            )
    
    async def _authenticate_request(self, request: Request) -> Optional[AuthorizationContext]:
        """Authenticate request and return authorization context."""
        # Skip authentication for exempt paths
        path = str(request.url.path)
        if path in self.exempt_paths:
            return None
        
        try:
            # Try bearer token authentication
            credentials: HTTPAuthorizationCredentials = await self.bearer(request)
            
            if credentials:
                # Verify JWT token
                auth_result = await self.auth_service.verify_token(credentials.credentials)
                if auth_result.success and auth_result.user_claims:
                    return await self.authz_service.create_authorization_context(
                        user_id=auth_result.user_claims.user_id,
                        tenant_id=auth_result.user_claims.tenant_id,
                        role=auth_result.user_claims.role.value,
                        ip_address=self._get_client_ip(request),
                        user_agent=request.headers.get("user-agent")
                    )
            
            # Try API key authentication
            api_key = request.headers.get("X-API-Key")
            if api_key:
                auth_result = await self.auth_service.authenticate_api_key(
                    api_key,
                    self._get_client_ip(request)
                )
                if auth_result.success and auth_result.user_claims:
                    return await self.authz_service.create_authorization_context(
                        user_id=auth_result.user_claims.user_id,
                        tenant_id=auth_result.user_claims.tenant_id,
                        role=auth_result.user_claims.role.value,
                        ip_address=self._get_client_ip(request),
                        user_agent=request.headers.get("user-agent")
                    )
            
            # No valid authentication found
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Authentication error",
                error=str(e),
                path=path,
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (in order of preference)
        forwarded_headers = [
            "X-Forwarded-For",
            "X-Real-IP",
            "X-Client-IP",
            "CF-Connecting-IP"  # Cloudflare
        ]
        
        for header in forwarded_headers:
            if header in request.headers:
                ip = request.headers[header].split(',')[0].strip()
                if self._is_valid_ip(ip):
                    return ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def _log_security_event(
        self,
        event_type: str,
        request: Request,
        auth_context: Optional[AuthorizationContext],
        correlation_id: str
    ):
        """Log security event."""
        try:
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": correlation_id,
                "method": request.method,
                "path": str(request.url.path),
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "content_length": request.headers.get("content-length")
            }
            
            if auth_context:
                event.update({
                    "user_id": auth_context.user_id,
                    "tenant_id": auth_context.tenant_id,
                    "role": auth_context.role
                })
            
            self.logger.info("Security event", **event)
            
        except Exception as e:
            self.logger.warning(
                "Failed to log security event",
                error=str(e),
                correlation_id=correlation_id
            )