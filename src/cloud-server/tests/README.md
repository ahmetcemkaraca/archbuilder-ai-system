# ArchBuilder.AI Cloud Server Tests

This directory contains the comprehensive test suite for the ArchBuilder.AI cloud server. The tests cover all major functionality including document processing, AI model integration, RAG functionality, API endpoints, and error handling scenarios.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared pytest fixtures and configuration
├── test_config.py             # Test configuration and environment variables
├── unit/                      # Unit tests for individual components
│   ├── __init__.py
│   ├── test_ai_service.py     # AI service unit tests
│   ├── test_document_processors.py  # Document processing unit tests
│   ├── test_rag_service.py    # RAG service unit tests
│   ├── test_models.py         # Pydantic models validation tests
│   └── test_utils.py          # Utility functions tests
├── integration/               # Integration tests for component interaction
│   ├── __init__.py
│   ├── test_api_endpoints.py  # API endpoint integration tests
│   ├── test_document_workflow.py  # Document processing workflow tests
│   ├── test_ai_integration.py # AI model integration tests
│   └── test_database.py       # Database integration tests
├── e2e/                      # End-to-end tests for complete workflows
│   ├── __init__.py
│   ├── test_document_upload_flow.py  # Complete document upload and processing
│   ├── test_ai_query_flow.py        # AI query and response workflow
│   └── test_rag_workflow.py         # RAG-enhanced query workflow
├── fixtures/                 # Test data and fixtures
│   ├── documents/            # Sample documents for testing
│   │   ├── sample.pdf
│   │   ├── sample.dxf
│   │   └── sample.txt
│   └── data/                 # Test data files
│       ├── mock_responses.json
│       └── test_building_codes.json
└── mocks/                    # Mock implementations for external services
    ├── __init__.py
    ├── mock_ai_models.py     # Mock AI model responses
    ├── mock_vector_db.py     # Mock vector database
    └── mock_external_apis.py # Mock external API responses
```

## Test Categories

### Unit Tests
- Individual component testing
- Function-level validation
- Model validation and serialization
- Error handling for specific functions

### Integration Tests
- API endpoint testing with FastAPI TestClient
- Database interaction testing
- Service layer integration
- Component communication validation

### End-to-End Tests
- Complete workflow testing
- User journey simulation
- Performance validation
- Error recovery testing

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### End-to-End Tests
```bash
pytest tests/e2e/ -v
```

### With Coverage
```bash
pytest --cov=app --cov-report=html
```

### Specific Test Categories
```bash
# AI-related tests
pytest -m ai

# Database tests
pytest -m database

# Slow tests (excluded by default)
pytest -m "not slow"
```

## Test Configuration

Tests use the following configuration:
- Async test support with pytest-asyncio
- Test database isolation
- Mock AI models for faster testing
- Fixtures for common test data
- Proper cleanup after each test

## Test Data

Sample files and test data are provided in the `fixtures/` directory:
- PDF documents for text extraction testing
- DXF files for CAD processing testing
- Mock AI responses for deterministic testing
- Building code samples for RAG testing

## Mocking Strategy

External dependencies are mocked to ensure:
- Fast test execution
- Deterministic results
- No external API calls during testing
- Isolated component testing

## Coverage Goals

- Overall coverage: 80%+
- Critical paths: 95%+
- Error handling: 90%+
- API endpoints: 100%