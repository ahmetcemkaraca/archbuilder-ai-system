"""
Architectural Prompt Engineering Engine for ArchBuilder.AI
Implements structured prompt generation for different AI models and architectural tasks
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from ....core.logging import get_logger

logger = get_logger(__name__)


class PromptType(str, Enum):
    """Types of architectural prompts"""
    LAYOUT_GENERATION = "layout_generation"
    ROOM_DESIGN = "room_design"
    EXISTING_PROJECT_ANALYSIS = "existing_project_analysis"
    BUILDING_CODE_COMPLIANCE = "building_code_compliance"
    CLASH_DETECTION = "clash_detection"
    SPACE_OPTIMIZATION = "space_optimization"
    SUSTAINABILITY_ANALYSIS = "sustainability_analysis"


class ArchitecturalPromptEngine:
    """
    Structured prompt engineering for architectural AI tasks
    Optimized for Vertex AI and GitHub Models with multi-language support
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Language-specific prompt templates
        self.language_templates = {
            "en": {
                "system": "You are an expert architectural AI assistant for ArchBuilder.AI. Provide detailed, accurate, and building-code-compliant architectural solutions.",
                "layout_intro": "Design a comprehensive architectural layout based on the following requirements:",
                "analysis_intro": "Analyze the following architectural project for improvements and compliance:",
                "compliance_intro": "Check the following design for building code compliance:",
            },
            "tr": {
                "system": "ArchBuilder.AI için uzman mimari AI asistanısınız. Detaylı, doğru ve yapı yönetmeliklerine uygun mimari çözümler sağlayın.",
                "layout_intro": "Aşağıdaki gereksinimlere göre kapsamlı bir mimari plan tasarlayın:",
                "analysis_intro": "Aşağıdaki mimari projeyi geliştirmeler ve uyumluluk açısından analiz edin:",
                "compliance_intro": "Aşağıdaki tasarımı yapı yönetmeliği uyumluluğu açısından kontrol edin:",
            },
            "de": {
                "system": "Sie sind ein Experte für architektonische KI-Assistenz für ArchBuilder.AI. Bieten Sie detaillierte, genaue und bauordnungskonforme architektonische Lösungen.",
                "layout_intro": "Entwerfen Sie ein umfassendes architektonisches Layout basierend auf den folgenden Anforderungen:",
                "analysis_intro": "Analysieren Sie das folgende architektonische Projekt auf Verbesserungen und Compliance:",
                "compliance_intro": "Überprüfen Sie das folgende Design auf Bauordnungskonformität:",
            },
            "fr": {
                "system": "Vous êtes un assistant IA architectural expert pour ArchBuilder.AI. Fournissez des solutions architecturales détaillées, précises et conformes aux codes du bâtiment.",
                "layout_intro": "Concevez une disposition architecturale complète basée sur les exigences suivantes:",
                "analysis_intro": "Analysez le projet architectural suivant pour les améliorations et la conformité:",
                "compliance_intro": "Vérifiez la conception suivante pour la conformité au code du bâtiment:",
            },
            "es": {
                "system": "Eres un asistente de IA arquitectónico experto para ArchBuilder.AI. Proporciona soluciones arquitectónicas detalladas, precisas y que cumplan con los códigos de construcción.",
                "layout_intro": "Diseña un diseño arquitectónico integral basado en los siguientes requisitos:",
                "analysis_intro": "Analiza el siguiente proyecto arquitectónico para mejoras y cumplimiento:",
                "compliance_intro": "Verifica el siguiente diseño para el cumplimiento del código de construcción:",
            }
        }
    
    async def create_prompt(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        provider: str = "github_models",
        language: str = "en"
    ) -> str:
        """
        Create structured prompt for AI processing
        
        Args:
            user_prompt: User's natural language input
            context: Additional context for prompt generation
            provider: AI provider (vertex_ai or github_models)
            language: Output language (en, tr, de, fr, es)
            
        Returns:
            Structured prompt optimized for the AI provider
        """
        
        self.logger.info(
            "Creating structured prompt",
            provider=provider,
            language=language,
            prompt_length=len(user_prompt)
        )
        
        # Get language-specific templates
        templates = self.language_templates.get(language, self.language_templates["en"])
        
        # Determine prompt type from context or user input
        prompt_type = self._determine_prompt_type(user_prompt, context)
        
        if prompt_type == PromptType.LAYOUT_GENERATION:
            return self._create_layout_prompt(user_prompt, context, templates, provider)
        elif prompt_type == PromptType.EXISTING_PROJECT_ANALYSIS:
            return self._create_analysis_prompt(user_prompt, context, templates, provider)
        elif prompt_type == PromptType.BUILDING_CODE_COMPLIANCE:
            return self._create_compliance_prompt(user_prompt, context, templates, provider)
        else:
            return self._create_generic_prompt(user_prompt, context, templates, provider)
    
    def create_layout_prompt(self, request: Any) -> str:
        """Create layout generation prompt"""
        
        language = getattr(request, 'language', 'en')
        templates = self.language_templates.get(language, self.language_templates["en"])
        
        return self._create_layout_prompt(
            user_prompt=getattr(request, 'user_prompt', ''),
            context=getattr(request, 'context', {}),
            templates=templates,
            provider="github_models"
        )
    
    def create_room_prompt(self, request: Any) -> str:
        """Create room design prompt"""
        
        language = getattr(request, 'language', 'en')
        templates = self.language_templates.get(language, self.language_templates["en"])
        
        room_type = getattr(request, 'room_type', 'unknown')
        area_m2 = getattr(request, 'area_m2', 0)
        requirements = getattr(request, 'requirements', [])
        
        prompt = f"""
        {templates['system']}

        Design a detailed {room_type} with the following specifications:
        - Area: {area_m2}m²
        - Requirements: {', '.join(requirements)}

        Provide your response in structured JSON format with:
        - Dimensions and layout
        - Furniture placement with exact positions
        - Lighting design
        - Material specifications
        - Compliance notes
        - Cost estimates

        Ensure the design is functional, accessible, and code-compliant.
        """
        
        return prompt.strip()
    
    def create_command_prompt(self, request: Any) -> str:
        """Create command processing prompt"""
        
        command_type = getattr(request, 'command_type', 'general')
        user_prompt = getattr(request, 'user_prompt', '')
        language = getattr(request, 'language', 'en')
        context = getattr(request, 'context', {})
        
        templates = self.language_templates.get(language, self.language_templates["en"])
        
        return self._create_generic_prompt(
            user_prompt=user_prompt,
            context=context,
            templates=templates,
            provider="github_models"
        )
    
    def create_project_analysis_prompt(self, project_data: Dict[str, Any]) -> str:
        """Create existing project analysis prompt"""
        
        prompt = f"""
        As an expert BIM analyst and architectural consultant, perform a comprehensive analysis of the following Revit project.

        Project Information:
        - Total Elements: {project_data.get('total_elements', 'Unknown')}
        - Project Type: {project_data.get('project_type', 'Unknown')}
        - Total Area: {project_data.get('total_area_m2', 'Unknown')}m²

        Element Breakdown:
        {self._format_element_breakdown(project_data.get('elements', {}))}

        Please provide a comprehensive analysis including:
        1. Project health assessment (overall score 0-1)
        2. Performance issues and optimization opportunities
        3. Design improvement recommendations
        4. Clash detection and coordination issues
        5. Building code compliance assessment
        6. Space utilization analysis
        7. Sustainability assessment
        8. Priority action items with timelines

        Format your response as structured JSON for easy parsing and implementation.
        Focus on actionable insights that will improve project quality and performance.
        """
        
        return prompt.strip()
    
    def _determine_prompt_type(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> PromptType:
        """Determine the type of prompt based on user input and context"""
        
        prompt_lower = user_prompt.lower()
        
        # Check context first
        if context:
            analysis_type = context.get("analysis_type", "")
            if analysis_type == "existing_project_analysis":
                return PromptType.EXISTING_PROJECT_ANALYSIS
            elif analysis_type == "building_code_compliance":
                return PromptType.BUILDING_CODE_COMPLIANCE
        
        # Analyze user prompt keywords
        if any(keyword in prompt_lower for keyword in ["layout", "plan", "design", "create", "generate"]):
            return PromptType.LAYOUT_GENERATION
        elif any(keyword in prompt_lower for keyword in ["analyze", "analysis", "improve", "optimize"]):
            return PromptType.EXISTING_PROJECT_ANALYSIS
        elif any(keyword in prompt_lower for keyword in ["compliance", "code", "regulation", "legal"]):
            return PromptType.BUILDING_CODE_COMPLIANCE
        elif any(keyword in prompt_lower for keyword in ["clash", "conflict", "interference"]):
            return PromptType.CLASH_DETECTION
        elif any(keyword in prompt_lower for keyword in ["room", "space", "bedroom", "kitchen", "bathroom"]):
            return PromptType.ROOM_DESIGN
        else:
            return PromptType.LAYOUT_GENERATION  # Default
    
    def _create_layout_prompt(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]],
        templates: Dict[str, str],
        provider: str
    ) -> str:
        """Create layout generation prompt"""
        
        # Extract context information
        total_area = context.get("total_area_m2", "not specified") if context else "not specified"
        rooms = context.get("rooms", []) if context else []
        region = context.get("region", "international") if context else "international"
        building_type = context.get("building_type", "residential") if context else "residential"
        
        # Build room requirements string
        room_requirements = ""
        if rooms:
            room_requirements = "\nRoom Requirements:\n"
            for room in rooms:
                room_requirements += f"- {room.get('type', 'Unknown')}: {room.get('area_m2', 'TBD')}m²\n"
        
        prompt = f"""
        {templates['system']}

        {templates['layout_intro']}

        User Request: {user_prompt}

        Project Context:
        - Total Area: {total_area}m²
        - Building Type: {building_type}
        - Region: {region}
        {room_requirements}

        Please provide a comprehensive architectural solution in structured JSON format including:

        1. LAYOUT DESIGN:
        - Detailed room layout with exact dimensions and positions
        - Wall specifications with start/end points and properties
        - Door and window placements with sizes and types
        - Circulation paths and accessibility routes

        2. BUILDING SYSTEMS:
        - HVAC system design and zoning
        - Electrical layout with circuits and loads
        - Plumbing layout with fixture positions
        - Fire safety systems and egress routes

        3. COMPLIANCE ANALYSIS:
        - Building code compliance check for {region}
        - Accessibility compliance assessment
        - Fire safety and egress requirements
        - Energy efficiency considerations

        4. OPTIMIZATION:
        - Space utilization efficiency
        - Natural lighting optimization
        - Circulation efficiency analysis
        - Cost optimization strategies

        5. IMPLEMENTATION:
        - Construction phase planning
        - Material specifications
        - Cost estimates by category
        - Timeline and dependencies

        Ensure all dimensions are in metric units (mm for precise measurements, m for general areas).
        All designs must comply with international building standards and be accessible.
        Provide confidence scores and highlight areas requiring human expert review.
        """
        
        return prompt.strip()
    
    def _create_analysis_prompt(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]],
        templates: Dict[str, str],
        provider: str
    ) -> str:
        """Create project analysis prompt"""
        
        project_data = context.get("project_data", {}) if context else {}
        
        prompt = f"""
        {templates['system']}

        {templates['analysis_intro']}

        User Request: {user_prompt}

        Project Data to Analyze:
        {self._format_project_data(project_data)}

        Please provide a comprehensive analysis including:

        1. PROJECT HEALTH ASSESSMENT:
        - Overall project score (0.0-1.0)
        - Model complexity assessment
        - Performance metrics and bottlenecks
        - Quality indicators

        2. DESIGN IMPROVEMENTS:
        - Spatial optimization opportunities
        - Functional improvements
        - Aesthetic enhancements
        - User experience improvements

        3. PERFORMANCE OPTIMIZATION:
        - BIM model optimization suggestions
        - File size and performance improvements
        - Workflow efficiency enhancements
        - Collaboration improvements

        4. COMPLIANCE REVIEW:
        - Building code compliance issues
        - Accessibility compliance gaps
        - Safety requirement violations
        - Required approvals and permits

        5. TECHNICAL ISSUES:
        - Clash detection and coordination problems
        - Structural integrity concerns
        - MEP system conflicts
        - Construction feasibility issues

        6. SUSTAINABILITY ASSESSMENT:
        - Energy efficiency opportunities
        - Sustainable material recommendations
        - Environmental impact analysis
        - LEED/BREEAM potential

        Provide actionable recommendations with priority levels and implementation timelines.
        """
        
        return prompt.strip()
    
    def _create_compliance_prompt(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]],
        templates: Dict[str, str],
        provider: str
    ) -> str:
        """Create building code compliance prompt"""
        
        region = context.get("region", "international") if context else "international"
        building_codes = context.get("building_codes", []) if context else []
        
        prompt = f"""
        {templates['system']}

        {templates['compliance_intro']}

        User Request: {user_prompt}

        Compliance Context:
        - Region: {region}
        - Applicable Codes: {', '.join(building_codes) if building_codes else 'Standard building codes'}

        Please perform a comprehensive compliance check including:

        1. BUILDING CODE COMPLIANCE:
        - Zoning compliance
        - Setback requirements
        - Height restrictions
        - Floor area ratios

        2. ACCESSIBILITY COMPLIANCE:
        - ADA/universal design compliance
        - Accessible routes and entrances
        - Accessible restroom facilities
        - Elevator and stair requirements

        3. FIRE SAFETY COMPLIANCE:
        - Egress requirements
        - Fire separation ratings
        - Sprinkler system requirements
        - Emergency lighting and exits

        4. STRUCTURAL COMPLIANCE:
        - Load requirements
        - Seismic design standards
        - Wind load requirements
        - Foundation requirements

        5. MEP COMPLIANCE:
        - Electrical code compliance
        - Plumbing code requirements
        - HVAC standards
        - Energy code compliance

        Provide detailed compliance analysis with violation identification, severity assessment, and resolution recommendations.
        Include required permits, approvals, and inspection requirements.
        """
        
        return prompt.strip()
    
    def _create_generic_prompt(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]],
        templates: Dict[str, str],
        provider: str
    ) -> str:
        """Create generic architectural prompt"""
        
        prompt = f"""
        {templates['system']}

        Please address the following architectural request:

        {user_prompt}

        Context: {context if context else 'None provided'}

        Provide a comprehensive response that includes:
        - Detailed analysis of the request
        - Professional architectural recommendations
        - Building code and compliance considerations
        - Implementation guidance
        - Cost and timeline estimates where applicable

        Format your response in clear, structured sections for easy understanding and implementation.
        """
        
        return prompt.strip()
    
    def _format_project_data(self, project_data: Dict[str, Any]) -> str:
        """Format project data for prompt inclusion"""
        
        if not project_data:
            return "No project data provided"
        
        formatted = []
        
        if "total_elements" in project_data:
            formatted.append(f"Total Elements: {project_data['total_elements']}")
        
        if "total_area_m2" in project_data:
            formatted.append(f"Total Area: {project_data['total_area_m2']}m²")
        
        if "elements" in project_data:
            formatted.append("Element Breakdown:")
            elements = project_data["elements"]
            for category, count in elements.items():
                formatted.append(f"  - {category}: {count}")
        
        return "\n".join(formatted)
    
    def _format_element_breakdown(self, elements: Dict[str, Any]) -> str:
        """Format element breakdown for analysis prompts"""
        
        if not elements:
            return "No element data available"
        
        formatted = []
        for category, count in elements.items():
            formatted.append(f"- {category}: {count}")
        
        return "\n".join(formatted)