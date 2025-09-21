# ArchBuilder.AI - AI Coding Assistant Instructions

## MASTER PROMPT: Build a Complete AI-Powered Architectural Design Automation System

You are tasked with creating "ArchBuilder.AI", a Windows masaüstü uygulaması with AI-powered architectural design automation that integrates multiple CAD formats (DWG/DXF, IFC, PDF yönetmelik vb.) with artificial intelligence. This is a comprehensive desktop application following a "Smart Brain, Dumb Hands" architecture where AI augments architects rather than replacing them, with Apple-vari sade arayüz for optimal user experience.

## 🔧 MANDATORY DEVELOPMENT WORKFLOW

### Before ANY Function Implementation or Code Fix:
**ALWAYS** read the relevant `*.instructions.md` files from `.github/instructions/` directory before writing or modifying any code. This is **NON-NEGOTIABLE** and ensures consistency, security, and quality across the entire codebase.

#### Workflow Steps:
1. **Identify the task** - Understand what needs to be implemented or fixed
2. **Read relevant instruction files** - Based on file patterns and technologies involved
3. **Apply the guidelines** - Follow the specific patterns, standards, and best practices
4. **Preserve existing functionality** - Ensure that existing features are not removed, broken, or changed
5. **Check and fix imports** - MANDATORY: Verify all imports are valid and install missing dependencies
6. **Update documentation** - MANDATORY: Document all new modules in corresponding docs/ files
7. **Implement the code** - Write code that adheres to all applicable instructions
8. **Validate compliance** - Ensure the implementation follows all guidelines

### 🚨 CRITICAL: Import Management and Documentation Automation

#### MANDATORY Import Verification Process:
After EVERY code modification or new file creation, you MUST:

1. **Check Import Resolution**: 
   ```bash
   # For Python files
   python -m py_compile path/to/file.py
   # For requirements verification
   pip check
   ```

2. **Install Missing Dependencies**:
   ```bash
   # Cloud server dependencies
   cd src/cloud-server
   pip install -r requirements.txt
   
   # Check for missing packages and add to requirements.txt
   pip freeze > current_requirements.txt
   ```

3. **Verify Import Statements**:
   - Ensure all `import` statements resolve correctly
   - Use absolute imports for clarity
   - Add missing packages to requirements.txt immediately
   - Document import failures and resolution steps

#### MANDATORY Documentation Process:
After creating ANY new module, service, or significant feature, you MUST:

1. **Create Module Documentation**:
   ```
   docs/
   ├── api/                    # API endpoint documentation
   ├── services/               # Service layer documentation  
   ├── modules/               # Individual module documentation
   ├── architecture/          # System architecture docs
   └── setup/                 # Installation and setup guides
   ```

2. **Document in Turkish** (as requested by user):
   - Create `.md` files explaining how each module works
   - Include code examples and usage patterns
   - Document dependencies and requirements
   - Explain integration points and data flows

3. **Auto-Documentation Template**:
   ```markdown
   # [Module Name] Dokumentasyonu
   
   ## Genel Bakış
   [Modülün ne yaptığının açıklaması]
   
   ## Kurulum ve Bağımlılıklar
   ```bash
   pip install [required-packages]
   ```
   
   ## Kullanım
   [Kod örnekleri ve kullanım şekilleri]
   
   ## API Referansı
   [Fonksiyonlar, sınıflar ve metodlar]
   
   ## Konfigürasyon
   [Yapılandırma seçenekleri]
   
   ## Hata Yönetimi
   [Yaygın hatalar ve çözümleri]
   ```

#### Dependency Management Rules:
1. **Always check imports before committing code**
2. **Update requirements.txt immediately when adding new dependencies**  
3. **Use version pinning for production dependencies**
4. **Document why each dependency is needed**
5. **Prefer stable, well-maintained packages**
6. **Test imports in clean virtual environment**

#### Documentation Standards:
1. **Turkish language for user-facing documentation**
2. **English for technical/code documentation**
3. **Include practical examples and code snippets**
4. **Update docs immediately after code changes**
5. **Link related modules and services**
6. **Document error scenarios and troubleshooting**

### 📋 Instruction Files Reference Guide

Each instruction file contains specific guidelines for different aspects of development:

