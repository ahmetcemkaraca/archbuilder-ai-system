"""
ArchBuilder.AI - Base Data Access Object
Generic CRUD operations with multi-tenant support and security
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TypeVar, Generic, Type
from uuid import UUID
import structlog
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..core.database import Base
from ..core.logging import get_logger

logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=Base)

class BaseDAO(Generic[T], ABC):
    """
    Base Data Access Object providing CRUD operations with multi-tenant support.
    
    Features:
    - Multi-tenant data isolation
    - Soft deletes
    - Audit logging
    - Performance optimization
    - Security validation
    """
    
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
        self.logger = get_logger(f"dao.{model.__name__.lower()}")
    
    async def create(self, **kwargs) -> T:
        """Create a new entity with audit logging."""
        try:
            # Add creation metadata
            kwargs.update({
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_deleted': False
            })
            
            entity = self.model(**kwargs)
            self.session.add(entity)
            await self.session.flush()  # Get ID without committing
            
            self.logger.info(
                "Entity created",
                entity_type=self.model.__name__,
                entity_id=str(entity.id) if hasattr(entity, 'id') else 'unknown',
                **self._get_audit_context(kwargs)
            )
            
            return entity
            
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.error(
                "Entity creation failed - integrity error",
                entity_type=self.model.__name__,
                error=str(e),
                **kwargs
            )
            raise ValueError(f"Entity creation failed: {str(e)}")
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Entity creation failed",
                entity_type=self.model.__name__,
                error=str(e),
                **kwargs
            )
            raise
    
    async def get_by_id(
        self, 
        entity_id: UUID, 
        tenant_id: Optional[UUID] = None,
        include_deleted: bool = False
    ) -> Optional[T]:
        """Get entity by ID with tenant isolation."""
        try:
            query = select(self.model).where(self.model.id == entity_id)
            
            # Add tenant filter if model supports multi-tenancy
            if hasattr(self.model, 'tenant_id') and tenant_id:
                query = query.where(self.model.tenant_id == tenant_id)
            
            # Filter out soft-deleted entities
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            entity = result.scalar_one_or_none()
            
            if entity:
                self.logger.debug(
                    "Entity retrieved",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id),
                    tenant_id=str(tenant_id) if tenant_id else None
                )
            
            return entity
            
        except Exception as e:
            self.logger.error(
                "Failed to get entity by ID",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e)
            )
            raise
    
    async def get_all(
        self, 
        tenant_id: Optional[UUID] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """Get all entities with filtering and pagination."""
        try:
            query = select(self.model)
            
            # Add tenant filter
            if hasattr(self.model, 'tenant_id') and tenant_id:
                query = query.where(self.model.tenant_id == tenant_id)
            
            # Filter out soft-deleted entities
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            # Apply additional filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.where(getattr(self.model, field).in_(value))
                        else:
                            query = query.where(getattr(self.model, field) == value)
            
            # Add ordering
            if order_by and hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))
            elif hasattr(self.model, 'created_at'):
                query = query.order_by(self.model.created_at.desc())
            
            # Add pagination
            query = query.offset(offset).limit(limit)
            
            result = await self.session.execute(query)
            entities = result.scalars().all()
            
            self.logger.debug(
                "Entities retrieved",
                entity_type=self.model.__name__,
                count=len(entities),
                tenant_id=str(tenant_id) if tenant_id else None,
                limit=limit,
                offset=offset
            )
            
            return entities
            
        except Exception as e:
            self.logger.error(
                "Failed to get entities",
                entity_type=self.model.__name__,
                error=str(e)
            )
            raise
    
    async def update(
        self, 
        entity_id: UUID, 
        updates: Dict[str, Any],
        tenant_id: Optional[UUID] = None
    ) -> Optional[T]:
        """Update entity with audit logging."""
        try:
            # Add update metadata
            updates['updated_at'] = datetime.utcnow()
            
            query = update(self.model).where(self.model.id == entity_id)
            
            # Add tenant filter
            if hasattr(self.model, 'tenant_id') and tenant_id:
                query = query.where(self.model.tenant_id == tenant_id)
            
            # Filter out soft-deleted entities
            if hasattr(self.model, 'is_deleted'):
                query = query.where(self.model.is_deleted == False)
            
            query = query.values(**updates).returning(self.model)
            
            result = await self.session.execute(query)
            entity = result.scalar_one_or_none()
            
            if entity:
                self.logger.info(
                    "Entity updated",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id),
                    tenant_id=str(tenant_id) if tenant_id else None,
                    updates=list(updates.keys())
                )
            
            return entity
            
        except IntegrityError as e:
            await self.session.rollback()
            self.logger.error(
                "Entity update failed - integrity error",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e)
            )
            raise ValueError(f"Entity update failed: {str(e)}")
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Entity update failed",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e)
            )
            raise
    
    async def delete(
        self, 
        entity_id: UUID, 
        tenant_id: Optional[UUID] = None,
        soft_delete: bool = True
    ) -> bool:
        """Delete entity (soft delete by default)."""
        try:
            if soft_delete and hasattr(self.model, 'is_deleted'):
                # Soft delete
                result = await self.update(
                    entity_id=entity_id,
                    updates={'is_deleted': True, 'deleted_at': datetime.utcnow()},
                    tenant_id=tenant_id
                )
                success = result is not None
            else:
                # Hard delete
                query = delete(self.model).where(self.model.id == entity_id)
                
                # Add tenant filter
                if hasattr(self.model, 'tenant_id') and tenant_id:
                    query = query.where(self.model.tenant_id == tenant_id)
                
                result = await self.session.execute(query)
                success = result.rowcount > 0
            
            if success:
                self.logger.info(
                    "Entity deleted",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id),
                    tenant_id=str(tenant_id) if tenant_id else None,
                    soft_delete=soft_delete
                )
            
            return success
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Entity deletion failed",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e)
            )
            raise
    
    async def count(
        self, 
        tenant_id: Optional[UUID] = None,
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count entities with filtering."""
        try:
            query = select(func.count(self.model.id))
            
            # Add tenant filter
            if hasattr(self.model, 'tenant_id') and tenant_id:
                query = query.where(self.model.tenant_id == tenant_id)
            
            # Filter out soft-deleted entities
            if hasattr(self.model, 'is_deleted') and not include_deleted:
                query = query.where(self.model.is_deleted == False)
            
            # Apply additional filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)
            
            result = await self.session.execute(query)
            count = result.scalar()
            
            return count or 0
            
        except Exception as e:
            self.logger.error(
                "Failed to count entities",
                entity_type=self.model.__name__,
                error=str(e)
            )
            raise
    
    async def exists(
        self, 
        entity_id: UUID, 
        tenant_id: Optional[UUID] = None,
        include_deleted: bool = False
    ) -> bool:
        """Check if entity exists."""
        try:
            entity = await self.get_by_id(
                entity_id=entity_id,
                tenant_id=tenant_id,
                include_deleted=include_deleted
            )
            return entity is not None
            
        except Exception as e:
            self.logger.error(
                "Failed to check entity existence",
                entity_type=self.model.__name__,
                entity_id=str(entity_id),
                error=str(e)
            )
            return False
    
    def _get_audit_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract audit context from data."""
        audit_fields = ['user_id', 'tenant_id', 'created_by', 'updated_by']
        return {
            field: str(data[field]) if field in data and data[field] else None
            for field in audit_fields
        }

class CacheableDAO(BaseDAO[T]):
    """
    Extended DAO with caching support for frequently accessed entities.
    """
    
    def __init__(self, model: Type[T], session: AsyncSession, cache_manager=None):
        super().__init__(model, session)
        self.cache_manager = cache_manager
        self.cache_prefix = f"{model.__name__.lower()}"
        self.cache_ttl = 3600  # 1 hour default
    
    async def get_by_id(
        self, 
        entity_id: UUID, 
        tenant_id: Optional[UUID] = None,
        include_deleted: bool = False,
        use_cache: bool = True
    ) -> Optional[T]:
        """Get entity by ID with caching support."""
        cache_key = f"{self.cache_prefix}:{entity_id}"
        if tenant_id:
            cache_key += f":{tenant_id}"
        
        # Try cache first
        if use_cache and self.cache_manager:
            cached_entity = await self.cache_manager.get(cache_key)
            if cached_entity:
                self.logger.debug(
                    "Entity retrieved from cache",
                    entity_type=self.model.__name__,
                    entity_id=str(entity_id)
                )
                return cached_entity
        
        # Get from database
        entity = await super().get_by_id(
            entity_id=entity_id,
            tenant_id=tenant_id,
            include_deleted=include_deleted
        )
        
        # Cache the result
        if entity and use_cache and self.cache_manager:
            await self.cache_manager.set(
                cache_key, 
                entity, 
                ttl=self.cache_ttl
            )
        
        return entity
    
    async def invalidate_cache(self, entity_id: UUID, tenant_id: Optional[UUID] = None):
        """Invalidate cache for specific entity."""
        if not self.cache_manager:
            return
        
        cache_key = f"{self.cache_prefix}:{entity_id}"
        if tenant_id:
            cache_key += f":{tenant_id}"
        
        await self.cache_manager.delete(cache_key)
        
        self.logger.debug(
            "Cache invalidated",
            entity_type=self.model.__name__,
            entity_id=str(entity_id)
        )