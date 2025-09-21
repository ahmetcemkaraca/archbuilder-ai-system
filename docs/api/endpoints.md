# API Endpoints Dökümantasyonu

ArchBuilder.AI Cloud Server, FastAPI tabanlı RESTful API sağlar. Bu dokümantasyon tüm available endpoints, request/response formats ve authentication requirements'ları kapsar.

## 📋 İçindekiler

1. [API Genel Bakış](#api-genel-bakış)
2. [Authentication](#authentication)
3. [Project Management APIs](#project-management-apis)
4. [Document Processing APIs](#document-processing-apis)
5. [AI Processing APIs](#ai-processing-apis)
6. [RAG Knowledge Base APIs](#rag-knowledge-base-apis)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [Monitoring ve Analytics](#monitoring-ve-analytics)

## 🔍 API Genel Bakış

### Base URL
```
Production: https://api.archbuilder.ai/v1
Development: http://localhost:8000/v1
```

### Response Format
Tüm API responses standard format kullanır:

```json
{
  "success": true,
  "data": {...},
  "message": "Operation completed successfully",
  "correlation_id": "req_123456789",
  "timestamp": "2024-01-15T10:30:00Z",
  "processing_time_ms": 1250
}
```

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid project parameters",
    "details": {...},
    "correlation_id": "req_123456789"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🔐 Authentication

### API Key Authentication
```http
Authorization: Bearer your_api_key_here
Content-Type: application/json
```

### User Authentication (OAuth2)
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### Getting API Key
```http
POST /v1/auth/api-key
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "key_name": "desktop_app_key"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "api_key": "ab_key_1234567890abcdef",
    "key_name": "desktop_app_key",
    "expires_at": "2025-01-15T10:30:00Z",
    "permissions": ["project:create", "document:upload", "ai:process"]
  }
}
```

## 🏗️ Project Management APIs

### Create New Project
```http
POST /v1/projects
Authorization: Bearer your_api_key
Content-Type: application/json

{
  "user_input": "3 bedroom apartment with modern kitchen",
  "project_type": "residential",
  "building_type": "apartment",
  "total_area": 120.0,
  "floors": 1,
  "location": "Istanbul, Turkey",
  "language": "tr",
  "special_requirements": [
    "Open kitchen design",
    "Master bedroom with ensuite"
  ],
  "uploaded_documents": ["doc_123", "doc_456"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj_789012345",
    "status": "planning",
    "workflow_type": "simple_layout",
    "total_steps": 12,
    "estimated_duration_minutes": 25,
    "created_at": "2024-01-15T10:30:00Z"
  },
  "correlation_id": "req_create_proj_123"
}
```

### Start Project Execution
```http
POST /v1/projects/{project_id}/execute
Authorization: Bearer your_api_key

{
  "execution_mode": "automatic",
  "enable_checkpoints": true,
  "notification_webhook": "https://your-app.com/webhooks/project-updates"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "execution_id": "exec_987654321",
    "status": "in_progress",
    "current_step": "requirement_analysis",
    "progress_percentage": 8.3
  }
}
```

### Get Project Status
```http
GET /v1/projects/{project_id}/status
Authorization: Bearer your_api_key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj_789012345",
    "status": "in_progress",
    "current_step": {
      "step_name": "layout_generation",
      "step_type": "layout_generation",
      "status": "executing",
      "started_at": "2024-01-15T10:35:00Z",
      "estimated_completion": "2024-01-15T10:45:00Z"
    },
    "progress": {
      "total_steps": 12,
      "completed_steps": 5,
      "progress_percentage": 41.7,
      "estimated_time_remaining_minutes": 15
    },
    "execution_history": [
      {
        "step_name": "requirement_analysis",
        "status": "completed",
        "execution_time_ms": 8500,
        "confidence_score": 0.87
      }
    ]
  }
}
```

### Get Project Results
```http
GET /v1/projects/{project_id}/results
Authorization: Bearer your_api_key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj_789012345",
    "status": "completed",
    "results": {
      "layout_data": {
        "rooms": [
          {
            "name": "Living Room",
            "area_sqm": 35.5,
            "position": {"x": 0, "y": 0},
            "dimensions": {"width": 6.0, "height": 5.9}
          }
        ],
        "circulation": {
          "corridors": [...],
          "doors": [...],
          "windows": [...]
        }
      },
      "revit_commands": [
        {
          "command_type": "create_room",
          "parameters": {...},
          "execution_order": 1
        }
      ],
      "compliance_report": {
        "compliant": true,
        "violations": [],
        "recommendations": [...]
      }
    },
    "completed_at": "2024-01-15T11:15:00Z",
    "total_execution_time_minutes": 28
  }
}
```

### List User Projects
```http
GET /v1/projects?page=1&limit=20&status=completed&building_type=apartment
Authorization: Bearer your_api_key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "projects": [
      {
        "project_id": "proj_789012345",
        "name": "Modern Apartment Layout",
        "building_type": "apartment",
        "status": "completed",
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T11:15:00Z"
      }
    ],
    "pagination": {
      "total": 156,
      "page": 1,
      "limit": 20,
      "total_pages": 8
    }
  }
}
```

### Pause/Resume Project
```http
POST /v1/projects/{project_id}/pause
Authorization: Bearer your_api_key
```

```http
POST /v1/projects/{project_id}/resume
Authorization: Bearer your_api_key

{
  "resume_from_checkpoint": "checkpoint_123",
  "notification_webhook": "https://your-app.com/webhooks/project-updates"
}
```

## 📄 Document Processing APIs

### Upload Document
```http
POST /v1/documents/upload
Authorization: Bearer your_api_key
Content-Type: multipart/form-data

file=@site_plan.dwg
project_id=proj_789012345
document_type=cad
description=Site plan with utilities
tags=site-plan,architectural,utilities
language=tr
```

**Response:**
```json
{
  "success": true,
  "data": {
    "document_id": "doc_123456789",
    "file_name": "site_plan.dwg",
    "file_size": 2048576,
    "document_type": "cad",
    "status": "uploaded",
    "upload_id": "upload_987654321"
  }
}
```

### Process Document
```http
POST /v1/documents/{document_id}/process
Authorization: Bearer your_api_key

{
  "parse_options": {
    "extract_entities": true,
    "extract_dimensions": true,
    "extract_text": true,
    "coordinate_precision": 3
  },
  "rag_integration": {
    "enable_rag": true,
    "chunk_strategy": "semantic",
    "max_chunk_size": 1000
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "processing_id": "proc_456789012",
    "status": "processing",
    "estimated_completion": "2024-01-15T10:35:00Z",
    "processing_stages": [
      "security_validation",
      "format_parsing",
      "content_extraction",
      "rag_integration"
    ]
  }
}
```

### Get Document Processing Status
```http
GET /v1/documents/{document_id}/processing/{processing_id}
Authorization: Bearer your_api_key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "processing_id": "proc_456789012",
    "document_id": "doc_123456789",
    "status": "completed",
    "current_stage": "completed",
    "progress_percentage": 100,
    "results": {
      "parse_result": {
        "entities_count": 1247,
        "layers_count": 15,
        "text_elements_count": 89,
        "dimensions_count": 156
      },
      "rag_integration": {
        "chunks_created": 23,
        "embeddings_generated": 23,
        "indexed": true
      }
    },
    "processing_time_ms": 18500
  }
}
```

### Get Document Content
```http
GET /v1/documents/{document_id}
Authorization: Bearer your_api_key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "document_id": "doc_123456789",
    "file_name": "site_plan.dwg",
    "document_type": "cad",
    "status": "processed",
    "metadata": {
      "file_size": 2048576,
      "upload_date": "2024-01-15T10:30:00Z",
      "processing_date": "2024-01-15T10:32:00Z"
    },
    "parse_result": {
      "format": "dwg",
      "version": "AutoCAD 2022",
      "entities": [...],
      "layers": [...],
      "text_elements": [...]
    }
  }
}
```

### List Documents
```http
GET /v1/documents?project_id=proj_789&document_type=cad&status=processed
Authorization: Bearer your_api_key
```

## 🤖 AI Processing APIs

### Generate Layout
```http
POST /v1/ai/layout/generate
Authorization: Bearer your_api_key

{
  "user_input": "3 bedroom apartment with modern kitchen",
  "project_type": "residential",
  "building_type": "apartment",
  "total_area": 120.0,
  "floors": 1,
  "language": "tr",
  "requirements": [
    "Open kitchen design",
    "Master bedroom with ensuite"
  ],
  "constraints": [
    "North-facing main entrance",
    "Maximum 3m ceiling height"
  ],
  "rag_context_documents": ["doc_123", "doc_456"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "layout_id": "layout_789012345",
    "confidence_score": 0.87,
    "model_used": "vertex_ai_gemini",
    "layout_data": {
      "rooms": [...],
      "circulation": {...},
      "structure": [...]
    },
    "revit_commands": [...],
    "compliance_report": {...},
    "processing_time_ms": 12500
  }
}
```

### Analyze Requirements
```http
POST /v1/ai/requirements/analyze
Authorization: Bearer your_api_key

{
  "user_input": "Modern office building with conference facilities",
  "building_type": "office",
  "project_context": {
    "location": "Istanbul, Turkey",
    "target_occupancy": 200,
    "special_needs": ["Conference center", "Cafeteria"]
  },
  "language": "tr"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "analysis_id": "analysis_456789012",
    "extracted_requirements": [
      {
        "category": "functional",
        "requirement": "Conference center on ground floor",
        "priority": "high",
        "compliance_refs": ["Building Code Article 15.3"]
      }
    ],
    "constraints": [...],
    "recommendations": [...],
    "confidence_score": 0.92
  }
}
```

### Validate Compliance
```http
POST /v1/ai/compliance/validate
Authorization: Bearer your_api_key

{
  "layout_data": {...},
  "building_type": "apartment",
  "location": "Istanbul, Turkey",
  "validation_scope": [
    "fire_safety",
    "accessibility",
    "structural"
  ],
  "language": "tr"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "validation_id": "validation_123456789",
    "overall_compliance": true,
    "compliance_score": 0.94,
    "validations": [
      {
        "category": "fire_safety",
        "compliant": true,
        "issues": [],
        "recommendations": [...]
      }
    ],
    "violations": [],
    "critical_issues": []
  }
}
```

## 🧠 RAG Knowledge Base APIs

### Query Knowledge Base
```http
POST /v1/rag/query
Authorization: Bearer your_api_key

{
  "query": "yangın güvenliği merdiven genişliği",
  "document_types": ["regulation", "reference"],
  "languages": ["tr"],
  "max_results": 10,
  "similarity_threshold": 0.3,
  "filters": {
    "building_type": "apartment",
    "regulation_year": 2024
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query_id": "query_789012345",
    "query": "yangın güvenliği merdiven genişliği",
    "total_results": 7,
    "chunks": [
      {
        "chunk_id": "chunk_123_001",
        "content": "Yangın güvenliği merdivenlerinin minimum genişliği...",
        "similarity_score": 0.87,
        "document_id": "doc_456",
        "metadata": {
          "article_number": "15.2.3",
          "section": "Yangın Güvenliği",
          "page_number": 47
        }
      }
    ],
    "formatted_context": "İlgili Yönetmelik Maddeleri:\n\nMadde 15.2.3..."
  }
}
```

### Add Document to Knowledge Base
```http
POST /v1/rag/documents
Authorization: Bearer your_api_key

{
  "document_id": "doc_123456789",
  "chunk_strategy": "semantic",
  "chunk_options": {
    "max_chunk_size": 1000,
    "chunk_overlap": 200,
    "min_chunk_size": 100
  },
  "embedding_model": "tfidf",
  "language": "tr"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "knowledge_base_id": "kb_789012345",
    "document_id": "doc_123456789",
    "chunks_created": 45,
    "embeddings_generated": 45,
    "processing_time_ms": 8500,
    "status": "indexed"
  }
}
```

### Search Similar Content
```http
POST /v1/rag/search/similar
Authorization: Bearer your_api_key

{
  "reference_text": "Apartman dairelerinde minimum tavan yüksekliği",
  "document_types": ["regulation"],
  "languages": ["tr"],
  "max_results": 5,
  "similarity_algorithm": "cosine"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reference_text": "Apartman dairelerinde minimum tavan yüksekliği",
    "similar_chunks": [
      {
        "chunk_id": "chunk_456_008",
        "content": "Konut yapılarında oda yüksekliği en az 2.40 m...",
        "similarity_score": 0.91,
        "document_info": {
          "document_name": "Turkish Building Code 2024",
          "section": "Konut Yapıları"
        }
      }
    ]
  }
}
```

## 🚨 Error Handling

### Error Codes
```json
{
  "error_codes": {
    "VALIDATION_ERROR": "Request validation failed",
    "AUTHENTICATION_ERROR": "Invalid or missing authentication",
    "AUTHORIZATION_ERROR": "Insufficient permissions",
    "RATE_LIMIT_EXCEEDED": "Too many requests",
    "RESOURCE_NOT_FOUND": "Requested resource not found",
    "PROCESSING_ERROR": "Internal processing error",
    "AI_SERVICE_ERROR": "AI model processing failed",
    "DOCUMENT_PARSE_ERROR": "Document parsing failed",
    "WORKFLOW_ERROR": "Project workflow execution failed"
  }
}
```

### Validation Error Example
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field_errors": [
        {
          "field": "total_area",
          "message": "Total area must be greater than 0",
          "value": -50
        },
        {
          "field": "building_type",
          "message": "Invalid building type",
          "value": "invalid_type",
          "allowed_values": ["apartment", "office", "hospital", "retail"]
        }
      ]
    },
    "correlation_id": "req_123456789"
  }
}
```

### AI Service Error Example
```json
{
  "success": false,
  "error": {
    "code": "AI_SERVICE_ERROR",
    "message": "AI model processing failed",
    "details": {
      "model_used": "vertex_ai_gemini",
      "error_type": "low_confidence",
      "confidence_score": 0.23,
      "fallback_available": true,
      "retry_recommended": true
    },
    "correlation_id": "req_ai_processing_456"
  }
}
```

## ⚡ Rate Limiting

### Rate Limits by Endpoint
```json
{
  "rate_limits": {
    "/v1/projects": {
      "limit": 100,
      "window": "1 hour",
      "per": "api_key"
    },
    "/v1/documents/upload": {
      "limit": 50,
      "window": "1 hour",
      "per": "api_key"
    },
    "/v1/ai/layout/generate": {
      "limit": 20,
      "window": "1 hour",
      "per": "api_key"
    },
    "/v1/rag/query": {
      "limit": 500,
      "window": "1 hour",
      "per": "api_key"
    }
  }
}
```

### Rate Limit Headers
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1642258800
X-RateLimit-Window: 3600
```

### Rate Limit Exceeded Response
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 100,
      "window_seconds": 3600,
      "reset_at": "2024-01-15T12:00:00Z",
      "retry_after_seconds": 1800
    }
  }
}
```

## 📊 Monitoring ve Analytics

### Get API Usage Stats
```http
GET /v1/analytics/usage?period=last_30_days
Authorization: Bearer your_api_key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "last_30_days",
    "total_requests": 2847,
    "successful_requests": 2698,
    "success_rate": 0.947,
    "endpoints": {
      "/v1/projects": {
        "total_requests": 1205,
        "success_rate": 0.943,
        "avg_response_time_ms": 1250
      },
      "/v1/ai/layout/generate": {
        "total_requests": 847,
        "success_rate": 0.891,
        "avg_response_time_ms": 12500
      }
    },
    "daily_usage": [
      {
        "date": "2024-01-15",
        "requests": 95,
        "successful": 92
      }
    ]
  }
}
```

### Health Check
```http
GET /v1/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "services": {
      "ai_service": "healthy",
      "document_service": "healthy",
      "rag_service": "healthy",
      "project_service": "healthy",
      "database": "healthy",
      "redis": "healthy"
    },
    "performance": {
      "avg_response_time_ms": 145,
      "cpu_usage_percent": 34.5,
      "memory_usage_percent": 67.2
    }
  }
}
```

## 🔧 SDK ve Integration

### Python SDK Example
```python
from archbuilder_ai import ArchBuilderClient