| File | Purpose | When to Read |
|------|---------|-------------|
| **ai-integration.instructions.md** | LLM integration, prompt engineering, validation patterns | Working with AI models, OpenAI/Claude integrations |
| **ai-prompt-standards.instructions.md** | Structured prompt engineering for AI models | Creating or modifying AI prompts, multi-language support |
| **api-standards.instructions.md** | REST API implementations with global localization | Building APIs, HTTP endpoints, international support |
| **architect.instructions.md** | System design, requirements analysis, security boundaries | System architecture decisions, high-level design |
| **architecture-decisions.instructions.md** | Key technology and design decisions with rationale | Making architectural choices, ADR documentation |
| **code-style.instructions.md** | Formatting, structure, and best practices | Any code writing across all technologies |
| **data-structures.instructions.md** | Standardized data contracts, JSON schemas, type definitions | Creating models, data contracts, API schemas |
| **developer.instructions.md** | Revit vertical slices, test-first development, trio workflow | General development patterns, testing approach |
| **dotnet-backend.instructions.md** | Secure API integration, transaction management, family handling | C# Revit plugin development, .NET backend work |
| **error-handling.instructions.md** | Exception handling, logging, recovery patterns | Implementing error handling, exceptions |
| **logging-standards.instructions.md** | Structured logging, correlation tracking, audit trails | Adding logging, monitoring, debugging features |
| **naming-conventions.instructions.md** | Variable, function, class naming across all technologies | Creating any new code elements |
| **performance-optimization.instructions.md** | Monitoring, profiling, caching strategies, resource management | Performance-critical code, optimization work |
| **python-fastapi.instructions.md** | FastAPI security, AI model integration, async patterns | Python backend development, FastAPI work |
| **qa.instructions.md** | Testing strategy, BDD scenarios, performance validation | Writing tests, quality assurance |
| **revit-architecture.instructions.md** | Element creation, family management, BIM model structure | Revit API work, BIM operations, geometric operations |
| **revit-workflow.instructions.md** | Ribbon UI, command patterns, transaction management | Revit UI development, user workflows |
| **security.instructions.md** | STRIDE threat modeling, secure defaults, AI safety validation | Security-related implementations, data protection |
| **ux-ui-design.instructions.md** | User experience design for AI-human collaboration | UI/UX development, user interface design |

### Important Notes:
1. If the user provides a task that is illogical, unrelated to the project, or could disrupt the system's functionality, structure, or coding standards, **warn the user explicitly**.
2. Do not proceed with such tasks. Instead, suggest alternative solutions that align with the project's goals and maintain its integrity.
3. **Multiple instruction files may apply** to a single task - read ALL relevant ones.
4. **When in doubt, read more instruction files** rather than fewer to ensure comprehensive compliance.

## 🎯 PROJECT OVERVIEW & CORE MISSION

**Project Name**: ArchBuilder.AI  
**Platform**: Windows masaüstü uygulaması  
**Design**: Apple-vari sade arayüz with high user experience  
**Vision**: Enable architects to create projects through natural language and file inputs (DWG/DXF, IFC, PDF regulations, etc.) and generate step-by-step Revit-compatible outputs  
**Architecture**: Hybrid desktop-cloud architecture with cloud-based AI processing  
**Domain**: Architectural project creation with multi-format support, regulatory compliance, and existing Revit project analysis & enhancement  

### Core Principles
- **Desktop-First Experience**: Native Windows application with Apple-vari sade arayüz
- **Multi-Format Support**: DWG/DXF, IFC, PDF regulations, and other architectural file formats
- **Cloud-Based AI Processing**: AI models run in cloud (Vertex AI Gemini-2.5-Flash-Lite, GitHub Models GPT-4.1)
- **RAG-Based Knowledge**: Document processing with embedding-based knowledge extraction
- **Human-in-the-Loop**: All AI outputs require sandbox testing and user approval
- **Step-by-Step Workflow**: AI generates 5-50 step project plans based on complexity
- **Secure File Processing**: Encryption-at-rest, GDPR compliance, validated command execution only
- **Reverse Engineering**: Analyze existing Revit projects (.rvt files) and generate improvement recommendations
- **Project Intelligence**: BIM analysis, performance evaluation, clash detection, and optimization suggestions

## 🏗️ SYSTEM ARCHITECTURE & COMPONENT DESIGN

