---
applyTo: "src/cloud-server/**/*.py,src/cloud-server/**/requirements*.txt,src/cloud-server/**/pyproject.toml"
description: Python Cloud Server — FastAPI security, AI model integration, async patterns, subscription management.
---
As Python Cloud Server Developer:
- Use FastAPI with comprehensive security middleware (CORS, rate limiting, authentication)
- Implement secure HTTPS REST API for cloud-based AI-Revit communication
- Apply async/await patterns for AI model inference and database operations
- Use Pydantic models for request/response validation and data contracts
- Implement multi-tenant architecture with proper data isolation
- Integrate subscription management and usage tracking
- Structure logs with request tracing and error correlation
- **ALL AI PROCESSING**: Centralize all AI logic in cloud server - no client-side AI processing

Cloud-Native FastAPI Setup:
```python
# Secure FastAPI setup with cloud SaaS features
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import redis
import asyncpg
from typing import Optional

# Rate limiting with Redis backend for cloud scaling
redis_client = redis.Redis(host="redis", port=6379, db=0)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379"
)

app = FastAPI(
    title="RevitAutoPlan Cloud API",
    version="1.0.0",
    description="Cloud-based AI architectural design automation",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware for cloud deployment
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.revit-autoplan.com", "*.api.revit-autoplan.com"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.revit-autoplan.com"],  # Frontend domain
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["X-Correlation-ID", "X-API-Key", "Authorization", "Content-Type"],
    allow_credentials=True
)

# Authentication setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
api_key_header = APIKeyHeader(name="X-API-Key")

# Database connection pool for PostgreSQL
DATABASE_URL = "postgresql://user:password@postgres:5432/revitautoplan"

async def get_db():
    """Get database connection with connection pooling"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# Multi-tenant user authentication
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: str = Depends(api_key_header),
    db = Depends(get_db)
) -> User:
    """Authenticate user with JWT + API key and check subscription"""
    
    user = await auth_service.authenticate_user(token, api_key, db)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
    
    # Check active subscription
    subscription = await billing_service.get_active_subscription(user.id, db)
    if not subscription:
        raise HTTPException(
            status_code=402,
            detail="Active subscription required"
        )
    
    user.subscription = subscription
    return user

# Usage tracking and rate limiting by subscription tier
async def check_usage_limits(
    operation_type: str,
    cost_units: int,
    current_user: User = Depends(get_current_user)
):
    """Check usage limits based on subscription tier"""
    
    can_proceed = await usage_tracker.check_usage_limit(
        current_user.id,
        operation_type,
        current_user.subscription.tier
    )
    
    if not can_proceed:
        raise HTTPException(
            status_code=402,
            detail=f"Usage limit exceeded for {operation_type}. Please upgrade your subscription."
        )
    
    return True

# Cloud-based AI endpoints with subscription management
@app.post("/v1/ai/layouts/generate")
@limiter.limit("20/minute")  # Base rate limit, further limited by subscription
async def generate_layout(
    request: LayoutRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _: bool = Depends(lambda: check_usage_limits("ai_layout_generation", 10)),
    correlation_id: str = Header(..., alias="X-Correlation-ID"),
    db = Depends(get_db)
) -> LayoutResponse:
    """Generate architectural layout using cloud AI models with usage tracking"""
    
    logger = structlog.get_logger().bind(
        correlation_id=correlation_id,
        user_id=current_user.id,
        subscription_tier=current_user.subscription.tier,
        endpoint="generate_layout"
    )
    
    try:
        logger.info("Layout generation started",
                   building_type=request.building_type,
                   total_area=request.total_area_m2)
        
        # Multi-model AI processing with tier-based model selection
        ai_result = await ai_service.generate_layout_with_tier_optimization(
            request,
            subscription_tier=current_user.subscription.tier,
            user_preferences=current_user.preferences
        )
        
        # Comprehensive validation
        validation = await validator.validate_layout(ai_result, request.region)
        
        # Store result with user isolation
        layout_id = await layout_storage.save_layout(
            user_id=current_user.id,
            layout_data=ai_result,
            validation_result=validation,
            correlation_id=correlation_id,
            db=db
        )
        
        # Track usage for billing
        background_tasks.add_task(
            usage_tracker.track_operation,
            current_user.id,
            "ai_layout_generation",
            10,  # cost units
            {"layout_id": layout_id, "building_type": request.building_type}
        )
        
        # Queue for human review if required
        if validation.requires_human_review:
            background_tasks.add_task(
                review_queue.add_for_review,
                layout_id,
                current_user.id,
                correlation_id
            )
        
        logger.info("Layout generated successfully",
                   layout_id=layout_id,
                   validation_status=validation.status.value,
                   requires_review=validation.requires_human_review)
        
        return LayoutResponse(
            layout_id=layout_id,
            layout=ai_result,
            validation=validation,
            requires_human_review=validation.requires_human_review,
            correlation_id=correlation_id,
            subscription_usage=await usage_tracker.get_current_usage(current_user.id)
        )
        
    except AIServiceException as ex:
        logger.error("AI service error", error=str(ex), exc_info=True)
        
        # Return rule-based fallback for paid subscribers
        if current_user.subscription.tier != SubscriptionTier.FREE:
            fallback_result = await fallback_service.generate_simple_layout(request)
            return LayoutResponse(
                layout_id=None,
                layout=fallback_result,
                validation=ValidationResult(status=ValidationStatus.FALLBACK_USED),
                requires_human_review=True,
                correlation_id=correlation_id,
                warnings=["AI service failed, using rule-based layout"]
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="AI service temporarily unavailable. Please try again or upgrade for fallback options."
            )
    
    except Exception as ex:
        logger.error("Unexpected error", error=str(ex), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please contact support."
        )

@app.get("/v1/users/{user_id}/layouts")
async def get_user_layouts(
    user_id: str,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db = Depends(get_db)
) -> LayoutListResponse:
    """Get user's layout history with pagination"""
    
    # Ensure user can only access their own layouts
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    layouts = await layout_storage.get_user_layouts(
        user_id=user_id,
        skip=skip,
        limit=limit,
        db=db
    )
    
    return LayoutListResponse(
        layouts=layouts,
        total_count=await layout_storage.count_user_layouts(user_id, db),
        page=skip // limit + 1,
        pages_total=(await layout_storage.count_user_layouts(user_id, db) + limit - 1) // limit
    )

@app.post("/v1/auth/register")
async def register_user(
    registration: UserRegistrationRequest,
    db = Depends(get_db)
) -> UserRegistrationResponse:
    """Register new user with free tier subscription"""
    
    try:
        # Validate registration data
        if await user_service.email_exists(registration.email, db):
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Create user account
        user = await user_service.create_user(
            email=registration.email,
            password=registration.password,
            full_name=registration.full_name,
            company=registration.company,
            db=db
        )
        
        # Create free subscription
        subscription = await billing_service.create_free_subscription(user.id, db)
        
        # Generate authentication tokens
        access_token = auth_service.create_access_token(user.id)
        api_key = auth_service.create_api_key(user.id)
        
        return UserRegistrationResponse(
            user_id=user.id,
            access_token=access_token,
            api_key=api_key,
            subscription_tier=subscription.tier,
            message="Registration successful. Welcome to RevitAutoPlan!"
        )
        
    except Exception as ex:
        logger.error("Registration failed", error=str(ex), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again."
        )

@app.post("/v1/subscriptions/upgrade")
async def upgrade_subscription(
    upgrade_request: SubscriptionUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> UpgradeResponse:
    """Upgrade user subscription with Stripe integration"""
    
    try:
        result = await billing_service.upgrade_subscription(
            user_id=current_user.id,
            new_tier=upgrade_request.new_tier,
            payment_method_id=upgrade_request.payment_method_id,
            billing_cycle=upgrade_request.billing_cycle,
            db=db
        )
        
        if result.success:
            logger.info("Subscription upgraded",
                       user_id=current_user.id,
                       old_tier=current_user.subscription.tier,
                       new_tier=upgrade_request.new_tier)
        
        return UpgradeResponse(
            success=result.success,
            new_tier=result.new_tier,
            next_billing_date=result.next_billing_date,
            message=result.message
        )
        
    except Exception as ex:
        logger.error("Subscription upgrade failed",
                    user_id=current_user.id,
                    error=str(ex),
                    exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Subscription upgrade failed. Please try again or contact support."
        )

# Webhook endpoint for Stripe events
@app.post("/v1/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db = Depends(get_db)
):
    """Handle Stripe webhook events for subscription management"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
        
        await billing_service.handle_stripe_webhook(event, db)
        
        return {"status": "success"}
        
    except Exception as ex:
        logger.error("Stripe webhook error", error=str(ex), exc_info=True)
        raise HTTPException(status_code=400, detail="Webhook error")

# Health check with dependency status
@app.get("/v1/health")
async def health_check() -> HealthResponse:
    """Comprehensive health check for cloud deployment"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "dependencies": {}
    }
    
    # Check database connectivity
    try:
        async with asyncpg.connect(DATABASE_URL) as conn:
            await conn.fetchval("SELECT 1")
        health_status["dependencies"]["database"] = "healthy"
    except Exception:
        health_status["dependencies"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        await redis_client.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception:
        health_status["dependencies"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check AI service connectivity
    try:
        await ai_service.health_check()
        health_status["dependencies"]["ai_service"] = "healthy"
    except Exception:
        health_status["dependencies"]["ai_service"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return HealthResponse(**health_status)
```

