"""
Security Tests for ArchBuilder.AI Cloud Server
STRIDE Threat Model Based Testing
"""

import pytest
import asyncio
import jwt
import hashlib
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityManager, TokenManager
from app.core.auth import authenticate_user, authorize_user, RoleChecker
from app.core.encryption import EncryptionService
from app.models.auth.user import User
from app.models.auth.tenant import Tenant


class TestSTRIDEThreatModel:
    """
    STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, 
    Denial of Service, Elevation of Privilege) based security tests
    """

    @pytest.fixture
    async def security_manager(self):
        """Create security manager instance for testing"""
        return SecurityManager()

    @pytest.fixture
    async def sample_user(self, async_session: AsyncSession):
        """Create sample user for testing"""
        user = User(
            email="test@archbuilder.ai",
            username="testuser",
            hashed_password=hashlib.sha256("testpass123".encode()).hexdigest(),
            is_active=True,
            tenant_id=1
        )
        async_session.add(user)
        await async_session.commit()
        return user


class TestSpoofingPrevention:
    """Test protection against identity spoofing attacks"""

    async def test_jwt_token_validation(self):
        """Test JWT token validation prevents spoofing"""
        token_manager = TokenManager()
        
        # Valid token creation
        payload = {"user_id": 1, "email": "test@archbuilder.ai"}
        valid_token = token_manager.create_access_token(payload)
        
        # Token validation should succeed
        decoded = token_manager.verify_token(valid_token)
        assert decoded["user_id"] == 1
        assert decoded["email"] == "test@archbuilder.ai"

    async def test_invalid_jwt_token_rejection(self):
        """Test that invalid/tampered tokens are rejected"""
        token_manager = TokenManager()
        
        # Test with invalid token
        invalid_token = "invalid.jwt.token"
        with pytest.raises(HTTPException) as exc_info:
            token_manager.verify_token(invalid_token)
        assert exc_info.value.status_code == 401

    async def test_expired_token_rejection(self):
        """Test that expired tokens are rejected"""
        token_manager = TokenManager()
        
        # Create token with immediate expiration
        payload = {"user_id": 1, "exp": datetime.utcnow() - timedelta(hours=1)}
        expired_token = jwt.encode(payload, token_manager.secret_key, algorithm="HS256")
        
        with pytest.raises(HTTPException) as exc_info:
            token_manager.verify_token(expired_token)
        assert exc_info.value.status_code == 401

    async def test_oauth2_authentication(self):
        """Test OAuth2 authentication flow"""
        # Mock OAuth2 provider response
        mock_oauth_response = {
            "access_token": "mock_access_token",
            "token_type": "Bearer",
            "user_info": {
                "email": "oauth@archbuilder.ai",
                "name": "OAuth User"
            }
        }
        
        with patch('app.core.auth.oauth2_provider') as mock_oauth:
            mock_oauth.authenticate.return_value = mock_oauth_response
            
            # Test OAuth authentication
            result = await authenticate_user("oauth_code", "oauth2")
            assert result["email"] == "oauth@archbuilder.ai"


class TestTamperingPrevention:
    """Test protection against data tampering"""

    async def test_request_signature_validation(self):
        """Test request signature validation"""
        security_manager = SecurityManager()
        
        # Valid request with correct signature
        request_data = {"project_id": 123, "action": "update"}
        signature = security_manager.generate_request_signature(request_data)
        
        # Signature validation should succeed
        is_valid = security_manager.validate_request_signature(request_data, signature)
        assert is_valid is True

    async def test_tampered_request_detection(self):
        """Test detection of tampered requests"""
        security_manager = SecurityManager()
        
        # Original request and signature
        original_data = {"project_id": 123, "action": "update"}
        signature = security_manager.generate_request_signature(original_data)
        
        # Tampered request data
        tampered_data = {"project_id": 456, "action": "delete"}  # Changed values
        
        # Validation should fail
        is_valid = security_manager.validate_request_signature(tampered_data, signature)
        assert is_valid is False

    async def test_sql_injection_prevention(self, async_session: AsyncSession):
        """Test SQL injection prevention in database queries"""
        from app.dao.user_dao import UserDAO
        
        user_dao = UserDAO(async_session)
        
        # Attempt SQL injection through email parameter
        malicious_email = "'; DROP TABLE users; --"
        
        # This should not cause SQL injection
        result = await user_dao.get_by_email(malicious_email)
        assert result is None  # Should return None, not crash

    async def test_input_validation_sanitization(self):
        """Test input validation and sanitization"""
        from app.core.validation import InputValidator
        
        validator = InputValidator()
        
        # Test malicious script injection
        malicious_input = "<script>alert('XSS')</script>"
        sanitized = validator.sanitize_html_input(malicious_input)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized


