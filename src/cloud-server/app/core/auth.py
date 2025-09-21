"""
Authentication and Authorization for ArchBuilder.AI
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException
import structlog

from app.core.security import hash_password, verify_password, TokenManager
from app.models.auth.user import User

logger = structlog.get_logger(__name__)


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with email and password
    
    Args:
        email: User email
        password: Plain text password
        
    Returns:
        User data dict if authentication successful, None otherwise
    """
    try:
        # In real implementation, fetch from database
        # This is a mock implementation
        mock_user = {
            "user_id": 1,
            "email": email,
            "hashed_password": hash_password("testpass123"),  # Mock password
            "is_active": True,
            "role": "user"
        }
        
        # Verify password
        if verify_password(password, mock_user["hashed_password"]):
            logger.info("User authenticated successfully", email=email)
            return {
                "user_id": mock_user["user_id"],
                "email": mock_user["email"],
                "role": mock_user["role"]
            }
        else:
            logger.warning("Authentication failed - invalid password", email=email)
            return None
            
    except Exception as e:
        logger.error("Authentication error", email=email, error=str(e))
        return None


async def authorize_user(user_id: int, required_permission: str) -> bool:
    """
    Check if user has required permission
    
    Args:
        user_id: User ID
        required_permission: Required permission string
        
    Returns:
        True if user has permission, False otherwise
    """
    try:
        # Mock authorization logic
        # In real implementation, check user roles and permissions from database
        user_permissions = {
            "project_read": True,
            "project_write": True,
            "project_delete": False,
            "admin_action": False
        }
        
        has_permission = user_permissions.get(required_permission, False)
        
        if has_permission:
            logger.debug("Authorization granted", 
                        user_id=user_id, permission=required_permission)
        else:
            logger.warning("Authorization denied", 
                          user_id=user_id, permission=required_permission)
        
        return has_permission
        
    except Exception as e:
        logger.error("Authorization error", 
                    user_id=user_id, permission=required_permission, error=str(e))
        return False


class RoleChecker:
    """
    Role-based access control checker
    """
    
    def __init__(self):
        self.role_permissions = {
            "user": [
                "project_read",
                "project_write",
                "file_upload"
            ],
            "admin": [
                "project_read",
                "project_write", 
                "project_delete",
                "user_management",
                "admin_action"
            ],
            "super_admin": [
                "project_read",
                "project_write",
                "project_delete", 
                "user_management",
                "admin_action",
                "system_config"
            ]
        }
    
    def check_permission(self, user: User, permission: str) -> bool:
        """Check if user role has permission"""
        user_role = getattr(user, 'role', 'user')
        allowed_permissions = self.role_permissions.get(user_role, [])
        
        has_permission = permission in allowed_permissions
        
        if not has_permission:
            logger.warning("Permission denied", 
                          user_id=getattr(user, 'id', None),
                          role=user_role, 
                          permission=permission)
        
        return has_permission
    
    def get_user_permissions(self, user_role: str) -> list:
        """Get all permissions for a role"""
        return self.role_permissions.get(user_role, [])


class PermissionChecker:
    """
    Permission checking utilities
    """
    
    @staticmethod
    def check_resource_access(user_id: int, resource_tenant_id: int, user_tenant_id: int) -> bool:
        """Check if user can access resource from different tenant"""
        # Basic tenant isolation check
        if resource_tenant_id != user_tenant_id:
            logger.warning("Cross-tenant access attempt blocked",
                          user_id=user_id,
                          user_tenant=user_tenant_id,
                          resource_tenant=resource_tenant_id)
            return False
        
        return True
    
    @staticmethod
    def check_project_ownership(user_id: int, project_owner_id: int) -> bool:
        """Check if user owns the project"""
        return user_id == project_owner_id


class APIKeyValidator:
    """
    API Key validation for service authentication
    """
    
    def __init__(self):
        # Mock API keys - in production, store in database
        self.valid_keys = {
            "ak_live_1234567890abcdef": {
                "user_id": 1,
                "permissions": ["api_access", "project_read", "project_write"],
                "rate_limit": 1000  # requests per hour
            }
        }
    
    async def validate_key(self, api_key: str) -> bool:
        """Validate API key"""
        try:
            if api_key in self.valid_keys:
                logger.debug("API key validated", key_prefix=api_key[:10])
                return True
            else:
                logger.warning("Invalid API key", key_prefix=api_key[:10] if api_key else "None")
                return False
                
        except Exception as e:
            logger.error("API key validation error", error=str(e))
            return False
    
    async def get_key_permissions(self, api_key: str) -> list:
        """Get permissions for API key"""
        key_data = self.valid_keys.get(api_key)
        if key_data:
            return key_data.get("permissions", [])
        return []


# Global instances
role_checker = RoleChecker()
permission_checker = PermissionChecker()
api_key_validator = APIKeyValidator()