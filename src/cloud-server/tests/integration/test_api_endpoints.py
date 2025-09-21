"""
API Integration tests for ArchBuilder.AI Cloud Server
Tests API endpoints, request/response validation, and service integration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import io
import json
from datetime import datetime

from app.main import app
from app.models.documents import DocumentType, ProcessingStatus
from app.models.ai import AIProcessingStatus, AIProvider
from app.models.projects import ProjectStatus


# Test client
client = TestClient(app)


class TestDocumentAPIEndpoints:
    """Test Document API endpoints"""
    
    def test_upload_document_success(self):
        """Test successful document upload via API"""
        # Prepare test file
        file_content = b"Mock DWG file content"
        files = {"file": ("test.dwg", io.BytesIO(file_content), "application/dwg")}
        
        data = {
            "description": "Test architectural drawing",
            "processing_options": json.dumps({"extract_dimensions": True})
        }
        
        # Mock the document service
        with patch("app.api.documents.document_service") as mock_service:
            mock_service.upload_document.return_value = Mock(
                document_id="doc-123",
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.95,
                processing_time_ms=1500,
                error_messages=[]
            )
            
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            
            # Assertions
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["document_id"] == "doc-123"
            assert response_data["status"] == "completed"
            assert response_data["confidence_score"] == 0.95
    
    def test_upload_document_invalid_file_type(self):
        """Test document upload with invalid file type"""
        # Prepare invalid file
        file_content = b"Not a valid file"
        files = {"file": ("test.xyz", io.BytesIO(file_content), "application/unknown")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_upload_document_too_large(self):
        """Test document upload with file too large"""
        # Prepare large file (>100MB)
        large_content = b"x" * (101 * 1024 * 1024)
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]
    
    def test_get_document_success(self):
        """Test successful document retrieval"""
        document_id = "doc-123"
        
        with patch("app.api.documents.document_service") as mock_service:
            mock_service.get_document.return_value = Mock(
                document_id=document_id,
                filename="test.dwg",
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.95,
                created_at=datetime.utcnow()
            )
            
            response = client.get(f"/api/v1/documents/{document_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["document_id"] == document_id
            assert response_data["filename"] == "test.dwg"
    
    def test_get_document_not_found(self):
        """Test document retrieval for non-existent document"""
        document_id = "non-existent"
        
        with patch("app.api.documents.document_service") as mock_service:
            mock_service.get_document.return_value = None
            
            response = client.get(f"/api/v1/documents/{document_id}")
            
            assert response.status_code == 404
            assert "Document not found" in response.json()["detail"]
    
    def test_list_documents_success(self):
        """Test successful document listing"""
        user_id = "user123"
        
        with patch("app.api.documents.document_service") as mock_service:
            mock_service.list_documents.return_value = [
                Mock(
                    document_id="doc-1",
                    filename="plan1.dwg",
                    processing_status=ProcessingStatus.COMPLETED
                ),
                Mock(
                    document_id="doc-2",
                    filename="code.pdf",
                    processing_status=ProcessingStatus.COMPLETED
                )
            ]
            
            # Mock user authentication
            with patch("app.api.documents.get_current_user", return_value=Mock(id=user_id)):
                response = client.get("/api/v1/documents/")
                
                assert response.status_code == 200
                response_data = response.json()
                assert len(response_data["documents"]) == 2
                assert response_data["documents"][0]["filename"] == "plan1.dwg"
    
    def test_delete_document_success(self):
        """Test successful document deletion"""
        document_id = "doc-123"
        
        with patch("app.api.documents.document_service") as mock_service:
            mock_service.delete_document.return_value = True
            
            response = client.delete(f"/api/v1/documents/{document_id}")
            
            assert response.status_code == 200
            assert response.json()["message"] == "Document deleted successfully"


class TestAIAPIEndpoints:
    """Test AI Processing API endpoints"""
    
    def test_process_ai_command_success(self):
        """Test successful AI command processing"""
        request_data = {
            "prompt": "Create a 3-bedroom residential layout",
            "context": {
                "language": "en",
                "region": "Turkey",
                "variables": {
                    "building_type": "residential",
                    "room_count": 3
                }
            },
            "ai_model_config": {
                "provider": "vertex_ai",
                "model_name": "gemini-2.5-flash-lite",
                "temperature": 0.1
            },
            "confidence_threshold": 0.7
        }
        
        with patch("app.api.ai.ai_service") as mock_service:
            mock_service.process_command.return_value = Mock(
                request_id="req-123",
                correlation_id="corr-123",
                status=AIProcessingStatus.COMPLETED,
                generated_content={"layout": "mock layout data"},
                model_used="gemini-2.5-flash-lite",
                provider=AIProvider.VERTEX_AI,
                confidence_score=0.95,
                validation_passed=True,
                processing_time_ms=2500
            )
            
            response = client.post("/api/v1/ai/process", json=request_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "completed"
            assert response_data["confidence_score"] == 0.95
            assert response_data["model_used"] == "gemini-2.5-flash-lite"
    
    def test_process_ai_command_validation_failure(self):
        """Test AI command processing with validation failure"""
        request_data = {
            "prompt": "Create an invalid layout",
            "ai_model_config": {
                "provider": "vertex_ai",
                "model_name": "gemini-2.5-flash-lite"
            },
            "confidence_threshold": 0.7
        }
        
        with patch("app.api.ai.ai_service") as mock_service:
            mock_service.process_command.return_value = Mock(
                request_id="req-456",
                status=AIProcessingStatus.COMPLETED,
                confidence_score=0.3,
                validation_passed=False,
                validation_errors=["Layout does not meet building codes"]
            )
            
            response = client.post("/api/v1/ai/process", json=request_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["validation_passed"] is False
            assert "building codes" in response_data["validation_errors"][0]
    
    def test_process_ai_command_invalid_request(self):
        """Test AI command processing with invalid request"""
        invalid_request = {
            "prompt": "",  # Empty prompt
            "ai_model_config": {
                "provider": "invalid_provider"  # Invalid provider
            }
        }
        
        response = client.post("/api/v1/ai/process", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_existing_project_success(self):
        """Test successful existing project analysis"""
        request_data = {
            "project_data": {
                "total_elements": 1500,
                "rooms": ["Living Room", "Kitchen", "Bedroom"],
                "area_m2": 120
            },
            "analysis_type": "comprehensive"
        }
        
        with patch("app.api.ai.ai_service") as mock_service:
            mock_service.analyze_existing_project.return_value = {
                "analysis": "Comprehensive project analysis completed",
                "recommendations": ["Improve circulation", "Optimize room sizes"],
                "priority_issues": ["Fire safety compliance"],
                "confidence": 0.92,
                "requires_expert_review": False
            }
            
            response = client.post("/api/v1/ai/analyze-project", json=request_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["confidence"] == 0.92
            assert len(response_data["recommendations"]) == 2
            assert len(response_data["priority_issues"]) == 1
    
    def test_get_ai_model_status(self):
        """Test AI model status endpoint"""
        with patch("app.api.ai.ai_service") as mock_service:
            mock_service.get_model_status.return_value = {
                "vertex_ai": {"status": "healthy", "response_time_ms": 150},
                "github_models": {"status": "healthy", "response_time_ms": 200}
            }
            
            response = client.get("/api/v1/ai/status")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["vertex_ai"]["status"] == "healthy"
            assert response_data["github_models"]["status"] == "healthy"


class TestProjectAPIEndpoints:
    """Test Project Management API endpoints"""
    
    def test_create_project_success(self):
        """Test successful project creation"""
        request_data = {
            "name": "Residential Complex A",
            "description": "3-building residential complex",
            "project_type": "residential",
            "location": {
                "country": "Turkey",
                "city": "Istanbul",
                "district": "Kadikoy"
            },
            "requirements": {
                "building_count": 3,
                "unit_count": 24,
                "total_area_m2": 2400
            }
        }
        
        with patch("app.api.projects.project_service") as mock_service:
            mock_service.create_project.return_value = Mock(
                id="proj-123",
                name="Residential Complex A",
                status=ProjectStatus.PLANNING,
                created_at=datetime.utcnow()
            )
            
            response = client.post("/api/v1/projects/", json=request_data)
            
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["id"] == "proj-123"
            assert response_data["name"] == "Residential Complex A"
            assert response_data["status"] == "planning"
    
    def test_get_project_success(self):
        """Test successful project retrieval"""
        project_id = "proj-123"
        
        with patch("app.api.projects.project_service") as mock_service:
            mock_service.get_project.return_value = Mock(
                id=project_id,
                name="Test Project",
                status=ProjectStatus.IN_PROGRESS,
                progress_percentage=45.5
            )
            
            response = client.get(f"/api/v1/projects/{project_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["id"] == project_id
            assert response_data["progress_percentage"] == 45.5
    
    def test_update_project_status(self):
        """Test project status update"""
        project_id = "proj-123"
        update_data = {
            "status": "in_progress",
            "notes": "Started implementation phase"
        }
        
        with patch("app.api.projects.project_service") as mock_service:
            mock_service.update_project_status.return_value = Mock(
                id=project_id,
                status=ProjectStatus.IN_PROGRESS
            )
            
            response = client.patch(f"/api/v1/projects/{project_id}/status", json=update_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "in_progress"
    
    def test_list_user_projects(self):
        """Test listing user projects"""
        user_id = "user123"
        
        with patch("app.api.projects.project_service") as mock_service:
            mock_service.list_user_projects.return_value = [
                Mock(
                    id="proj-1",
                    name="Project 1",
                    status=ProjectStatus.COMPLETED
                ),
                Mock(
                    id="proj-2", 
                    name="Project 2",
                    status=ProjectStatus.IN_PROGRESS
                )
            ]
            
            with patch("app.api.projects.get_current_user", return_value=Mock(id=user_id)):
                response = client.get("/api/v1/projects/")
                
                assert response.status_code == 200
                response_data = response.json()
                assert len(response_data["projects"]) == 2
                assert response_data["projects"][0]["name"] == "Project 1"


class TestAuthenticationEndpoints:
    """Test Authentication API endpoints"""
    
    def test_login_success(self):
        """Test successful user login"""
        login_data = {
            "username": "testuser@example.com",
            "password": "securepassword123"
        }
        
        with patch("app.api.auth.authenticate_user") as mock_auth:
            with patch("app.api.auth.create_access_token") as mock_token:
                mock_auth.return_value = Mock(
                    id="user123",
                    email="testuser@example.com",
                    is_active=True
                )
                mock_token.return_value = "mock.jwt.token"
                
                response = client.post("/api/v1/auth/login", data=login_data)
                
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["access_token"] == "mock.jwt.token"
                assert response_data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            "username": "invalid@example.com",
            "password": "wrongpassword"
        }
        
        with patch("app.api.auth.authenticate_user", return_value=None):
            response = client.post("/api/v1/auth/login", data=login_data)
            
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]
    
    def test_register_success(self):
        """Test successful user registration"""
        register_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
            "company": "Test Company"
        }
        
        with patch("app.api.auth.user_service") as mock_service:
            mock_service.create_user.return_value = Mock(
                id="user456",
                email="newuser@example.com",
                full_name="New User"
            )
            
            response = client.post("/api/v1/auth/register", json=register_data)
            
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["email"] == "newuser@example.com"
            assert response_data["full_name"] == "New User"
    
    def test_get_current_user_success(self):
        """Test getting current user info"""
        with patch("app.api.auth.get_current_user") as mock_get_user:
            mock_get_user.return_value = Mock(
                id="user123",
                email="testuser@example.com",
                full_name="Test User",
                is_active=True
            )
            
            # Mock authentication
            headers = {"Authorization": "Bearer mock.jwt.token"}
            response = client.get("/api/v1/auth/me", headers=headers)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["email"] == "testuser@example.com"
            assert response_data["full_name"] == "Test User"


class TestErrorHandling:
    """Test API error handling"""
    
    def test_404_error_handling(self):
        """Test 404 error handling"""
        response = client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == 404
        assert "Not Found" in response.json()["detail"]
    
    def test_method_not_allowed_error(self):
        """Test 405 Method Not Allowed error"""
        response = client.put("/api/v1/documents/upload")  # Should be POST
        
        assert response.status_code == 405
        assert "Method Not Allowed" in response.json()["detail"]
    
    def test_request_validation_error(self):
        """Test request validation error handling"""
        invalid_data = {
            "invalid_field": "invalid_value"
        }
        
        response = client.post("/api/v1/ai/process", json=invalid_data)
        
        assert response.status_code == 422
        assert "validation error" in response.json()["detail"][0]["type"]
    
    def test_internal_server_error_handling(self):
        """Test internal server error handling"""
        with patch("app.api.documents.document_service") as mock_service:
            mock_service.upload_document.side_effect = Exception("Internal error")
            
            files = {"file": ("test.dwg", io.BytesIO(b"content"), "application/dwg")}
            response = client.post("/api/v1/documents/upload", files=files)
            
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestRateLimiting:
    """Test API rate limiting"""
    
    def test_rate_limit_enforcement(self):
        """Test rate limiting enforcement"""
        # Mock rate limiter
        with patch("app.core.middleware.rate_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = False
            
            response = client.get("/api/v1/documents/")
            
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_rate_limit_headers(self):
        """Test rate limiting headers"""
        with patch("app.core.middleware.rate_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_requests.return_value = 95
            
            response = client.get("/api/v1/ai/status")
            
            assert response.status_code == 200
            assert "X-RateLimit-Remaining" in response.headers
            assert response.headers["X-RateLimit-Remaining"] == "95"


class TestAPIPerformance:
    """Test API performance and caching"""
    
    def test_response_time_headers(self):
        """Test response time headers"""
        response = client.get("/api/v1/ai/status")
        
        assert "X-Response-Time" in response.headers
        # Response time should be reasonable (< 1000ms for status check)
        response_time = float(response.headers["X-Response-Time"].replace("ms", ""))
        assert response_time < 1000
    
    def test_caching_headers(self):
        """Test caching headers for appropriate endpoints"""
        response = client.get("/api/v1/ai/status")
        
        # Status endpoint should have cache headers
        assert "Cache-Control" in response.headers
        assert "ETag" in response.headers or "Last-Modified" in response.headers
    
    def test_compression_support(self):
        """Test response compression support"""
        headers = {"Accept-Encoding": "gzip, deflate"}
        response = client.get("/api/v1/documents/", headers=headers)
        
        # Large responses should be compressed
        assert "Content-Encoding" in response.headers or len(response.content) < 1000


@pytest.mark.asyncio
class TestWebSocketEndpoints:
    """Test WebSocket endpoints for real-time updates"""
    
    async def test_project_progress_websocket(self):
        """Test project progress WebSocket connection"""
        project_id = "proj-123"
        
        with client.websocket_connect(f"/ws/projects/{project_id}/progress") as websocket:
            # Mock sending progress update
            mock_progress = {
                "project_id": project_id,
                "stage": "ai_processing",
                "progress_percentage": 25.5,
                "current_step": "Generating layout",
                "estimated_completion": "2024-01-15T10:30:00Z"
            }
            
            # In a real test, this would be triggered by the service
            websocket.send_json(mock_progress)
            
            # Receive the progress update
            data = websocket.receive_json()
            assert data["project_id"] == project_id
            assert data["progress_percentage"] == 25.5
    
    async def test_ai_processing_websocket(self):
        """Test AI processing WebSocket for real-time status"""
        correlation_id = "corr-123"
        
        with client.websocket_connect(f"/ws/ai/processing/{correlation_id}") as websocket:
            # Mock AI processing status update
            mock_status = {
                "correlation_id": correlation_id,
                "status": "processing",
                "stage": "validation",
                "confidence_score": 0.87,
                "processing_time_ms": 5500
            }
            
            websocket.send_json(mock_status)
            
            data = websocket.receive_json()
            assert data["correlation_id"] == correlation_id
            assert data["status"] == "processing"
            assert data["confidence_score"] == 0.87