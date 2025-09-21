"""
Pytest Configuration and Shared Fixtures for ArchBuilder.AI Tests
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import get_settings
from app.core.database import get_async_session, Base
from app.models.documents import (
    ProcessingResult,
    DocumentMetadata,
    ProcessingStatus,
    DocumentType,
    RAGContext,
    DocumentChunk
)
from app.models.ai import AIProcessingRequest, AIProcessingResponse
from app.services.ai_service import AIService
from app.services.rag_service import RAGService

# Test configuration
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings():
    """Get test settings configuration."""
    return get_settings()


@pytest.fixture
async def async_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test.db",
        echo=True,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def override_get_async_session(async_session):
    """Override database session dependency for testing."""
    def _override_get_async_session():
        return async_session
    
    app.dependency_overrides[get_async_session] = _override_get_async_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_async_session):
    """Create FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(override_get_async_session):
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def temp_directory():
    """Create temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_pdf_file(temp_directory):
    """Create a sample PDF file for testing."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_file = temp_directory / "sample.pdf"
    pdf_file.write_bytes(pdf_content)
    return pdf_file


@pytest.fixture
def sample_text_file(temp_directory):
    """Create a sample text file for testing."""
    text_content = """
    Building Code Requirements for Residential Construction
    
    Chapter 1: General Requirements
    All residential buildings must comply with local building codes and regulations.
    
    Chapter 2: Structural Requirements
    - Minimum ceiling height: 2.4 meters
    - Maximum room span without support: 6 meters
    - Foundation depth: minimum 0.8 meters below frost line
    
    Chapter 3: Fire Safety
    - Smoke detectors required in all bedrooms
    - Fire exits must be clearly marked
    - Maximum travel distance to exit: 30 meters
    """
    text_file = temp_directory / "building_code.txt"
    text_file.write_text(text_content, encoding="utf-8")
    return text_file


@pytest.fixture
def sample_dxf_content():
    """Sample DXF file content for testing."""
    return """0
SECTION
2
HEADER
9
$ACADVER
1
AC1015
0
ENDSEC
0
SECTION
2
ENTITIES
0
LINE
8
0
10
0.0
20
0.0
30
0.0
11
100.0
21
100.0
31
0.0
0
ENDSEC
0
EOF
"""


@pytest.fixture
def sample_dxf_file(temp_directory, sample_dxf_content):
    """Create a sample DXF file for testing."""
    dxf_file = temp_directory / "sample.dxf"
    dxf_file.write_text(sample_dxf_content, encoding="utf-8")
    return dxf_file


@pytest.fixture
def mock_document_metadata():
    """Create mock document metadata."""
    return DocumentMetadata(
        filename="test_document.pdf",
        file_type=DocumentType.PDF,
        file_size_bytes=1024,
        content_hash="abc123def456",
        encoding="utf-8"
    )


@pytest.fixture
def mock_processing_result(mock_document_metadata):
    """Create mock document processing result."""
    return ProcessingResult(
        document_id="test-doc-123",
        correlation_id="test-corr-456",
        processing_status=ProcessingStatus.COMPLETED,
        extracted_text="This is sample extracted text from a building code document.",
        confidence_score=0.95,
        processing_time_ms=1500
    )


@pytest.fixture
def mock_document_chunks():
    """Create mock document chunks for RAG testing."""
    return [
        DocumentChunk(
            document_id="test-doc-123",
            chunk_index=0,
            text="Building codes require minimum ceiling height of 2.4 meters.",
            start_position=0,
            end_position=62
        ),
        DocumentChunk(
            document_id="test-doc-123",
            chunk_index=1,
            text="Fire exits must be clearly marked and accessible.",
            start_position=63,
            end_position=111
        )
    ]


@pytest.fixture
def mock_rag_context(mock_document_chunks):
    """Create mock RAG context."""
    return RAGContext(
        query="What are the ceiling height requirements?",
        relevant_chunks=mock_document_chunks,
        confidence_score=0.85,
        max_chunks=5
    )


@pytest.fixture
def mock_ai_request():
    """Create mock AI processing request."""
    return AIProcessingRequest(
        command="Create a residential layout with 3 bedrooms",
        context="Single family house, Turkish building codes",
        region="Turkey",
        language="en",
        building_type="residential",
        options={
            "include_furniture": True,
            "optimize_layout": True
        }
    )


@pytest.fixture
def mock_ai_response():
    """Create mock AI processing response."""
    return AIProcessingResponse(
        success=True,
        response_text="Generated residential layout with 3 bedrooms following Turkish building codes.",
        model_used="gpt-4.1",
        confidence=0.92,
        processing_time_ms=2500,
        validation_results={
            "building_code_compliance": True,
            "accessibility_check": True,
            "safety_validation": True
        },
        metadata={
            "total_rooms": 6,
            "total_area": 120.5,
            "compliance_score": 0.95
        }
    )


@pytest.fixture
def mock_ai_service():
    """Create mock AI service for testing."""
    mock_service = Mock(spec=AIService)
    mock_service.process_command = AsyncMock()
    mock_service.validate_output = AsyncMock(return_value=True)
    mock_service.get_model_status = AsyncMock(return_value={"status": "healthy"})
    return mock_service


@pytest.fixture
def mock_rag_service():
    """Create mock RAG service for testing."""
    mock_service = Mock(spec=RAGService)
    mock_service.process_document_for_rag = AsyncMock(return_value=True)
    mock_service.create_rag_context = AsyncMock()
    mock_service.get_document_statistics = AsyncMock(return_value={
        "total_documents": 10,
        "total_chunks": 50,
        "total_embeddings": 50
    })
    return mock_service


@pytest.fixture
def mock_vertex_ai_response():
    """Mock Vertex AI API response."""
    return {
        "predictions": [{
            "content": "This is a mock response from Vertex AI",
            "metadata": {
                "confidence": 0.95,
                "safety_ratings": [
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "probability": "NEGLIGIBLE"}
                ]
            }
        }]
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "choices": [{
            "message": {
                "content": "This is a mock response from OpenAI GPT-4",
                "role": "assistant"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 25,
            "total_tokens": 75
        }
    }


@pytest.fixture
def mock_embedding_response():
    """Mock embedding API response."""
    return {
        "data": [{
            "embedding": [0.1, 0.2, 0.3] * 512,  # Mock 1536-dimensional embedding
            "index": 0
        }],
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 10
        }
    }


# Test data generators
def generate_test_correlation_id() -> str:
    """Generate test correlation ID."""
    return f"test-{uuid.uuid4().hex[:8]}"


def generate_test_document_id() -> str:
    """Generate test document ID."""
    return f"doc-{uuid.uuid4().hex[:8]}"


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow
pytest.mark.ai = pytest.mark.ai
pytest.mark.database = pytest.mark.database