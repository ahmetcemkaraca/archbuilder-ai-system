---
applyTo: "**/*.md,src/revit-plugin/**/*.cs,src/cloud-server/**/*.py,src/desktop-app/**/*.cs"
description: Architecture Decision Records — key technology and design decisions with rationale for ArchBuilder.AI.
---

# Architecture Decision Records (ADRs)

## ADR-001: Hybrid Desktop-Cloud Architecture for ArchBuilder.AI

**Date**: 2025-09-14  
**Status**: Accepted  
**Context**: Need for desktop-first user experience with Apple-vari design while leveraging cloud-based AI processing for multi-format CAD analysis and prompt processing.

**Decision**: Hybrid architecture with Windows desktop application as primary interface, cloud-based Python server for AI processing using Vertex AI (Gemini-2.5-Flash-Lite) and GitHub Models (GPT-4.1), integrated with Revit plugin for final output generation.

**Rationale**:
- Enables SaaS monetization model with subscription-based pricing
- Centralized AI model updates and improvements benefit all users
- Reduced client-side resource requirements
- Better scaling and load management
- Centralized analytics and usage tracking
- Cost-effective AI model usage through shared infrastructure

**Consequences**:
- ✅ Sustainable business model with recurring revenue
- ✅ Centralized AI improvements benefit all users
- ✅ Reduced client infrastructure requirements
- ✅ Better analytics and usage insights
- ❌ Network dependency for AI operations
- ❌ Data privacy considerations for sensitive projects
- ❌ Need for robust authentication and security

**Implementation**:
- Cloud-hosted Python FastAPI server with multi-tenant architecture
- Secure API key authentication and rate limiting
- Data encryption in transit and at rest
- Regional deployment for GDPR compliance
- Hybrid mode for sensitive projects (on-premise option)

---

## ADR-002: Secure Cloud API with Authentication and Rate Limiting

**Date**: 2025-09-10  
**Status**: Accepted  
**Context**: Cloud-based monetization requires secure API access with proper authentication and usage tracking.

**Decision**: Use HTTPS REST APIs with API key authentication, rate limiting, and comprehensive security measures.

**Rationale**:
- HTTPS ensures data encryption in transit
- API key authentication enables monetization and usage tracking
- Rate limiting prevents abuse and manages costs
- Standard REST patterns are well-understood and maintainable
- JWT tokens for session management and user identification

**Consequences**:
- ✅ Secure communication over internet
- ✅ Monetization through API usage tracking
- ✅ Protection against abuse and attacks
- ✅ Standard tooling and monitoring
- ❌ More complex authentication flow
- ❌ Network dependency for all operations

**Implementation**:
- FastAPI with OAuth2 + API Key authentication
- HTTPS enforcement with TLS 1.3
- Rate limiting per user/subscription tier
- Request/response encryption and validation
- Comprehensive audit logging

---

## ADR-003: Realistic Performance Targets

**Date**: 2025-01-10  
**Status**: Accepted  
**Context**: Initial targets of <500ms for AI operations were unrealistic.

**Decision**: Establish realistic performance targets based on actual AI processing times.

**Rationale**:
- AI model inference takes 10-30 seconds for complex layouts
- Document OCR can take 1-2 minutes
- Setting realistic expectations improves user experience
- Allows proper progress indicators and user feedback

**New Targets**:
- Simple queries: <2s (project metadata, basic queries)
- AI layout generation: <30s (with progress indicators)
- Document OCR processing: <2min (with progress indicators)
- Building code validation: <10s

**Implementation**:
- Comprehensive progress indicators
- Background processing with WebSocket updates
- User-friendly waiting experiences
- Proper timeout handling and recovery

---

## ADR-004: Multi-Language AI Model Selection

**Date**: 2025-01-10  
**Status**: Accepted  
**Context**: Initial design used fixed AI models without considering language and regional differences.

**Decision**: Implement dynamic AI model selection based on language, region, and document type.

**Rationale**:
- Different AI models have different language capabilities
- Regional building codes require specialized processing
- Cost optimization through appropriate model selection
- Better accuracy for non-English documents

**Selection Criteria**:
- Language: Turkish, English, German, French, Spanish
- Document type: Building codes, technical drawings, user prompts
- Complexity: Simple vs complex architectural tasks
- Cost: Balance between accuracy and cost

**Implementation**:
- ModelSelector service in Python
- Language detection pipeline
- Fallback model hierarchy
- Cost and performance monitoring

---

## ADR-005: Project Versioning and Change Tracking

