# Revit AutoPlan - AI-Powered Architectural Design Automation

<div align="center">

![Revit AutoPlan Logo](docs/images/logo.png)

**Revolutionizing architectural design through AI-powered automation in Autodesk Revit**

[![Build Status](https://github.com/revitautoplan/revit-autoplan/workflows/CI/badge.svg)](https://github.com/revitautoplan/revit-autoplan/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![.NET Version](https://img.shields.io/badge/.NET-4.8-blue)](https://dotnet.microsoft.com/)
[![Python Version](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![Revit Version](https://img.shields.io/badge/Revit-2026-orange)](https://www.autodesk.com/products/revit/)

</div>

## 🎯 Project Overview

Revit AutoPlan is a hybrid AI-powered architectural design automation system that integrates Autodesk Revit with artificial intelligence. Following a "Smart Brain, Dumb Hands" architecture, the system combines:

- **C# Revit Plugin** ("Hands") - Executes validated commands in Revit
- **Python MCP Server** ("Brain") - AI processing and business logic  
- **Multi-AI Integration** - OpenAI GPT-4, Claude 3.5 Sonnet, Gemini Pro
- **Global Compliance** - International building codes and regional regulations

## 🚀 Key Features

### 🤖 AI-Powered Design
- Natural language to architectural layouts
- Multi-model AI integration with fallback systems
- Human-in-the-loop validation workflows
- Confidence scoring and uncertainty handling

### 🌍 Global Compliance
- International building code validation
- Regional measurement systems (metric/imperial)
- Cultural design preferences
- Multi-language support (TR, EN, DE, FR, ES, etc.)

### 🏗️ Revit Integration
- Native Revit API integration
- Automatic BIM element creation
- Family management and parameter handling
- Transaction-safe operations

### 📊 Enterprise Features
- Comprehensive audit trails
- Performance monitoring
- Error handling and recovery
- Multi-user collaboration support

## 🏗️ System Architecture

```
┌─────────────────┐    ┌────────────────────┐    ┌──────────────────┐
│   Revit Plugin  │────│  Python MCP Server │────│   AI Models      │
│   ("Hands")     │    │     ("Brain")      │    │  (OpenAI/Claude) │
│   C# .NET       │    │   FastAPI/MCP      │    │                  │
└─────────────────┘    └────────────────────┘    └──────────────────┘
         │                        │                        │
         │                        ▼                        │
         │              ┌─────────────────┐                │
         │              │   SQLite DB     │                │
         │              │  (Project Data) │                │
         │              └─────────────────┘                │
         │                                                 │
         └─────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
revit-autoplan/
├── .github/                    # GitHub workflows and instructions
├── src/
│   ├── revit-plugin/          # C# Revit Add-in
│   ├── mcp-server/            # Python FastAPI backend
│   └── ai-models/             # C# AI algorithms
├── configs/                   # Configuration files
│   ├── building-codes/        # International regulations
│   ├── ai-prompts/           # Localized AI prompts
│   └── app-settings/         # Application configurations
├── tests/                     # Test suites
├── docs/                      # Documentation
└── scripts/                   # Build and deployment scripts
```

## 🛠️ Technology Stack

### Backend
- **Python 3.13+** with FastAPI
- **MCP Protocol** for AI communication
- **SQLAlchemy** with SQLite/PostgreSQL
- **Redis** for caching
- **Structured logging** with Structlog

### Frontend/Plugin
- **C# .NET Framework 4.8**
- **Revit API 2026**
- **WPF** for user interfaces
- **Serilog** for logging
- **Polly** for resilience

### AI Integration
- **OpenAI GPT-4** (primary)
- **Claude 3.5 Sonnet** (fallback)
- **Gemini Pro** (secondary fallback)
- **ML.NET** for local algorithms

## 🚀 Quick Start

### Prerequisites
- Autodesk Revit 2026
- .NET Framework 4.8
- Python 3.13+
- Redis server
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/revitautoplan/revit-autoplan.git
   cd revit-autoplan
   ```

2. **Set up Python environment**
   ```bash
   cd src/mcp-server
   pip install poetry
   poetry install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Build C# components**
   ```bash
   cd src/revit-plugin
   dotnet build
   ```

5. **Install Revit add-in**
   ```bash
   # Copy add-in files to Revit
   scripts/install-revit-addin.ps1
   ```

6. **Start the MCP server**
   ```bash
   cd src/mcp-server
   poetry run uvicorn main:app --reload
   ```

7. **Open Revit** and find the AutoPlan tab in the ribbon

## 📖 Documentation

- [**User Guide**](docs/user-guide.md) - How to use Revit AutoPlan
- [**Developer Guide**](docs/developer-guide.md) - Development setup and contribution
- [**API Documentation**](docs/api.md) - REST API and MCP protocol reference
- [**Architecture Guide**](docs/architecture.md) - System design and patterns
- [**Building Codes**](docs/building-codes.md) - Supported international regulations

## 🌍 Supported Regions

| Region | Building Codes | Measurement | Language |
|--------|---------------|-------------|----------|
| 🇹🇷 Turkey | İmar Yönetmeliği | Metric | Turkish |
| 🇺🇸 USA | IBC, IRC | Imperial | English |
| 🇪🇺 Europe | Eurocode | Metric | Multi-language |
| 🇬🇧 UK | Building Regulations | Imperial | English |
| 🇨🇦 Canada | NBC | Mixed | English/French |
| 🇦🇺 Australia | NCC | Metric | English |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@revitautoplan.com
- 💬 Discord: [Join our community](https://discord.gg/revitautoplan)
- 📖 Documentation: [docs.revitautoplan.com](https://docs.revitautoplan.com)
- 🐛 Issues: [GitHub Issues](https://github.com/revitautoplan/revit-autoplan/issues)

## 🎯 Roadmap

### Version 1.0 - MVP (Current)
- ✅ Basic AI layout generation
- ✅ Turkish building code compliance
- ✅ Revit plugin with ribbon UI
- ✅ Multi-AI model integration

### Version 1.1 - Enhanced Features
- 🔄 Visual sketch analysis (GPT-4V)
- 🔄 Advanced room optimization
- 🔄 MEP system integration
- 🔄 Collaborative design features

### Version 2.0 - Enterprise
- 📋 Multi-project management
- 📋 Advanced analytics
- 📋 Custom AI model training
- 📋 Enterprise deployment tools

---

<div align="center">

**Made with ❤️ by the RevitAutoPlan Team**

[Website](https://revitautoplan.com) • [Documentation](https://docs.revitautoplan.com) • [Community](https://discord.gg/revitautoplan)

</div>

