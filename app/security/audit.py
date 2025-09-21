import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

logger = structlog.get_logger(__name__)

class AuditLogger:
    """Uygulama genelinde güvenlik denetim günlüklerini yönetir."""

    def log_event(
        self,
        event_type: str,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        message: str = ""
    ):
        """Genel bir denetim olayını loglar."""
        log_data = {
            "event_type": event_type,
            "user_id": str(user_id) if user_id else None,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "message": message,
            "details": details or {}
        }
        logger.info("AUDIT_LOG", **log_data)

    def log_authentication_event(
        self,
        user_id: Optional[UUID],
        email: str,
        ip_address: str,
        user_agent: str,
        correlation_id: str,
        success: bool,
        reason: str = ""
    ):
        """Kimlik doğrulama olaylarını loglar (giriş/çıkış/başarısız giriş)."""
        self.log_event(
            event_type="AUTHENTICATION",
            user_id=user_id,
            correlation_id=correlation_id,
            success=success,
            message=f"Kullanıcı {email} için kimlik doğrulama {'başarılı' if success else 'başarısız'}",
            details={
                "email": email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "reason": reason
            }
        )

    def log_authorization_event(
        self,
        user_id: UUID,
        action: str,
        resource: str,
        correlation_id: str,
        success: bool,
        reason: str = ""
    ):
        """Yetkilendirme olaylarını loglar (erişim başarılı/başarısız)."""
        self.log_event(
            event_type="AUTHORIZATION",
            user_id=user_id,
            correlation_id=correlation_id,
            success=success,
            message=f"Kullanıcı {user_id} için {action} işlemi {resource} üzerinde {'başarılı' if success else 'başarısız'}",
            details={
                "action": action,
                "resource": resource,
                "reason": reason
            }
        )

    def log_data_access_event(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        action: str,
        correlation_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Hassas veri erişim olaylarını loglar."""
        self.log_event(
            event_type="DATA_ACCESS",
            user_id=user_id,
            correlation_id=correlation_id,
            message=f"Kullanıcı {user_id}, {resource_type} (ID: {resource_id}) kaynağına {action} işlemi yaptı.",
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "action": action,
                "additional_details": details or {}
            }
        )

    def log_system_event(
        self,
        event_name: str,
        correlation_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Sistemle ilgili olayları loglar (yapılandırma değişiklikleri, servis başlatma/durdurma)."""
        self.log_event(
            event_type="SYSTEM_EVENT",
            correlation_id=correlation_id,
            success=success,
            message=f"Sistem olayı: {event_name} - {'başarılı' if success else 'başarısız'}",
            details={
                "event_name": event_name,
                "additional_details": details or {}
            }
        )

audit_logger = AuditLogger()

