"""
ArchBuilder.AI - Authorization Service
Role-based access control (RBAC) with fine-grained permissions, tenant isolation, and resource-level authorization.
"""

from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
import structlog
from abc import ABC, abstractmethod
from datetime import datetime
import secrets

try:
    import redis.asyncio as redis
except ImportError:
    import redis

class Permission(Enum):
    """System permissions."""
    # Project permissions
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_SHARE = "project:share"
    
    # Document permissions
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_PROCESS = "document:process"
    
    # AI permissions
    AI_GENERATE = "ai:generate"
    AI_ANALYZE = "ai:analyze"
    AI_OPTIMIZE = "ai:optimize"
    AI_VALIDATE = "ai:validate"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SYSTEM = "admin:system"
    
    # API permissions
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"
    
    # Special permissions
    ALL = "*"

class ResourceType(Enum):
    """Resource types for fine-grained authorization."""
    PROJECT = "project"
    DOCUMENT = "document"
    USER = "user"
    TENANT = "tenant"
    API_KEY = "api_key"
    SYSTEM = "system"

@dataclass
class AuthorizationContext:
    """Authorization context for requests."""
    user_id: str
    tenant_id: str
    role: str
    permissions: List[str]
    ip_address: str
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def has_permission(self, permission: Union[Permission, str]) -> bool:
        """Check if user has specific permission."""
        if isinstance(permission, Permission):
            permission = permission.value
        
        # Wildcard permission grants everything
        if Permission.ALL.value in self.permissions:
            return True
        
        return permission in self.permissions

@dataclass
class Resource:
    """Resource for authorization checks."""
    type: ResourceType
    id: str
    tenant_id: str
    owner_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AuthorizationRequest:
    """Authorization request."""
    context: AuthorizationContext
    permission: Union[Permission, str]
    resource: Optional[Resource] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AuthorizationResult:
    """Authorization result."""
    allowed: bool
    reason: Optional[str] = None
    required_permissions: Optional[List[str]] = None
    correlation_id: Optional[str] = None

class AuthorizationPolicy(ABC):
    """Base class for authorization policies."""
    
    @abstractmethod
    async def evaluate(
        self,
        request: AuthorizationRequest
    ) -> AuthorizationResult:
        """Evaluate authorization request."""
        pass

class TenantIsolationPolicy(AuthorizationPolicy):
    """Enforce tenant isolation."""
    
    async def evaluate(
        self,
        request: AuthorizationRequest
    ) -> AuthorizationResult:
        """Ensure users can only access resources in their tenant."""
        if not request.resource:
            return AuthorizationResult(allowed=True)
        
        # System admin can access all tenants
        if request.context.role == "admin" and Permission.ADMIN_SYSTEM.value in request.context.permissions:
            return AuthorizationResult(allowed=True)
        
        # Check tenant isolation
        if request.resource.tenant_id != request.context.tenant_id:
            return AuthorizationResult(
                allowed=False,
                reason="Access denied: Resource belongs to different tenant",
                correlation_id=request.context.correlation_id
            )
        
        return AuthorizationResult(allowed=True)

class PermissionPolicy(AuthorizationPolicy):
    """Check basic permission requirements."""
    
    async def evaluate(
        self,
        request: AuthorizationRequest
    ) -> AuthorizationResult:
        """Check if user has required permission."""
        if request.context.has_permission(request.permission):
            return AuthorizationResult(allowed=True)
        
        permission_str = request.permission.value if isinstance(request.permission, Permission) else request.permission
        
        return AuthorizationResult(
            allowed=False,
            reason=f"Access denied: Missing permission '{permission_str}'",
            required_permissions=[permission_str],
            correlation_id=request.context.correlation_id
        )

class OwnershipPolicy(AuthorizationPolicy):
    """Check resource ownership for sensitive operations."""
    
    def __init__(self, ownership_required_permissions: Optional[Set[str]] = None):
        self.ownership_required_permissions = ownership_required_permissions or {
            Permission.PROJECT_DELETE.value,
            Permission.DOCUMENT_DELETE.value
        }
    
    async def evaluate(
        self,
        request: AuthorizationRequest
    ) -> AuthorizationResult:
        """Check resource ownership for sensitive operations."""
        if not request.resource:
            return AuthorizationResult(allowed=True)
        
        permission_str = request.permission.value if isinstance(request.permission, Permission) else request.permission
        
        # Check if this permission requires ownership
        if permission_str not in self.ownership_required_permissions:
            return AuthorizationResult(allowed=True)
        
        # Admin can access all resources
        if request.context.role == "admin":
            return AuthorizationResult(allowed=True)
        
        # Check ownership
        if request.resource.owner_id and request.resource.owner_id != request.context.user_id:
            return AuthorizationResult(
                allowed=False,
                reason="Access denied: You can only perform this action on resources you own",
                correlation_id=request.context.correlation_id
            )
        
        return AuthorizationResult(allowed=True)

