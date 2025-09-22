"""
Enhanced AI service dependency injection for ArchBuilder.AI Cloud Server
Provides properly configured AI service instances with all dependencies
"""

from typing import Optional
import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.services.ai_service import AIService
from app.services.billing_service import BillingService
from app.services.rag_service import RAGService
from app.services.validation_service import ValidationService

logger = structlog.get_logger(__name__)

# Global service instances (will be properly initialized)
_ai_service_instance: Optional[AIService] = None
_billing_service_instance: Optional[BillingService] = None
_rag_service_instance: Optional[RAGService] = None
_validation_service_instance: Optional[ValidationService] = None

async def get_ai_service() -> AIService:
    """Get configured AI service instance with all dependencies"""
    global _ai_service_instance
    
    if _ai_service_instance is None:
        try:
            # Initialize dependencies
            rag_service = await get_rag_service()
            validation_service = await get_validation_service()
            
            # Initialize AI service with dependencies
            _ai_service_instance = AIService(
                rag_service=rag_service,
                validation_service=validation_service
            )
            
            logger.info("AI service instance created with dependencies")
            
        except Exception as e:
            logger.warning("Failed to initialize AI service with full dependencies", error=str(e))
            # Fallback to basic AI service
            _ai_service_instance = AIService()
    
    return _ai_service_instance

async def get_billing_service() -> BillingService:
    """Get billing service instance"""
    global _billing_service_instance
    
    if _billing_service_instance is None:
        _billing_service_instance = BillingService()
        logger.info("Billing service instance created")
    
    return _billing_service_instance

async def get_rag_service() -> RAGService:
    """Get RAG service instance"""
    global _rag_service_instance
    
    if _rag_service_instance is None:
        try:
            _rag_service_instance = RAGService()
            logger.info("RAG service instance created")
        except Exception as e:
            logger.warning("Failed to initialize RAG service", error=str(e))
            # Return mock RAG service for development
            _rag_service_instance = MockRAGService()
    
    return _rag_service_instance

async def get_validation_service() -> ValidationService:
    """Get validation service instance"""
    global _validation_service_instance
    
    if _validation_service_instance is None:
        try:
            _validation_service_instance = ValidationService()
            logger.info("Validation service instance created")
        except Exception as e:
            logger.warning("Failed to initialize validation service", error=str(e))
            # Return mock validation service for development
            _validation_service_instance = MockValidationService()
    
    return _validation_service_instance

# Mock services for development when full services aren't available
class MockRAGService:
    """Mock RAG service for development"""
    
    async def query_knowledge_base(self, query: str, max_results: int = 5, correlation_id: str = None):
        logger.info("Mock RAG service query", query=query[:50])
        return None

class MockValidationService:
    """Mock validation service for development"""
    
    async def validate_ai_output(self, ai_output: dict, correlation_id: str = None):
        logger.info("Mock validation service check")
        return {
            "is_valid": True,
            "requires_human_review": True,
            "errors": [],
            "warnings": [],
            "confidence": 0.8
        }
    
    async def validate_layout(self, layout: dict, correlation_id: str = None):
        logger.info("Mock layout validation")
        return {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "confidence": 0.8
        }

# Cleanup function for service instances
async def cleanup_services():
    """Cleanup service instances on shutdown"""
    global _ai_service_instance, _billing_service_instance, _rag_service_instance, _validation_service_instance
    
    if _ai_service_instance and hasattr(_ai_service_instance, 'shutdown'):
        await _ai_service_instance.shutdown()
    
    _ai_service_instance = None
    _billing_service_instance = None
    _rag_service_instance = None
    _validation_service_instance = None
    
    logger.info("All service instances cleaned up")