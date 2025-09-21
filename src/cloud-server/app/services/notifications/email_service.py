"""
ArchBuilder.AI Email Service

Comprehensive email service for user notifications, project updates, system alerts,
and multi-channel communication with template support and delivery tracking.
"""

import asyncio
import smtplib
import base64
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog

try:
    import aiosmtplib
    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    AIOSMTPLIB_AVAILABLE = False

try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    import premailer
    PREMAILER_AVAILABLE = True
except ImportError:
    PREMAILER_AVAILABLE = False

logger = structlog.get_logger(__name__)


class EmailPriority(str, Enum):
    """Email priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailTemplate(str, Enum):
    """Email template types."""
    WELCOME = "welcome"
    PROJECT_CREATED = "project_created"
    PROJECT_COMPLETED = "project_completed"
    AI_PROCESSING_STARTED = "ai_processing_started"
    AI_PROCESSING_COMPLETED = "ai_processing_completed"
    AI_PROCESSING_FAILED = "ai_processing_failed"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    USAGE_LIMIT_WARNING = "usage_limit_warning"
    USAGE_LIMIT_EXCEEDED = "usage_limit_exceeded"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SECURITY_ALERT = "security_alert"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    TEAM_INVITATION = "team_invitation"
    REVIT_SYNC_SUCCESS = "revit_sync_success"
    REVIT_SYNC_FAILED = "revit_sync_failed"


@dataclass
class EmailRecipient:
    """Email recipient information."""
    email: str
    name: Optional[str] = None
    user_id: Optional[str] = None
    locale: str = "en-US"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailAttachment:
    """Email attachment information."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    inline: bool = False
    content_id: Optional[str] = None


