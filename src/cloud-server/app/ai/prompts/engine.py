"""
AI Prompt Engineering System for ArchBuilder.AI
Manages structured prompts for different AI models and languages
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, Template

logger = structlog.get_logger(__name__)


class PromptEngine:
    """Central prompt management and engineering system"""
    
    def __init__(self, prompts_base_path: str = "configs/ai-prompts"):
        self.prompts_base_path = Path(prompts_base_path)
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Jinja2 environment for template rendering
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.prompts_base_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        except Exception as e:
            self.logger.warning(f"Could not initialize template loader: {e}")
            self.jinja_env = Environment()
        
        # Load building code context cache
        self.building_codes_cache = {}
        
        self.logger.info(
            "Prompt Engine initialized",
            prompts_path=str(self.prompts_base_path)
        )
    
    def get_layout_generation_prompt(self,
                                   room_program: Dict[str, Any],
                                   building_codes: List[str],
                                   language: str = "en",
                                   measurement_system: str = "metric",
                                   region: str = "turkey") -> str:
        """Generate structured prompt for layout generation"""
        
        # Load region-specific building codes
        building_code_context = self._get_building_code_context(building_codes, region)
        
        # Load localized templates
        template_name = f"{language}/layout_generation.j2"
        
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception:
            # Fallback to English if localized template not found
            template = self.jinja_env.get_template("en/layout_generation.j2")
            self.logger.warning(f"Fallback to English template for language: {language}")
        
        # Prepare template variables
        template_vars = {
            "room_program": room_program,
            "building_codes": building_code_context,
            "measurement_system": measurement_system,
            "region": region,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "units": self._get_measurement_units(measurement_system),
            "min_room_sizes": self._get_min_room_sizes(region, measurement_system),
            "standard_dimensions": self._get_standard_dimensions(region, measurement_system)
        }
        
        try:
            prompt = template.render(**template_vars)
            
            self.logger.info(
                "Layout generation prompt created",
                language=language,
                region=region,
                measurement_system=measurement_system,
                prompt_length=len(prompt)
            )
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Failed to render template: {e}")
            return self._get_fallback_layout_prompt(room_program, building_codes, language)
    
    def get_building_code_analysis_prompt(self,
                                        document_content: str,
                                        region: str,
                                        language: str = "en") -> str:
        """Generate prompt for building code document analysis"""
        
        template_name = f"{language}/building_code_analysis.j2"
        
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception:
            template = self.jinja_env.get_template("en/building_code_analysis.j2")
        
        template_vars = {
            "document_content": document_content[:10000],  # Limit content length
            "region": region,
            "analysis_categories": [
                "room_sizes",
                "accessibility",
                "fire_safety",
                "structural",
                "energy_efficiency",
                "ventilation",
                "natural_lighting"
            ],
            "extraction_rules": self._get_extraction_rules(region)
        }
        
        prompt = template.render(**template_vars)
        
        self.logger.info(
            "Building code analysis prompt created",
            region=region,
            language=language,
            document_length=len(document_content)
        )
        
        return prompt
    
    def get_project_analysis_prompt(self,
                                  project_data: Dict[str, Any],
                                  analysis_type: str,
                                  language: str = "en") -> str:
        """Generate prompt for existing project analysis"""
        
        template_name = f"{language}/project_analysis.j2"
        
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception:
            template = self.jinja_env.get_template("en/project_analysis.j2")
        
        template_vars = {
            "project_data": project_data,
            "analysis_type": analysis_type,
            "analysis_frameworks": {
                "efficiency": ["space_utilization", "circulation", "natural_light", "ventilation"],
                "compliance": ["building_codes", "accessibility", "fire_safety", "structural"],
                "sustainability": ["energy_performance", "material_efficiency", "water_usage", "waste_reduction"],
                "cost_optimization": ["material_costs", "labor_efficiency", "maintenance", "lifecycle_costs"]
            },
            "evaluation_criteria": self._get_evaluation_criteria(analysis_type)
        }
        
        prompt = template.render(**template_vars)
        
        self.logger.info(
            "Project analysis prompt created",
            analysis_type=analysis_type,
            language=language
        )
        
        return prompt
    
    def get_step_plan_prompt(self,
                           requirements: Dict[str, Any],
                           complexity_level: str,
                           language: str = "en") -> str:
        """Generate prompt for step-by-step project planning"""
        
        template_name = f"{language}/step_plan.j2"
        
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception:
            template = self.jinja_env.get_template("en/step_plan.j2")
        
        step_ranges = {
            "simple": {"min": 5, "max": 15, "hours": "10-25"},
            "medium": {"min": 15, "max": 30, "hours": "25-60"},
            "complex": {"min": 30, "max": 50, "hours": "60-150"}
        }
        
        step_config = step_ranges.get(complexity_level, step_ranges["medium"])
        
        template_vars = {
            "requirements": requirements,
            "complexity_level": complexity_level,
            "step_range": step_config,
            "workflow_phases": [
                "preparation",
                "foundation",
                "structure",
                "envelope",
                "interior",
                "mep_systems",
                "finishes",
                "documentation"
            ],
            "quality_gates": self._get_quality_gates(),
            "revit_command_patterns": self._get_revit_command_patterns()
        }
        
        prompt = template.render(**template_vars)
        
        self.logger.info(
            "Step plan prompt created",
            complexity_level=complexity_level,
            language=language
        )
        
        return prompt
    
    def _get_building_code_context(self, 
                                 building_codes: List[str], 
                                 region: str) -> Dict[str, Any]:
        """Load and cache building code context for region"""
        
        cache_key = f"{region}_{hash(tuple(sorted(building_codes)))}"
        
        if cache_key in self.building_codes_cache:
            return self.building_codes_cache[cache_key]
        
        # Load building code summaries
        building_code_path = self.prompts_base_path.parent / "building-codes" / "processed" / region
        
        context = {
            "region": region,
            "codes": [],
            "key_requirements": [],
            "min_dimensions": {}
        }
        
        try:
            if building_code_path.exists():
                # Load processed building code summaries
                summaries_file = building_code_path / "summaries" / "key_requirements.json"
                if summaries_file.exists():
                    with open(summaries_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        context.update(data)
            
        except Exception as e:
            self.logger.warning(f"Could not load building codes for {region}: {e}")
        
        # Cache the result
        self.building_codes_cache[cache_key] = context
        
        return context
    
    def _get_measurement_units(self, measurement_system: str) -> Dict[str, str]:
        """Get measurement units for the system"""
        
        units_map = {
            "metric": {
                "length": "mm",
                "area": "m²",
                "volume": "m³",
                "temperature": "°C"
            },
            "imperial": {
                "length": "inches",
                "area": "sq ft",
                "volume": "cu ft", 
                "temperature": "°F"
            }
        }
        
        return units_map.get(measurement_system, units_map["metric"])
    
    def _get_min_room_sizes(self, region: str, measurement_system: str) -> Dict[str, float]:
        """Get minimum room sizes for region and measurement system"""
        
        # Base sizes in metric (m²)
        base_sizes = {
            "bedroom": 9.0,
            "living_room": 12.0,
            "kitchen": 6.0,
            "bathroom": 3.0,
            "corridor": 1.2,  # width in meters
            "storage": 2.0
        }
        
        # Regional adjustments
        regional_multipliers = {
            "turkey": 1.0,
            "usa": 1.2,
            "uk": 0.9,
            "germany": 1.1,
            "france": 1.0
        }
        
        multiplier = regional_multipliers.get(region, 1.0)
        
        adjusted_sizes = {k: v * multiplier for k, v in base_sizes.items()}
        
        # Convert to imperial if needed
        if measurement_system == "imperial":
            adjusted_sizes = {k: v * 10.764 for k, v in adjusted_sizes.items()}  # m² to sq ft
        
        return adjusted_sizes
    
    def _get_standard_dimensions(self, region: str, measurement_system: str) -> Dict[str, Dict[str, int]]:
        """Get standard dimensions for doors, windows, etc."""
        
        # Base dimensions in mm
        base_dims = {
            "doors": {
                "single": {"width": 800, "height": 2100},
                "double": {"width": 1600, "height": 2100}
            },
            "windows": {
                "small": {"width": 800, "height": 1200},
                "medium": {"width": 1200, "height": 1400},
                "large": {"width": 1800, "height": 1600}
            },
            "walls": {
                "interior": {"thickness": 100},
                "exterior": {"thickness": 200},
                "height": 2700
            }
        }
        
        # Regional adjustments for different standards
        if region == "usa":
            base_dims["doors"]["single"]["width"] = 914  # 36 inches
            base_dims["walls"]["height"] = 2743  # 9 feet
        
        # Convert to imperial if needed
        if measurement_system == "imperial":
            # Convert mm to inches
            def convert_dict(d):
                if isinstance(d, dict):
                    return {k: convert_dict(v) for k, v in d.items()}
                elif isinstance(d, (int, float)):
                    return int(d / 25.4)  # mm to inches
                return d
            
            base_dims = convert_dict(base_dims)
        
        return base_dims
    
    def _get_extraction_rules(self, region: str) -> List[Dict[str, str]]:
        """Get extraction rules for building code analysis"""
        
        return [
            {
                "pattern": r"minimum.*?(\d+\.?\d*)\s*(m²|sq\s*ft)",
                "category": "room_sizes",
                "description": "Extract minimum area requirements"
            },
            {
                "pattern": r"ceiling.*?height.*?(\d+\.?\d*)\s*(m|ft)",
                "category": "room_dimensions",
                "description": "Extract ceiling height requirements"
            },
            {
                "pattern": r"door.*?width.*?(\d+\.?\d*)\s*(mm|cm|inches)",
                "category": "openings",
                "description": "Extract door width requirements"
            },
            {
                "pattern": r"window.*?area.*?(\d+\.?\d*)\s*%",
                "category": "natural_lighting",
                "description": "Extract window-to-floor area ratios"
            }
        ]
    
    def _get_evaluation_criteria(self, analysis_type: str) -> List[Dict[str, Any]]:
        """Get evaluation criteria for project analysis"""
        
        criteria_map = {
            "efficiency": [
                {"name": "Space Utilization", "weight": 0.3, "scale": "1-10"},
                {"name": "Circulation Efficiency", "weight": 0.25, "scale": "1-10"},
                {"name": "Natural Light Access", "weight": 0.25, "scale": "1-10"},
                {"name": "Functional Layout", "weight": 0.2, "scale": "1-10"}
            ],
            "compliance": [
                {"name": "Building Code Compliance", "weight": 0.4, "scale": "pass/fail"},
                {"name": "Accessibility Standards", "weight": 0.3, "scale": "pass/fail"},
                {"name": "Fire Safety Requirements", "weight": 0.3, "scale": "pass/fail"}
            ],
            "sustainability": [
                {"name": "Energy Efficiency", "weight": 0.35, "scale": "A-G"},
                {"name": "Material Sustainability", "weight": 0.25, "scale": "1-10"},
                {"name": "Water Efficiency", "weight": 0.2, "scale": "1-10"},
                {"name": "Waste Reduction", "weight": 0.2, "scale": "1-10"}
            ]
        }
        
        return criteria_map.get(analysis_type, criteria_map["efficiency"])
    
    def _get_quality_gates(self) -> List[Dict[str, Any]]:
        """Get quality checkpoints for project workflow"""
        
        return [
            {
                "name": "Foundation Complete",
                "after_steps": [5, 10],
                "criteria": ["Levels created", "Grid lines positioned", "Foundation elements placed"]
            },
            {
                "name": "Structure Review",
                "after_steps": [15, 20],
                "criteria": ["All structural elements", "Load paths verified", "Connections detailed"]
            },
            {
                "name": "Envelope Sealed",
                "after_steps": [25, 30],
                "criteria": ["Walls complete", "Roof structure", "Openings placed"]
            },
            {
                "name": "MEP Coordination", 
                "after_steps": [35, 40],
                "criteria": ["Systems routed", "No clashes", "Equipment placed"]
            }
        ]
    
    def _get_revit_command_patterns(self) -> Dict[str, List[str]]:
        """Get common Revit command patterns"""
        
        return {
            "setup": [
                "File > New > Project",
                "Manage > Project Units",
                "Architecture > Level",
                "Architecture > Grid"
            ],
            "structure": [
                "Structure > Wall",
                "Structure > Floor", 
                "Structure > Roof",
                "Structure > Column"
            ],
            "architecture": [
                "Architecture > Wall",
                "Architecture > Door",
                "Architecture > Window",
                "Architecture > Stair"
            ],
            "mep": [
                "Systems > Duct",
                "Systems > Pipe",
                "Systems > Electrical > Device",
                "Systems > Mechanical Equipment"
            ]
        }
    
    def _get_fallback_layout_prompt(self, 
                                  room_program: Dict[str, Any], 
                                  building_codes: List[str],
                                  language: str) -> str:
        """Fallback prompt when template loading fails"""
        
        return f"""
        You are an expert architect creating Revit-compatible layouts.
        
        ROOM PROGRAM:
        {json.dumps(room_program, indent=2)}
        
        BUILDING CODES: {', '.join(building_codes)}
        LANGUAGE: {language}
        
        Create a JSON layout with walls, doors, windows, and rooms.
        All coordinates in millimeters. Include confidence score.
        
        Ensure compliance with building codes and minimum room sizes.
        """