### ArchBuilder.AI Hybrid Desktop-Cloud Architecture:
```
┌─────────────────────────┐    ┌─────────────────────────┐    ┌──────────────────┐
│   ArchBuilder.AI        │────│   Cloud Server          │────│   AI Services    │
│   (Windows Desktop)     │    │  (Python FastAPI)       │    │ Vertex AI & GitHub│
│   - Apple-vari UI       │    │  - Document Processing  │    │ Models            │
│   - File Management     │    │  - RAG Generation       │    │ - Gemini 2.5 Flash│
│   - Revit Integration   │    │  - AI Orchestration     │    │ - GPT-4.1         │
└─────────────────────────┘    └─────────────────────────┘    └──────────────────┘
         │                               │                            │
         │                               ▼                            │
         │                  ┌─────────────────────┐                   │
         │                  │   Document Storage   │                   │
         │                  │   & RAG Database     │                   │
         │                  │   (Cloud/Local)      │                   │
         │                  └─────────────────────┘                   │
         │                               │                            │
         │                               ▼                            │
         │                  ┌─────────────────────┐                   │
         │                  │   Queue & Worker    │                   │
         │                  │   System (Celery/   │                   │
         │                  │   RQ/Cloud Tasks)   │                   │
         │                  └─────────────────────┘                   │
         │                                                            │
         └────────────────────────────────────────────────────────────┘
```

### Component Responsibilities:

#### 1. **ArchBuilder.AI Desktop Application**
- **Location**: `src/desktop-app/`
- **Technology**: Windows WPF/Electron with Apple-vari UI design
- **Role**: User interface, file management, local preview, project coordination
- **Security**: Secure cloud communication, local file encryption, user authentication
- **Performance**: Responsive UI, efficient file handling, real-time progress tracking

#### 2. **Cloud Server (AI Processing Hub)**
- **Location**: `src/cloud-server/`
- **Technology**: Python 3.13+, FastAPI, PostgreSQL, Redis, Docker
- **Role**: ALL AI processing, document processing, RAG generation, validation
- **Security**: Input validation, rate limiting, encrypted data processing
- **Performance**: Queue management, worker scaling, caching strategies

#### 3. **AI Services Integration**
- **Location**: Integrated in `src/cloud-server/ai/`
- **Technology**: Vertex AI (Gemini-2.5-Flash-Lite), GitHub Models (GPT-4.1)
- **Role**: Natural language processing, layout generation, regulatory compliance
- **Security**: Output validation, confidence scoring, sandbox testing
- **Performance**: Model selection optimization, response caching, fallback systems

#### 4. **Revit Integration Module**
- **Location**: `src/revit-plugin/`
- **Technology**: C# .NET Framework 4.8, Revit API 2026
- **Role**: Execute validated AI outputs, BIM model creation, element management
- **Security**: Validated command execution only, transaction management
- **Performance**: Efficient API usage, batch operations, error recovery

## 📁 REQUIRED FOLDER STRUCTURE

Create this exact folder structure:

