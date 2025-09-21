# 🏗️ ArchBuilder.AI - AI-Powered Architectural Design Automation

<div align="center">

![ArchBuilder.AI](https://img.shields.io/badge/ArchBuilder.AI-v1.0-brightgreen?style=for-the-badge)
![Progress](https://img.shields.io/badge/Progress-86%25_Complete-blue?style=for-the-badge)

**Revolutionizing architectural design through AI-powered automation with hybrid desktop-cloud architecture**

[![Build Status](https://github.com/ahmetcemkaraca/archbuilder-ai-system/workflows/ArchBuilder.AI%20CI/CD%20Pipeline/badge.svg)](https://github.com/ahmetcemkaraca/archbuilder-ai-system/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![.NET Version](https://img.shields.io/badge/.NET-8.0-blue)](https://dotnet.microsoft.com/)
[![Python Version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![Revit Version](https://img.shields.io/badge/Revit-2026-orange)](https://www.autodesk.com/products/revit/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)](https://fastapi.tiangolo.com/)

</div>

## 🎯 Project Overview

ArchBuilder.AI is a comprehensive Windows desktop application with Apple-vari design that revolutionizes architectural project creation through AI-powered automation. The system employs a "Smart Brain, Dumb Hands" architecture where AI augments architects rather than replacing them.

**Key Innovation**: Hybrid desktop-cloud architecture that processes natural language and file inputs (DWG/DXF, IFC, PDF regulations) to generate step-by-step Revit-compatible architectural projects.

### 🏗️ System Architecture
```
┌─────────────────────────┐    ┌─────────────────────────┐    ┌──────────────────┐
│   ArchBuilder.AI        │────│   Cloud Server          │────│   AI Services    │
│   (Windows Desktop)     │    │  (Python FastAPI)       │    │ Vertex AI & GitHub│
│   - Apple-vari UI       │    │  - Document Processing  │    │ Models            │
│   - File Management     │    │  - RAG Generation       │    │ - Gemini 2.5 Flash│
│   - Revit Integration   │    │  - AI Orchestration     │    │ - GPT-4.1         │
└─────────────────────────┘    └─────────────────────────┘    └──────────────────┘
```

## 🚀 Current Status (86% Complete)

### ✅ **Completed Major Components (19/22)**
- **Cloud Server Infrastructure** - FastAPI, middleware, routing
- **Authentication System** - JWT, OAuth2, user management
- **AI Integration Framework** - OpenAI, Claude, Vertex AI with fallbacks
- **Document Processing System** - Upload, parsing, RAG generation
- **Project Management API** - CRUD operations, management endpoints
- **Billing & Subscription System** - Stripe integration, usage tracking
- **Email & Notification System** - Templates, scheduling, automation
- **Background Task Queue** - Celery/RQ, worker management
- **Security Implementation** - Headers, CORS, rate limiting
- **Testing Framework** - Pytest, coverage, integration tests
- **Database Architecture** - SQLAlchemy models, migrations
- **Regional Localization** - Multi-language, building codes support
- **Performance Optimization** - Caching, async patterns
- **API Validation** - Request/response validation, error handling
- **File Upload System** - Secure upload, validation, storage
- **RAG System** - Vector embeddings, semantic search
- **Logging & Monitoring** - Structured logging, correlation tracking
- **AI Task Management** - Background processing, validation
- **Building Codes Integration** - Regional framework, compliance

### ❌ **Remaining Critical Components (3)**
1. **Desktop Application UI** - WPF Views, Apple-vari design system
2. **Revit Plugin Commands** - AI command implementation, BIM integration
3. **Production Deployment** - Docker containerization, CI/CD pipeline

## 🌟 Key Features

### 🤖 **Multi-AI Integration**
- **OpenAI GPT-4.1** (Primary)
- **Claude 3.5 Sonnet** (Fallback)
- **Vertex AI Gemini-2.5-Flash-Lite** (Secondary)
- Intelligent fallback systems with confidence scoring
- Cost optimization and response caching

### 🌍 **Global Building Code Compliance**
- **Regional Support**: Turkey, USA, Europe, UK, Canada, Australia, Asia-Pacific
- **International Standards**: IBC, Eurocode, National building codes
- **Cultural Adaptation**: Multi-language support (TR, EN, DE, FR, ES, etc.)
- **Measurement Systems**: Metric, Imperial, Mixed systems

### 📄 **Multi-Format Document Processing**
- **CAD Formats**: DWG, DXF, IFC file processing
- **Regulations**: PDF building code parsing with OCR
- **RAG System**: Vector embeddings for intelligent document search
- **Content Extraction**: Structured data from architectural drawings

### 🏗️ **Revit Integration**
- **Native API Integration**: Revit 2026 compatibility
- **BIM Element Creation**: Automated family placement
- **Transaction Management**: Safe Revit operations
- **Project Analysis**: Existing Revit project reverse engineering

### � **Enterprise-Grade Features**
- **Subscription Management**: Stripe billing integration
- **Usage Tracking**: API quotas and rate limiting
- **Security**: GDPR compliance, encryption at rest/transit
- **Audit Trails**: Comprehensive logging and monitoring

## 📁 Project Structure

```
archbuilder.ai/
├── .github/                    # AI coding guidelines & CI/CD
│   ├── instructions/           # 19+ development instruction files
│   ├── workflows/             # GitHub Actions CI/CD pipeline
│   └── copilot-instructions.md # Main AI assistant configuration
├── src/
│   ├── cloud-server/          # Python FastAPI Backend (95% Complete)
│   │   ├── app/               # Core application logic
│   │   ├── services/          # Business logic services
│   │   ├── api/               # REST API endpoints
│   │   └── tests/             # Comprehensive test suite
│   ├── desktop-app/           # Windows WPF Application (30% Complete)
│   │   ├── Views/             # Apple-vari UI components
│   │   ├── ViewModels/        # MVVM pattern implementation
│   │   └── Services/          # Business logic services
│   ├── revit-plugin/          # Revit Integration (40% Complete)
│   │   ├── Commands/          # AI-powered Revit commands
│   │   ├── UI/                # Ribbon and dialog interfaces
│   │   └── Services/          # BIM processing services
│   └── shared/                # Shared libraries and utilities
├── configs/                   # Regional configurations
│   ├── building-codes/        # International building codes
│   ├── ai-prompts/           # Localized AI prompt templates
│   └── app-settings/         # Regional app configurations
├── docs/                      # Comprehensive documentation
└── tests/                     # Integration and e2e tests
```

## 🛠️ Technology Stack

### **Backend (Cloud Server)**
- **Python 3.13+** with FastAPI
- **SQLAlchemy** with PostgreSQL/SQLite
- **Redis** for caching and sessions
- **Celery/RQ** for background tasks
- **Stripe** for billing and subscriptions
- **Structured logging** with correlation tracking

### **Frontend (Desktop Application)**
- **C# .NET 8.0** with WPF
- **MVVM pattern** with dependency injection
- **Apple-vari UI design** for optimal UX
- **HTTP client** for cloud API communication

### **Revit Integration**
- **C# .NET Framework 4.8**
- **Revit API 2026**
- **Transaction-safe operations**
- **Family management** and parameter handling

### **AI & ML**
- **OpenAI GPT-4.1** via official API
- **Claude 3.5 Sonnet** via Anthropic API
- **Vertex AI Gemini** via Google Cloud
- **Vector embeddings** for RAG system
- **Confidence scoring** and validation

## 🚀 Quick Start

### Prerequisites
- **Windows 10/11** (64-bit)
- **Autodesk Revit 2026**
- **.NET 8.0 Runtime**
- **Python 3.13+** (for development)
- **Git** for version control

### Installation (Development)

1. **Clone the repository**
   ```powershell
   git clone https://github.com/ahmetcemkaraca/archbuilder-ai-system.git
   cd archbuilder-ai-system
   ```

2. **Set up Cloud Server**
   ```powershell
   cd src/cloud-server
   pip install -r requirements.txt
   
   # Configure environment variables
   cp .env.example .env
   # Edit .env with your API keys (OpenAI, Claude, Vertex AI)
   ```

3. **Start the Cloud Server**
   ```powershell
   cd src/cloud-server
   python -m uvicorn main:app --reload
   ```

4. **Build Desktop Application**
   ```powershell
   cd src/desktop-app
   dotnet build
   dotnet run
   ```

5. **Build Revit Plugin**
   ```powershell
   cd src/revit-plugin
   dotnet build
   # Copy to Revit add-ins folder
   Copy-Item "bin/Debug/ArchBuilderRevit.dll" "$env:APPDATA\Autodesk\Revit\Addins\2026\"
   ```

### API Configuration

Required environment variables:
```bash
# AI Model APIs
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
GOOGLE_CLOUD_PROJECT=your_vertex_ai_project

# Database
DATABASE_URL=sqlite:///./archbuilder.db

# Security
SECRET_KEY=your_secret_key
STRIPE_SECRET_KEY=your_stripe_key
```

## 📖 Documentation

- [**User Guide**](docs/user-guide.md) - How to use ArchBuilder.AI
- [**Developer Guide**](docs/developer-guide.md) - Development setup and contribution
- [**API Documentation**](docs/api/endpoints.md) - REST API reference
- [**Architecture Guide**](docs/architecture/system-overview.md) - System design patterns
- [**AI Integration**](docs/services/ai-service.md) - AI model integration guide
- [**Security Implementation**](docs/security/security-implementation.md) - Security guidelines

## 🌍 Supported Regions & Building Codes

| Region | Building Codes | Measurement | Language | Status |
|--------|---------------|-------------|----------|---------|
| 🇹🇷 Turkey | İmar Yönetmeliği | Metric | Turkish | ✅ Ready |
| 🇺🇸 USA | IBC, IRC | Imperial | English | ✅ Ready |
| 🇪🇺 Europe | Eurocode | Metric | Multi-language | ✅ Ready |
| 🇬🇧 UK | Building Regulations | Imperial | English | ✅ Ready |
| 🇨🇦 Canada | NBC | Mixed | English/French | ✅ Ready |
| 🇦🇺 Australia | NCC | Metric | English | ✅ Ready |
| 🌏 Asia-Pacific | Regional codes | Metric | Multi-language | 🔄 In Progress |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our coding standards
4. Add tests and documentation
5. Submit a pull request

### Development Workflow
- **Read instruction files** in `.github/instructions/` before coding
- **Follow coding standards** defined in instruction files
- **Add comprehensive tests** for new features
- **Update documentation** for any API changes

## 📊 Progress Tracking

### ✅ Phase 1: Infrastructure (Complete)
- Cloud server foundation with FastAPI
- Authentication and security systems
- Database architecture and migrations
- API framework with validation

### ✅ Phase 2: AI Integration (Complete)
- Multi-AI model integration
- Document processing and RAG system
- Regional building codes framework
- AI output validation and safety

### ✅ Phase 3: Business Logic (Complete)
- Project management system
- Billing and subscription system
- Email and notification system
- Background task processing

### 🔄 Phase 4: User Interfaces (In Progress)
- Desktop application UI/UX (Apple-vari design)
- Revit plugin commands and dialogs
- User workflow optimization

### 📋 Phase 5: Production (Planned)
- Docker containerization
- CI/CD pipeline optimization
- Cloud deployment (AWS/Azure/GCP)
- Performance optimization and monitoring

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- 📧 **Email**: support@archbuilder.ai
- 💬 **Discord**: [Join our community](https://discord.gg/archbuilder-ai)
- 📖 **Documentation**: [docs.archbuilder.ai](https://docs.archbuilder.ai)
- 🐛 **Issues**: [GitHub Issues](https://github.com/ahmetcemkaraca/archbuilder-ai-system/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/ahmetcemkaraca/archbuilder-ai-system/discussions)

## 🎯 Roadmap

### Version 1.0 - MVP (Current - 86% Complete)
- ✅ Cloud server infrastructure with AI integration
- ✅ Comprehensive backend services and APIs
- ✅ Multi-format document processing
- ✅ Regional building codes support
- 🔄 Desktop application UI completion
- 🔄 Revit plugin command implementation
- 📋 Production deployment pipeline

### Version 1.1 - Enhanced Features
- � Visual sketch analysis (GPT-4V integration)
- � Advanced room optimization algorithms
- � MEP (Mechanical, Electrical, Plumbing) system integration
- � Collaborative design features with real-time sync

### Version 2.0 - Enterprise
- 📋 Multi-project management dashboard
- 📋 Advanced analytics and reporting
- 📋 Custom AI model fine-tuning
- 📋 Enterprise deployment tools and SSO integration
- 📋 Advanced clash detection and resolution

---

<div align="center">

**Made with ❤️ and 🤖 AI by the ArchBuilder.AI Team**

[Website](https://archbuilder.ai) • [Documentation](https://docs.archbuilder.ai) • [Community](https://discord.gg/archbuilder-ai) • [LinkedIn](https://linkedin.com/company/archbuilder-ai)

*Empowering architects worldwide through intelligent design automation*

</div>