Multi-Language Document Processing with Cloud Storage:
```python
class CloudDocumentProcessor:
    """Process building codes and regulations with cloud storage integration"""
    
    def __init__(self, s3_client, redis_client):
        self.s3 = s3_client
        self.redis = redis_client
        self.language_models = {
            "tr": "tr_core_news_sm",
            "en": "en_core_web_sm",
            "de": "de_core_news_sm",
            "fr": "fr_core_news_sm",
            "es": "es_core_news_sm"
        }
    
    async def process_building_code_document(
        self,
        document_url: str,
        user_id: str,
        language: str = None,
        correlation_id: str = None
    ) -> DocumentProcessingResult:
        """Process building code documents with cloud storage and caching"""
        
        logger = structlog.get_logger().bind(
            correlation_id=correlation_id,
            user_id=user_id,
            document_url=document_url
        )
        
        # Check cache first
        cache_key = f"document:{hashlib.md5(document_url.encode()).hexdigest()}"
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            logger.info("Document found in cache")
            return DocumentProcessingResult.parse_raw(cached_result)
        
        # Download document from S3 or URL
        document_content = await self._download_document(document_url)
        
        # Auto-detect language if not provided
        if not language:
            language = await self.detect_language(document_content)
            logger.info("Language detected", language=language)
        
        # OCR with language-specific optimization
        text_content = await self.extract_text_with_ocr(
            document_content,
            language=language
        )
        
        # Process with language-specific NLP model
        extracted_rules = await self.extract_building_rules(
            text_content,
            language=language,
            user_id=user_id
        )
        
        # Store processed knowledge in cloud storage
        knowledge_id = await self.knowledge_store.save_processed_document(
            user_id=user_id,
            document_url=document_url,
            language=language,
            extracted_rules=extracted_rules,
            correlation_id=correlation_id
        )
        
        result = DocumentProcessingResult(
            knowledge_id=knowledge_id,
            language=language,
            rules_count=len(extracted_rules),
            processing_time_seconds=time.time() - start_time,
            confidence_score=self.calculate_extraction_confidence(extracted_rules)
        )
        
        # Cache result for 24 hours
        await self.redis.setex(
            cache_key,
            86400,  # 24 hours
            result.json()
        )
        
        logger.info("Document processed successfully",
                   knowledge_id=knowledge_id,
                   language=language,
                   rules_extracted=len(extracted_rules))
        
        return result
```

