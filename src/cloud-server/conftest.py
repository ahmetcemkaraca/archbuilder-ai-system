"""
ArchBuilder.AI - Test Configuration and Setup
Comprehensive testing framework configuration with pytest, async support, and mocking
"""

import os
import sys
import pytest
import asyncio
import tempfile
from typing import Generator, AsyncGenerator
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db_session
from app.core.config import get_settings
from app.main import app

# Test Database Configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with session_factory() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_client(test_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override."""
    
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()

@pytest.fixture
def temp_directory():
    """Create temporary directory for file tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def sample_files(temp_directory):
    """Create sample files for testing."""
    files = {}
    
    # Sample DWG file content (mock)
    dwg_file = temp_directory / "sample.dwg"
    dwg_file.write_bytes(b"Mock DWG content for testing")
    files["dwg"] = dwg_file
    
    # Sample PDF file content (mock)
    pdf_file = temp_directory / "sample.pdf"
    pdf_file.write_bytes(b"Mock PDF content for testing")
    files["pdf"] = pdf_file
    
    # Sample text file
    txt_file = temp_directory / "sample.txt"
    txt_file.write_text("Sample text content for testing")
    files["txt"] = txt_file
    
    return files

@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    class MockSettings:
        debug_mode = True
        environment = "test"
        secret_key = "test-secret-key"
        algorithm = "HS256"
        access_token_expire_minutes = 30
        
        # Database settings
        database_url = TEST_DATABASE_URL
        
        # Redis settings (mock)
        redis_url = "redis://localhost:6379/0"
        
        # AI service settings (mock)
        vertex_ai_project = "test-project"
        vertex_ai_location = "us-central1"
        github_token = "test-token"
        
        # File storage settings
        max_file_size = 10 * 1024 * 1024  # 10MB
        allowed_file_types = [".dwg", ".dxf", ".ifc", ".pdf", ".txt"]
    
    return MockSettings()

@pytest.fixture
async def authenticated_user(test_session):
    """Create an authenticated test user."""
    from app.dao.user_dao import UserDAO
    from uuid import uuid4
    
    # Create a test tenant first
    tenant_id = uuid4()
    
    # Create test user
    user_dao = UserDAO(test_session)
    user = await user_dao.create_user(
        email="test@example.com",
        password="TestPassword123!",
        full_name="Test User",
        tenant_id=tenant_id,
        role="admin",
        is_active=True
    )
    
    return user

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    class MockAIService:
        async def generate_text(self, prompt: str, **kwargs):
            return f"Mock AI response for: {prompt[:50]}..."
        
        async def analyze_document(self, content: str, **kwargs):
            return {
                "summary": "Mock document analysis",
                "key_points": ["Point 1", "Point 2", "Point 3"],
                "confidence": 0.95
            }
        
        async def generate_layout(self, requirements: dict, **kwargs):
            return {
                "layout_id": "mock-layout-123",
                "rooms": [
                    {"name": "Living Room", "area": 25.0, "position": {"x": 0, "y": 0}},
                    {"name": "Kitchen", "area": 15.0, "position": {"x": 5, "y": 0}},
                    {"name": "Bedroom", "area": 20.0, "position": {"x": 0, "y": 5}}
                ],
                "total_area": 60.0
            }
    
    return MockAIService()

@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing."""
    class MockCacheManager:
        def __init__(self):
            self._cache = {}
        
        async def get(self, key: str):
            return self._cache.get(key)
        
        async def set(self, key: str, value, ttl: int = 300):
            self._cache[key] = value
        
        async def delete(self, key: str):
            self._cache.pop(key, None)
        
        async def clear(self):
            self._cache.clear()
        
        async def ping(self):
            return True
        
        def get_total_keys(self):
            return len(self._cache)
        
        def get_cache_stats(self):
            return {
                "keys": len(self._cache),
                "memory_usage": "N/A",
                "hit_ratio": 0.85
            }
    
    return MockCacheManager()

@pytest.fixture
def mock_performance_tracker():
    """Mock performance tracker for testing."""
    class MockPerformanceTracker:
        def __init__(self):
            self._metrics = {}
        
        def track_operation(self, operation: str, duration: float):
            if operation not in self._metrics:
                self._metrics[operation] = []
            self._metrics[operation].append(duration)
        
        def get_metrics(self, operation: str = None):
            if operation:
                return {
                    "operation": operation,
                    "count": len(self._metrics.get(operation, [])),
                    "avg_duration": sum(self._metrics.get(operation, [])) / len(self._metrics.get(operation, [])) if self._metrics.get(operation) else 0,
                    "total_duration": sum(self._metrics.get(operation, []))
                }
            return self._metrics
        
        def get_metrics_summary(self):
            return {
                "total_operations": sum(len(ops) for ops in self._metrics.values()),
                "operations": list(self._metrics.keys()),
                "avg_response_time": 0.25
            }
    
    return MockPerformanceTracker()

# Custom pytest markers
pytest_plugins = [
    "pytest_asyncio",
    "pytest_mock",
    "pytest_xdist"
]

# Test markers
pytestmark = pytest.mark.asyncio

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "ai: mark test as requiring AI services"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security-related"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test path/name
        if "test_unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        if "test_ai" in item.nodeid or "ai_service" in item.nodeid:
            item.add_marker(pytest.mark.ai)
        
        if "test_database" in item.nodeid or "dao" in item.nodeid:
            item.add_marker(pytest.mark.database)
        
        if "test_security" in item.nodeid or "auth" in item.nodeid:
            item.add_marker(pytest.mark.security)
        
        if "test_slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)

# Async test utilities
class AsyncTestHelper:
    """Helper class for async testing operations."""
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
        """Wait for a condition to become true."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    def create_mock_async_context_manager(return_value=None):
        """Create a mock async context manager."""
        class MockAsyncContextManager:
            async def __aenter__(self):
                return return_value
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return MockAsyncContextManager()

# Test data factories
class TestDataFactory:
    """Factory for creating test data objects."""
    
    @staticmethod
    def create_user_data(override=None):
        """Create test user data."""
        data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "role": "user",
            "is_active": True
        }
        if override:
            data.update(override)
        return data
    
    @staticmethod
    def create_project_data(override=None):
        """Create test project data."""
        data = {
            "name": "Test Project",
            "description": "A test project for unit testing",
            "project_type": "residential",
            "status": "draft"
        }
        if override:
            data.update(override)
        return data
    
    @staticmethod
    def create_document_data(override=None):
        """Create test document data."""
        data = {
            "filename": "test_document.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "content_type": "application/pdf"
        }
        if override:
            data.update(override)
        return data