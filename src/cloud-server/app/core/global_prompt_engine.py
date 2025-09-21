"""
Global AI Prompt Template Engine
Multi-regional, multi-language AI prompt generation with building code integration.

This module generates culturally-appropriate and regionally-compliant AI prompts
for ArchBuilder.AI, supporting different AI models and international building codes.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
import structlog
from jinja2 import Environment, FileSystemLoader, Template

from .localization import LocalizationService, SupportedRegion, SupportedLanguage
from .measurement_converter import RegionalMeasurementConverter, MeasurementSystem

logger = structlog.get_logger(__name__)


class AIModelType(str, Enum):
    """Supported AI model types with different prompt optimization strategies."""
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    CLAUDE_SONNET = "claude_sonnet"
    CLAUDE_HAIKU = "claude_haiku"
    GEMINI_PRO = "gemini_pro"
    GEMINI_FLASH = "gemini_flash"


class PromptType(str, Enum):
    """Different types of AI prompts for various architectural tasks."""
    LAYOUT_GENERATION = "layout_generation"
    ROOM_PLANNING = "room_planning"
    COMPLIANCE_CHECK = "compliance_check"
    DESIGN_OPTIMIZATION = "design_optimization"
    CULTURAL_ADAPTATION = "cultural_adaptation"
    COST_ESTIMATION = "cost_estimation"


@dataclass
class AIPromptRequest:
    """Request data for AI prompt generation."""
    building_type: str = "residential"
    total_area_m2: float = 100.0
    floor_count: int = 1
    room_requirements: List[Dict[str, Any]] = field(default_factory=list)
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    budget_range: Optional[str] = None
    special_requirements: List[str] = field(default_factory=list)
    accessibility_required: bool = False
    energy_efficiency_target: str = "standard"
    user_prompt: str = ""


@dataclass
class RegionalPromptContext:
    """Context for regional prompt generation."""
    region: SupportedRegion
    country: str
    locale: str
    building_codes: List[str]
    cultural_preferences: Dict[str, Any]
    measurement_system: MeasurementSystem
    climate_zone: str = "temperate"
    seismic_zone: Optional[str] = None


class GlobalPromptTemplateEngine:
    """
    Advanced AI prompt template engine with multi-regional support.
    
    Generates optimized prompts for different AI models while incorporating
    regional building codes, cultural preferences, and measurement systems.
    """
    
    def __init__(self, 
                 region: str, 
                 country: str, 
                 locale: str,
                 localization_service: Optional[LocalizationService] = None,
                 configs_path: Optional[Path] = None):
        """
        Initialize global prompt template engine.
        
        Args:
            region: Geographic region
            country: Country code
            locale: Locale string (e.g., "en-US", "tr-TR")
            localization_service: Optional localization service instance
            configs_path: Path to configuration files
        """
        self.region = region
        self.country = country
        self.locale = locale
        
        self.localization = localization_service or LocalizationService(configs_path)
        self.measurement_converter = RegionalMeasurementConverter(region)
        self.configs_path = configs_path or Path(__file__).parent.parent.parent.parent / "configs"
        
        # Initialize Jinja2 template environment
        template_paths = [
            self.configs_path / "ai-prompts" / "templates",
            self.configs_path / "ai-prompts" / locale.split('-')[0]  # Language-specific templates
        ]
        
        self.jinja_env = Environment(
            loader=FileSystemLoader([str(p) for p in template_paths if p.exists()]),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Load model-specific configurations
        self.model_configs: Dict[AIModelType, Dict[str, Any]] = {}
        self.prompt_templates: Dict[PromptType, Dict[str, Template]] = {}
        
    async def initialize(self):
        """Initialize the prompt template engine."""
        logger.info("Initializing global prompt template engine")
        
        try:
            await asyncio.gather(
                self._load_model_configurations(),
                self._load_prompt_templates(),
                self.localization.initialize()
            )
            logger.info("Global prompt template engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize prompt template engine: {e}")
            raise
    
    async def generate_prompt(self, 
                            model_type: AIModelType,
                            prompt_type: PromptType,
                            request_data: AIPromptRequest) -> str:
        """
        Generate optimized AI prompt for specific model and region.
        
        Args:
            model_type: Target AI model type
            prompt_type: Type of prompt to generate
            request_data: Request data for prompt generation
            
        Returns:
            Generated prompt string optimized for the model and region
        """
        try:
            # Get regional context
            regional_context = await self._build_regional_context()
            
            # Get model-specific configuration
            model_config = self.model_configs.get(model_type, {})
            
            # Prepare template variables
            template_vars = await self._prepare_template_variables(
                request_data, 
                regional_context, 
                model_config
            )
            
            # Generate prompt based on model type
            if model_type in [AIModelType.OPENAI_GPT4, AIModelType.OPENAI_GPT35]:
                return await self._generate_openai_prompt(prompt_type, template_vars)
            elif model_type in [AIModelType.CLAUDE_SONNET, AIModelType.CLAUDE_HAIKU]:
                return await self._generate_claude_prompt(prompt_type, template_vars)
            elif model_type in [AIModelType.GEMINI_PRO, AIModelType.GEMINI_FLASH]:
                return await self._generate_gemini_prompt(prompt_type, template_vars)
            else:
                # Fallback to generic prompt
                return await self._generate_generic_prompt(prompt_type, template_vars)
                
        except Exception as e:
            logger.error(f"Failed to generate prompt: {e}")
            raise
    
    async def _build_regional_context(self) -> RegionalPromptContext:
        """Build regional context for prompt generation."""
        region_enum = SupportedRegion(self.region)
        
        # Get regional building codes
        building_codes_data = self.localization.get_building_codes(region_enum)
        
        # Get cultural preferences
        cultural_prefs = self.localization.get_cultural_preferences(region_enum)
        
        # Convert cultural preferences to dict
        cultural_dict = {
            "privacy_level": cultural_prefs.privacy_level,
            "family_structure": cultural_prefs.family_structure,
            "entertainment_style": cultural_prefs.entertainment_style,
            "outdoor_connection": cultural_prefs.outdoor_connection,
            "religious_considerations": cultural_prefs.religious_considerations,
            "dining_traditions": cultural_prefs.dining_traditions,
            "work_from_home": cultural_prefs.work_from_home,
            "multi_generational_living": cultural_prefs.multi_generational_living
        }
        
        return RegionalPromptContext(
            region=region_enum,
            country=self.country,
            locale=self.locale,
            building_codes=building_codes_data.primary_codes,
            cultural_preferences=cultural_dict,
            measurement_system=self.measurement_converter.system
        )
    
    async def _prepare_template_variables(self, 
                                        request_data: AIPromptRequest,
                                        regional_context: RegionalPromptContext,
                                        model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables for template rendering."""
        
        # Convert area to regional units
        area_value, area_unit = self.measurement_converter.convert_area(
            request_data.total_area_m2
        )
        
        # Get localized room types
        language = self.locale.split('-')[0]
        localized_room_types = self.localization.get_localized_room_types(
            regional_context.region, language
        )
        
        # Get building code requirements
        building_codes_data = self.localization.get_building_codes(regional_context.region)
        
        # Prepare comprehensive template variables
        template_vars = {
            # Request data
            "building_type": request_data.building_type,
            "total_area": area_value,
            "area_unit": area_unit.value,
            "floor_count": request_data.floor_count,
            "room_requirements": request_data.room_requirements,
            "style_preferences": request_data.style_preferences,
            "budget_range": request_data.budget_range,
            "special_requirements": request_data.special_requirements,
            "accessibility_required": request_data.accessibility_required,
            "energy_efficiency_target": request_data.energy_efficiency_target,
            "user_prompt": request_data.user_prompt,
            
            # Regional context
            "region": regional_context.region.value,
            "country": regional_context.country,
            "locale": regional_context.locale,
            "language": language,
            "measurement_system": regional_context.measurement_system.value,
            
            # Building codes and compliance
            "building_codes": regional_context.building_codes,
            "primary_codes": building_codes_data.primary_codes,
            "accessibility_standard": building_codes_data.accessibility_standard,
            "energy_standard": building_codes_data.energy_standard,
            "seismic_requirements": building_codes_data.seismic_requirements,
            "climate_adaptations": building_codes_data.climate_adaptations,
            "minimum_room_sizes": building_codes_data.minimum_room_sizes,
            "max_occupancy_ratios": building_codes_data.max_occupancy_ratios,
            "setback_requirements": building_codes_data.setback_requirements,
            "height_restrictions": building_codes_data.height_restrictions,
            
            # Cultural preferences
            "cultural_preferences": regional_context.cultural_preferences,
            "privacy_level": regional_context.cultural_preferences.get("privacy_level", 0.5),
            "family_structure": regional_context.cultural_preferences.get("family_structure", "nuclear"),
            "entertainment_style": regional_context.cultural_preferences.get("entertainment_style", "mixed"),
            "outdoor_connection": regional_context.cultural_preferences.get("outdoor_connection", "medium"),
            "religious_considerations": regional_context.cultural_preferences.get("religious_considerations", []),
            "dining_traditions": regional_context.cultural_preferences.get("dining_traditions", "western"),
            
            # Localized content
            "localized_room_types": localized_room_types,
            
            # Model-specific configurations
            "model_config": model_config,
            "max_tokens": model_config.get("max_tokens", 4000),
            "temperature": model_config.get("temperature", 0.7),
            "response_format": model_config.get("response_format", "json"),
            
            # Helper functions for templates
            "format_area": self.measurement_converter.format_area,
            "format_length": self.measurement_converter.format_length,
            "get_translation": self.localization.get_translation,
        }
        
        return template_vars
    
    async def _generate_openai_prompt(self, prompt_type: PromptType, template_vars: Dict[str, Any]) -> str:
        """Generate OpenAI-optimized prompt."""
        template_name = f"openai_{prompt_type.value}.j2"
        
        if prompt_type == PromptType.LAYOUT_GENERATION:
            template_content = """You are an expert architectural designer specializing in {{ region }} {{ building_type }} buildings.

REGIONAL CONTEXT:
- Country: {{ country }}
- Region: {{ region }}
- Building Codes: {{ building_codes | join(', ') }}
- Measurement System: {{ measurement_system }}
- Cultural Context: {{ locale }}

TASK: Generate an optimized room layout based on the following requirements:

INPUT SPECIFICATION:
- Building Type: {{ building_type }}
- Total Area: {{ total_area }} {{ area_unit }}
- Floor Count: {{ floor_count }}
- Room Requirements: {{ room_requirements | tojson }}
- Style Preferences: {{ style_preferences | tojson }}
- Cultural Preferences: {{ cultural_preferences | tojson }}
- Available Room Types: {{ localized_room_types | tojson }}

REGIONAL COMPLIANCE REQUIREMENTS:
{% if region == "north_america" %}
- Must comply with International Building Code (IBC) or International Residential Code (IRC)
- Egress requirements: Bedrooms must have proper egress windows or secondary exits
- Accessibility: Comply with ADA requirements where applicable
- Energy codes: Meet regional energy efficiency standards
{% elif region == "europe" %}
- Must comply with Eurocode standards and national building regulations
- Energy performance: Meet or exceed regional energy efficiency directives
- Accessibility: Comply with European accessibility standards
- Fire safety: Meet European fire safety regulations
{% elif region == "middle_east" and country == "turkey" %}
- Turkish İmar Yönetmeliği compliance required
- TAKS (Building Coverage Ratio) must not exceed {{ max_occupancy_ratios.get('residential', 0.4) }}
- KAKS (Floor Area Ratio) restrictions apply
- Earthquake resistance requirements (Turkey is in seismic zone)
{% elif region == "asia_pacific" %}
- Comply with national building codes (e.g., NCC for Australia, Building Standards Act for Japan)
- Climate adaptation: Design for regional climate conditions
- Seismic considerations: Include earthquake resistance where applicable
{% endif %}

CULTURAL DESIGN CONSIDERATIONS:
- Privacy Level: {{ privacy_level }} (0.0 = open, 1.0 = very private)
- Family Structure: {{ family_structure }}
- Entertainment Style: {{ entertainment_style }}
- Outdoor Connection: {{ outdoor_connection }}
{% if religious_considerations %}
- Religious Considerations: {{ religious_considerations | join(', ') }}
{% endif %}

MINIMUM ROOM SIZES (per regional codes):
{% for room_type, min_size in minimum_room_sizes.items() %}
- {{ localized_room_types.get(room_type, room_type) }}: {{ min_size }} m²
{% endfor %}

OUTPUT FORMAT:
Provide your response as a structured JSON with the following schema:
{
  "confidence": 0.0-1.0,
  "requires_human_review": boolean,
  "region": "{{ region }}",
  "applicable_codes": [list of relevant building codes],
  "layout": {
    "rooms": [
      {
        "name": "string",
        "type": "one of the localized room types",
        "area_{{ area_unit.replace(' ', '_').lower() }}": number,
        "dimensions": {"width_{{ measurement_system }}": number, "length_{{ measurement_system }}": number},
        "position": {"x": number, "y": number},
        "connections": ["room_name1", "room_name2"],
        "cultural_adaptations": []
      }
    ],
    "walls": [...],
    "doors": [...],
    "windows": [...]
  },
  "compliance_check": {
    "regional_code_compliant": boolean,
    "accessibility_compliant": boolean,
    "energy_efficient": boolean,
    "culturally_appropriate": boolean
  },
  "cultural_considerations": {
    "privacy_level": "{{ privacy_level }}",
    "family_interaction_spaces": boolean,
    "climate_adaptations": []
  },
  "reasoning": "Brief explanation of design decisions with regional context"
}

CONSTRAINTS:
- Prioritize natural lighting and ventilation appropriate for the climate
- Design circulation patterns that respect cultural norms
- Ensure compliance with local accessibility requirements
- Consider regional material availability and construction methods
- Optimize for local climate conditions (heating/cooling requirements)
- Respect cultural privacy and family dynamics requirements

Generate the layout now considering {{ region }} standards and {{ locale }} cultural context:
{{ user_prompt }}"""
        else:
            # Fallback for other prompt types
            template_content = "Generate {{ prompt_type }} for {{ building_type }} in {{ region }}."
        
        template = Template(template_content)
        return template.render(**template_vars, prompt_type=prompt_type)
    
    async def _generate_claude_prompt(self, prompt_type: PromptType, template_vars: Dict[str, Any]) -> str:
        """Generate Claude-optimized prompt."""
        # Claude prefers structured, clear instructions with examples
        template_vars["model_style"] = "claude"
        return await self._generate_openai_prompt(prompt_type, template_vars)
    
    async def _generate_gemini_prompt(self, prompt_type: PromptType, template_vars: Dict[str, Any]) -> str:
        """Generate Gemini-optimized prompt."""
        # Gemini works well with conversational style prompts
        template_vars["model_style"] = "gemini"
        return await self._generate_openai_prompt(prompt_type, template_vars)
    
    async def _generate_generic_prompt(self, prompt_type: PromptType, template_vars: Dict[str, Any]) -> str:
        """Generate generic prompt for unknown model types."""
        return await self._generate_openai_prompt(prompt_type, template_vars)
    
    async def _load_model_configurations(self):
        """Load model-specific configurations."""
        model_config_path = self.configs_path / "ai-prompts" / "model-configs.json"
        
        if model_config_path.exists():
            with open(model_config_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
                
                for model_str, config in model_data.items():
                    try:
                        model_type = AIModelType(model_str)
                        self.model_configs[model_type] = config
                    except ValueError:
                        logger.warning(f"Unknown model type in config: {model_str}")
        else:
            # Create default model configurations
            await self._create_default_model_configs()
    
    async def _load_prompt_templates(self):
        """Load Jinja2 prompt templates."""
        # Templates are loaded by Jinja2 FileSystemLoader
        # This method can be extended to preload and validate templates
        pass
    
    async def _create_default_model_configs(self):
        """Create default model configurations."""
        default_configs = {
            AIModelType.OPENAI_GPT4.value: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "response_format": "json",
                "system_message_style": "professional",
                "context_window": 32000,
                "supports_json_mode": True
            },
            AIModelType.OPENAI_GPT35.value: {
                "max_tokens": 3000,
                "temperature": 0.7,
                "response_format": "json",
                "system_message_style": "concise",
                "context_window": 16000,
                "supports_json_mode": True
            },
            AIModelType.CLAUDE_SONNET.value: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "response_format": "json",
                "system_message_style": "structured",
                "context_window": 200000,
                "supports_json_mode": False
            },
            AIModelType.CLAUDE_HAIKU.value: {
                "max_tokens": 3000,
                "temperature": 0.7,
                "response_format": "json",
                "system_message_style": "concise",
                "context_window": 200000,
                "supports_json_mode": False
            },
            AIModelType.GEMINI_PRO.value: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "response_format": "json",
                "system_message_style": "conversational",
                "context_window": 32000,
                "supports_json_mode": True
            },
            AIModelType.GEMINI_FLASH.value: {
                "max_tokens": 3000,
                "temperature": 0.7,
                "response_format": "json",
                "system_message_style": "efficient",
                "context_window": 32000,
                "supports_json_mode": True
            }
        }
        
        self.model_configs = {AIModelType(k): v for k, v in default_configs.items()}
        
        # Save to file
        model_config_path = self.configs_path / "ai-prompts" / "model-configs.json"
        model_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(model_config_path, 'w', encoding='utf-8') as f:
            json.dump(default_configs, f, ensure_ascii=False, indent=2)


def create_prompt_engine(region: str, 
                        country: str, 
                        locale: str,
                        localization_service: Optional[LocalizationService] = None,
                        configs_path: Optional[Path] = None) -> GlobalPromptTemplateEngine:
    """
    Factory function to create a global prompt template engine.
    
    Args:
        region: Geographic region
        country: Country code
        locale: Locale string
        localization_service: Optional localization service instance
        configs_path: Path to configuration files
        
    Returns:
        Configured GlobalPromptTemplateEngine instance
    """
    return GlobalPromptTemplateEngine(
        region=region,
        country=country,
        locale=locale,
        localization_service=localization_service,
        configs_path=configs_path
    )