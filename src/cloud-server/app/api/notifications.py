"""
ArchBuilder.AI Notification API

RESTful API endpoints for email notifications, scheduling, automation rules,
and delivery tracking with comprehensive notification management capabilities.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, EmailStr, Field
import structlog

from ...services.notifications.email_service import (
    EmailService, EmailTemplate, EmailRecipient, EmailPriority, EmailAttachment, EmailConfig
)
from ...services.notifications.notification_scheduler import (
    NotificationScheduler, NotificationType, ScheduledNotification, NotificationRule
)

logger = structlog.get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/notifications", tags=["notifications"])

# Pydantic models for API
class EmailRecipientModel(BaseModel):
    """Email recipient API model."""
    email: EmailStr
    name: Optional[str] = None
    user_id: Optional[str] = None
    locale: str = "en-US"
    metadata: Dict[str, Any] = {}


class EmailAttachmentModel(BaseModel):
    """Email attachment API model."""
    filename: str
    content_base64: str
    content_type: str = "application/octet-stream"
    inline: bool = False
    content_id: Optional[str] = None


class SendNotificationRequest(BaseModel):
    """Send notification request model."""
    template: EmailTemplate
    recipients: List[EmailRecipientModel]
    template_data: Dict[str, Any] = {}
    priority: EmailPriority = EmailPriority.NORMAL
    attachments: Optional[List[EmailAttachmentModel]] = None
    reply_to: Optional[str] = None
    track_opens: bool = True
    track_clicks: bool = True
    metadata: Dict[str, Any] = {}


class ScheduleNotificationRequest(BaseModel):
    """Schedule notification request model."""
    template: EmailTemplate
    recipients: List[EmailRecipientModel]
    template_data: Dict[str, Any] = {}
    scheduled_for: datetime
    priority: EmailPriority = EmailPriority.NORMAL
    notification_type: NotificationType = NotificationType.EMAIL
    metadata: Dict[str, Any] = {}


class BulkNotificationRequest(BaseModel):
    """Bulk notification request model."""
    template: EmailTemplate
    recipients: List[EmailRecipientModel]
    template_data: Dict[str, Any] = {}
    priority: EmailPriority = EmailPriority.NORMAL


class NotificationRuleRequest(BaseModel):
    """Notification rule request model."""
    id: str
    name: str
    trigger_event: str
    template: EmailTemplate
    notification_type: NotificationType = NotificationType.EMAIL
    priority: EmailPriority = EmailPriority.NORMAL
    conditions: Dict[str, Any] = {}
    target_selector: str = "user"
    delay_minutes: int = 0
    enabled: bool = True


class EventTriggerRequest(BaseModel):
    """Event trigger request model."""
    event_name: str
    event_data: Dict[str, Any]


class NotificationResponse(BaseModel):
    """Notification response model."""
    success: bool
    message: str
    notification_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DeliveryStatsResponse(BaseModel):
    """Delivery statistics response model."""
    period_days: int
    total_sent: int
    total_successful: int
    total_failed: int
    success_rate: float
    template_breakdown: Dict[str, Dict[str, int]]
    total_batches: int
    generated_at: str


class SchedulerStatsResponse(BaseModel):
    """Scheduler statistics response model."""
    status: str
    pending_notifications: int
    failed_notifications: int
    completed_notifications: int
    total_rules: int
    enabled_rules: int
    processing_interval: int
    uptime: float
    rule_statistics: Dict[str, Dict[str, Any]]
    generated_at: str


# Dependency injection for services
async def get_email_service() -> EmailService:
    """Get email service instance."""
    # In production, this would be injected from a service container
    config = EmailConfig(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="noreply@archbuilder.ai",
        password="app_password",
        use_tls=True,
        from_email="noreply@archbuilder.ai",
        from_name="ArchBuilder.AI",
        reply_to="support@archbuilder.ai",
        templates_dir="templates/email",
        base_url="https://archbuilder.ai"
    )
    return EmailService(config)


async def get_notification_scheduler(email_service: EmailService = Depends(get_email_service)) -> NotificationScheduler:
    """Get notification scheduler instance."""
    return NotificationScheduler(email_service)


# Email notification endpoints
@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    background_tasks: BackgroundTasks,
    email_service: EmailService = Depends(get_email_service)
):
    """Send an immediate notification."""
    try:
        # Convert API models to service models
        recipients = [
            EmailRecipient(
                email=r.email,
                name=r.name,
                user_id=r.user_id,
                locale=r.locale,
                metadata=r.metadata
            )
            for r in request.recipients
        ]
        
        attachments = []
        if request.attachments:
            import base64
            for att in request.attachments:
                attachments.append(EmailAttachment(
                    filename=att.filename,
                    content=base64.b64decode(att.content_base64),
                    content_type=att.content_type,
                    inline=att.inline,
                    content_id=att.content_id
                ))
        
        # Send notification in background
        result = await email_service.send_bulk_notification(
            template=request.template,
            recipients=recipients,
            template_data=request.template_data,
            priority=request.priority
        )
        
        logger.info("Notification sent via API",
                   template=request.template.value,
                   recipients=len(recipients),
                   successful=result.get("successful", 0))
        
        return NotificationResponse(
            success=result.get("successful", 0) > 0,
            message=f"Notification sent to {result.get('successful', 0)} of {result.get('total_recipients', 0)} recipients",
            details=result
        )
        
    except Exception as e:
        logger.error("Failed to send notification via API",
                    template=request.template.value,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/send-bulk", response_model=NotificationResponse)
async def send_bulk_notification(
    request: BulkNotificationRequest,
    background_tasks: BackgroundTasks,
    email_service: EmailService = Depends(get_email_service)
):
    """Send bulk notifications to multiple recipients."""
    try:
        recipients = [
            EmailRecipient(
                email=r.email,
                name=r.name,
                user_id=r.user_id,
                locale=r.locale,
                metadata=r.metadata
            )
            for r in request.recipients
        ]
        
        # Send bulk notification
        result = await email_service.send_bulk_notification(
            template=request.template,
            recipients=recipients,
            template_data=request.template_data,
            priority=request.priority
        )
        
        logger.info("Bulk notification sent via API",
                   template=request.template.value,
                   total_recipients=len(recipients),
                   successful=result.get("successful", 0))
        
        return NotificationResponse(
            success=result.get("successful", 0) > 0,
            message=f"Bulk notification sent to {result.get('successful', 0)} of {result.get('total_recipients', 0)} recipients",
            details=result
        )
        
    except Exception as e:
        logger.error("Failed to send bulk notification via API",
                    template=request.template.value,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to send bulk notification: {str(e)}")


# Scheduling endpoints
@router.post("/schedule", response_model=NotificationResponse)
async def schedule_notification(
    request: ScheduleNotificationRequest,
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Schedule a notification for future delivery."""
    try:
        recipients = [
            EmailRecipient(
                email=r.email,
                name=r.name,
                user_id=r.user_id,
                locale=r.locale,
                metadata=r.metadata
            )
            for r in request.recipients
        ]
        
        notification_id = await scheduler.schedule_notification(
            template=request.template,
            recipients=recipients,
            template_data=request.template_data,
            scheduled_for=request.scheduled_for,
            priority=request.priority,
            notification_type=request.notification_type,
            metadata=request.metadata
        )
        
        logger.info("Notification scheduled via API",
                   notification_id=notification_id,
                   template=request.template.value,
                   scheduled_for=request.scheduled_for.isoformat())
        
        return NotificationResponse(
            success=True,
            message=f"Notification scheduled for {request.scheduled_for.isoformat()}",
            notification_id=notification_id
        )
        
    except Exception as e:
        logger.error("Failed to schedule notification via API",
                    template=request.template.value,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to schedule notification: {str(e)}")


@router.delete("/schedule/{notification_id}", response_model=NotificationResponse)
async def cancel_scheduled_notification(
    notification_id: str,
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Cancel a scheduled notification."""
    try:
        success = await scheduler.cancel_notification(notification_id)
        
        if success:
            return NotificationResponse(
                success=True,
                message=f"Notification {notification_id} cancelled successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel notification via API",
                    notification_id=notification_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel notification: {str(e)}")


# Automation rule endpoints
@router.post("/rules", response_model=NotificationResponse)
async def create_notification_rule(
    request: NotificationRuleRequest,
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Create an automated notification rule."""
    try:
        rule = NotificationRule(
            id=request.id,
            name=request.name,
            trigger_event=request.trigger_event,
            template=request.template,
            notification_type=request.notification_type,
            priority=request.priority,
            conditions=request.conditions,
            target_selector=request.target_selector,
            delay_minutes=request.delay_minutes,
            enabled=request.enabled
        )
        
        success = await scheduler.add_notification_rule(rule)
        
        if success:
            logger.info("Notification rule created via API",
                       rule_id=request.id,
                       trigger_event=request.trigger_event)
            
            return NotificationResponse(
                success=True,
                message=f"Notification rule '{request.name}' created successfully"
            )
        else:
            raise HTTPException(status_code=409, detail="Rule with this ID already exists")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create notification rule via API",
                    rule_id=request.id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")


@router.post("/trigger", response_model=NotificationResponse)
async def trigger_event_notifications(
    request: EventTriggerRequest,
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Trigger automated notifications based on an event."""
    try:
        triggered_count = await scheduler.trigger_event(
            event_name=request.event_name,
            event_data=request.event_data
        )
        
        logger.info("Event triggered via API",
                   event=request.event_name,
                   triggered_count=triggered_count)
        
        return NotificationResponse(
            success=triggered_count > 0,
            message=f"Event '{request.event_name}' triggered {triggered_count} notifications",
            details={"triggered_count": triggered_count}
        )
        
    except Exception as e:
        logger.error("Failed to trigger event via API",
                    event=request.event_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger event: {str(e)}")


# Statistics and monitoring endpoints
@router.get("/stats/delivery", response_model=DeliveryStatsResponse)
async def get_delivery_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in statistics"),
    email_service: EmailService = Depends(get_email_service)
):
    """Get email delivery statistics."""
    try:
        stats = await email_service.get_delivery_stats(days=days)
        
        return DeliveryStatsResponse(**stats)
        
    except Exception as e:
        logger.error("Failed to get delivery stats via API",
                    days=days,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get delivery statistics: {str(e)}")


@router.get("/stats/scheduler", response_model=SchedulerStatsResponse)
async def get_scheduler_statistics(
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Get scheduler statistics."""
    try:
        stats = await scheduler.get_scheduler_stats()
        
        return SchedulerStatsResponse(**stats)
        
    except Exception as e:
        logger.error("Failed to get scheduler stats via API",
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler statistics: {str(e)}")


@router.get("/history")
async def get_notification_history(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of notifications to return"),
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Get notification delivery history."""
    try:
        history = await scheduler.get_notification_history(limit=limit)
        
        return {
            "success": True,
            "total_returned": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error("Failed to get notification history via API",
                    limit=limit,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get notification history: {str(e)}")


# Scheduler control endpoints
@router.post("/scheduler/start", response_model=NotificationResponse)
async def start_scheduler(
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Start the notification scheduler."""
    try:
        await scheduler.start_scheduler()
        
        return NotificationResponse(
            success=True,
            message="Notification scheduler started successfully"
        )
        
    except Exception as e:
        logger.error("Failed to start scheduler via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/scheduler/stop", response_model=NotificationResponse)
async def stop_scheduler(
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Stop the notification scheduler."""
    try:
        await scheduler.stop_scheduler()
        
        return NotificationResponse(
            success=True,
            message="Notification scheduler stopped successfully"
        )
        
    except Exception as e:
        logger.error("Failed to stop scheduler via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@router.post("/scheduler/pause", response_model=NotificationResponse)
async def pause_scheduler(
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Pause the notification scheduler."""
    try:
        await scheduler.pause_scheduler()
        
        return NotificationResponse(
            success=True,
            message="Notification scheduler paused successfully"
        )
        
    except Exception as e:
        logger.error("Failed to pause scheduler via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to pause scheduler: {str(e)}")


@router.post("/scheduler/resume", response_model=NotificationResponse)
async def resume_scheduler(
    scheduler: NotificationScheduler = Depends(get_notification_scheduler)
):
    """Resume the notification scheduler."""
    try:
        await scheduler.resume_scheduler()
        
        return NotificationResponse(
            success=True,
            message="Notification scheduler resumed successfully"
        )
        
    except Exception as e:
        logger.error("Failed to resume scheduler via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to resume scheduler: {str(e)}")


# Template management endpoints
@router.get("/templates")
async def list_email_templates():
    """List available email templates."""
    try:
        templates = []
        for template in EmailTemplate:
            templates.append({
                "name": template.value,
                "display_name": template.value.replace('_', ' ').title(),
                "description": f"Template for {template.value.replace('_', ' ')} notifications"
            })
        
        return {
            "success": True,
            "total_templates": len(templates),
            "templates": templates
        }
        
    except Exception as e:
        logger.error("Failed to list templates via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.post("/test-connection", response_model=NotificationResponse)
async def test_email_connection(
    email_service: EmailService = Depends(get_email_service)
):
    """Test email service connection."""
    try:
        result = await email_service.test_connection()
        
        return NotificationResponse(
            success=result.get("success", False),
            message=result.get("message", "Connection test completed"),
            details=result
        )
        
    except Exception as e:
        logger.error("Failed to test email connection via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to test connection: {str(e)}")