@dataclass
class EmailMessage:
    """Email message structure."""
    template: EmailTemplate
    recipients: List[EmailRecipient]
    subject: str
    priority: EmailPriority = EmailPriority.NORMAL
    template_data: Dict[str, Any] = field(default_factory=dict)
    attachments: List[EmailAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    track_opens: bool = True
    track_clicks: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailConfig:
    """Email service configuration."""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_email: str = ""
    from_name: str = "ArchBuilder.AI"
    reply_to: str = ""
    templates_dir: str = "templates/email"
    base_url: str = "https://archbuilder.ai"


class EmailService:
    """Comprehensive email service with template support and delivery tracking."""
    
    def __init__(self, config: EmailConfig):
        """Initialize email service."""
        self.config = config
        self.logger = logger.bind(service="email")
        
        # Initialize Jinja2 environment for templates
        if JINJA2_AVAILABLE:
            self.template_env = Environment(
                loader=FileSystemLoader(config.templates_dir),
                autoescape=True
            )
        else:
            self.template_env = None
            self.logger.warning("Jinja2 not available, using fallback templates")
        
        # Email delivery tracking
        self.delivery_log: List[Dict[str, Any]] = []
        
        self.logger.info("Email service initialized", 
                        smtp_server=config.smtp_server,
                        smtp_port=config.smtp_port,
                        from_email=config.from_email)

    async def send_email(self, message: EmailMessage) -> Dict[str, Any]:
        """Send an email message."""
        try:
            # Generate email content from template
            html_content, text_content = await self._render_template(message)
            
            # Create email message
            email_msg = await self._create_email_message(
                message, html_content, text_content
            )
            
            # Send email for each recipient
            results = []
            for recipient in message.recipients:
                try:
                    # Personalize content for recipient
                    personalized_html = await self._personalize_content(
                        html_content, recipient, message.template_data
                    )
                    personalized_text = await self._personalize_content(
                        text_content, recipient, message.template_data, is_html=False
                    )
                    
                    # Create recipient-specific message
                    recipient_msg = await self._create_recipient_message(
                        message, recipient, personalized_html, personalized_text
                    )
                    
                    # Send email
                    if message.scheduled_for and message.scheduled_for > datetime.utcnow():
                        # Schedule for later
                        result = await self._schedule_email(recipient_msg, message.scheduled_for)
                    else:
                        # Send immediately
                        result = await self._send_smtp_email(recipient_msg, recipient)
                    
                    results.append({
                        "recipient": recipient.email,
                        "status": "success" if result else "failed",
                        "message_id": result.get("message_id") if result else None,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    self.logger.error("Failed to send email to recipient",
                                    recipient=recipient.email,
                                    template=message.template.value,
                                    error=str(e))
                    results.append({
                        "recipient": recipient.email,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Log delivery results
            delivery_summary = {
                "template": message.template.value,
                "total_recipients": len(message.recipients),
                "successful": sum(1 for r in results if r["status"] == "success"),
                "failed": sum(1 for r in results if r["status"] == "failed"),
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.delivery_log.append(delivery_summary)
            
            self.logger.info("Email batch sent",
                           template=message.template.value,
                           recipients=len(message.recipients),
                           successful=delivery_summary["successful"],
                           failed=delivery_summary["failed"])
            
            return delivery_summary
            
        except Exception as e:
            self.logger.error("Failed to send email batch",
                            template=message.template.value,
                            recipients=len(message.recipients),
                            error=str(e))
            raise Exception(f"Email sending failed: {str(e)}")

    async def send_notification(self, template: EmailTemplate, recipient: EmailRecipient,
                               template_data: Dict[str, Any], priority: EmailPriority = EmailPriority.NORMAL,
                               attachments: Optional[List[EmailAttachment]] = None) -> Dict[str, Any]:
        """Send a single notification email."""
        try:
            # Get template configuration
            template_config = await self._get_template_config(template, recipient.locale)
            
            message = EmailMessage(
                template=template,
                recipients=[recipient],
                subject=template_config["subject"],
                priority=priority,
                template_data=template_data,
                attachments=attachments or [],
                track_opens=True,
                track_clicks=True
            )
            
            result = await self.send_email(message)
            
            self.logger.info("Notification sent",
                           template=template.value,
                           recipient=recipient.email,
                           priority=priority.value)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to send notification",
                            template=template.value,
                            recipient=recipient.email,
                            error=str(e))
            raise Exception(f"Notification sending failed: {str(e)}")

    async def send_bulk_notification(self, template: EmailTemplate, recipients: List[EmailRecipient],
                                   template_data: Dict[str, Any], priority: EmailPriority = EmailPriority.NORMAL) -> Dict[str, Any]:
        """Send bulk notification to multiple recipients."""
        try:
            # Group recipients by locale for template optimization
            recipients_by_locale = {}
            for recipient in recipients:
                locale = recipient.locale
                if locale not in recipients_by_locale:
                    recipients_by_locale[locale] = []
                recipients_by_locale[locale].append(recipient)
            
            all_results = []
            
            # Send to each locale group
            for locale, locale_recipients in recipients_by_locale.items():
                template_config = await self._get_template_config(template, locale)
                
                message = EmailMessage(
                    template=template,
                    recipients=locale_recipients,
                    subject=template_config["subject"],
                    priority=priority,
                    template_data=template_data,
                    track_opens=True,
                    track_clicks=True
                )
                
                result = await self.send_email(message)
                all_results.extend(result["results"])
            
            # Combine results
            bulk_summary = {
                "template": template.value,
                "total_recipients": len(recipients),
                "successful": sum(1 for r in all_results if r["status"] == "success"),
                "failed": sum(1 for r in all_results if r["status"] == "failed"),
                "results": all_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info("Bulk notification sent",
                           template=template.value,
                           total_recipients=len(recipients),
                           successful=bulk_summary["successful"],
                           failed=bulk_summary["failed"])
            
            return bulk_summary
            
        except Exception as e:
            self.logger.error("Failed to send bulk notification",
                            template=template.value,
                            recipients=len(recipients),
                            error=str(e))
            raise Exception(f"Bulk notification failed: {str(e)}")

    async def _render_template(self, message: EmailMessage) -> tuple[str, str]:
        """Render email template to HTML and text."""
        try:
            # Get template files
            template_name = message.template.value
            html_template_path = f"{template_name}.html"
            text_template_path = f"{template_name}.txt"
            
            # Render HTML template
            try:
                html_template = self.template_env.get_template(html_template_path)
                html_content = html_template.render(**message.template_data)
                
                # Inline CSS for better email client compatibility
                html_content = premailer.transform(html_content)
                
            except Exception as e:
                self.logger.warning("HTML template not found, using fallback",
                                  template=template_name,
                                  error=str(e))
                html_content = await self._create_fallback_html(message)
            
            # Render text template
            try:
                text_template = self.template_env.get_template(text_template_path)
                text_content = text_template.render(**message.template_data)
            except Exception as e:
                self.logger.warning("Text template not found, using fallback",
                                  template=template_name,
                                  error=str(e))
                text_content = await self._create_fallback_text(message)
            
            return html_content, text_content
            
        except Exception as e:
            self.logger.error("Failed to render template",
                            template=message.template.value,
                            error=str(e))
            raise Exception(f"Template rendering failed: {str(e)}")

    async def _create_email_message(self, message: EmailMessage, html_content: str, 
                                  text_content: str) -> MIMEMultipart:
        """Create email message object."""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['Reply-To'] = message.reply_to or self.config.reply_to
            msg['Subject'] = message.subject
            
            # Set priority headers
            if message.priority == EmailPriority.HIGH:
                msg['X-Priority'] = '2'
                msg['Importance'] = 'high'
            elif message.priority == EmailPriority.URGENT:
                msg['X-Priority'] = '1'
                msg['Importance'] = 'high'
            elif message.priority == EmailPriority.LOW:
                msg['X-Priority'] = '4'
                msg['Importance'] = 'low'
            
            # Attach text and HTML parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments
            for attachment in message.attachments:
                if attachment.inline:
                    # Inline attachment (for images in HTML)
                    att_part = MIMEImage(attachment.content)
                    att_part.add_header('Content-ID', f'<{attachment.content_id}>')
                else:
                    # Regular attachment
                    att_part = MIMEText(attachment.content, 'base64', 'utf-8')
                    att_part.add_header('Content-Disposition', 
                                      f'attachment; filename="{attachment.filename}"')
                    att_part.add_header('Content-Type', attachment.content_type)
                
                msg.attach(att_part)
            
            return msg
            
        except Exception as e:
            self.logger.error("Failed to create email message",
                            template=message.template.value,
                            error=str(e))
            raise Exception(f"Email message creation failed: {str(e)}")

    async def _send_smtp_email(self, message: MIMEMultipart, recipient: EmailRecipient) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            # Create SMTP connection
            if self.config.use_ssl:
                smtp = aiosmtplib.SMTP(hostname=self.config.smtp_server, 
                                     port=self.config.smtp_port, 
                                     use_tls=False, use_ssl=True)
            else:
                smtp = aiosmtplib.SMTP(hostname=self.config.smtp_server, 
                                     port=self.config.smtp_port,
                                     use_tls=self.config.use_tls)
            
            await smtp.connect()
            
            if self.config.username and self.config.password:
                await smtp.login(self.config.username, self.config.password)
            
            # Set recipient
            message['To'] = f"{recipient.name} <{recipient.email}>" if recipient.name else recipient.email
            
            # Send email
            result = await smtp.send_message(message)
            await smtp.quit()
            
            message_id = message.get('Message-ID', f"archbuilder-{datetime.utcnow().timestamp()}")
            
            self.logger.info("Email sent successfully",
                           recipient=recipient.email,
                           message_id=message_id)
            
            return {
                "success": True,
                "message_id": message_id,
                "smtp_response": str(result)
            }
            
        except Exception as e:
            self.logger.error("SMTP sending failed",
                            recipient=recipient.email,
                            error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def _personalize_content(self, content: str, recipient: EmailRecipient, 
                                 template_data: Dict[str, Any], is_html: bool = True) -> str:
        """Personalize content for specific recipient."""
        try:
            # Add recipient-specific data
            personalization_data = {
                **template_data,
                "recipient_name": recipient.name or "Valued User",
                "recipient_email": recipient.email,
                "user_id": recipient.user_id,
                "locale": recipient.locale,
                "base_url": self.config.base_url,
                **recipient.metadata
            }
            
            # Use Jinja2 for personalization
            template = Template(content)
            personalized_content = template.render(**personalization_data)
            
            # Add tracking pixels for HTML emails
            if is_html and recipient.user_id:
                tracking_pixel = f'<img src="{self.config.base_url}/email/track/open/{recipient.user_id}" width="1" height="1" style="display:none;">'
                personalized_content = personalized_content.replace('</body>', f'{tracking_pixel}</body>')
            
            return personalized_content
            
        except Exception as e:
            self.logger.error("Content personalization failed",
                            recipient=recipient.email,
                            error=str(e))
            return content

    async def _create_recipient_message(self, message: EmailMessage, recipient: EmailRecipient,
                                      html_content: str, text_content: str) -> MIMEMultipart:
        """Create personalized message for recipient."""
        return await self._create_email_message(message, html_content, text_content)

    async def _schedule_email(self, message: MIMEMultipart, scheduled_time: datetime) -> Dict[str, Any]:
        """Schedule email for future delivery."""
        try:
            # In production, this would integrate with a job queue like Celery
            # For now, we'll just log the scheduling
            
            self.logger.info("Email scheduled",
                           scheduled_time=scheduled_time.isoformat(),
                           subject=message['Subject'])
            
            return {
                "success": True,
                "scheduled": True,
                "scheduled_time": scheduled_time.isoformat(),
                "message_id": f"scheduled-{datetime.utcnow().timestamp()}"
            }
            
        except Exception as e:
            self.logger.error("Email scheduling failed",
                            scheduled_time=scheduled_time.isoformat(),
                            error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_template_config(self, template: EmailTemplate, locale: str = "en-US") -> Dict[str, Any]:
        """Get template configuration including subject lines."""
        # Template configurations with localized subjects
        template_configs = {
            EmailTemplate.WELCOME: {
                "en-US": {"subject": "Welcome to ArchBuilder.AI! 🏗️"},
                "tr-TR": {"subject": "ArchBuilder.AI'ye Hoş Geldiniz! 🏗️"}
            },
            EmailTemplate.PROJECT_CREATED: {
                "en-US": {"subject": "Your project '{{project_name}}' has been created"},
                "tr-TR": {"subject": "'{{project_name}}' projeniz oluşturuldu"}
            },
            EmailTemplate.PROJECT_COMPLETED: {
                "en-US": {"subject": "Project '{{project_name}}' completed successfully! 🎉"},
                "tr-TR": {"subject": "'{{project_name}}' projesi başarıyla tamamlandı! 🎉"}
            },
            EmailTemplate.AI_PROCESSING_STARTED: {
                "en-US": {"subject": "AI processing started for '{{project_name}}'"},
                "tr-TR": {"subject": "'{{project_name}}' için AI işleme başladı"}
            },
            EmailTemplate.AI_PROCESSING_COMPLETED: {
                "en-US": {"subject": "AI processing completed for '{{project_name}}'"},
                "tr-TR": {"subject": "'{{project_name}}' için AI işleme tamamlandı"}
            },
            EmailTemplate.USAGE_LIMIT_WARNING: {
                "en-US": {"subject": "Usage limit warning - {{limit_type}}"},
                "tr-TR": {"subject": "Kullanım limiti uyarısı - {{limit_type}}"}
            }
        }
        
        config = template_configs.get(template, {})
        locale_config = config.get(locale, config.get("en-US", {"subject": "ArchBuilder.AI Notification"}))
        
        return locale_config

    async def _create_fallback_html(self, message: EmailMessage) -> str:
        """Create fallback HTML content when template is not found."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>ArchBuilder.AI</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">ArchBuilder.AI</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Notification: {message.template.value.replace('_', ' ').title()}</h2>
                <p>This is an automated notification from ArchBuilder.AI.</p>
                <p>Template data: {str(message.template_data)}</p>
            </div>
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p>© 2025 ArchBuilder.AI. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

    async def _create_fallback_text(self, message: EmailMessage) -> str:
        """Create fallback text content when template is not found."""
        return f"""
        ArchBuilder.AI Notification
        
        Notification Type: {message.template.value.replace('_', ' ').title()}
        
        This is an automated notification from ArchBuilder.AI.
        
        Template data: {str(message.template_data)}
        
        --
        © 2025 ArchBuilder.AI. All rights reserved.
        """

    async def get_delivery_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get email delivery statistics."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Filter recent deliveries
            recent_deliveries = [
                log for log in self.delivery_log 
                if datetime.fromisoformat(log["timestamp"]) > cutoff_date
            ]
            
            # Calculate statistics
            total_sent = sum(log["total_recipients"] for log in recent_deliveries)
            total_successful = sum(log["successful"] for log in recent_deliveries)
            total_failed = sum(log["failed"] for log in recent_deliveries)
            
            # Template breakdown
            template_stats = {}
            for log in recent_deliveries:
                template = log["template"]
                if template not in template_stats:
                    template_stats[template] = {"sent": 0, "successful": 0, "failed": 0}
                
                template_stats[template]["sent"] += log["total_recipients"]
                template_stats[template]["successful"] += log["successful"]
                template_stats[template]["failed"] += log["failed"]
            
            stats = {
                "period_days": days,
                "total_sent": total_sent,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "success_rate": (total_successful / total_sent * 100) if total_sent > 0 else 0,
                "template_breakdown": template_stats,
                "total_batches": len(recent_deliveries),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            self.logger.info("Email delivery stats generated",
                           period_days=days,
                           total_sent=total_sent,
                           success_rate=stats["success_rate"])
            
            return stats
            
        except Exception as e:
            self.logger.error("Failed to generate delivery stats",
                            days=days,
                            error=str(e))
            return {}

    async def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection."""
        try:
            if self.config.use_ssl:
                smtp = aiosmtplib.SMTP(hostname=self.config.smtp_server, 
                                     port=self.config.smtp_port, 
                                     use_tls=False, use_ssl=True)
            else:
                smtp = aiosmtplib.SMTP(hostname=self.config.smtp_server, 
                                     port=self.config.smtp_port,
                                     use_tls=self.config.use_tls)
            
            await smtp.connect()
            
            if self.config.username and self.config.password:
                await smtp.login(self.config.username, self.config.password)
            
            await smtp.quit()
            
            self.logger.info("SMTP connection test successful")
            
            return {
                "success": True,
                "message": "SMTP connection successful",
                "server": self.config.smtp_server,
                "port": self.config.smtp_port
            }
            
        except Exception as e:
            self.logger.error("SMTP connection test failed",
                            error=str(e))
            return {
                "success": False,
                "error": str(e),
                "server": self.config.smtp_server,
                "port": self.config.smtp_port
            }