"""
Authentication service for ArchBuilder.AI
Implements OAuth2 + API Key authentication with subscription validation
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import redis
from sqlalchemy.orm import Session

from ...models.auth import UserCreate, UserInDB, TokenData
from ...models.subscriptions import SubscriptionTier
from ...core.config import get_settings
from ...core.database import get_db
from ...core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Authentication schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis for session management and rate limiting
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)


class AuthenticationService:
    """Core authentication service with subscription integration"""
    
    def __init__(self):
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.api_key_expire_days = 365
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash password for storage"""
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=self.algorithm
        )
        
        logger.info(f"Created access token for user {data.get('sub')}")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[self.algorithm]
            )
            
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            
            return TokenData(user_id=user_id)
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    def create_api_key(self, user_id: str) -> str:
        """Generate secure API key for user"""
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        
        # Store API key in Redis with expiration
        redis_key = f"api_key:{api_key}"
        redis_client.setex(
            redis_key,
            timedelta(days=self.api_key_expire_days),
            user_id
        )
        
        logger.info(f"Created API key for user {user_id}")
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return user ID"""
        if not api_key or not api_key.startswith("ak_"):
            return None
        
        redis_key = f"api_key:{api_key}"
        user_id = redis_client.get(redis_key)
        
        if user_id:
            # Extend API key expiration on use
            redis_client.expire(redis_key, timedelta(days=self.api_key_expire_days))
            return user_id
        
        return None
    
    async def authenticate_user(
        self, 
        username: str, 
        password: str,
        db: Session
    ) -> Optional[UserInDB]:
        """Authenticate user credentials"""
        
        # Get user from database
        user = await self.get_user_by_username(db, username)
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        logger.info(f"User {username} authenticated successfully")
        return user
    
    async def get_user_by_username(
        self, 
        db: Session, 
        username: str
    ) -> Optional[UserInDB]:
        """Get user by username from database"""
        # TODO: Implement database query
        # This is a placeholder - implement with your ORM
        pass
    
    async def get_user_by_id(
        self, 
        db: Session, 
        user_id: str
    ) -> Optional[UserInDB]:
        """Get user by ID from database"""
        # TODO: Implement database query
        # This is a placeholder - implement with your ORM
        pass
    
    async def create_user(
        self, 
        db: Session, 
        user: UserCreate
    ) -> UserInDB:
        """Create new user account"""
        
        # Check if user already exists
        existing_user = await self.get_user_by_username(db, user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Hash password and create user
        hashed_password = self.hash_password(user.password)
        
        db_user = UserInDB(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            is_active=True,
            subscription_tier=SubscriptionTier.FREE,
            created_at=datetime.utcnow()
        )
        
        # TODO: Implement database save
        # db.add(db_user)
        # db.commit()
        # db.refresh(db_user)
        
        logger.info(f"Created new user: {user.username}")
        return db_user


# Global authentication service instance
auth_service = AuthenticationService()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> UserInDB:
    """
    Dependency to get current authenticated user
    Supports both JWT token and API key authentication
    """
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = None
    
    # Try API key authentication first
    if api_key:
        user_id = auth_service.verify_api_key(api_key)
        if user_id:
            logger.debug(f"Authenticated via API key: {user_id}")
    
    # If API key failed, try JWT token
    if not user_id and token:
        token_data = auth_service.verify_token(token)
        if token_data:
            user_id = token_data.user_id
            logger.debug(f"Authenticated via JWT token: {user_id}")
    
    if not user_id:
        logger.warning("Authentication failed - invalid credentials")
        raise credentials_exception
    
    # Get user from database
    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        logger.warning(f"User not found in database: {user_id}")
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """
    Dependency to get current active user with subscription validation
    """
    
    # Additional subscription checks can be added here
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    return current_user


class RateLimiter:
    """Rate limiting with Redis backend"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_rate_limit(
        self,
        user_id: str,
        operation: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """Check if user is within rate limits"""
        
        key = f"rate_limit:{user_id}:{operation}"
        current = self.redis.get(key)
        
        if current is None:
            # First request in window
            self.redis.setex(key, window_seconds, 1)
            return True
        
        if int(current) >= max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id} operation {operation}")
            return False
        
        # Increment counter
        self.redis.incr(key)
        return True
    
    async def get_remaining_requests(
        self,
        user_id: str,
        operation: str,
        max_requests: int
    ) -> int:
        """Get remaining requests in current window"""
        
        key = f"rate_limit:{user_id}:{operation}"
        current = self.redis.get(key)
        
        if current is None:
            return max_requests
        
        return max(0, max_requests - int(current))


# Global rate limiter instance
rate_limiter = RateLimiter(redis_client)


def require_subscription_tier(required_tier: SubscriptionTier):
    """Decorator to require minimum subscription tier"""
    
    def dependency(
        current_user: UserInDB = Depends(get_current_active_user)
    ) -> UserInDB:
        
        user_tier_value = current_user.subscription_tier.value
        required_tier_value = required_tier.value
        
        if user_tier_value < required_tier_value:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"This feature requires {required_tier.name} subscription or higher"
            )
        
        return current_user
    
    return dependency