Always implement comprehensive security, usage tracking, multi-tenancy, and cloud-native patterns.

---

Multi-Language Document Processing:
```python
class MultiLanguageDocumentProcessor:
    """Process building codes and regulations in multiple languages"""
    
    def __init__(self):
        self.language_models = {
            "tr": "tr_core_news_sm",  # Turkish
            "en": "en_core_web_sm",   # English  
            "de": "de_core_news_sm",  # German
            "fr": "fr_core_news_sm",  # French
            "es": "es_core_news_sm"   # Spanish
        }
        self.ocr_configs = {
            "tr": {"lang": "tur", "dpi": 300},
            "en": {"lang": "eng", "dpi": 300},
            "de": {"lang": "deu", "dpi": 300}
        }
    
    async def process_building_code_document(
        self,
        document_path: str,
        language: str = None,
        correlation_id: str = None
    ) -> DocumentProcessingResult:
        """Process building code documents with language-specific optimization"""
        
        logger = structlog.get_logger().bind(
            correlation_id=correlation_id,
            document_path=document_path
        )
        
        # Auto-detect language if not provided
        if not language:
            language = await self.detect_language(document_path)
            logger.info("Language detected", language=language)
        
        # OCR with language-specific configuration
        ocr_config = self.ocr_configs.get(language, self.ocr_configs["en"])
        text_content = await self.extract_text_with_ocr(document_path, ocr_config)
        
        # Process with language-specific NLP model
        nlp_model = self.language_models.get(language, self.language_models["en"])
        extracted_rules = await self.extract_building_rules(text_content, nlp_model, language)
        
        # Store processed knowledge
        await self.knowledge_store.save_processed_document(
            document_path=document_path,
            language=language,
            extracted_rules=extracted_rules,
            correlation_id=correlation_id
        )
        
        logger.info("Document processed successfully",
                   language=language,
                   rules_extracted=len(extracted_rules))
        
        return DocumentProcessingResult(
            language=language,
            rules_count=len(extracted_rules),
            processing_time_seconds=(time.time() - start_time),
            confidence_score=self.calculate_extraction_confidence(extracted_rules)
        )
```