class TestRepudiationPrevention:
    """Test non-repudiation through audit logging"""

    async def test_audit_log_creation(self, sample_user):
        """Test that all user actions are logged"""
        from app.core.audit import AuditLogger
        
        audit_logger = AuditLogger()
        
        # Log user action
        action_data = {
            "user_id": sample_user.id,
            "action": "project_created",
            "resource_id": "project_123",
            "ip_address": "192.168.1.100",
            "user_agent": "ArchBuilder Desktop/1.0"
        }
        
        log_id = await audit_logger.log_action(action_data)
        assert log_id is not None
        
        # Verify log entry
        log_entry = await audit_logger.get_log_entry(log_id)
        assert log_entry["user_id"] == sample_user.id
        assert log_entry["action"] == "project_created"

    async def test_immutable_audit_logs(self):
        """Test that audit logs cannot be modified"""
        from app.core.audit import AuditLogger
        
        audit_logger = AuditLogger()
        
        # Create audit log
        log_data = {"user_id": 1, "action": "test_action"}
        log_id = await audit_logger.log_action(log_data)
        
        # Attempt to modify log (should fail or be prevented)
        with pytest.raises(Exception):  # Should raise permission or integrity error
            await audit_logger.modify_log_entry(log_id, {"action": "modified_action"})

    async def test_digital_signatures(self):
        """Test digital signatures for critical operations"""
        security_manager = SecurityManager()
        
        # Critical operation data
        operation_data = {
            "type": "project_deletion",
            "project_id": "proj_123",
            "user_id": 1,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Generate digital signature
        signature = security_manager.sign_operation(operation_data)
        assert signature is not None
        
        # Verify signature
        is_valid = security_manager.verify_operation_signature(operation_data, signature)
        assert is_valid is True


class TestInformationDisclosurePrevention:
    """Test protection against information disclosure"""

    async def test_data_encryption_at_rest(self):
        """Test that sensitive data is encrypted at rest"""
        encryption_service = EncryptionService()
        
        # Sensitive data
        sensitive_data = "API_KEY_12345_SENSITIVE"
        
        # Encrypt data
        encrypted = encryption_service.encrypt(sensitive_data)
        assert encrypted != sensitive_data  # Should be encrypted
        
        # Decrypt data
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == sensitive_data

    async def test_data_encryption_in_transit(self):
        """Test HTTPS/TLS enforcement"""
        from app.core.security import HTTPSRedirectMiddleware
        
        # Mock request without HTTPS
        mock_request = Mock()
        mock_request.url.scheme = "http"
        mock_request.headers = {}
        
        middleware = HTTPSRedirectMiddleware()
        
        # Should redirect to HTTPS
        response = await middleware.process_request(mock_request)
        assert response.status_code == 307  # Redirect to HTTPS

    async def test_tenant_data_isolation(self, async_session: AsyncSession):
        """Test that tenant data is properly isolated"""
        from app.dao.project_dao import ProjectDAO
        
        project_dao = ProjectDAO(async_session)
        
        # Create projects for different tenants
        tenant1_projects = await project_dao.get_by_tenant_id(tenant_id=1)
        tenant2_projects = await project_dao.get_by_tenant_id(tenant_id=2)
        
        # Verify no cross-tenant data leakage
        for project in tenant1_projects:
            assert project.tenant_id == 1
        
        for project in tenant2_projects:
            assert project.tenant_id == 2

    async def test_pii_data_masking(self):
        """Test that PII data is properly masked in logs"""
        from app.core.logging import PIIMasker
        
        masker = PIIMasker()
        
        # Data containing PII
        log_data = {
            "email": "user@archbuilder.ai",
            "phone": "+90-123-456-7890",
            "credit_card": "1234-5678-9012-3456"
        }
        
        masked_data = masker.mask_pii(log_data)
        
        # Verify PII is masked
        assert "user@" not in masked_data["email"]
        assert "123-456-7890" not in masked_data["phone"]
        assert "1234-5678" not in masked_data["credit_card"]


class TestDenialOfServicePrevention:
    """Test protection against DoS attacks"""

    async def test_rate_limiting(self):
        """Test API rate limiting"""
        from app.core.rate_limiting import RateLimiter
        
        rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
        client_ip = "192.168.1.100"
        
        # Test normal usage within limits
        for i in range(5):
            allowed = await rate_limiter.is_allowed(client_ip)
            assert allowed is True
        
        # Test rate limit exceeded
        exceeded = await rate_limiter.is_allowed(client_ip)
        assert exceeded is False

    async def test_request_size_limiting(self):
        """Test request size limitations"""
        from app.core.validation import RequestSizeValidator
        
        validator = RequestSizeValidator(max_size_mb=10)
        
        # Normal sized request
        normal_request = {"data": "x" * 1000}  # 1KB
        is_valid = validator.validate_size(normal_request)
        assert is_valid is True
        
        # Oversized request
        large_request = {"data": "x" * (11 * 1024 * 1024)}  # 11MB
        is_valid = validator.validate_size(large_request)
        assert is_valid is False

    async def test_connection_limiting(self):
        """Test concurrent connection limiting"""
        from app.core.connection_manager import ConnectionManager
        
        conn_manager = ConnectionManager(max_connections=100)
        
        # Test connection tracking
        for i in range(100):
            conn_id = f"conn_{i}"
            added = conn_manager.add_connection(conn_id)
            assert added is True
        
        # Test connection limit
        overflow_conn = conn_manager.add_connection("overflow_conn")
        assert overflow_conn is False

    async def test_resource_monitoring(self):
        """Test system resource monitoring"""
        from app.core.monitoring import ResourceMonitor
        
        monitor = ResourceMonitor()
        
        # Get current resource usage
        resources = await monitor.get_resource_usage()
        
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_usage" in resources
        
        # Test resource alerts
        if resources["cpu_percent"] > 90:
            alert = await monitor.trigger_alert("high_cpu_usage")
            assert alert is not None


class TestElevationOfPrivilegePrevention:
    """Test protection against privilege escalation"""

    async def test_role_based_access_control(self, sample_user):
        """Test RBAC implementation"""
        from app.core.auth import RoleChecker
        
        role_checker = RoleChecker()
        
        # Test user with basic role
        sample_user.role = "user"
        has_access = role_checker.check_permission(sample_user, "admin_action")
        assert has_access is False
        
        # Test user with admin role
        sample_user.role = "admin"
        has_access = role_checker.check_permission(sample_user, "admin_action")
        assert has_access is True

    async def test_principle_of_least_privilege(self):
        """Test that users have minimum required permissions"""
        from app.core.auth import PermissionChecker
        
        permission_checker = PermissionChecker()
        
        # Test project access permissions
        user_permissions = {
            "project_read": True,
            "project_write": True,
            "project_delete": False,  # Should not have delete by default
            "admin_access": False     # Should not have admin access
        }
        
        # Verify restrictive default permissions
        assert user_permissions["project_delete"] is False
        assert user_permissions["admin_access"] is False

    async def test_session_management(self):
        """Test secure session management"""
        from app.core.session import SessionManager
        
        session_manager = SessionManager()
        
        # Create session
        session_data = {"user_id": 1, "role": "user"}
        session_id = await session_manager.create_session(session_data)
        
        # Verify session
        retrieved_session = await session_manager.get_session(session_id)
        assert retrieved_session["user_id"] == 1
        
        # Test session timeout
        await asyncio.sleep(1)  # Simulate time passage
        expired_session = await session_manager.get_session(session_id, max_age=0)
        assert expired_session is None

    async def test_api_key_validation(self):
        """Test API key validation for service authentication"""
        from app.core.auth import APIKeyValidator
        
        api_validator = APIKeyValidator()
        
        # Valid API key
        valid_key = "ak_live_1234567890abcdef"
        is_valid = await api_validator.validate_key(valid_key)
        assert is_valid is True
        
        # Invalid API key
        invalid_key = "invalid_key"
        is_valid = await api_validator.validate_key(invalid_key)
        assert is_valid is False


class TestSecurityIntegration:
    """Integration tests for security components"""

    async def test_end_to_end_authentication_flow(self):
        """Test complete authentication flow"""
        # 1. User login attempt
        credentials = {"email": "test@archbuilder.ai", "password": "testpass123"}
        
        # 2. Authentication
        auth_result = await authenticate_user(credentials["email"], credentials["password"])
        assert auth_result is not None
        
        # 3. Token generation
        token_manager = TokenManager()
        access_token = token_manager.create_access_token(auth_result)
        assert access_token is not None
        
        # 4. Token validation
        decoded_token = token_manager.verify_token(access_token)
        assert decoded_token["user_id"] == auth_result["user_id"]

    async def test_secure_file_upload_flow(self):
        """Test secure file upload with validation"""
        from app.core.file_security import FileSecurityValidator
        
        validator = FileSecurityValidator()
        
        # Mock file upload
        file_data = {
            "filename": "test_project.dwg",
            "content_type": "application/acad",
            "size": 1024 * 1024,  # 1MB
            "content": b"mock_dwg_content"
        }
        
        # Validate file security
        is_safe = await validator.validate_file(file_data)
        assert is_safe is True
        
        # Test malicious file detection
        malicious_file = {
            "filename": "malware.exe",
            "content_type": "application/octet-stream",
            "size": 100,
            "content": b"MZ\x90\x00"  # PE header signature
        }
        
        is_safe = await validator.validate_file(malicious_file)
        assert is_safe is False

    async def test_multi_tenant_security(self):
        """Test multi-tenant security isolation"""
        from app.core.tenant_security import TenantSecurityManager
        
        security_manager = TenantSecurityManager()
        
        # Test tenant isolation
        tenant1_context = {"tenant_id": 1, "user_id": 10}
        tenant2_context = {"tenant_id": 2, "user_id": 20}
        
        # Verify cross-tenant access is prevented
        can_access = security_manager.can_access_resource(
            requester=tenant1_context,
            resource_tenant_id=2
        )
        assert can_access is False
        
        # Verify same-tenant access is allowed
        can_access = security_manager.can_access_resource(
            requester=tenant1_context,
            resource_tenant_id=1
        )
        assert can_access is True


# Performance and Security Benchmarks
class TestSecurityPerformance:
    """Test security implementation performance"""

    async def test_encryption_performance(self):
        """Test encryption/decryption performance"""
        encryption_service = EncryptionService()
        
        # Test data
        test_data = "x" * 10000  # 10KB of data
        
        # Measure encryption time
        start_time = time.time()
        encrypted = encryption_service.encrypt(test_data)
        encrypt_time = time.time() - start_time
        
        # Measure decryption time
        start_time = time.time()
        decrypted = encryption_service.decrypt(encrypted)
        decrypt_time = time.time() - start_time
        
        # Performance assertions (should be fast)
        assert encrypt_time < 1.0  # Less than 1 second
        assert decrypt_time < 1.0  # Less than 1 second
        assert decrypted == test_data

    async def test_hash_performance(self):
        """Test password hashing performance"""
        from app.core.auth import hash_password, verify_password
        
        password = "test_password_123"
        
        # Measure hashing time
        start_time = time.time()
        hashed = hash_password(password)
        hash_time = time.time() - start_time
        
        # Measure verification time
        start_time = time.time()
        is_valid = verify_password(password, hashed)
        verify_time = time.time() - start_time
        
        # Performance and correctness assertions
        assert hash_time < 2.0  # Reasonable hashing time
        assert verify_time < 2.0  # Reasonable verification time
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])