**Date**: 2025-01-10  
**Status**: Accepted  
**Context**: Need to track all AI operations and enable rollback capabilities.

**Decision**: Implement comprehensive project versioning with AI operation tracking.

**Rationale**:
- Architects need to see evolution of AI suggestions
- Rollback capability for failed AI operations
- Audit trail for regulatory compliance
- Learning from human corrections

**Features**:
- Version created before/after each AI operation
- Element-level change tracking
- Human review and correction tracking
- Export of project evolution timeline
- Rollback to any previous state

**Implementation**:
- ProjectVersionManager in C#
- SQLite database for version storage
- Element snapshot and diff capabilities
- UI for viewing version history

---

## ADR-006: Mandatory Human Review for All AI Outputs

**Date**: 2025-01-10  
**Status**: Accepted  
**Context**: Need to ensure AI outputs are always validated by human architects.

**Decision**: All AI outputs must require human review and explicit approval before execution.

**Rationale**:
- Professional responsibility and liability
- AI models can make errors or misunderstand requirements
- Building code compliance requires human judgment
- Maintains architect control over design decisions

**Implementation**:
- HumanReviewWorkflow service
- ReviewQueue for pending approvals
- Comprehensive validation UI
- Feedback collection for AI improvement
- Audit trail of all human decisions

---

## ADR-007: UX/UI Design for Professional Architects

**Date**: 2025-01-10  
**Status**: Accepted  
**Context**: Need clear UI/UX design guidelines for AI-human collaboration.

**Decision**: Design professional architect-focused interfaces with clear AI collaboration workflows.

**Design Principles**:
- Professional, not consumer-focused design
- Clear progress indicators for 10-30s AI operations
- Intuitive review and approval workflows
- Comprehensive error recovery paths
- Accessibility compliance

**Key Interfaces**:
- AI Layout Generation Dialog
- Progress Indicators with realistic timing
- Layout Review Interface with 3D/2D viewers
- Human Approval Workflow
- Error Recovery and Help Systems

**Implementation**:
- WinForms with professional styling
- Custom progress indicators
- Tabbed interfaces for complex workflows
- Comprehensive help and tips system

---

## ADR-008: Multi-Tenant SaaS Architecture with Subscription Management

**Date**: 2025-09-10  
**Status**: Accepted  
**Context**: Need for scalable monetization model that supports multiple subscription tiers and usage tracking.

**Decision**: Implement multi-tenant SaaS architecture with subscription-based pricing and usage analytics.

**Rationale**:
- Enables scalable business model with predictable revenue
- Different pricing tiers for different user needs
- Usage analytics help optimize AI model costs
- Multi-tenancy enables efficient resource sharing
- Subscription management automates billing and access control

**Features**:
- Subscription tiers: Free, Professional, Enterprise
- Usage-based pricing with monthly quotas
- Real-time usage tracking and billing
- Multi-tenant data isolation
- Automated subscription lifecycle management

**Implementation**:
- FastAPI with multi-tenant database design
- Stripe integration for subscription management
- Redis for usage tracking and rate limiting
- Comprehensive analytics dashboard
- Automated billing and access control

---

## ADR-009: Hybrid Deployment Options for Enterprise Clients

**Date**: 2025-09-10  
**Status**: Accepted  
**Context**: Enterprise clients may require on-premise deployment for sensitive architectural projects.

**Decision**: Provide hybrid deployment options including on-premise installations for enterprise clients.

**Rationale**:
- Addresses data privacy concerns for sensitive projects
- Enables enterprise sales and higher revenue per client
- Maintains cloud benefits while offering flexibility
- Compliance with international data protection laws

**Deployment Options**:
- Cloud SaaS (default for most users)
- Private Cloud (dedicated instances)
- On-Premise (enterprise installations)
- Hybrid (cloud + on-premise for different projects)

**Implementation**:
- Containerized deployment with Docker/Kubernetes
- Automated on-premise installation scripts
- Central license and update management
- Unified monitoring across all deployment types

---

## Future ADRs to Consider

1. **Data Privacy and GDPR Compliance**: Enhanced data handling for international compliance
2. **AI Model Cost Optimization**: Dynamic model selection based on subscription tier
3. **Real-time Collaboration**: Multi-user collaboration on architectural projects
4. **Mobile and Web Interfaces**: Expanding beyond Revit to other platforms
5. **Enterprise SSO Integration**: Active Directory and SAML integration
6. **API Marketplace**: Third-party integration marketplace
