"""
Integration tests for API endpoints
Tests full request-response cycle with database integration
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import User


@pytest.mark.integration
@pytest.mark.api
class TestHealthEndpoints:
    """Test suite for health check endpoints."""
    
    async def test_health_check(self, test_client: AsyncClient):
        """Test basic health check endpoint."""
        # Act
        response = await test_client.get("/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    async def test_health_detailed(self, test_client: AsyncClient):
        """Test detailed health check endpoint."""
        # Act
        response = await test_client.get("/health/detailed")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "cache" in data
        assert "ai_services" in data


@pytest.mark.integration
@pytest.mark.api
class TestAuthEndpoints:
    """Test suite for authentication endpoints."""
    
    async def test_user_registration(self, test_client: AsyncClient):
        """Test user registration endpoint."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User",
            "tenant_name": "Test Tenant"
        }
        
        # Act
        response = await test_client.post("/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    async def test_user_login(self, test_client: AsyncClient, authenticated_user: User):
        """Test user login endpoint."""
        # Arrange
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # Act
        response = await test_client.post("/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    async def test_user_login_invalid_credentials(self, test_client: AsyncClient):
        """Test login with invalid credentials."""
        # Arrange
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        # Act
        response = await test_client.post("/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
@pytest.mark.api
class TestProjectEndpoints:
    """Test suite for project management endpoints."""
    
    async def test_create_project(self, test_client: AsyncClient, authenticated_user: User):
        """Test project creation endpoint."""
        # Arrange
        project_data = {
            "name": "Test Project",
            "description": "A test project for integration testing",
            "project_type": "residential",
            "requirements": {
                "rooms": ["living_room", "kitchen", "bedroom"],
                "area": 100,
                "budget": 50000
            }
        }
        
        # Get auth token first
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Act
        response = await test_client.post(
            "/projects/", 
            json=project_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == project_data["name"]
        assert data["project_type"] == project_data["project_type"]
        assert "id" in data
        assert "created_at" in data
    
    async def test_get_projects(self, test_client: AsyncClient, authenticated_user: User):
        """Test getting user projects."""
        # Arrange
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Act
        response = await test_client.get("/projects/", headers=headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.api
class TestDocumentEndpoints:
    """Test suite for document processing endpoints."""
    
    async def test_upload_document(self, test_client: AsyncClient, authenticated_user: User, sample_files):
        """Test document upload endpoint."""
        # Arrange
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Prepare file upload
        with open(sample_files["txt"], "rb") as f:
            files = {"file": ("test.txt", f, "text/plain")}
            data = {"document_type": "regulation"}
            
            # Act
            response = await test_client.post(
                "/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["filename"] == "test.txt"
        assert response_data["file_type"] == "txt"
        assert "id" in response_data
    
    async def test_get_documents(self, test_client: AsyncClient, authenticated_user: User):
        """Test getting user documents."""
        # Arrange
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Act
        response = await test_client.get("/documents/", headers=headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.ai
class TestAIEndpoints:
    """Test suite for AI processing endpoints."""
    
    async def test_analyze_requirements(self, test_client: AsyncClient, authenticated_user: User):
        """Test AI requirements analysis endpoint."""
        # Arrange
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        requirements_data = {
            "description": "I need a 3-bedroom house with a modern kitchen and large living room",
            "budget": 150000,
            "area": 120,
            "style": "modern"
        }
        
        # Act
        response = await test_client.post(
            "/ai/analyze-requirements",
            json=requirements_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "suggestions" in data
        assert "estimated_timeline" in data
    
    async def test_generate_layout(self, test_client: AsyncClient, authenticated_user: User):
        """Test AI layout generation endpoint."""
        # Arrange
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        layout_data = {
            "rooms": ["living_room", "kitchen", "bedroom_1", "bedroom_2", "bathroom"],
            "total_area": 100,
            "constraints": {
                "max_width": 15,
                "max_depth": 10
            }
        }
        
        # Act
        response = await test_client.post(
            "/ai/generate-layout",
            json=layout_data,
            headers=headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "layout_id" in data
        assert "rooms" in data
        assert "total_area" in data


@pytest.mark.integration
@pytest.mark.slow
class TestSystemIntegration:
    """Test suite for full system integration scenarios."""
    
    async def test_complete_project_workflow(
        self, 
        test_client: AsyncClient, 
        authenticated_user: User,
        sample_files
    ):
        """Test complete project creation workflow."""
        # Arrange
        login_response = await test_client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: Upload a requirements document
        with open(sample_files["txt"], "rb") as f:
            files = {"file": ("requirements.txt", f, "text/plain")}
            data = {"document_type": "requirements"}
            
            upload_response = await test_client.post(
                "/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        assert upload_response.status_code == 201
        document_id = upload_response.json()["id"]
        
        # Step 2: Analyze requirements with AI
        analysis_data = {
            "document_id": document_id,
            "analysis_type": "full"
        }
        
        analysis_response = await test_client.post(
            "/ai/analyze-document",
            json=analysis_data,
            headers=headers
        )
        
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()
        
        # Step 3: Create a project based on analysis
        project_data = {
            "name": "AI Generated Project",
            "description": "Project created from AI analysis",
            "project_type": "residential",
            "requirements": analysis.get("extracted_requirements", {})
        }
        
        project_response = await test_client.post(
            "/projects/",
            json=project_data,
            headers=headers
        )
        
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]
        
        # Step 4: Generate layout for the project
        layout_data = {
            "project_id": project_id,
            "preferences": {
                "style": "modern",
                "priority": "efficiency"
            }
        }
        
        layout_response = await test_client.post(
            "/ai/generate-layout",
            json=layout_data,
            headers=headers
        )
        
        assert layout_response.status_code == 200
        layout = layout_response.json()
        
        # Step 5: Verify project was updated with layout
        project_get_response = await test_client.get(
            f"/projects/{project_id}",
            headers=headers
        )
        
        assert project_get_response.status_code == 200
        updated_project = project_get_response.json()
        assert "layout" in updated_project or "layouts" in updated_project