"""
ArchBuilder.AI Billing API Endpoints

RESTful API for subscription management, billing operations, and usage tracking.
Handles Stripe integration, pricing plans, and payment processing.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from app.services.billing_service import BillingService
from app.security.authentication import get_current_active_user, verify_subscription
from app.models.database import User, Subscription
from app.models.subscriptions import (
    SubscriptionResponse, PricingPlanResponse, UsageLimitsResponse,
    CreateCustomerRequest, StartSubscriptionRequest, ChangeSubscriptionRequest,
    CancelSubscriptionRequest, UsageTrackingRequest, BillingInfoResponse
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


# ===== Request/Response Models =====

# Request/Response modelleri zaten yukarıda import edildi


# ===== Dependencies =====

# get_subscription_service kaldırıldı, doğrudan BillingService Depends ile alacağız.


# ===== API Endpoints =====

@router.get("/pricing-plans", response_model=Dict[str, PricingPlanResponse])
async def get_pricing_plans(
    billing_service: BillingService = Depends(BillingService)
) -> Dict[str, PricingPlanResponse]:
    """Tüm mevcut fiyatlandırma planlarını al."""
    try:
        plans = await billing_service.get_pricing_plans() # async olarak çağır
        
        response = {}
        for plan in plans:
            response[plan.tier.value] = PricingPlanResponse(
                tier=plan.tier,
                name=plan.name,
                monthly_price=plan.monthly_price,
                yearly_price=plan.yearly_price,
                features=plan.features,
                limits=plan.limits,
                trial_days=plan.trial_days
            )
        
        logger.info("Fiyatlandırma planları alındı", plans_count=len(response))
        return response
        
    except Exception as e:
        logger.error("Fiyatlandırma planları alınamadı", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fiyatlandırma planları alınamadı.")


@router.post("/customer", response_model=Dict[str, str])
async def create_customer(
    request: CreateCustomerRequest,
    current_user: User = Depends(get_current_active_user), # User tipini kullandık
    billing_service: BillingService = Depends(BillingService)
) -> Dict[str, str]:
    """Yeni bir Stripe müşterisi oluştur."""
    try:
        customer_id = await billing_service.create_customer(
            user_id=current_user.id, # User objesinden id aldık
            email=request.email,
            name=request.name,
            metadata=request.metadata
        )
        
        logger.info("Müşteri oluşturuldu", user_id=current_user.id, customer_id=customer_id)
        
        return {"customer_id": customer_id, "status": "success", "message": "Müşteri başarıyla oluşturuldu."}
        
    except Exception as e:
        logger.error("Müşteri oluşturulamadı", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/subscription/start", response_model=SubscriptionResponse)
async def start_subscription(
    request: StartSubscriptionRequest,
    customer_id: str = Header(..., alias="X-Stripe-Customer-ID"), # Customer ID'yi header'dan alıyoruz
    current_user: User = Depends(verify_subscription), # User tipini kullandık ve abonelik kontrolü yaptık
    billing_service: BillingService = Depends(BillingService)
) -> SubscriptionResponse:
    """Yeni bir abonelik başlat."""
    try:
        result = await billing_service.start_subscription(
            user_id=current_user.id,
            customer_id=customer_id,
            tier=request.tier,
            billing_cycle=request.billing_cycle
        )
        
        logger.info("Abonelik başlatıldı", 
                   user_id=current_user.id, 
                   subscription_id=result["subscription_id"],
                   tier=request.tier.value)
        
        return SubscriptionResponse(
            subscription_id=result["subscription_id"],
            status=result["status"],
            tier=request["tier"],
            billing_cycle=result["billing_cycle"],
            client_secret=result.get("client_secret"),
            trial_end=result.get("trial_end")
        )
        
    except Exception as e:
        logger.error("Abonelik başlatılamadı", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/subscription/{subscription_id}", response_model=SubscriptionResponse)
async def change_subscription(
    subscription_id: str,
    request: ChangeSubscriptionRequest,
    current_user: User = Depends(verify_subscription), # User tipini kullandık ve abonelik kontrolü yaptık
    billing_service: BillingService = Depends(BillingService)
) -> SubscriptionResponse:
    """Abonelik katmanını veya faturalandırma döngüsünü değiştir."""
    try:
        result = await billing_service.change_subscription(
            subscription_id=subscription_id,
            new_tier=request.new_tier,
            billing_cycle=request.billing_cycle
        )
        
        logger.info("Abonelik değiştirildi", 
                   user_id=current_user.id,
                   subscription_id=subscription_id,
                   new_tier=request.new_tier.value)
        
        return SubscriptionResponse(
            subscription_id=result["subscription_id"],
            status=result["status"],
            tier=result["tier"],
            billing_cycle=result["billing_cycle"]
        )
        
    except Exception as e:
        logger.error("Abonelik değiştirilemedi", 
                    user_id=current_user.id,
                    subscription_id=subscription_id,
                    error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/subscription/{subscription_id}", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    request: CancelSubscriptionRequest,
    current_user: User = Depends(verify_subscription), # User tipini kullandık ve abonelik kontrolü yaptık
    billing_service: BillingService = Depends(BillingService)
) -> SubscriptionResponse:
    """Aboneliği iptal et."""
    try:
        result = await billing_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=request.at_period_end
        )
        
        logger.info("Abonelik iptal edildi", 
                   user_id=current_user.id,
                   subscription_id=subscription_id,
                   immediate=not request.at_period_end)
        
        return SubscriptionResponse(
            subscription_id=result["subscription_id"],
            status=result["status"]
        )
        
    except Exception as e:
        logger.error("Abonelik iptal edilemedi", 
                    user_id=current_user.id,
                    subscription_id=subscription_id,
                    error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/info", response_model=BillingInfoResponse)
async def get_billing_info(
    current_user: User = Depends(verify_subscription), # User tipini kullandık ve abonelik kontrolü yaptık
    billing_service: BillingService = Depends(BillingService)
) -> BillingInfoResponse:
    """Kullanıcı faturalandırma bilgilerini al."""
    try:
        billing_info = await billing_service.get_billing_info(current_user.id) # user_id doğrudan alınıyor
        
        if not billing_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faturalandırma bilgileri bulunamadı.")
        
        logger.info("Faturalandırma bilgileri alındı", user_id=current_user.id)
        
        return BillingInfoResponse(
            user_id=billing_info.user_id,
            subscription_id=billing_info.subscription_id,
            stripe_customer_id=billing_info.stripe_customer_id,
            current_tier=billing_info.current_tier,
            status=billing_info.status,
            billing_cycle=billing_info.billing_cycle,
            current_period_start=billing_info.current_period_start,
            current_period_end=billing_info.current_period_end,
            trial_end=billing_info.trial_end,
            usage_metrics=billing_info.usage_metrics.model_dump() if billing_info.usage_metrics else {},
            metadata=billing_info.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Faturalandırma bilgileri alınamadı", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Faturalandırma bilgileri alınamadı.")


@router.post("/usage/track", response_model=Dict[str, Any])
async def track_usage(
    request: UsageTrackingRequest,
    current_user: User = Depends(verify_subscription), # User tipini kullandık ve abonelik kontrolü yaptık
    billing_service: BillingService = Depends(BillingService)
) -> Dict[str, Any]:
    """Kullanıcı kullanımını takip et."""
    try:
        success = await billing_service.track_usage(
            user_id=current_user.id,
            usage_type=request.usage_type,
            amount=request.amount
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kullanım takip edilemedi.")
        
        logger.info("Kullanım takip edildi", 
                   user_id=current_user.id,
                   usage_type=request.usage_type,
                   amount=request.amount)
        
        return {"status": "success", "message": "Kullanım başarıyla takip edildi.", "usage_type": request.usage_type, "amount": request.amount}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Kullanım takip edilemedi", 
                    user_id=current_user.id,
                    usage_type=request.usage_type,
                    error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kullanım takip edilemedi.")


@router.get("/usage/limits/{usage_type}", response_model=UsageLimitsResponse)
async def check_usage_limits(
    usage_type: str,
    current_user: User = Depends(verify_subscription), # User tipini kullandık ve abonelik kontrolü yaptık
    billing_service: BillingService = Depends(BillingService)
) -> UsageLimitsResponse:
    """Belirli bir kullanım türü için kullanım limitlerini kontrol et."""
    try:
        result = await billing_service.check_usage_limits(
            user_id=current_user.id,
            usage_type=usage_type
        )
        
        logger.info("Kullanım limitleri kontrol edildi", 
                   user_id=current_user.id,
                   usage_type=usage_type,
                   allowed=result.allowed)
        
        return UsageLimitsResponse(
            allowed=result.allowed,
            reason=result.reason,
            current=result.current,
            limit=result.limit,
            remaining=result.remaining
        )
        
    except Exception as e:
        logger.error("Kullanım limitleri kontrol edilemedi", 
                    user_id=current_user.id,
                    usage_type=usage_type,
                    error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kullanım limitleri kontrol edilemedi.")


@router.post("/webhook", response_model=Dict[str, str])
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature"),
    billing_service: BillingService = Depends(BillingService)
) -> Dict[str, str]:
    """Stripe webhooks'larını işle."""
    try:
        payload = await request.body()
        
        result = await billing_service.process_webhook(
            payload=payload.decode("utf-8"),
            sig_header=stripe_signature
        )
        
        logger.info("Stripe webhook işlendi", 
                   event_type=result.event_type if hasattr(result, 'event_type') else "unknown")
        
        return {"status": "success", "message": "Webhook başarıyla işlendi."}
        
    except Exception as e:
        logger.error("Webhook işlenemedi", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/health")
async def billing_health_check(
    billing_service: BillingService = Depends(BillingService)
) -> Dict[str, str]:
    """Faturalandırma hizmeti için sağlık kontrolü endpoint'i."""
    try:
        health_status = await billing_service.health_check()
        logger.info("Faturalandırma hizmeti sağlık kontrolü başarılı", status=health_status.status)
        return {"status": health_status.status, "service": "billing", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error("Faturalandırma hizmeti sağlık kontrolü başarısız", error=str(e))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Hizmet sağlıklı değil.")