class RateLimitPolicy(AuthorizationPolicy):
    """Rate limiting policy for API operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.limits = {
            # Per-user limits (requests per hour)
            "architect": 1000,
            "viewer": 100,
            "api_client": 5000,
            "admin": 10000
        }
        
        # Special limits for resource-intensive operations
        self.operation_limits = {
            Permission.AI_GENERATE.value: 50,  # 50 AI generations per hour
            Permission.AI_ANALYZE.value: 100,  # 100 AI analyses per hour
            Permission.DOCUMENT_PROCESS.value: 200  # 200 document processes per hour
        }
    
    async def evaluate(
        self,
        request: AuthorizationRequest
    ) -> AuthorizationResult:
        """Check rate limits."""
        try:
            # Get user's role-based limit
            user_limit = self.limits.get(request.context.role, 100)
            
            # Check general rate limit
            user_key = f"rate_limit:user:{request.context.user_id}"
            current_count = await self.redis_client.get(user_key)
            
            if current_count and int(current_count) >= user_limit:
                return AuthorizationResult(
                    allowed=False,
                    reason=f"Rate limit exceeded: {user_limit} requests per hour",
                    correlation_id=request.context.correlation_id
                )
            
            # Check operation-specific limit
            permission_str = request.permission.value if isinstance(request.permission, Permission) else request.permission
            operation_limit = self.operation_limits.get(permission_str)
            
            if operation_limit:
                operation_key = f"rate_limit:operation:{request.context.user_id}:{permission_str}"
                operation_count = await self.redis_client.get(operation_key)
                
                if operation_count and int(operation_count) >= operation_limit:
                    return AuthorizationResult(
                        allowed=False,
                        reason=f"Operation rate limit exceeded: {operation_limit} {permission_str} operations per hour",
                        correlation_id=request.context.correlation_id
                    )
            
            return AuthorizationResult(allowed=True)
            
        except Exception as e:
            # On error, allow request but log warning
            structlog.get_logger(__name__).warning(
                "Rate limit check failed",
                error=str(e),
                user_id=request.context.user_id,
                correlation_id=request.context.correlation_id
            )
            return AuthorizationResult(allowed=True)

class AuthorizationService:
    """
    Comprehensive authorization service with RBAC, tenant isolation, and fine-grained permissions.
    
    Features:
    - Role-based access control (RBAC)
    - Tenant isolation
    - Resource-level permissions
    - Ownership checks
    - Rate limiting
    - Audit logging
    - Policy composition
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        correlation_id: Optional[str] = None
    ):
        self.redis_client = redis_client
        self.logger = structlog.get_logger(__name__)
        self.correlation_id = correlation_id or secrets.token_hex(16)
        
        # Initialize policies
        self.policies = [
            TenantIsolationPolicy(),
            PermissionPolicy(),
            OwnershipPolicy(),
            RateLimitPolicy(redis_client)
        ]
        
        # Role definitions
        self.role_permissions = {
            "admin": [Permission.ALL.value],
            "architect": [
                Permission.PROJECT_CREATE.value,
                Permission.PROJECT_READ.value,
                Permission.PROJECT_UPDATE.value,
                Permission.PROJECT_DELETE.value,
                Permission.PROJECT_SHARE.value,
                Permission.DOCUMENT_UPLOAD.value,
                Permission.DOCUMENT_READ.value,
                Permission.DOCUMENT_UPDATE.value,
                Permission.DOCUMENT_DELETE.value,
                Permission.DOCUMENT_PROCESS.value,
                Permission.AI_GENERATE.value,
                Permission.AI_ANALYZE.value,
                Permission.AI_OPTIMIZE.value,
                Permission.AI_VALIDATE.value
            ],
            "viewer": [
                Permission.PROJECT_READ.value,
                Permission.DOCUMENT_READ.value,
                Permission.AI_ANALYZE.value
            ],
            "api_client": [
                Permission.API_READ.value,
                Permission.API_WRITE.value,
                Permission.PROJECT_READ.value,
                Permission.DOCUMENT_READ.value,
                Permission.AI_ANALYZE.value
            ]
        }
    
    async def authorize(
        self,
        context: AuthorizationContext,
        permission: Union[Permission, str],
        resource: Optional[Resource] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuthorizationResult:
        """
        Authorize request against all policies.
        
        Args:
            context: Authorization context with user info
            permission: Required permission
            resource: Resource being accessed (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Authorization result
        """
        try:
            # Create authorization request
            request = AuthorizationRequest(
                context=context,
                permission=permission,
                resource=resource,
                metadata=metadata
            )
            
            # Evaluate all policies
            for policy in self.policies:
                result = await policy.evaluate(request)
                if not result.allowed:
                    # Log authorization failure
                    await self._log_authorization_event(
                        "authorization_denied",
                        request,
                        result
                    )
                    return result
            
            # Log successful authorization
            await self._log_authorization_event(
                "authorization_granted",
                request,
                AuthorizationResult(allowed=True, correlation_id=self.correlation_id)
            )
            
            # Update rate limit counters
            await self._update_rate_limits(context, permission)
            
            return AuthorizationResult(
                allowed=True,
                correlation_id=self.correlation_id
            )
            
        except Exception as e:
            self.logger.error(
                "Authorization error",
                error=str(e),
                user_id=context.user_id,
                permission=str(permission),
                correlation_id=self.correlation_id,
                exc_info=True
            )
            
            # Fail closed - deny on error
            return AuthorizationResult(
                allowed=False,
                reason="Authorization failed due to internal error",
                correlation_id=self.correlation_id
            )
    
    async def check_permission(
        self,
        context: AuthorizationContext,
        permission: Union[Permission, str]
    ) -> bool:
        """Simple permission check without resource context."""
        result = await self.authorize(context, permission)
        return result.allowed
    
    async def check_resource_access(
        self,
        context: AuthorizationContext,
        permission: Union[Permission, str],
        resource: Resource
    ) -> bool:
        """Check access to specific resource."""
        result = await self.authorize(context, permission, resource)
        return result.allowed
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: str,
        role: str
    ) -> List[str]:
        """
        Get effective permissions for user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: User role
            
        Returns:
            List of permission strings
        """
        try:
            # Get base permissions from role
            base_permissions = self.role_permissions.get(role, [])
            
            # Get custom permissions from Redis (if any)
            custom_key = f"user_permissions:{tenant_id}:{user_id}"
            custom_permissions = await self.redis_client.lrange(custom_key, 0, -1)
            
            # Combine permissions
            all_permissions = set(base_permissions)
            all_permissions.update(custom_permissions)
            
            return list(all_permissions)
            
        except Exception as e:
            self.logger.warning(
                "Failed to get user permissions",
                error=str(e),
                user_id=user_id,
                correlation_id=self.correlation_id
            )
            return []
    
    async def grant_permission(
        self,
        admin_context: AuthorizationContext,
        target_user_id: str,
        target_tenant_id: str,
        permission: Union[Permission, str]
    ) -> bool:
        """
        Grant custom permission to user (admin only).
        
        Args:
            admin_context: Admin authorization context
            target_user_id: User to grant permission to
            target_tenant_id: Target user's tenant
            permission: Permission to grant
            
        Returns:
            True if successful
        """
        # Check admin permission
        if not await self.check_permission(admin_context, Permission.ADMIN_USERS):
            return False
        
        try:
            permission_str = permission.value if isinstance(permission, Permission) else permission
            
            # Add permission to user's custom permissions
            custom_key = f"user_permissions:{target_tenant_id}:{target_user_id}"
            await self.redis_client.sadd(custom_key, permission_str)
            
            await self._log_authorization_event(
                "permission_granted",
                None,
                None,
                {
                    "admin_user_id": admin_context.user_id,
                    "target_user_id": target_user_id,
                    "permission": permission_str
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to grant permission",
                error=str(e),
                target_user_id=target_user_id,
                permission=str(permission),
                correlation_id=self.correlation_id,
                exc_info=True
            )
            return False
    
    async def revoke_permission(
        self,
        admin_context: AuthorizationContext,
        target_user_id: str,
        target_tenant_id: str,
        permission: Union[Permission, str]
    ) -> bool:
        """
        Revoke custom permission from user (admin only).
        
        Args:
            admin_context: Admin authorization context
            target_user_id: User to revoke permission from
            target_tenant_id: Target user's tenant
            permission: Permission to revoke
            
        Returns:
            True if successful
        """
        # Check admin permission
        if not await self.check_permission(admin_context, Permission.ADMIN_USERS):
            return False
        
        try:
            permission_str = permission.value if isinstance(permission, Permission) else permission
            
            # Remove permission from user's custom permissions
            custom_key = f"user_permissions:{target_tenant_id}:{target_user_id}"
            await self.redis_client.srem(custom_key, permission_str)
            
            await self._log_authorization_event(
                "permission_revoked",
                None,
                None,
                {
                    "admin_user_id": admin_context.user_id,
                    "target_user_id": target_user_id,
                    "permission": permission_str
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to revoke permission",
                error=str(e),
                target_user_id=target_user_id,
                permission=str(permission),
                correlation_id=self.correlation_id,
                exc_info=True
            )
            return False
    
    async def create_authorization_context(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        custom_permissions: Optional[List[str]] = None
    ) -> AuthorizationContext:
        """
        Create authorization context for user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: User role
            ip_address: Client IP address
            user_agent: Client user agent
            custom_permissions: Additional custom permissions
            
        Returns:
            Authorization context
        """
        # Get user permissions
        permissions = await self.get_user_permissions(user_id, tenant_id, role)
        
        # Add custom permissions
        if custom_permissions:
            permissions.extend(custom_permissions)
        
        return AuthorizationContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=self.correlation_id
        )
    
    def create_resource(
        self,
        resource_type: ResourceType,
        resource_id: str,
        tenant_id: str,
        owner_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Resource:
        """Create resource object for authorization."""
        return Resource(
            type=resource_type,
            id=resource_id,
            tenant_id=tenant_id,
            owner_id=owner_id,
            metadata=metadata or {}
        )
    
    async def _update_rate_limits(
        self,
        context: AuthorizationContext,
        permission: Union[Permission, str]
    ):
        """Update rate limit counters."""
        try:
            # Update general rate limit
            user_key = f"rate_limit:user:{context.user_id}"
            await self.redis_client.incr(user_key)
            await self.redis_client.expire(user_key, 3600)  # 1 hour
            
            # Update operation-specific rate limit
            permission_str = permission.value if isinstance(permission, Permission) else permission
            operation_key = f"rate_limit:operation:{context.user_id}:{permission_str}"
            await self.redis_client.incr(operation_key)
            await self.redis_client.expire(operation_key, 3600)  # 1 hour
            
        except Exception as e:
            self.logger.warning(
                "Failed to update rate limits",
                error=str(e),
                user_id=context.user_id,
                correlation_id=self.correlation_id
            )
    
    async def _log_authorization_event(
        self,
        event_type: str,
        request: Optional[AuthorizationRequest],
        result: Optional[AuthorizationResult],
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """Log authorization event for audit trail."""
        try:
            event: Dict[str, Any] = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": self.correlation_id
            }
            
            if request:
                event["user_id"] = request.context.user_id
                event["tenant_id"] = request.context.tenant_id
                event["role"] = request.context.role
                event["permission"] = request.permission.value if isinstance(request.permission, Permission) else request.permission
                event["ip_address"] = request.context.ip_address
                if request.context.user_agent:
                    event["user_agent"] = request.context.user_agent
                
                if request.resource:
                    event["resource_type"] = request.resource.type.value
                    event["resource_id"] = request.resource.id
                    event["resource_tenant_id"] = request.resource.tenant_id
                    if request.resource.owner_id:
                        event["resource_owner_id"] = request.resource.owner_id
            
            if result:
                event["allowed"] = result.allowed
                if result.reason:
                    event["reason"] = result.reason
                if result.required_permissions:
                    event["required_permissions"] = result.required_permissions
            
            if extra_data:
                event.update(extra_data)
            
            # Store in audit log
            audit_key = f"audit:authorization:{datetime.utcnow().strftime('%Y%m%d')}"
            await self.redis_client.lpush(audit_key, json.dumps(event))
            await self.redis_client.expire(audit_key, 86400 * 90)  # Keep for 90 days
            
            # Log to structured logger
            self.logger.info(
                "Authorization event",
                **event
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log authorization event",
                error=str(e),
                correlation_id=self.correlation_id,
                exc_info=True
            )