# Initialize client
client = ArchBuilderClient(
    api_key="ab_key_1234567890abcdef",
    base_url="https://api.archbuilder.ai/v1"
)

# Create project
project = await client.projects.create(
    user_input="3 bedroom apartment with modern kitchen",
    project_type="residential",
    building_type="apartment",
    total_area=120.0,
    language="tr"
)

# Monitor progress
async for update in client.projects.monitor_progress(project.project_id):
    print(f"Progress: {update.progress_percentage}%")
    print(f"Current step: {update.current_step_name}")
    
    if update.status == "completed":
        results = await client.projects.get_results(project.project_id)
        print(f"Layout generated with {len(results.layout_data.rooms)} rooms")
        break
```

### C# SDK Example
```csharp
using ArchBuilderAI.SDK;

// Initialize client
var client = new ArchBuilderClient("ab_key_1234567890abcdef");

// Create project
var request = new ProjectCreationRequest
{
    UserInput = "3 bedroom apartment with modern kitchen",
    ProjectType = "residential",
    BuildingType = "apartment",
    TotalArea = 120.0f,
    Language = "tr"
};

var project = await client.Projects.CreateAsync(request);

// Monitor progress
await foreach (var update in client.Projects.MonitorProgressAsync(project.ProjectId))
{
    Console.WriteLine($"Progress: {update.ProgressPercentage}%");
    Console.WriteLine($"Current step: {update.CurrentStepName}");
    
    if (update.Status == ProjectStatus.Completed)
    {
        var results = await client.Projects.GetResultsAsync(project.ProjectId);
        Console.WriteLine($"Layout generated with {results.LayoutData.Rooms.Count} rooms");
        break;
    }
}
```

---

**Bu dokümantasyon ArchBuilder.AI Cloud Server'ın tüm API endpoints'lerini ve kullanım örneklerini kapsamaktadır. Rate limiting, authentication ve error handling guidelines'ları production environment için kritiktir.**