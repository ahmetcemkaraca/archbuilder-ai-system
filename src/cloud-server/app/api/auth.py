"""
Authentication API endpoints for ArchBuilder.AI
Implements OAuth2 + API Key authentication with subscription validation
"""

from datetime import timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import UUID
import jwt

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.auth.token import TokenResponse, RefreshTokenRequest
from app.models.auth.user import UserCreate, UserResponse, UserLogin, User
from app.models.subscriptions import SubscriptionResponse
from app.security.authentication import (
    create_access_token,
    create_api_key,
    authenticate_user,
    get_current_user,
    get_current_active_user,
    verify_subscription,
)
from app.security.password import get_password_hash
from app.services.billing_service import BillingService
from app.dao.user_dao import UserDAO
from app.dao.tenant_dao import TenantDAO
from app.dao.subscription_dao import SubscriptionDAO
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    user_dao: UserDAO = Depends(UserDAO),
    tenant_dao: TenantDAO = Depends(TenantDAO),
    subscription_dao: SubscriptionDAO = Depends(SubscriptionDAO),
    billing_service: BillingService = Depends(BillingService)
) -> UserResponse:
    """
    Yeni kullanıcı hesabı kaydı
    
    ÜCRETSİZ katman aboneliği ile yeni bir kullanıcı oluşturur.
    """
    
    if await user_dao.get_user_by_email(session, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu e-posta zaten kayıtlı.")
    
    # Varsayılan tenant veya mevcut bir tenant'ı bul
    default_tenant = await tenant_dao.get_tenant_by_slug(session, "default-tenant")
    if not default_tenant:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Varsayılan tenant bulunamadı.")

    hashed_password = get_password_hash(user_data.password) # Şifreyi hash'le
    
    new_user = await user_dao.create_user(
        session,
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        tenant_id=default_tenant.id,
    )

    # Ücretsiz abonelik oluştur
    await billing_service.create_free_subscription(session, new_user.id)

    logger.info("Kullanıcı kaydedildi", user_id=new_user.id, email=new_user.email, tenant_id=default_tenant.id)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        role=new_user.role,
        tenant_id=new_user.tenant_id,
        created_at=new_user.created_at,
        last_login=new_user.last_login,
        full_name=f"{new_user.first_name} {new_user.last_name}" if new_user.first_name and new_user.last_name else new_user.email # Geçici olarak tam ad ekledim
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
    billing_service: BillingService = Depends(BillingService)
) -> TokenResponse:
    """
    OAuth2 parola akışı ile kullanıcı kimlik doğrulaması
    
    Erişim token'ı, yenileme token'ı ve API anahtarı döndürür.
    """
    
    user = await authenticate_user(form_data.username, form_data.password, session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hatalı kullanıcı adı veya parola",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hesabınız pasif. Lütfen yöneticinizle iletişime geçin."
        )
    
    subscription = await billing_service.get_active_subscription(session, user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Aktif abonelik gerekli. Lütfen aboneliğinizi yükseltin veya yenileyin."
        )
    
    settings = get_settings()
    access_token = create_access_token(data={"user_id": str(user.id)})
    api_key = create_api_key(user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        api_key=api_key,
        subscription_tier=subscription.plan_name,
        usage_remaining=await billing_service.get_remaining_usage(session, user.id)
    )

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
    billing_service: BillingService = Depends(BillingService)
) -> TokenResponse:
    """
    OAuth2 uyumlu token endpoint'i
    
    OAuth2 uyumluluğu için alternatif endpoint
    """
    return await login_user(form_data, session, billing_service)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
    billing_service: BillingService = Depends(BillingService)
) -> TokenResponse:
    """
    Yenileme token'ı kullanarak erişim token'ını yenile
    """
    
    settings = get_settings()
    try:
        payload = jwt.decode(refresh_request.refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yenileme token'ı geçersiz")
        
        user = await session.get(User, UUID(user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı")
        
        access_token = create_access_token(data={"user_id": str(user.id)})
        api_key = create_api_key(user.id)
        
        subscription = await billing_service.get_active_subscription(session, user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Aktif abonelik gerekli. Lütfen aboneliğinizi yükseltin veya yenileyin."
            )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            api_key=api_key,
            subscription_tier=subscription.plan_name,
            usage_remaining=await billing_service.get_remaining_usage(session, user.id)
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yenileme token'ı geçersiz")

@router.post("/api-key", response_model=APIKeyResponse)
async def generate_new_api_key(
    current_user: User = Depends(get_current_active_user)
) -> APIKeyResponse:
    """
    Kimliği doğrulanmış kullanıcı için yeni API anahtarı oluştur
    """
    api_key = create_api_key(current_user.id)
    return APIKeyResponse(
        api_key=api_key,
        expires_in_days=get_settings().API_KEY_EXPIRE_DAYS,
        created_at=datetime.utcnow(), # TODO: API Key oluşturulduğu zamanı APIKey tablosundan almalıyız
    )

@router.delete("/api-key/{api_key_str}") # api_key yerine api_key_str kullanıyoruz
async def revoke_api_key(
    api_key_str: str, # parametre adını güncelledik
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    user_dao: UserDAO = Depends(UserDAO)
) -> dict:
    """
    API anahtarını iptal et
    """
    await user_dao.revoke_api_key(session, current_user.id, api_key_str) # user_dao kullanarak API anahtarını iptal et
    logger.info("API anahtarı iptal edildi", user_id=current_user.id, api_key_str=api_key_str)
    return {"message": "API anahtarı başarıyla iptal edildi.", "api_key": api_key_str}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Mevcut kullanıcı bilgilerini al
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        full_name=f"{current_user.first_name} {current_user.last_name}" if current_user.first_name and current_user.last_name else current_user.email
    )

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(verify_subscription), # verify_subscription bağımlılığını kullanıyoruz
    session: AsyncSession = Depends(get_db_session),
    billing_service: BillingService = Depends(BillingService)
) -> SubscriptionResponse:
    """
    Mevcut kullanıcı abonelik detaylarını al
    """
    subscription = await billing_service.get_subscription_details(session, current_user.id)
    usage = await billing_service.get_remaining_usage(session, current_user.id)
    
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        plan_name=subscription.plan_name,
        status=subscription.status,
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        max_projects=subscription.max_projects,
        max_documents=subscription.max_documents,
        max_storage_gb=subscription.max_storage_gb,
        ai_requests_monthly=subscription.ai_requests_monthly,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        usage=usage,
        limits={ # limits alanını subscription modelinden alarak güncelliyoruz
            "max_projects": subscription.max_projects,
            "max_documents": subscription.max_documents,
            "max_storage_gb": subscription.max_storage_gb,
            "ai_requests_monthly": subscription.ai_requests_monthly,
        }
    )

@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Kullanıcı oturumunu kapat (token'ları geçersiz kıl)
    """
    logger.info("Kullanıcı çıkış yaptı", user_id=current_user.id)
    return {"message": "Başarıyla çıkış yapıldı.", "user_id": str(current_user.id)}