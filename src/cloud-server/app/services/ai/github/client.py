"""
GitHub Models Client for ArchBuilder.AI
Implements GitHub Models (GPT-4.1) integration for complex architectural reasoning
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from openai import AsyncOpenAI

from ....core.config import get_settings
from ....core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GitHubModelsClient:
    """
    GitHub Models client for ArchBuilder.AI with GPT-4.1 integration
    Optimized for complex architectural reasoning and multi-format CAD parsing
    """
    
    def __init__(self):
        self.api_key = settings.GITHUB_MODELS_API_KEY
        self.base_url = "https://models.inference.ai.azure.com"
        self.model_name = "gpt-4.1"
        
        # Initialize OpenAI client for GitHub Models
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Model parameters optimized for architectural tasks
        self.default_params = {
            "max_tokens": 128000,
            "temperature": 0.2,  # Slightly higher than Vertex AI for creative architectural solutions
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }
        
        logger.info(
            "GitHub Models client initialized",
            base_url=self.base_url,
            model=self.model_name
        )
    
    async def generate_content(
        self,
        prompt: str,
        model: Optional[str] = None,
        correlation_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate content using GitHub Models GPT-4.1
        
        Args:
            prompt: Input prompt for the model
            model: Model name override (default: gpt-4.1)
            correlation_id: Request correlation ID for tracking
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Dict containing generated content and metadata
        """
        
        start_time = datetime.utcnow()
        
        logger.info(
            "Generating content with GitHub Models",
            correlation_id=correlation_id,
            model=model or self.model_name,
            prompt_length=len(prompt)
        )
        
        try:
            # Prepare parameters
            params = self.default_params.copy()
            if temperature is not None:
                params["temperature"] = temperature
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            # Create chat completion
            response = await self.client.chat.completions.create(
                model=model or self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert architectural AI assistant for ArchBuilder.AI. Provide detailed, accurate, and building-code-compliant architectural solutions. Always respond with structured, actionable information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **params
            )
            
            # Extract content
            content = response.choices[0].message.content if response.choices else ""
            
            # Extract JSON if response contains structured data
            structured_data = self._extract_json_content(content)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                "GitHub Models content generation completed",
                correlation_id=correlation_id,
                response_length=len(content),
                processing_time_seconds=processing_time,
                has_structured_data=structured_data is not None,
                finish_reason=response.choices[0].finish_reason if response.choices else "unknown"
            )
            
            return {
                "content": content,
                "structured_data": structured_data,
                "model_used": model or self.model_name,
                "processing_time_seconds": processing_time,
                "token_usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "finish_reason": response.choices[0].finish_reason if response.choices else "unknown"
            }
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.error(
                "GitHub Models content generation failed",
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_seconds=processing_time
            )
            
            # Return error response
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "model_used": model or self.model_name,
                "processing_time_seconds": processing_time
            }
    
    async def analyze_existing_project(
        self,
        project_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze existing Revit project for improvements and optimization
        """
        
        logger.info(
            "Analyzing existing project with GitHub Models",
            correlation_id=correlation_id,
            element_count=project_data.get("total_elements", 0)
        )
        
        analysis_prompt = f"""
        As an expert BIM analyst and architectural consultant, perform a comprehensive analysis of the following Revit project data.

        Project Data:
        {json.dumps(project_data, indent=2)}

        Please provide a detailed analysis in the following JSON format:
        {{
            "project_analysis": {{
                "overall_score": <0.0-1.0>,
                "project_health": "<excellent|good|needs_improvement|poor>",
                "total_elements": <number>,
                "model_complexity": "<low|medium|high|very_high>",
                "performance_issues": [
                    {{
                        "issue": "<description>",
                        "severity": "<low|medium|high|critical>",
                        "impact": "<performance_impact>",
                        "recommendation": "<fix_suggestion>"
                    }}
                ],
                "design_improvements": [
                    {{
                        "category": "<spatial|structural|mep|sustainability>",
                        "improvement": "<description>",
                        "benefit": "<expected_benefit>",
                        "effort": "<low|medium|high>",
                        "priority": "<low|medium|high>"
                    }}
                ],
                "clash_detection": {{
                    "total_clashes": <number>,
                    "critical_clashes": <number>,
                    "clash_categories": [
                        {{
                            "category": "<architectural|structural|mep>",
                            "count": <number>,
                            "severity": "<low|medium|high>"
                        }}
                    ]
                }},
                "compliance_issues": [
                    {{
                        "code": "<building_code_reference>",
                        "issue": "<description>",
                        "location": "<element_or_space>",
                        "resolution": "<recommended_fix>"
                    }}
                ],
                "optimization_opportunities": [
                    {{
                        "area": "<space_planning|circulation|sustainability|cost>",
                        "opportunity": "<description>",
                        "potential_savings": "<percentage_or_amount>",
                        "implementation": "<steps_to_implement>"
                    }}
                ],
                "space_analysis": {{
                    "total_area_m2": <number>,
                    "usable_area_m2": <number>,
                    "circulation_efficiency": <0.0-1.0>,
                    "space_utilization": <0.0-1.0>,
                    "room_adjacency_score": <0.0-1.0>
                }},
                "sustainability_assessment": {{
                    "energy_efficiency_score": <0.0-1.0>,
                    "daylighting_score": <0.0-1.0>,
                    "ventilation_adequacy": <0.0-1.0>,
                    "material_sustainability": <0.0-1.0>,
                    "recommendations": ["<rec1>", "<rec2>"]
                }}
            }},
            "next_steps": [
                {{
                    "step": "<action>",
                    "priority": "<high|medium|low>",
                    "estimated_time": "<duration>",
                    "required_expertise": "<discipline>"
                }}
            ],
            "confidence": <0.0-1.0>,
            "requires_expert_review": <boolean>,
            "analysis_timestamp": "{datetime.utcnow().isoformat()}"
        }}

        Focus on actionable insights that will improve the project's quality, performance, and compliance.
        """
        
        return await self.generate_content(
            prompt=analysis_prompt,
            correlation_id=correlation_id,
            temperature=0.1  # Low temperature for consistent analysis
        )
    
    async def generate_complex_layout(
        self,
        requirements: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complex architectural layout with advanced reasoning
        """
        
        logger.info(
            "Generating complex layout with GitHub Models",
            correlation_id=correlation_id,
            total_area=requirements.get("total_area_m2", 0)
        )
        
        layout_prompt = f"""
        As an expert architect, design a comprehensive layout based on the following requirements:

        Requirements:
        {json.dumps(requirements, indent=2)}

        Please provide a detailed architectural solution in the following JSON format:
        {{
            "architectural_solution": {{
                "layout": {{
                    "total_area_m2": <number>,
                    "usable_area_m2": <number>,
                    "circulation_area_m2": <number>,
                    "efficiency_ratio": <0.0-1.0>,
                    "rooms": [
                        {{
                            "id": "<unique_id>",
                            "name": "<room_name>",
                            "type": "<room_type>",
                            "area_m2": <number>,
                            "dimensions": {{"width_m": <number>, "length_m": <number>, "height_m": <number>}},
                            "position": {{"x_mm": <number>, "y_mm": <number>}},
                            "adjacencies": ["<adjacent_room_id1>", "<adjacent_room_id2>"],
                            "natural_light": <boolean>,
                            "ventilation_type": "<natural|mechanical|mixed>",
                            "accessibility": <boolean>,
                            "special_requirements": ["<req1>", "<req2>"]
                        }}
                    ],
                    "circulation": {{
                        "corridors": [
                            {{
                                "id": "<corridor_id>",
                                "width_mm": <number>,
                                "length_mm": <number>,
                                "connects": ["<room_id1>", "<room_id2>"],
                                "emergency_route": <boolean>
                            }}
                        ],
                        "vertical_circulation": [
                            {{
                                "type": "<stairs|elevator|escalator>",
                                "location": {{"x_mm": <number>, "y_mm": <number>}},
                                "capacity": <number>,
                                "accessibility_compliant": <boolean>
                            }}
                        ]
                    }}
                }},
                "structural_elements": {{
                    "walls": [
                        {{
                            "id": "<wall_id>",
                            "type": "<load_bearing|partition|shear>",
                            "start_point": {{"x_mm": <number>, "y_mm": <number>, "z_mm": 0}},
                            "end_point": {{"x_mm": <number>, "y_mm": <number>, "z_mm": 0}},
                            "thickness_mm": <number>,
                            "height_mm": <number>,
                            "material": "<concrete|steel|wood|masonry>",
                            "fire_rating_hours": <number>
                        }}
                    ],
                    "columns": [
                        {{
                            "id": "<column_id>",
                            "position": {{"x_mm": <number>, "y_mm": <number>}},
                            "cross_section": {{"width_mm": <number>, "depth_mm": <number>}},
                            "material": "<concrete|steel>",
                            "load_capacity_kn": <number>
                        }}
                    ],
                    "beams": [
                        {{
                            "id": "<beam_id>",
                            "start_point": {{"x_mm": <number>, "y_mm": <number>, "z_mm": <number>}},
                            "end_point": {{"x_mm": <number>, "y_mm": <number>, "z_mm": <number>}},
                            "cross_section": {{"width_mm": <number>, "height_mm": <number>}},
                            "material": "<concrete|steel|wood>",
                            "load_capacity_kn": <number>
                        }}
                    ]
                }},
                "openings": {{
                    "doors": [
                        {{
                            "id": "<door_id>",
                            "wall_id": "<wall_id>",
                            "position_on_wall_mm": <number>,
                            "width_mm": <number>,
                            "height_mm": <number>,
                            "door_type": "<single|double|sliding|folding>",
                            "fire_rated": <boolean>,
                            "accessibility_compliant": <boolean>,
                            "swing_direction": "<inward|outward|bidirectional>"
                        }}
                    ],
                    "windows": [
                        {{
                            "id": "<window_id>",
                            "wall_id": "<wall_id>",
                            "position_on_wall_mm": <number>,
                            "width_mm": <number>,
                            "height_mm": <number>,
                            "sill_height_mm": <number>,
                            "window_type": "<fixed|casement|sliding|awning>",
                            "glazing_type": "<single|double|triple>",
                            "u_value": <number>
                        }}
                    ]
                }},
                "building_services": {{
                    "hvac": {{
                        "system_type": "<central|split|vrf>",
                        "zones": [
                            {{
                                "zone_id": "<zone_id>",
                                "rooms": ["<room_id1>", "<room_id2>"],
                                "heating_load_kw": <number>,
                                "cooling_load_kw": <number>,
                                "ventilation_rate_l_s": <number>
                            }}
                        ]
                    }},
                    "electrical": {{
                        "main_panel_location": {{"x_mm": <number>, "y_mm": <number>}},
                        "circuits": [
                            {{
                                "circuit_id": "<circuit_id>",
                                "type": "<lighting|power|hvac>",
                                "load_watts": <number>,
                                "rooms_served": ["<room_id1>", "<room_id2>"]
                            }}
                        ]
                    }},
                    "plumbing": {{
                        "water_supply": {{
                            "main_line_location": {{"x_mm": <number>, "y_mm": <number>}},
                            "fixtures": [
                                {{
                                    "fixture_id": "<fixture_id>",
                                    "type": "<sink|toilet|shower|bathtub>",
                                    "room_id": "<room_id>",
                                    "position": {{"x_mm": <number>, "y_mm": <number>}}
                                }}
                            ]
                        }},
                        "drainage": {{
                            "main_drain_location": {{"x_mm": <number>, "y_mm": <number>}},
                            "drain_lines": [
                                {{
                                    "line_id": "<line_id>",
                                    "diameter_mm": <number>,
                                    "slope_percent": <number>,
                                    "fixtures_served": ["<fixture_id1>", "<fixture_id2>"]
                                }}
                            ]
                        }}
                    }}
                }}
            }},
            "compliance_analysis": {{
                "building_codes_checked": ["<code1>", "<code2>"],
                "compliance_score": <0.0-1.0>,
                "violations": [
                    {{
                        "code": "<code_reference>",
                        "violation": "<description>",
                        "location": "<element_or_room>",
                        "severity": "<minor|major|critical>",
                        "resolution": "<fix_recommendation>"
                    }}
                ],
                "accessibility_compliance": <boolean>,
                "fire_safety_compliance": <boolean>,
                "energy_efficiency_rating": "<A+|A|B|C|D|E|F>"
            }},
            "design_rationale": {{
                "spatial_organization": "<explanation>",
                "circulation_strategy": "<explanation>",
                "daylighting_strategy": "<explanation>",
                "sustainability_features": ["<feature1>", "<feature2>"],
                "cost_optimization_strategies": ["<strategy1>", "<strategy2>"]
            }},
            "construction_phases": [
                {{
                    "phase": "<phase_name>",
                    "duration_weeks": <number>,
                    "activities": ["<activity1>", "<activity2>"],
                    "dependencies": ["<dependency1>", "<dependency2>"],
                    "estimated_cost": <number>
                }}
            ],
            "confidence": <0.0-1.0>,
            "requires_human_review": <boolean>,
            "complexity_level": "<low|medium|high|very_high>"
        }}

        Ensure the design is optimized for functionality, compliance, sustainability, and cost-effectiveness.
        """
        
        return await self.generate_content(
            prompt=layout_prompt,
            correlation_id=correlation_id,
            temperature=0.2  # Slightly higher for creative solutions
        )
    
    async def perform_clash_detection(
        self,
        model_elements: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform AI-powered clash detection on BIM elements
        """
        
        logger.info(
            "Performing clash detection with GitHub Models",
            correlation_id=correlation_id,
            element_count=len(model_elements)
        )
        
        clash_prompt = f"""
        As a BIM coordination expert, analyze the following model elements for potential clashes and coordination issues:

        Model Elements:
        {json.dumps(model_elements, indent=2)}

        Perform comprehensive clash detection and provide results in JSON format:
        {{
            "clash_detection_results": {{
                "total_elements_analyzed": <number>,
                "analysis_timestamp": "{datetime.utcnow().isoformat()}",
                "hard_clashes": [
                    {{
                        "clash_id": "<unique_id>",
                        "element_1": {{
                            "id": "<element_id>",
                            "category": "<architectural|structural|mechanical|electrical|plumbing>",
                            "type": "<element_type>",
                            "location": {{"x": <number>, "y": <number>, "z": <number>}}
                        }},
                        "element_2": {{
                            "id": "<element_id>",
                            "category": "<architectural|structural|mechanical|electrical|plumbing>",
                            "type": "<element_type>",
                            "location": {{"x": <number>, "y": <number>, "z": <number>}}
                        }},
                        "clash_type": "<geometric_overlap|material_conflict|spatial_conflict>",
                        "severity": "<minor|major|critical>",
                        "clash_volume_m3": <number>,
                        "description": "<detailed_description>",
                        "resolution_strategies": [
                            {{
                                "strategy": "<move|resize|reroute|redesign>",
                                "element_to_modify": "<element_id>",
                                "estimated_effort": "<low|medium|high>",
                                "cost_impact": "<low|medium|high>"
                            }}
                        ]
                    }}
                ],
                "soft_clashes": [
                    {{
                        "clash_id": "<unique_id>",
                        "element_1": "<element_details>",
                        "element_2": "<element_details>",
                        "clearance_issue": "<description>",
                        "required_clearance_mm": <number>,
                        "actual_clearance_mm": <number>,
                        "code_requirement": "<code_reference>",
                        "recommendation": "<suggested_action>"
                    }}
                ],
                "coordination_issues": [
                    {{
                        "issue_id": "<unique_id>",
                        "category": "<accessibility|maintenance|installation|operation>",
                        "description": "<issue_description>",
                        "affected_elements": ["<element_id1>", "<element_id2>"],
                        "potential_problems": ["<problem1>", "<problem2>"],
                        "prevention_measures": ["<measure1>", "<measure2>"]
                    }}
                ],
                "summary": {{
                    "total_hard_clashes": <number>,
                    "total_soft_clashes": <number>,
                    "critical_issues": <number>,
                    "coordination_score": <0.0-1.0>,
                    "model_quality": "<excellent|good|needs_improvement|poor>",
                    "recommended_actions": ["<action1>", "<action2>"]
                }}
            }},
            "confidence": <0.0-1.0>,
            "requires_expert_review": <boolean>
        }}

        Focus on identifying all potential conflicts and providing actionable resolution strategies.
        """
        
        return await self.generate_content(
            prompt=clash_prompt,
            correlation_id=correlation_id,
            temperature=0.1  # Low temperature for consistent clash detection
        )
    
    def _extract_json_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON content from AI response"""
        
        try:
            # Look for JSON content between ```json and ``` or just parse directly
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif content.strip().startswith("{") and content.strip().endswith("}"):
                json_str = content.strip()
            else:
                return None
            
            return json.loads(json_str)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Failed to extract JSON from AI response",
                error=str(e),
                content_preview=content[:200]
            )
            return None
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available GitHub Models"""
        
        return {
            "provider": "github_models",
            "available_models": [
                {
                    "name": "gpt-4.1",
                    "max_tokens": 128000,
                    "languages": ["en", "tr", "de", "fr", "es"],
                    "specialties": ["complex_reasoning", "multi_format_parsing", "revit_commands"],
                    "cost": "medium"
                }
            ],
            "default_model": self.model_name,
            "base_url": self.base_url
        }