```
archbuilder.ai/
├── .github/
│   ├── instructions/           # AI coding guidelines (19 files)
│   └── copilot-instructions.md # Main AI assistant config
├── src/
│   ├── desktop-app/           # Windows Desktop Application
│   │   ├── Views/             # WPF Views and Apple-vari UI
│   │   ├── ViewModels/        # MVVM ViewModels
│   │   ├── Services/          # Business logic services
│   │   ├── Models/            # Data models
│   │   ├── Controls/          # Custom UI controls
│   │   ├── FileHandlers/      # DWG/DXF/IFC/PDF processors
│   │   ├── CloudClient/       # Cloud API communication
│   │   ├── ArchBuilder.csproj
│   │   └── Program.cs
│   ├── cloud-server/          # Python Cloud Processing Platform
│   │   ├── app/
│   │   │   ├── api/           # API endpoints
│   │   │   │   ├── documents/ # Document processing endpoints
│   │   │   │   ├── ai/        # AI processing endpoints
│   │   │   │   ├── projects/  # Project management endpoints
│   │   │   │   └── auth/      # Authentication endpoints
│   │   │   ├── core/          # Core business logic
│   │   │   │   ├── ai/        # AI service layer (Vertex AI, GitHub Models)
│   │   │   │   ├── documents/ # Document processing and RAG
│   │   │   │   ├── projects/  # Project management logic
│   │   │   │   └── validation/# Output validation and safety
│   │   │   ├── models/        # Pydantic models
│   │   │   │   ├── projects/  # Project and layout models
│   │   │   │   ├── documents/ # Document and RAG models
│   │   │   │   └── ai/        # AI request/response models
│   │   │   ├── services/      # Service layer
│   │   │   │   ├── ai_service.py        # AI orchestration
│   │   │   │   ├── document_service.py  # Document processing
│   │   │   │   ├── project_service.py   # Project management
│   │   │   │   └── rag_service.py       # RAG generation and querying
│   │   │   ├── documents/     # Document processing engine
│   │   │   │   ├── parsers/   # DWG/DXF/IFC/PDF parsers
│   │   │   │   ├── extractors/# Content extraction logic
│   │   │   │   ├── embedding/ # Vector embedding generation
│   │   │   │   └── validation/# Document validation engine
│   │   │   ├── ai/            # AI integration modules
│   │   │   │   ├── vertex/    # Vertex AI (Gemini-2.5-Flash-Lite)
│   │   │   │   ├── github/    # GitHub Models (GPT-4.1)
│   │   │   │   ├── prompts/   # Prompt engineering
│   │   │   │   └── validation/# AI output validation
│   │   │   ├── utils/         # Utilities
│   │   │   └── __init__.py
│   │   ├── deployment/        # Cloud deployment configs
│   │   │   ├── docker/        # Docker configurations
│   │   │   ├── kubernetes/    # K8s deployment files
│   │   │   ├── terraform/     # Infrastructure as code
│   │   │   └── scripts/       # Deployment scripts
│   │   ├── tests/             # Python tests
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── revit-plugin/          # Revit Integration Module
│   │   ├── Commands/          # Revit command classes
│   │   ├── Services/          # Business logic services  
│   │   ├── Models/            # Data models
│   │   ├── UI/                # Ribbon and dialog components
│   │   ├── Utils/             # Utility classes
│   │   ├── ArchBuilderRevit.csproj
│   │   ├── ArchBuilderRevit.addin
│   │   └── Program.cs
│   └── shared/                # Shared libraries and utilities
│       ├── FileFormats/       # DWG/DXF/IFC format handlers
│       ├── ProjectAnalysis/   # Existing Revit project analysis engines
│       ├── DataContracts/     # Shared data models
│       └── Security/          # Encryption and security utilities
├── configs/
│   ├── building-codes/        # International building codes and regulations
│   │   ├── documents/        # Uploaded PDF/text regulations
│   │   │   ├── turkey/       # Turkish building documents
│   │   │   │   ├── pdfs/     # Original PDF files
│   │   │   │   ├── extracted/# Processed text content
│   │   │   │   └── metadata/ # Document metadata and versions
│   │   │   ├── usa/          # US building documents  
│   │   │   ├── europe/       # European building documents
│   │   │   ├── uk/           # British building documents
│   │   │   ├── canada/       # Canadian building documents
│   │   │   ├── australia/    # Australian building documents
│   │   │   ├── asia-pacific/ # Regional Asian documents
│   │   │   └── custom/       # Custom regional documents
│   │   ├── processed/        # AI-processed knowledge base
│   │   │   ├── embeddings/   # Vector embeddings of regulations
│   │   │   ├── summaries/    # AI-generated summaries
│   │   │   ├── rules/        # Extracted rules in JSON format
│   │   │   └── indexes/      # Search indexes
│   │   └── templates/        # Document processing templates
│   ├── ai-prompts/           # Localized AI prompts with regulation context
│   │   ├── en/               # English prompts
│   │   ├── tr/               # Turkish prompts
│   │   ├── es/               # Spanish prompts
│   │   ├── fr/               # French prompts
│   │   ├── de/               # German prompts
│   │   └── templates/        # Dynamic prompt templates with regulation injection
│   ├── measurements/         # Regional measurement systems
│   │   ├── metric/           # Metric system (m², °C)
│   │   ├── imperial/         # Imperial system (ft², °F)
│   │   └── mixed/            # Mixed systems by region
│   └── app-settings/         # Regional app configurations
├── tests/                     # Integration tests
├── docs/                      # Documentation
└── scripts/                   # Build and deployment scripts
```