AI Safety and Human Review Integration:
```python
from enum import Enum
from typing import Optional

class ValidationStatus(Enum):
    VALID = "valid"
    REQUIRES_REVIEW = "requires_review"
    REJECTED = "rejected"

class AIOutputValidator:
    """Comprehensive AI output validation with human review flags"""
    
    async def validate_ai_output(self, ai_result: dict) -> ValidationResult:
        """Always validate AI outputs before sending to Revit"""
        validation_errors = []
        confidence_score = ai_result.get("confidence", 0.0)
        
        # Geometric validation
        if not self._validate_geometry(ai_result):
            validation_errors.append("Invalid geometry detected")
        
        # Spatial validation  
        if not self._validate_spatial_constraints(ai_result):
            validation_errors.append("Spatial constraints violated")
        
        # Code compliance
        if not await self._validate_zoning_compliance(ai_result):
            validation_errors.append("Zoning violations detected")
        
        # Confidence threshold check
        if confidence_score < 0.8:
            validation_errors.append(f"Low AI confidence: {confidence_score}")
        
        # Determine status
        if validation_errors:
            status = ValidationStatus.REJECTED if len(validation_errors) > 2 else ValidationStatus.REQUIRES_REVIEW
        else:
            # Even valid outputs need human review
            status = ValidationStatus.REQUIRES_REVIEW
        
        return ValidationResult(
            status=status,
            errors=validation_errors,
            confidence=confidence_score,
            requires_human_review=True  # Always require human review
        )
```

Comprehensive Database & Logging:
```python
# Database setup with full audit trail
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
import structlog

Base = declarative_base()

class AICommand(Base):
    __tablename__ = "ai_commands"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    command_text = Column(Text, nullable=False)
    ai_response = Column(JSON)
    validation_result = Column(JSON)
    human_review_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    correlation_id = Column(String, nullable=False)

# Structured logging setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()
```

Always validate inputs, implement timeouts, provide fallbacks, log operations.
