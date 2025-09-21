"""
ArchBuilder.AI - User Data Access Object
User management with authentication and multi-tenant support
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from .base_dao import CacheableDAO
from ..models.database import User, UserSession
from ..core.security import hash_password, verify_password

logger = structlog.get_logger(__name__)

class UserDAO(CacheableDAO[User]):
    """
    User Data Access Object with authentication and security features.
    
    Features:
    - User authentication
    - Password management
    - Session tracking
    - Multi-tenant user management
    - Security audit logging
    """
    
    def __init__(self, session: AsyncSession, cache_manager=None):
        super().__init__(User, session, cache_manager)
        self.cache_ttl = 1800  # 30 minutes for user data
    
    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        tenant_id: UUID,
        role: str = "user",
        is_active: bool = True,
        **kwargs
    ) -> User:
        """Create a new user with hashed password."""
        try:
            # Check if user already exists
            existing_user = await self.get_by_email(email)
            if existing_user:
                raise ValueError(f"User with email {email} already exists")
            
            # Hash password
            password_hash = hash_password(password)
            
            # Create user
            user_data = {
                'email': email.lower().strip(),
                'password_hash': password_hash,
                'full_name': full_name.strip(),
                'tenant_id': tenant_id,
                'role': role,
                'is_active': is_active,
                'email_verified': False,
                'failed_login_attempts': 0,
                **kwargs
            }
            
            user = await self.create(**user_data)
            
            logger.info(
                "User created successfully",
                user_id=str(user.id),
                email=user.email,
                tenant_id=str(tenant_id),
                role=role
            )
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to create user",
                email=email,
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def get_by_email(
        self, 
        email: str, 
        include_deleted: bool = False
    ) -> Optional[User]:
        """Get user by email address."""
        try:
            query = select(self.model).where(
                func.lower(self.model.email) == email.lower().strip()
            )
            
            # Filter out soft-deleted users
            if not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                logger.debug(
                    "User retrieved by email",
                    user_id=str(user.id),
                    email=email
                )
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to get user by email",
                email=email,
                error=str(e)
            )
            raise
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str,
        update_last_login: bool = True
    ) -> Optional[User]:
        """Authenticate user with email and password."""
        try:
            user = await self.get_by_email(email)
            if not user:
                logger.warning(
                    "Authentication failed - user not found",
                    email=email
                )
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(
                    "Authentication failed - user inactive",
                    user_id=str(user.id),
                    email=email
                )
                return None
            
            # Check if account is locked
            if user.failed_login_attempts >= 5:
                logger.warning(
                    "Authentication failed - account locked",
                    user_id=str(user.id),
                    email=email,
                    failed_attempts=user.failed_login_attempts
                )
                return None
            
            # Verify password
            if not verify_password(password, user.password_hash):
                # Increment failed login attempts
                await self.update(
                    entity_id=user.id,
                    updates={
                        'failed_login_attempts': user.failed_login_attempts + 1,
                        'last_failed_login': datetime.utcnow()
                    }
                )
                
                logger.warning(
                    "Authentication failed - invalid password",
                    user_id=str(user.id),
                    email=email,
                    failed_attempts=user.failed_login_attempts + 1
                )
                return None
            
            # Authentication successful
            updates = {
                'failed_login_attempts': 0,
                'last_failed_login': None
            }
            
            if update_last_login:
                updates['last_login'] = datetime.utcnow()
            
            await self.update(entity_id=user.id, updates=updates)
            
            # Invalidate cache
            await self.invalidate_cache(user.id)
            
            logger.info(
                "User authenticated successfully",
                user_id=str(user.id),
                email=email
            )
            
            return user
            
        except Exception as e:
            logger.error(
                "Authentication error",
                email=email,
                error=str(e)
            )
            raise
    
    async def update_password(
        self, 
        user_id: UUID, 
        new_password: str,
        current_password: Optional[str] = None
    ) -> bool:
        """Update user password with validation."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Verify current password if provided
            if current_password:
                if not verify_password(current_password, user.password_hash):
                    logger.warning(
                        "Password update failed - invalid current password",
                        user_id=str(user_id)
                    )
                    return False
            
            # Hash new password
            new_password_hash = hash_password(new_password)
            
            # Update password
            await self.update(
                entity_id=user_id,
                updates={
                    'password_hash': new_password_hash,
                    'password_changed_at': datetime.utcnow()
                }
            )
            
            # Invalidate cache
            await self.invalidate_cache(user_id)
            
            logger.info(
                "Password updated successfully",
                user_id=str(user_id)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update password",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    async def get_users_by_tenant(
        self, 
        tenant_id: UUID,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """Get users by tenant with filtering."""
        try:
            filters: Dict[str, Any] = {}
            
            if role:
                filters['role'] = role
            
            if is_active is not None:
                filters['is_active'] = is_active
            
            users = await self.get_all(
                tenant_id=tenant_id,
                filters=filters,
                limit=limit,
                offset=offset,
                order_by='created_at'
            )
            
            logger.debug(
                "Users retrieved by tenant",
                tenant_id=str(tenant_id),
                count=len(users),
                role=role,
                is_active=is_active
            )
            
            return users
            
        except Exception as e:
            logger.error(
                "Failed to get users by tenant",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise
    
    async def activate_user(self, user_id: UUID) -> bool:
        """Activate user account."""
        try:
            result = await self.update(
                entity_id=user_id,
                updates={'is_active': True}
            )
            
            if result:
                await self.invalidate_cache(user_id)
                logger.info(
                    "User activated",
                    user_id=str(user_id)
                )
            
            return result is not None
            
        except Exception as e:
            logger.error(
                "Failed to activate user",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """Deactivate user account."""
        try:
            result = await self.update(
                entity_id=user_id,
                updates={
                    'is_active': False,
                    'deactivated_at': datetime.utcnow()
                }
            )
            
            if result:
                await self.invalidate_cache(user_id)
                logger.info(
                    "User deactivated",
                    user_id=str(user_id)
                )
            
            return result is not None
            
        except Exception as e:
            logger.error(
                "Failed to deactivate user",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    async def verify_email(self, user_id: UUID) -> bool:
        """Mark user email as verified."""
        try:
            result = await self.update(
                entity_id=user_id,
                updates={
                    'email_verified': True,
                    'email_verified_at': datetime.utcnow()
                }
            )
            
            if result:
                await self.invalidate_cache(user_id)
                logger.info(
                    "User email verified",
                    user_id=str(user_id)
                )
            
            return result is not None
            
        except Exception as e:
            logger.error(
                "Failed to verify user email",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    async def update_user_profile(
        self, 
        user_id: UUID, 
        profile_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update user profile information."""
        try:
            # Filter allowed profile fields
            allowed_fields = [
                'full_name', 'phone_number', 'preferred_language',
                'timezone', 'avatar_url', 'bio', 'company'
            ]
            
            updates = {
                field: value for field, value in profile_data.items()
                if field in allowed_fields and value is not None
            }
            
            if not updates:
                return await self.get_by_id(user_id)
            
            result = await self.update(entity_id=user_id, updates=updates)
            
            if result:
                await self.invalidate_cache(user_id)
                logger.info(
                    "User profile updated",
                    user_id=str(user_id),
                    updated_fields=list(updates.keys())
                )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to update user profile",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    async def get_active_sessions(self, user_id: UUID) -> List[UserSession]:
        """Get active sessions for user."""
        try:
            query = select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            ).order_by(UserSession.created_at.desc())
            
            result = await self.session.execute(query)
            sessions = list(result.scalars().all())
            
            logger.debug(
                "Active sessions retrieved",
                user_id=str(user_id),
                session_count=len(sessions)
            )
            
            return sessions
            
        except Exception as e:
            logger.error(
                "Failed to get active sessions",
                user_id=str(user_id),
                error=str(e)
            )
            raise