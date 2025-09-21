"""
Unit tests for User Data Access Object
Tests user creation, authentication, and management operations
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.user_dao import UserDAO
from app.models.database import User


@pytest.mark.unit
@pytest.mark.database
class TestUserDAO:
    """Test suite for UserDAO operations."""
    
    async def test_create_user_success(self, test_session: AsyncSession):
        """Test successful user creation."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "test@example.com"
        password = "TestPassword123!"
        full_name = "Test User"
        
        # Act
        user = await user_dao.create_user(
            email=email,
            password=password,
            full_name=full_name,
            tenant_id=tenant_id,
            role="user"
        )
        
        # Assert
        assert user is not None
        assert user.email == email.lower()
        assert user.full_name == full_name
        assert user.tenant_id == tenant_id
        assert user.role == "user"
        assert user.is_active is True
        assert user.email_verified is False
        assert user.password_hash != password  # Password should be hashed
        assert len(user.password_hash) > 0
    
    async def test_create_user_duplicate_email(self, test_session: AsyncSession):
        """Test that creating a user with duplicate email fails."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "duplicate@example.com"
        
        # Create first user
        await user_dao.create_user(
            email=email,
            password="Password123!",
            full_name="First User",
            tenant_id=tenant_id
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            await user_dao.create_user(
                email=email,
                password="Password456!",
                full_name="Second User",
                tenant_id=tenant_id
            )
    
    async def test_get_by_email_success(self, test_session: AsyncSession):
        """Test getting user by email address."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "getbyemail@example.com"
        
        created_user = await user_dao.create_user(
            email=email,
            password="Password123!",
            full_name="Get By Email User",
            tenant_id=tenant_id
        )
        
        # Act
        found_user = await user_dao.get_by_email(email)
        
        # Assert
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == email.lower()
    
    async def test_get_by_email_not_found(self, test_session: AsyncSession):
        """Test getting user by non-existent email."""
        # Arrange
        user_dao = UserDAO(test_session)
        
        # Act
        user = await user_dao.get_by_email("nonexistent@example.com")
        
        # Assert
        assert user is None
    
    async def test_authenticate_user_success(self, test_session: AsyncSession):
        """Test successful user authentication."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "auth@example.com"
        password = "AuthPassword123!"
        
        await user_dao.create_user(
            email=email,
            password=password,
            full_name="Auth User",
            tenant_id=tenant_id
        )
        
        # Act
        authenticated_user = await user_dao.authenticate_user(email, password)
        
        # Assert
        assert authenticated_user is not None
        assert authenticated_user.email == email.lower()
        assert authenticated_user.failed_login_attempts == 0
    
    async def test_authenticate_user_invalid_password(self, test_session: AsyncSession):
        """Test authentication with invalid password."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "authfail@example.com"
        password = "CorrectPassword123!"
        
        await user_dao.create_user(
            email=email,
            password=password,
            full_name="Auth Fail User",
            tenant_id=tenant_id
        )
        
        # Act
        authenticated_user = await user_dao.authenticate_user(email, "WrongPassword123!")
        
        # Assert
        assert authenticated_user is None
    
    async def test_authenticate_user_nonexistent(self, test_session: AsyncSession):
        """Test authentication with non-existent user."""
        # Arrange
        user_dao = UserDAO(test_session)
        
        # Act
        authenticated_user = await user_dao.authenticate_user(
            "nonexistent@example.com", 
            "Password123!"
        )
        
        # Assert
        assert authenticated_user is None
    
    async def test_update_password_success(self, test_session: AsyncSession):
        """Test successful password update."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "updatepass@example.com"
        old_password = "OldPassword123!"
        new_password = "NewPassword456!"
        
        user = await user_dao.create_user(
            email=email,
            password=old_password,
            full_name="Update Pass User",
            tenant_id=tenant_id
        )
        
        # Act
        success = await user_dao.update_password(
            user.id, 
            new_password, 
            current_password=old_password
        )
        
        # Assert
        assert success is True
        
        # Verify old password no longer works
        auth_with_old = await user_dao.authenticate_user(email, old_password)
        assert auth_with_old is None
        
        # Verify new password works
        auth_with_new = await user_dao.authenticate_user(email, new_password)
        assert auth_with_new is not None
    
    async def test_update_password_invalid_current(self, test_session: AsyncSession):
        """Test password update with invalid current password."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "updatepassfail@example.com"
        password = "Password123!"
        
        user = await user_dao.create_user(
            email=email,
            password=password,
            full_name="Update Pass Fail User",
            tenant_id=tenant_id
        )
        
        # Act
        success = await user_dao.update_password(
            user.id, 
            "NewPassword456!", 
            current_password="WrongCurrentPassword!"
        )
        
        # Assert
        assert success is False
    
    async def test_activate_user(self, test_session: AsyncSession):
        """Test user activation."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "activate@example.com"
        
        user = await user_dao.create_user(
            email=email,
            password="Password123!",
            full_name="Activate User",
            tenant_id=tenant_id,
            is_active=False
        )
        
        # Act
        success = await user_dao.activate_user(user.id)
        
        # Assert
        assert success is True
        
        # Verify user is now active
        updated_user = await user_dao.get_by_id(user.id)
        assert updated_user.is_active is True
    
    async def test_deactivate_user(self, test_session: AsyncSession):
        """Test user deactivation."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "deactivate@example.com"
        
        user = await user_dao.create_user(
            email=email,
            password="Password123!",
            full_name="Deactivate User",
            tenant_id=tenant_id,
            is_active=True
        )
        
        # Act
        success = await user_dao.deactivate_user(user.id)
        
        # Assert
        assert success is True
        
        # Verify user is now inactive
        updated_user = await user_dao.get_by_id(user.id)
        assert updated_user.is_active is False
        assert updated_user.deactivated_at is not None
    
    async def test_verify_email(self, test_session: AsyncSession):
        """Test email verification."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "verify@example.com"
        
        user = await user_dao.create_user(
            email=email,
            password="Password123!",
            full_name="Verify User",
            tenant_id=tenant_id
        )
        
        # Act
        success = await user_dao.verify_email(user.id)
        
        # Assert
        assert success is True
        
        # Verify email is verified
        updated_user = await user_dao.get_by_id(user.id)
        assert updated_user.email_verified is True
        assert updated_user.email_verified_at is not None
    
    async def test_update_user_profile(self, test_session: AsyncSession):
        """Test user profile update."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        email = "profile@example.com"
        
        user = await user_dao.create_user(
            email=email,
            password="Password123!",
            full_name="Original Name",
            tenant_id=tenant_id
        )
        
        # Act
        profile_data = {
            "full_name": "Updated Name",
            "phone_number": "+1234567890",
            "bio": "Updated bio",
            "company": "Test Company"
        }
        
        updated_user = await user_dao.update_user_profile(user.id, profile_data)
        
        # Assert
        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.phone_number == "+1234567890"
        assert updated_user.bio == "Updated bio"
        assert updated_user.company == "Test Company"
    
    async def test_get_users_by_tenant(self, test_session: AsyncSession):
        """Test getting users by tenant."""
        # Arrange
        user_dao = UserDAO(test_session)
        tenant_id = uuid4()
        other_tenant_id = uuid4()
        
        # Create users for the target tenant
        await user_dao.create_user(
            email="tenant1user1@example.com",
            password="Password123!",
            full_name="Tenant 1 User 1",
            tenant_id=tenant_id,
            role="admin"
        )
        
        await user_dao.create_user(
            email="tenant1user2@example.com",
            password="Password123!",
            full_name="Tenant 1 User 2",
            tenant_id=tenant_id,
            role="user"
        )
        
        # Create user for different tenant
        await user_dao.create_user(
            email="tenant2user1@example.com",
            password="Password123!",
            full_name="Tenant 2 User 1",
            tenant_id=other_tenant_id,
            role="user"
        )
        
        # Act
        tenant_users = await user_dao.get_users_by_tenant(tenant_id)
        admin_users = await user_dao.get_users_by_tenant(tenant_id, role="admin")
        
        # Assert
        assert len(tenant_users) == 2
        assert len(admin_users) == 1
        assert all(user.tenant_id == tenant_id for user in tenant_users)
        assert admin_users[0].role == "admin"