## File Structure & Key Directories

- `.github/instructions/`: Role-specific development guidelines
- `src/desktop-app/`: Windows desktop application with Apple-vari UI
- `src/cloud-server/`: Python FastAPI backend for AI processing
- `src/revit-plugin/`: C# Revit integration module
- `src/shared/`: Shared libraries and file format handlers
- `configs/building-codes/`: International building codes and regional regulations

## Critical AI Safety & Validation Principles

### Human-in-the-Loop Validation
- **Never trust AI outputs without validation**: All AI-generated content must pass through validation layers
- **Mandatory human review**: AI outputs should be flagged for architect review before execution
- **Uncertainty handling**: When AI confidence is low, always fall back to rule-based systems
- **Error transparency**: Log all AI failures and validation errors for analysis

### Natural Language Ambiguity Management
- **Prompt engineering**: Use structured prompts to minimize ambiguity
- **Clarification requests**: When input is unclear, ask users for more specific details
- **Example-driven input**: Encourage users to provide measurements and concrete examples
- **Fallback to defaults**: Use sensible defaults when information is missing

### Global Regulatory Compliance
- **AI limitations acknowledged**: AI models may not fully understand all international building codes
- **Pre-validation required**: All layouts must pass through automated regional compliance checks
- **Expert oversight**: Complex compliance issues require human architect review  
- **Conservative approach**: When in doubt, apply most restrictive interpretations
- **Regional expertise**: System provides contact information for local building code experts

## Testing Strategy

- **Unit tests**: 70% minimum coverage
- **Integration tests**: 20% for component interaction
- **E2E tests**: 10% for full workflow validation
- **BDD scenarios**: Use Gherkin for architectural requirements
- **Performance targets**: API responses <500ms, room generation <30s, floor generation <5min, building generation 25min-5 hours

## Domain-Specific Knowledge

### Global Building Code Integration
- Multi-regional compliance validation (North America, Europe, Asia-Pacific, Middle East)
- Pluggable building code framework (IBC, Eurocode, National codes)
- Cultural adaptation and localization support
- International measurement system handling (metric/imperial/mixed)

### Revit Families & Furniture
- Family metadata parsing for AI recommendations
- Collision detection using BoundingBoxIntersectsFilter
- Context-aware furniture placement

### Genetic Algorithm Optimization
- Multi-objective optimization for layout efficiency
- Space Syntax analysis for circulation optimization
- Environmental factor integration (solar, wind analysis)

## Common Commands & Workflows

### Building & Running
```powershell
# Build Desktop Application
dotnet build src/desktop-app/ArchBuilder.sln

# Start Cloud Server
cd src/cloud-server
python -m uvicorn main:app --reload

# Build and Install Revit plugin
dotnet build src/revit-plugin/ArchBuilderRevit.sln
Copy-Item "bin/Debug/ArchBuilderRevit.dll" "$env:APPDATA\Autodesk\Revit\Addins\2026\"

# Run Desktop Application
cd src/desktop-app
dotnet run
```

### Development Setup
1. Install Visual Studio 2022 with WPF/Windows development workload
2. Install Revit 2026 SDK and reference RevitAPI.dll/RevitAPIUI.dll
3. Configure Python 3.13+ environment with FastAPI
4. Set up Vertex AI and GitHub Models authentication
5. Configure local development database (PostgreSQL/SQLite)

## Error Handling & Logging

- **Structured logging**: Use Serilog (C#) and structlog (Python)
- **Correlation IDs**: Track requests across components
- **Graceful degradation**: Always provide fallbacks
- **User-friendly errors**: Translate technical errors for architects

## Performance Considerations

- Use FilteredElementCollector efficiently for Revit queries
- Implement async/await for AI model calls (expect 10-30s response times)
- Cache family metadata and zoning rules
- Monitor memory usage in long-running operations

## Role-Specific Instructions

Refer to `.github/instructions/` for detailed role-specific guidelines:
- `architect.instructions.md`: System design and ADRs
- `developer.instructions.md`: Coding standards and patterns
- `security.instructions.md`: STRIDE threat modeling
- `qa.instructions.md`: Testing strategies and BDD


---


