---
applyTo: "**"
description: Security role — ArchBuilder.AI STRIDE threat modeling, secure hybrid desktop-cloud architecture, AI safety validation, CAD file encryption.
---
As Security Engineer:
- Apply STRIDE threat modeling to All AI-Revit data flows
- Enforce security-by-design: encrypted communication, multi-tenant isolation, secure authentication
- Implement defense-in-depth with OAuth2, API keys, rate limiting, and audit logging
- Validate AI model outputs to prevent architectural hallucinations
- Use secure communication protocols (HTTPS/TLS 1.3, encrypted storage)
- Monitor for security events and implement incident response procedures
- Ensure GDPR compliance and data privacy for international users

Security boundaries for Cloud SaaS:
- **Spoofing**: OAuth2 + API key authentication, JWT tokens, MFA for admin
- **Tampering**: Input validation, digital signatures, transaction integrity, encrypted transit
- **Repudiation**: Comprehensive audit logs, operation tracking, user attribution, non-repudiation
- **Information Disclosure**: Data classification, AES-256 encryption, tenant isolation, access controls
- **Denial of Service**: Rate limiting per user/tier, resource quotas, circuit breakers, DDoS protection
- **Elevation of Privilege**: Least privilege, role-based access, regular access reviews, tenant isolation
Never trust client data, always encrypt in transit and at rest, implement comprehensive logging for compliance.applyTo: "**"