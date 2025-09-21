"""
ArchBuilder.AI Notification Scheduler

Centralized notification scheduling and delivery management for all system events,
user communications, and automated alerts with priority handling and retry logic.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import structlog
from .email_service import EmailService, EmailTemplate, EmailRecipient, EmailPriority, EmailMessage

logger = structlog.get_logger(__name__)


class SchedulerStatus(str, Enum):
    """Scheduler status types."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class NotificationType(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


@dataclass
class ScheduledNotification:
    """Scheduled notification structure."""
    id: str
    notification_type: NotificationType
    template: EmailTemplate
    recipients: List[EmailRecipient]
    template_data: Dict[str, Any]
    priority: EmailPriority
    scheduled_for: datetime
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: int = 300  # 5 minutes
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt: Optional[datetime] = None
    status: str = "pending"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationRule:
    """Automated notification rule."""
    id: str
    name: str
    trigger_event: str
    template: EmailTemplate
    notification_type: NotificationType
    priority: EmailPriority
    conditions: Dict[str, Any]
    target_selector: str  # e.g., "user.subscription_tier == 'professional'"
    delay_minutes: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


class NotificationScheduler:
    """Centralized notification scheduler with multi-channel support."""
    
    def __init__(self, email_service: EmailService):
        """Initialize notification scheduler."""
        self.email_service = email_service
        self.logger = logger.bind(service="notification_scheduler")
        
        # Scheduling queues
        self.pending_notifications: List[ScheduledNotification] = []
        self.failed_notifications: List[ScheduledNotification] = []
        self.completed_notifications: List[ScheduledNotification] = []
        
        # Automation rules
        self.notification_rules: List[NotificationRule] = []
        
        # Scheduler state
        self.status = SchedulerStatus.ACTIVE
        self.worker_task: Optional[asyncio.Task] = None
        self.processing_interval = 30  # seconds
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        self.logger.info("Notification scheduler initialized")

    async def start_scheduler(self):
        """Start the notification scheduler worker."""
        try:
            if self.worker_task and not self.worker_task.done():
                self.logger.warning("Scheduler already running")
                return
            
            self.status = SchedulerStatus.ACTIVE
            self.worker_task = asyncio.create_task(self._scheduler_worker())
            
            self.logger.info("Notification scheduler started")
            
        except Exception as e:
            self.logger.error("Failed to start scheduler", error=str(e))
            raise Exception(f"Scheduler start failed: {str(e)}")

    async def stop_scheduler(self):
        """Stop the notification scheduler worker."""
        try:
            self.status = SchedulerStatus.STOPPED
            
            if self.worker_task and not self.worker_task.done():
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("Notification scheduler stopped")
            
        except Exception as e:
            self.logger.error("Failed to stop scheduler", error=str(e))

    async def pause_scheduler(self):
        """Pause the notification scheduler."""
        self.status = SchedulerStatus.PAUSED
        self.logger.info("Notification scheduler paused")

    async def resume_scheduler(self):
        """Resume the notification scheduler."""
        self.status = SchedulerStatus.ACTIVE
        self.logger.info("Notification scheduler resumed")

    async def schedule_notification(self, template: EmailTemplate, recipients: List[EmailRecipient],
                                  template_data: Dict[str, Any], scheduled_for: datetime,
                                  priority: EmailPriority = EmailPriority.NORMAL,
                                  notification_type: NotificationType = NotificationType.EMAIL,
                                  metadata: Dict[str, Any] = None) -> str:
        """Schedule a notification for future delivery."""
        try:
            notification_id = f"notif_{datetime.utcnow().timestamp()}_{template.value}"
            
            notification = ScheduledNotification(
                id=notification_id,
                notification_type=notification_type,
                template=template,
                recipients=recipients,
                template_data=template_data,
                priority=priority,
                scheduled_for=scheduled_for,
                metadata=metadata or {}
            )
            
            self.pending_notifications.append(notification)
            
            self.logger.info("Notification scheduled",
                           notification_id=notification_id,
                           template=template.value,
                           scheduled_for=scheduled_for.isoformat(),
                           recipients=len(recipients))
            
            return notification_id
            
        except Exception as e:
            self.logger.error("Failed to schedule notification",
                            template=template.value,
                            error=str(e))
            raise Exception(f"Notification scheduling failed: {str(e)}")

    async def schedule_immediate_notification(self, template: EmailTemplate, recipients: List[EmailRecipient],
                                            template_data: Dict[str, Any],
                                            priority: EmailPriority = EmailPriority.NORMAL,
                                            notification_type: NotificationType = NotificationType.EMAIL) -> str:
        """Schedule an immediate notification."""
        immediate_time = datetime.utcnow() + timedelta(seconds=1)
        return await self.schedule_notification(
            template, recipients, template_data, immediate_time, priority, notification_type
        )

    async def cancel_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification."""
        try:
            # Find and remove from pending notifications
            for i, notification in enumerate(self.pending_notifications):
                if notification.id == notification_id:
                    cancelled_notification = self.pending_notifications.pop(i)
                    cancelled_notification.status = "cancelled"
                    self.completed_notifications.append(cancelled_notification)
                    
                    self.logger.info("Notification cancelled",
                                   notification_id=notification_id)
                    return True
            
            self.logger.warning("Notification not found for cancellation",
                              notification_id=notification_id)
            return False
            
        except Exception as e:
            self.logger.error("Failed to cancel notification",
                            notification_id=notification_id,
                            error=str(e))
            return False

    async def add_notification_rule(self, rule: NotificationRule) -> bool:
        """Add an automated notification rule."""
        try:
            # Check if rule ID already exists
            existing_rule = next((r for r in self.notification_rules if r.id == rule.id), None)
            if existing_rule:
                self.logger.warning("Notification rule already exists",
                                  rule_id=rule.id)
                return False
            
            self.notification_rules.append(rule)
            
            self.logger.info("Notification rule added",
                           rule_id=rule.id,
                           trigger_event=rule.trigger_event,
                           template=rule.template.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to add notification rule",
                            rule_id=rule.id,
                            error=str(e))
            return False

    async def trigger_event(self, event_name: str, event_data: Dict[str, Any]) -> int:
        """Trigger automated notifications based on event."""
        try:
            triggered_count = 0
            
            # Find matching rules
            matching_rules = [
                rule for rule in self.notification_rules
                if rule.enabled and rule.trigger_event == event_name
            ]
            
            for rule in matching_rules:
                try:
                    # Check rule conditions
                    if await self._evaluate_rule_conditions(rule, event_data):
                        # Generate recipients based on target selector
                        recipients = await self._generate_rule_recipients(rule, event_data)
                        
                        if recipients:
                            # Calculate scheduled time
                            scheduled_time = datetime.utcnow() + timedelta(minutes=rule.delay_minutes)
                            
                            # Schedule notification
                            await self.schedule_notification(
                                template=rule.template,
                                recipients=recipients,
                                template_data=event_data,
                                scheduled_for=scheduled_time,
                                priority=rule.priority,
                                notification_type=rule.notification_type,
                                metadata={"rule_id": rule.id, "event": event_name}
                            )
                            
                            # Update rule statistics
                            rule.last_triggered = datetime.utcnow()
                            rule.trigger_count += 1
                            triggered_count += 1
                            
                            self.logger.info("Rule triggered notification",
                                           rule_id=rule.id,
                                           event=event_name,
                                           recipients=len(recipients))
                
                except Exception as e:
                    self.logger.error("Failed to process notification rule",
                                    rule_id=rule.id,
                                    event=event_name,
                                    error=str(e))
            
            if triggered_count > 0:
                self.logger.info("Event triggered notifications",
                               event=event_name,
                               triggered_count=triggered_count)
            
            return triggered_count
            
        except Exception as e:
            self.logger.error("Failed to trigger event notifications",
                            event=event_name,
                            error=str(e))
            return 0

    async def _scheduler_worker(self):
        """Main scheduler worker loop."""
        try:
            while self.status != SchedulerStatus.STOPPED:
                try:
                    if self.status == SchedulerStatus.ACTIVE:
                        await self._process_pending_notifications()
                        await self._retry_failed_notifications()
                        await self._cleanup_old_notifications()
                    
                    await asyncio.sleep(self.processing_interval)
                    
                except Exception as e:
                    self.logger.error("Error in scheduler worker loop", error=str(e))
                    await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            self.logger.info("Scheduler worker cancelled")
        except Exception as e:
            self.logger.error("Scheduler worker failed", error=str(e))

    async def _process_pending_notifications(self):
        """Process pending notifications that are due."""
        try:
            current_time = datetime.utcnow()
            due_notifications = []
            
            # Find due notifications
            for notification in self.pending_notifications[:]:
                if notification.scheduled_for <= current_time:
                    due_notifications.append(notification)
                    self.pending_notifications.remove(notification)
            
            # Process due notifications
            for notification in due_notifications:
                try:
                    success = await self._send_notification(notification)
                    
                    if success:
                        notification.status = "completed"
                        self.completed_notifications.append(notification)
                        
                        self.logger.info("Notification sent successfully",
                                       notification_id=notification.id,
                                       template=notification.template.value)
                    else:
                        await self._handle_notification_failure(notification)
                
                except Exception as e:
                    notification.error_message = str(e)
                    await self._handle_notification_failure(notification)
                    
                    self.logger.error("Failed to send notification",
                                    notification_id=notification.id,
                                    error=str(e))
            
        except Exception as e:
            self.logger.error("Error processing pending notifications", error=str(e))

    async def _send_notification(self, notification: ScheduledNotification) -> bool:
        """Send a notification via the appropriate channel."""
        try:
            notification.last_attempt = datetime.utcnow()
            
            if notification.notification_type == NotificationType.EMAIL:
                result = await self.email_service.send_bulk_notification(
                    template=notification.template,
                    recipients=notification.recipients,
                    template_data=notification.template_data,
                    priority=notification.priority
                )
                
                # Check if all emails were successful
                success_count = result.get("successful", 0)
                total_count = result.get("total_recipients", 0)
                
                return success_count == total_count
            
            elif notification.notification_type == NotificationType.SMS:
                # SMS implementation would go here
                self.logger.warning("SMS notifications not implemented yet")
                return False
            
            elif notification.notification_type == NotificationType.PUSH:
                # Push notification implementation would go here
                self.logger.warning("Push notifications not implemented yet")
                return False
            
            else:
                self.logger.error("Unsupported notification type",
                                notification_type=notification.notification_type.value)
                return False
            
        except Exception as e:
            self.logger.error("Failed to send notification",
                            notification_id=notification.id,
                            error=str(e))
            return False

    async def _handle_notification_failure(self, notification: ScheduledNotification):
        """Handle failed notification delivery."""
        try:
            notification.retry_count += 1
            
            if notification.retry_count < notification.max_retries:
                # Schedule retry
                retry_delay = notification.retry_delay * (2 ** (notification.retry_count - 1))
                notification.scheduled_for = datetime.utcnow() + timedelta(seconds=retry_delay)
                notification.status = "retrying"
                
                self.failed_notifications.append(notification)
                
                self.logger.warning("Notification scheduled for retry",
                                  notification_id=notification.id,
                                  retry_count=notification.retry_count,
                                  retry_in_seconds=retry_delay)
            else:
                # Max retries exceeded
                notification.status = "failed"
                self.completed_notifications.append(notification)
                
                self.logger.error("Notification failed permanently",
                                notification_id=notification.id,
                                retry_count=notification.retry_count)
            
        except Exception as e:
            self.logger.error("Failed to handle notification failure",
                            notification_id=notification.id,
                            error=str(e))

    async def _retry_failed_notifications(self):
        """Retry failed notifications that are due for retry."""
        try:
            current_time = datetime.utcnow()
            retry_notifications = []
            
            # Find notifications ready for retry
            for notification in self.failed_notifications[:]:
                if notification.scheduled_for <= current_time:
                    retry_notifications.append(notification)
                    self.failed_notifications.remove(notification)
            
            # Add back to pending queue
            self.pending_notifications.extend(retry_notifications)
            
            if retry_notifications:
                self.logger.info("Notifications moved to retry queue",
                               count=len(retry_notifications))
            
        except Exception as e:
            self.logger.error("Error processing retry notifications", error=str(e))

    async def _cleanup_old_notifications(self):
        """Clean up old completed and failed notifications."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Clean completed notifications
            initial_completed = len(self.completed_notifications)
            self.completed_notifications = [
                n for n in self.completed_notifications
                if n.created_at > cutoff_date
            ]
            
            cleaned_count = initial_completed - len(self.completed_notifications)
            
            if cleaned_count > 0:
                self.logger.info("Cleaned up old notifications",
                               cleaned_count=cleaned_count)
            
        except Exception as e:
            self.logger.error("Error cleaning up notifications", error=str(e))

    async def _evaluate_rule_conditions(self, rule: NotificationRule, event_data: Dict[str, Any]) -> bool:
        """Evaluate if rule conditions are met."""
        try:
            # Simple condition evaluation - can be extended for complex logic
            conditions = rule.conditions
            
            for key, expected_value in conditions.items():
                if key not in event_data:
                    return False
                
                actual_value = event_data[key]
                
                # Support different comparison types
                if isinstance(expected_value, dict):
                    operator = expected_value.get("operator", "eq")
                    value = expected_value.get("value")
                    
                    if operator == "eq" and actual_value != value:
                        return False
                    elif operator == "ne" and actual_value == value:
                        return False
                    elif operator == "gt" and actual_value <= value:
                        return False
                    elif operator == "lt" and actual_value >= value:
                        return False
                    elif operator == "gte" and actual_value < value:
                        return False
                    elif operator == "lte" and actual_value > value:
                        return False
                    elif operator == "in" and actual_value not in value:
                        return False
                    elif operator == "contains" and value not in str(actual_value):
                        return False
                else:
                    # Simple equality check
                    if actual_value != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to evaluate rule conditions",
                            rule_id=rule.id,
                            error=str(e))
            return False

    async def _generate_rule_recipients(self, rule: NotificationRule, 
                                      event_data: Dict[str, Any]) -> List[EmailRecipient]:
        """Generate recipients based on rule target selector."""
        try:
            recipients = []
            
            # Simple recipient generation - can be extended for complex selectors
            if "user_email" in event_data:
                recipients.append(EmailRecipient(
                    email=event_data["user_email"],
                    name=event_data.get("user_name"),
                    user_id=event_data.get("user_id"),
                    locale=event_data.get("locale", "en-US")
                ))
            
            # Support for admin notifications
            if rule.target_selector == "admin" or event_data.get("notify_admin"):
                admin_email = "admin@archbuilder.ai"  # From config
                recipients.append(EmailRecipient(
                    email=admin_email,
                    name="ArchBuilder Admin",
                    locale="en-US"
                ))
            
            return recipients
            
        except Exception as e:
            self.logger.error("Failed to generate rule recipients",
                            rule_id=rule.id,
                            error=str(e))
            return []

    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        try:
            stats = {
                "status": self.status.value,
                "pending_notifications": len(self.pending_notifications),
                "failed_notifications": len(self.failed_notifications),
                "completed_notifications": len(self.completed_notifications),
                "total_rules": len(self.notification_rules),
                "enabled_rules": len([r for r in self.notification_rules if r.enabled]),
                "processing_interval": self.processing_interval,
                "uptime": (datetime.utcnow() - datetime.utcnow()).total_seconds(),  # Will be corrected with actual start time
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Rule statistics
            rule_stats = {}
            for rule in self.notification_rules:
                rule_stats[rule.id] = {
                    "name": rule.name,
                    "trigger_event": rule.trigger_event,
                    "trigger_count": rule.trigger_count,
                    "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                    "enabled": rule.enabled
                }
            
            stats["rule_statistics"] = rule_stats
            
            return stats
            
        except Exception as e:
            self.logger.error("Failed to generate scheduler stats", error=str(e))
            return {"error": str(e)}

    async def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get notification delivery history."""
        try:
            # Combine all notifications and sort by creation time
            all_notifications = (
                self.pending_notifications + 
                self.failed_notifications + 
                self.completed_notifications
            )
            
            # Sort by creation time (newest first)
            all_notifications.sort(key=lambda x: x.created_at, reverse=True)
            
            # Convert to dict format and limit results
            history = []
            for notification in all_notifications[:limit]:
                history.append({
                    "id": notification.id,
                    "template": notification.template.value,
                    "notification_type": notification.notification_type.value,
                    "priority": notification.priority.value,
                    "recipients": len(notification.recipients),
                    "scheduled_for": notification.scheduled_for.isoformat(),
                    "created_at": notification.created_at.isoformat(),
                    "last_attempt": notification.last_attempt.isoformat() if notification.last_attempt else None,
                    "status": notification.status,
                    "retry_count": notification.retry_count,
                    "error_message": notification.error_message
                })
            
            return history
            
        except Exception as e:
            self.logger.error("Failed to get notification history", error=str(e))
            return []