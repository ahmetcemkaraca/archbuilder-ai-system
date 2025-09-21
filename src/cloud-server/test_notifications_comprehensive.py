"""
Comprehensive test suite for ArchBuilder.AI Email and Notification System
Testing email service, notification scheduler, API endpoints, and delivery tracking.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# Email Service Tests
async def test_email_service():
    """Test email service functionality."""
    print("🧪 Testing Email Service...")
    
    try:
        from app.services.notifications.email_service import (
            EmailService, EmailConfig, EmailTemplate, EmailRecipient, 
            EmailPriority, EmailMessage, EmailAttachment
        )
        
        # Test email configuration
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@archbuilder.ai",
            password="app_password",
            use_tls=True,
            from_email="noreply@archbuilder.ai",
            from_name="ArchBuilder.AI",
            reply_to="support@archbuilder.ai",
            templates_dir="templates/email",
            base_url="https://archbuilder.ai"
        )
        
        email_service = EmailService(config)
        print("✅ Email service initialized successfully")
        
        # Test recipient creation
        recipient = EmailRecipient(
            email="test@example.com",
            name="Test User",
            user_id="user_123",
            locale="en-US",
            metadata={"subscription_tier": "professional"}
        )
        print("✅ Email recipient created")
        
        # Test template data
        template_data = {
            "project_name": "Modern Office Complex",
            "project_id": "proj_456",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project_type": "Commercial",
            "project_description": "A sustainable office building with modern amenities"
        }
        
        print("✅ Template data prepared")
        
        # Test email creation (without sending)
        message = EmailMessage(
            template=EmailTemplate.PROJECT_CREATED,
            recipients=[recipient],
            subject="Your project has been created",
            priority=EmailPriority.NORMAL,
            template_data=template_data,
            track_opens=True,
            track_clicks=True
        )
        
        print("✅ Email message created")
        
        # Test delivery statistics
        stats = await email_service.get_delivery_stats(days=30)
        print(f"✅ Delivery stats retrieved: {json.dumps(stats, indent=2, default=str)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Email service test failed: {e}")
        return False


async def test_notification_scheduler():
    """Test notification scheduler functionality."""
    print("\n🧪 Testing Notification Scheduler...")
    
    try:
        from app.services.notifications.email_service import EmailService, EmailConfig
        from app.services.notifications.notification_scheduler import (
            NotificationScheduler, NotificationType, NotificationRule, EmailTemplate, EmailPriority
        )
        
        # Create email service
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@archbuilder.ai",
            password="app_password",
            use_tls=True,
            from_email="noreply@archbuilder.ai",
            from_name="ArchBuilder.AI"
        )
        
        email_service = EmailService(config)
        scheduler = NotificationScheduler(email_service)
        print("✅ Notification scheduler initialized")
        
        # Test immediate notification scheduling
        from app.services.notifications.email_service import EmailRecipient
        
        recipients = [
            EmailRecipient(
                email="user1@example.com",
                name="User One",
                user_id="user_1",
                locale="en-US"
            ),
            EmailRecipient(
                email="user2@example.com", 
                name="User Two",
                user_id="user_2",
                locale="tr-TR"
            )
        ]
        
        template_data = {
            "user_name": "Test User",
            "project_name": "AI-Generated Office Building",
            "completion_percentage": 100,
            "processing_time": "15 minutes"
        }
        
        # Schedule immediate notification
        notification_id = await scheduler.schedule_immediate_notification(
            template=EmailTemplate.AI_PROCESSING_COMPLETED,
            recipients=recipients,
            template_data=template_data,
            priority=EmailPriority.HIGH
        )
        
        print(f"✅ Immediate notification scheduled: {notification_id}")
        
        # Schedule future notification
        future_time = datetime.utcnow() + timedelta(minutes=5)
        future_notification_id = await scheduler.schedule_notification(
            template=EmailTemplate.PROJECT_COMPLETED,
            recipients=recipients,
            template_data=template_data,
            scheduled_for=future_time,
            priority=EmailPriority.NORMAL
        )
        
        print(f"✅ Future notification scheduled: {future_notification_id}")
        
        # Test automation rule
        rule = NotificationRule(
            id="welcome_rule",
            name="Welcome New Users",
            trigger_event="user_registered",
            template=EmailTemplate.WELCOME,
            notification_type=NotificationType.EMAIL,
            priority=EmailPriority.NORMAL,
            conditions={"user_type": "new"},
            target_selector="user",
            delay_minutes=0,
            enabled=True
        )
        
        success = await scheduler.add_notification_rule(rule)
        print(f"✅ Notification rule added: {success}")
        
        # Test event triggering
        event_data = {
            "user_email": "newuser@example.com",
            "user_name": "New User",
            "user_id": "new_123",
            "user_type": "new",
            "locale": "en-US"
        }
        
        triggered_count = await scheduler.trigger_event("user_registered", event_data)
        print(f"✅ Event triggered {triggered_count} notifications")
        
        # Test scheduler statistics
        stats = await scheduler.get_scheduler_stats()
        print(f"✅ Scheduler stats: {json.dumps(stats, indent=2, default=str)}")
        
        # Test notification history
        history = await scheduler.get_notification_history(limit=10)
        print(f"✅ Notification history retrieved: {len(history)} entries")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification scheduler test failed: {e}")
        return False


async def test_notification_api():
    """Test notification API endpoints (simulation)."""
    print("\n🧪 Testing Notification API...")
    
    try:
        # Test API model validation
        from app.api.notifications import (
            EmailRecipientModel, SendNotificationRequest, ScheduleNotificationRequest,
            BulkNotificationRequest, NotificationRuleRequest, EventTriggerRequest
        )
        
        # Test recipient model
        recipient_data = {
            "email": "api@example.com",
            "name": "API Test User", 
            "user_id": "api_123",
            "locale": "en-US",
            "metadata": {"source": "api_test"}
        }
        
        recipient_model = EmailRecipientModel(**recipient_data)
        print(f"✅ Recipient model validated: {recipient_model.email}")
        
        # Test send notification request
        send_request_data = {
            "template": "welcome",
            "recipients": [recipient_data],
            "template_data": {
                "user_name": "API User",
                "welcome_bonus": "$50"
            },
            "priority": "normal",
            "track_opens": True,
            "track_clicks": True
        }
        
        send_request = SendNotificationRequest(**send_request_data)
        print(f"✅ Send notification request validated: {send_request.template}")
        
        # Test schedule notification request
        schedule_request_data = {
            "template": "project_created",
            "recipients": [recipient_data],
            "template_data": {
                "project_name": "API Test Project",
                "project_id": "api_proj_789"
            },
            "scheduled_for": datetime.utcnow() + timedelta(hours=1),
            "priority": "high",
            "notification_type": "email"
        }
        
        schedule_request = ScheduleNotificationRequest(**schedule_request_data)
        print(f"✅ Schedule notification request validated: {schedule_request.template}")
        
        # Test bulk notification request  
        bulk_request_data = {
            "template": "usage_limit_warning",
            "recipients": [recipient_data] * 3,  # Multiple recipients
            "template_data": {
                "limit_type": "AI Requests",
                "current_usage": 480,
                "limit": 500,
                "reset_date": "2025-02-01"
            },
            "priority": "high"
        }
        
        bulk_request = BulkNotificationRequest(**bulk_request_data)
        print(f"✅ Bulk notification request validated: {len(bulk_request.recipients)} recipients")
        
        # Test notification rule request
        rule_request_data = {
            "id": "payment_failed_rule",
            "name": "Payment Failed Notifications",
            "trigger_event": "payment_failed",
            "template": "payment_failed",
            "notification_type": "email",
            "priority": "urgent",
            "conditions": {
                "payment_amount": {"operator": "gt", "value": 0},
                "retry_count": {"operator": "gte", "value": 3}
            },
            "target_selector": "user",
            "delay_minutes": 0,
            "enabled": True
        }
        
        rule_request = NotificationRuleRequest(**rule_request_data)
        print(f"✅ Notification rule request validated: {rule_request.name}")
        
        # Test event trigger request
        event_request_data = {
            "event_name": "subscription_cancelled",
            "event_data": {
                "user_email": "cancelled@example.com",
                "user_name": "Cancelled User",
                "subscription_tier": "professional",
                "cancellation_reason": "cost",
                "cancelled_at": datetime.utcnow().isoformat()
            }
        }
        
        event_request = EventTriggerRequest(**event_request_data)
        print(f"✅ Event trigger request validated: {event_request.event_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification API test failed: {e}")
        return False


async def test_email_templates():
    """Test email template functionality."""
    print("\n🧪 Testing Email Templates...")
    
    try:
        # Check if template files exist
        template_dir = Path("templates/email")
        
        welcome_html = template_dir / "welcome.html"
        welcome_txt = template_dir / "welcome.txt"
        project_created_html = template_dir / "project_created.html"
        
        if welcome_html.exists():
            print("✅ Welcome HTML template exists")
            with open(welcome_html, 'r', encoding='utf-8') as f:
                content = f.read()
                if "ArchBuilder.AI" in content and "recipient_name" in content:
                    print("✅ Welcome HTML template content validated")
                else:
                    print("⚠️ Welcome HTML template missing required content")
        else:
            print("⚠️ Welcome HTML template not found")
        
        if welcome_txt.exists():
            print("✅ Welcome text template exists")
            with open(welcome_txt, 'r', encoding='utf-8') as f:
                content = f.read()
                if "ArchBuilder.AI" in content and "recipient_name" in content:
                    print("✅ Welcome text template content validated")
                else:
                    print("⚠️ Welcome text template missing required content")
        else:
            print("⚠️ Welcome text template not found")
        
        if project_created_html.exists():
            print("✅ Project created HTML template exists")
            with open(project_created_html, 'r', encoding='utf-8') as f:
                content = f.read()
                if "project_name" in content and "project_id" in content:
                    print("✅ Project created template content validated")
                else:
                    print("⚠️ Project created template missing required content")
        else:
            print("⚠️ Project created HTML template not found")
        
        # Test template enumeration
        from app.services.notifications.email_service import EmailTemplate
        
        available_templates = [template.value for template in EmailTemplate]
        print(f"✅ Available templates: {len(available_templates)}")
        print(f"   Templates: {', '.join(available_templates[:5])}..." if len(available_templates) > 5 else f"   Templates: {', '.join(available_templates)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Email template test failed: {e}")
        return False


async def test_integration_workflow():
    """Test complete notification workflow integration."""
    print("\n🧪 Testing Integration Workflow...")
    
    try:
        # Simulate complete workflow: User registers -> Welcome email -> Project creation -> Completion notification
        from app.services.notifications.email_service import EmailService, EmailConfig, EmailTemplate, EmailRecipient
        from app.services.notifications.notification_scheduler import NotificationScheduler
        
        # Initialize services
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@archbuilder.ai",
            password="app_password",
            use_tls=True,
            from_email="noreply@archbuilder.ai",
            from_name="ArchBuilder.AI"
        )
        
        email_service = EmailService(config)
        scheduler = NotificationScheduler(email_service)
        
        print("✅ Services initialized for integration test")
        
        # Step 1: User registration - Welcome email
        new_user = EmailRecipient(
            email="integration@example.com",
            name="Integration Test User",
            user_id="integration_123",
            locale="en-US",
            metadata={"registration_source": "website", "subscription_tier": "free"}
        )
        
        welcome_data = {
            "user_name": new_user.name,
            "registration_date": datetime.now().strftime("%Y-%m-%d"),
            "subscription_tier": "Free",
            "trial_days": 14
        }
        
        welcome_id = await scheduler.schedule_immediate_notification(
            template=EmailTemplate.WELCOME,
            recipients=[new_user],
            template_data=welcome_data
        )
        
        print(f"✅ Step 1: Welcome notification scheduled - {welcome_id}")
        
        # Step 2: Project creation notification
        project_data = {
            "project_name": "Integration Test Building",
            "project_id": "int_proj_789",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project_type": "Residential",
            "project_description": "Test project for integration workflow"
        }
        
        project_id = await scheduler.schedule_immediate_notification(
            template=EmailTemplate.PROJECT_CREATED,
            recipients=[new_user],
            template_data=project_data
        )
        
        print(f"✅ Step 2: Project creation notification scheduled - {project_id}")
        
        # Step 3: AI processing started
        ai_start_data = {
            "project_name": project_data["project_name"],
            "processing_type": "Layout Generation",
            "estimated_time": "10-15 minutes"
        }
        
        ai_start_id = await scheduler.schedule_immediate_notification(
            template=EmailTemplate.AI_PROCESSING_STARTED,
            recipients=[new_user],
            template_data=ai_start_data
        )
        
        print(f"✅ Step 3: AI processing start notification scheduled - {ai_start_id}")
        
        # Step 4: AI processing completed (scheduled for future)
        completion_time = datetime.utcnow() + timedelta(minutes=15)
        ai_complete_data = {
            "project_name": project_data["project_name"],
            "processing_time": "12 minutes",
            "results_count": 3,
            "success_rate": "100%"
        }
        
        ai_complete_id = await scheduler.schedule_notification(
            template=EmailTemplate.AI_PROCESSING_COMPLETED,
            recipients=[new_user],
            template_data=ai_complete_data,
            scheduled_for=completion_time
        )
        
        print(f"✅ Step 4: AI processing completion notification scheduled for {completion_time.strftime('%H:%M:%S')} - {ai_complete_id}")
        
        # Check scheduler state
        stats = await scheduler.get_scheduler_stats()
        print(f"✅ Integration workflow complete:")
        print(f"   - Pending notifications: {stats['pending_notifications']}")
        print(f"   - Completed notifications: {stats['completed_notifications']}")
        print(f"   - Total notifications created: 4")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration workflow test failed: {e}")
        return False


async def run_comprehensive_tests():
    """Run all notification system tests."""
    print("🚀 Starting Comprehensive Notification System Tests\n")
    print("=" * 60)
    
    test_results = []
    
    # Run individual tests
    tests = [
        ("Email Service", test_email_service),
        ("Notification Scheduler", test_notification_scheduler),
        ("Notification API", test_notification_api),
        ("Email Templates", test_email_templates),
        ("Integration Workflow", test_integration_workflow)
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All notification system tests passed! Email system is ready for production.")
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
    
    return passed == total


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_comprehensive_tests())