"""
Unit tests for Base Data Access Object
Tests generic CRUD operations and multi-tenant support
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.database import User


@pytest.mark.unit
@pytest.mark.database
class TestBaseDAO:
    """Test suite for BaseDAO operations."""
    
    async def test_create_entity(self, test_session: AsyncSession):
        """Test creating an entity using BaseDAO."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        # Act
        user = await base_dao.create(
            email="basedao@example.com",
            password_hash="hashed_password",
            full_name="Base DAO User",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0
        )
        
        # Assert
        assert user is not None
        assert user.email == "basedao@example.com"
        assert user.tenant_id == tenant_id
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.is_deleted is False
    
    async def test_get_by_id(self, test_session: AsyncSession):
        """Test getting entity by ID."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        created_user = await base_dao.create(
            email="getbyid@example.com",
            password_hash="hashed_password",
            full_name="Get By ID User",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0
        )
        
        # Act
        retrieved_user = await base_dao.get_by_id(created_user.id, tenant_id)
        
        # Assert
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
    
    async def test_get_by_id_different_tenant(self, test_session: AsyncSession):
        """Test that tenant isolation works."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        other_tenant_id = uuid4()
        
        created_user = await base_dao.create(
            email="tenant@example.com",
            password_hash="hashed_password",
            full_name="Tenant User",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0
        )
        
        # Act - Try to get user with different tenant ID
        retrieved_user = await base_dao.get_by_id(created_user.id, other_tenant_id)
        
        # Assert
        assert retrieved_user is None
    
    async def test_get_all_with_pagination(self, test_session: AsyncSession):
        """Test getting all entities with pagination."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        # Create multiple users
        for i in range(5):
            await base_dao.create(
                email=f"user{i}@example.com",
                password_hash="hashed_password",
                full_name=f"User {i}",
                tenant_id=tenant_id,
                role="user",
                is_active=True,
                email_verified=False,
                failed_login_attempts=0
            )
        
        # Act
        all_users = await base_dao.get_all(tenant_id=tenant_id, limit=10)
        paginated_users = await base_dao.get_all(tenant_id=tenant_id, limit=2, offset=1)
        
        # Assert
        assert len(all_users) == 5
        assert len(paginated_users) == 2
    
    async def test_update_entity(self, test_session: AsyncSession):
        """Test updating an entity."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        created_user = await base_dao.create(
            email="update@example.com",
            password_hash="hashed_password",
            full_name="Original Name",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0
        )
        
        # Act
        updates = {
            "full_name": "Updated Name",
            "email_verified": True
        }
        updated_user = await base_dao.update(created_user.id, updates, tenant_id)
        
        # Assert
        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.email_verified is True
        assert updated_user.updated_at > created_user.updated_at
    
    async def test_soft_delete(self, test_session: AsyncSession):
        """Test soft deleting an entity."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        created_user = await base_dao.create(
            email="softdelete@example.com",
            password_hash="hashed_password",
            full_name="Soft Delete User",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0
        )
        
        # Act
        delete_success = await base_dao.delete(created_user.id, tenant_id, soft_delete=True)
        
        # Assert
        assert delete_success is True
        
        # Verify user is soft deleted
        retrieved_user = await base_dao.get_by_id(created_user.id, tenant_id, include_deleted=False)
        assert retrieved_user is None
        
        # Verify user can be retrieved when including deleted
        deleted_user = await base_dao.get_by_id(created_user.id, tenant_id, include_deleted=True)
        assert deleted_user is not None
        assert deleted_user.is_deleted is True
    
    async def test_count_entities(self, test_session: AsyncSession):
        """Test counting entities."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        # Create users
        for i in range(3):
            await base_dao.create(
                email=f"count{i}@example.com",
                password_hash="hashed_password",
                full_name=f"Count User {i}",
                tenant_id=tenant_id,
                role="user" if i < 2 else "admin",
                is_active=True,
                email_verified=False,
                failed_login_attempts=0
            )
        
        # Act
        total_count = await base_dao.count(tenant_id=tenant_id)
        user_count = await base_dao.count(tenant_id=tenant_id, filters={"role": "user"})
        admin_count = await base_dao.count(tenant_id=tenant_id, filters={"role": "admin"})
        
        # Assert
        assert total_count == 3
        assert user_count == 2
        assert admin_count == 1
    
    async def test_exists_entity(self, test_session: AsyncSession):
        """Test checking if entity exists."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        non_existent_id = uuid4()
        
        created_user = await base_dao.create(
            email="exists@example.com",
            password_hash="hashed_password",
            full_name="Exists User",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=False,
            failed_login_attempts=0
        )
        
        # Act
        exists = await base_dao.exists(created_user.id, tenant_id)
        not_exists = await base_dao.exists(non_existent_id, tenant_id)
        
        # Assert
        assert exists is True
        assert not_exists is False
    
    async def test_get_all_with_filters(self, test_session: AsyncSession):
        """Test getting entities with filters."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        
        # Create users with different properties
        await base_dao.create(
            email="active@example.com",
            password_hash="hashed_password",
            full_name="Active User",
            tenant_id=tenant_id,
            role="user",
            is_active=True,
            email_verified=True,
            failed_login_attempts=0
        )
        
        await base_dao.create(
            email="inactive@example.com",
            password_hash="hashed_password",
            full_name="Inactive User",
            tenant_id=tenant_id,
            role="user",
            is_active=False,
            email_verified=False,
            failed_login_attempts=0
        )
        
        await base_dao.create(
            email="admin@example.com",
            password_hash="hashed_password",
            full_name="Admin User",
            tenant_id=tenant_id,
            role="admin",
            is_active=True,
            email_verified=True,
            failed_login_attempts=0
        )
        
        # Act
        active_users = await base_dao.get_all(
            tenant_id=tenant_id,
            filters={"is_active": True}
        )
        
        verified_users = await base_dao.get_all(
            tenant_id=tenant_id,
            filters={"email_verified": True}
        )
        
        admin_users = await base_dao.get_all(
            tenant_id=tenant_id,
            filters={"role": "admin"}
        )
        
        # Assert
        assert len(active_users) == 2
        assert len(verified_users) == 2
        assert len(admin_users) == 1
        assert all(user.is_active for user in active_users)
        assert all(user.email_verified for user in verified_users)
        assert all(user.role == "admin" for user in admin_users)
    
    async def test_update_nonexistent_entity(self, test_session: AsyncSession):
        """Test updating a non-existent entity."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        non_existent_id = uuid4()
        
        # Act
        updated_user = await base_dao.update(
            non_existent_id, 
            {"full_name": "Updated Name"}, 
            tenant_id
        )
        
        # Assert
        assert updated_user is None
    
    async def test_delete_nonexistent_entity(self, test_session: AsyncSession):
        """Test deleting a non-existent entity."""
        # Arrange
        base_dao = BaseDAO(User, test_session)
        tenant_id = uuid4()
        non_existent_id = uuid4()
        
        # Act
        delete_success = await base_dao.delete(non_existent_id, tenant_id)
        
        # Assert
        assert delete_success is False