from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.database import User, Subscription
from app.core.exceptions import RevitAutoPlanException

# Şifre hashleme için context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 şemaları
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
api_key_header = APIKeyHeader(name="X-API-Key")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """JWT erişim token'ı oluşturur."""
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "sub": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_api_key(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """API anahtarı oluşturur."""
    settings = get_settings()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.API_KEY_EXPIRE_DAYS)
    data = {"user_id": str(user_id), "exp": expire, "sub": "api_key"}
    encoded_jwt = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str, session: AsyncSession) -> Optional[User]:
    """E-posta ile kullanıcıyı getirir."""
    return await session.scalar(User.query.filter_by(email=email).first())

async def authenticate_user(email: str, password: str, session: AsyncSession) -> Optional[User]:
    """Kullanıcı kimlik bilgilerini doğrular."""
    user = await get_user_by_email(email, session)
    if not user or not pwd_context.verify(password, user.password_hash):
        return None
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Mevcut kullanıcıyı JWT veya API anahtarı ile alır ve aboneliğini kontrol eder."""
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama bilgileri geçersiz",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        if token:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id: str = payload.get("user_id")
            if user_id is None:
                raise credentials_exception
            
            user = await session.get(User, UUID(user_id))
            if user is None:
                raise credentials_exception
            
            return user
        
        elif api_key:
            payload = jwt.decode(api_key, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id: str = payload.get("user_id")
            if user_id is None:
                raise credentials_exception
            
            user = await session.get(User, UUID(user_id))
            if user is None:
                raise credentials_exception
            
            return user
        
        else:
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Etkin mevcut kullanıcıyı kontrol eder."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hesap pasif")
    return current_user

async def get_current_active_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Yönetici rolüne sahip etkin mevcut kullanıcıyı kontrol eder."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Yönetici ayrıcalıkları gerekli")
    return current_user

async def verify_subscription(current_user: User = Depends(get_current_active_user)) -> User:
    """Kullanıcının aktif bir aboneliği olup olmadığını kontrol eder."""
    async for session in get_db_session():
        subscription = await session.scalar(Subscription.query.filter_by(user_id=current_user.id, status="active").first())
        if not subscription:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Aktif abonelik gerekli.")
        current_user.subscription = subscription # Kullanıcı objesine abonelik bilgisini ekle
        return current_user

