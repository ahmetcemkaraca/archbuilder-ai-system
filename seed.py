import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.models.database import User, Tenant, Subscription, UserRole
from passlib.context import CryptContext
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_data():
    """Initial database seeding with default user, tenant, and subscription."""
    async for session in get_db_session():
        try:
            # Check if tenant already exists
            existing_tenant = await session.get(Tenant, UUID('a0a0a0a0-a0a0-4a0a-8a0a-0a0a0a0a0a0a')) # Örnek UUID
            if not existing_tenant:
                tenant = Tenant(
                    id=UUID('a0a0a0a0-a0a0-4a0a-8a0a-0a0a0a0a0a0a'),
                    name="Default Tenant",
                    slug="default-tenant",
                    is_active=True,
                )
                session.add(tenant)
                await session.commit()
                await session.refresh(tenant)
                logger.info(f"Tenant created: {tenant.name}")
            else:
                tenant = existing_tenant
                logger.info(f"Tenant already exists: {tenant.name}")

            # Check if user already exists
            existing_user = await session.get(User, UUID('b1b1b1b1-b1b1-4b1b-8b1b-0b1b0b1b0b1b')) # Örnek UUID
            if not existing_user:
                hashed_password = pwd_context.hash("password")
                user = User(
                    id=UUID('b1b1b1b1-b1b1-4b1b-8b1b-0b1b0b1b0b1b'),
                    email="admin@archbuilder.ai",
                    password_hash=hashed_password,
                    first_name="Admin",
                    last_name="User",
                    role=UserRole.ADMIN.value,
                    tenant_id=tenant.id,
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"Admin user created: {user.email}")
            else:
                user = existing_user
                logger.info(f"Admin user already exists: {user.email}")

            # Check if subscription already exists for the user
            existing_subscription = await session.get(Subscription, UUID('c2c2c2c2-c2c2-4c2c-8c2c-0c2c0c2c0c2c')) # Örnek UUID
            if not existing_subscription:
                subscription = Subscription(
                    id=UUID('c2c2c2c2-c2c2-4c2c-8c2c-0c2c0c2c0c2c'),
                    user_id=user.id,
                    plan_name="enterprise",
                    status="active",
                    max_projects=100,
                    max_documents=1000,
                    max_storage_gb=500.0,
                    ai_requests_monthly=100000,
                )
                session.add(subscription)
                await session.commit()
                await session.refresh(subscription)
                logger.info(f"Subscription created for {user.email}: {subscription.plan_name}")
            else:
                logger.info(f"Subscription already exists for {user.email}: {existing_subscription.plan_name}")

        except Exception as e:
            logger.error(f"Database seeding failed: {e}", exc_info=True)
            await session.rollback()
            raise

    logger.info("Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_data())

