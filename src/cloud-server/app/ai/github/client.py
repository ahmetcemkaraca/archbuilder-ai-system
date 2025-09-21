"""
GitHub Models Client for ArchBuilder.AI
Handles GitHub Models GPT-4.1 integration for AI processing
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class GitHubModelsClient:
    """Client for GitHub Models API (GPT-4.1)"""
    
    def __init__(self, api_key: str, base_url: str = "https://models.inference.ai.azure.com"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.logger = structlog.get_logger(__name__)
        
        self.logger.info(
            "GitHub Models client initialized",
            base_url=base_url
        )
    
    async def generate_content(self,
                             prompt: str,
                             model: str = "gpt-4o",
                             temperature: float = 0.1,
                             max_tokens: int = 8192,
                             correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate content using GitHub Models GPT-4.1"""
        
        start_time = time.time()
        
        self.logger.info(
            "Generating content with GitHub Models",
            correlation_id=correlation_id,
            model=model,
            prompt_length=len(prompt)
        )
        
        try:
            # Create chat completion request
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert architectural AI assistant. Always respond with valid JSON unless specifically requested otherwise."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            
            processing_time = time.time() - start_time
            
            # Extract response content
            content = response.choices[0].message.content
            
            try:
                # Parse JSON response
                result = json.loads(content)
                confidence = result.get("confidence", 0.8)
            except json.JSONDecodeError:
                # Fallback if response is not JSON
                result = {"content": content, "confidence": 0.7}
                confidence = 0.7
            
            self.logger.info(
                "GitHub Models content generated successfully",
                correlation_id=correlation_id,
                confidence=confidence,
                processing_time_ms=int(processing_time * 1000),
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0
            )
            
            return {
                "content": result,
                "confidence": confidence,
                "model_used": model,
                "processing_time": processing_time,
                "token_count": response.usage.total_tokens if response.usage else 0,
                "provider": "github_models"
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            self.logger.error(
                "GitHub Models content generation failed",
                correlation_id=correlation_id,
                error=str(e),
                processing_time_ms=int(processing_time * 1000)
            )
            
            raise Exception(f"GitHub Models generation failed: {str(e)}")
    
    async def generate_detailed_design(self,
                                     layout_data: Dict[str, Any],
                                     user_requirements: Dict[str, Any],
                                     correlation_id: str) -> Dict[str, Any]:
        """Generate detailed architectural design using GitHub Models"""
        
        prompt = self._create_detailed_design_prompt(layout_data, user_requirements)
        
        return await self.generate_content(
            prompt=prompt,
            model="gpt-4o",
            temperature=0.2,
            correlation_id=correlation_id
        )
    
    async def analyze_existing_project(self,
                                     project_data: Dict[str, Any],
                                     analysis_type: str,
                                     correlation_id: str) -> Dict[str, Any]:
        """Analyze existing Revit project using GitHub Models"""
        
        prompt = self._create_project_analysis_prompt(project_data, analysis_type)
        
        return await self.generate_content(
            prompt=prompt,
            model="gpt-4o",
            temperature=0.0,  # Deterministic for analysis
            correlation_id=correlation_id
        )
    
    async def generate_step_plan(self,
                               requirements: Dict[str, Any],
                               complexity_level: str,
                               correlation_id: str) -> Dict[str, Any]:
        """Generate step-by-step project plan using GitHub Models"""
        
        prompt = self._create_step_plan_prompt(requirements, complexity_level)
        
        return await self.generate_content(
            prompt=prompt,
            model="gpt-4o",
            temperature=0.1,
            correlation_id=correlation_id
        )
    
    def _create_detailed_design_prompt(self, 
                                     layout_data: Dict[str, Any], 
                                     user_requirements: Dict[str, Any]) -> str:
        """Create prompt for detailed architectural design"""
        
        return f"""
        You are an expert architect creating detailed Revit designs.
        
        BASIC LAYOUT:
        {json.dumps(layout_data, indent=2)}
        
        USER REQUIREMENTS:
        {json.dumps(user_requirements, indent=2)}
        
        TASK: Generate detailed design specifications including:
        1. Material selections and specifications
        2. Detailed family placements (furniture, fixtures)
        3. Electrical and mechanical considerations
        4. Sustainability features
        5. Cost estimation guidelines
        
        OUTPUT FORMAT: Return JSON with detailed specifications:
        {{
            "materials": [
                {{
                    "category": "flooring",
                    "room": "living_room",
                    "material_name": "Engineered Hardwood",
                    "specifications": "Oak, 15mm thickness",
                    "area_m2": 25.0,
                    "estimated_cost_per_m2": 80.0
                }}
            ],
            "furniture_layout": [
                {{
                    "family_name": "Sofa",
                    "type_name": "3-Seater L-Shape",
                    "room": "living_room",
                    "position": {{"x": 2000, "y": 1000, "z": 0}},
                    "rotation_degrees": 0
                }}
            ],
            "electrical_plan": [
                {{
                    "type": "outlet",
                    "room": "living_room", 
                    "wall_index": 0,
                    "height_mm": 300,
                    "position_ratio": 0.3
                }}
            ],
            "mechanical_systems": [
                {{
                    "system_type": "hvac",
                    "equipment": "Split AC Unit",
                    "capacity": "12000 BTU",
                    "location": "living_room"
                }}
            ],
            "sustainability_features": [
                "Double-glazed windows",
                "LED lighting throughout",
                "Energy-efficient appliances"
            ],
            "estimated_total_cost": 45000.0,
            "currency": "USD",
            "confidence": 0.9
        }}
        """
    
    def _create_project_analysis_prompt(self, 
                                      project_data: Dict[str, Any], 
                                      analysis_type: str) -> str:
        """Create prompt for project analysis"""
        
        return f"""
        You are an expert architectural analyst reviewing an existing Revit project.
        
        PROJECT DATA:
        {json.dumps(project_data, indent=2)}
        
        ANALYSIS TYPE: {analysis_type}
        
        TASK: Perform comprehensive analysis and provide actionable recommendations.
        
        Focus areas:
        1. Design efficiency and optimization opportunities
        2. Building code compliance issues
        3. Energy performance improvements
        4. Cost optimization possibilities
        5. Structural considerations
        6. User experience enhancements
        
        OUTPUT FORMAT: Return JSON analysis:
        {{
            "analysis_type": "{analysis_type}",
            "project_summary": {{
                "total_area_m2": 150.0,
                "number_of_rooms": 5,
                "building_type": "residential",
                "current_efficiency_score": 7.5
            }},
            "issues_found": [
                {{
                    "category": "code_compliance",
                    "severity": "high",
                    "description": "Bedroom window size below minimum requirement",
                    "location": "Bedroom 1",
                    "recommendation": "Increase window width to 1500mm"
                }}
            ],
            "optimization_opportunities": [
                {{
                    "category": "energy_efficiency",
                    "description": "Add insulation to exterior walls",
                    "estimated_savings_annual": 800.0,
                    "implementation_cost": 3500.0,
                    "payback_years": 4.4
                }}
            ],
            "recommended_improvements": [
                {{
                    "priority": "high",
                    "description": "Reconfigure kitchen layout for better workflow",
                    "estimated_cost": 8000.0,
                    "benefits": ["Better functionality", "Increased property value"]
                }}
            ],
            "confidence": 0.85
        }}
        """
    
    def _create_step_plan_prompt(self, 
                               requirements: Dict[str, Any], 
                               complexity_level: str) -> str:
        """Create prompt for step-by-step project plan"""
        
        step_count_map = {
            "simple": "5-15",
            "medium": "15-30", 
            "complex": "30-50"
        }
        
        step_count = step_count_map.get(complexity_level, "15-30")
        
        return f"""
        You are an expert project manager creating step-by-step architectural project plans.
        
        PROJECT REQUIREMENTS:
        {json.dumps(requirements, indent=2)}
        
        COMPLEXITY LEVEL: {complexity_level}
        TARGET STEP COUNT: {step_count} steps
        
        TASK: Create a detailed, sequential project plan for Revit implementation.
        
        Plan should include:
        1. Preparation and setup steps
        2. Foundation and structural elements
        3. Walls, doors, and windows
        4. Interior elements and finishes
        5. MEP (Mechanical, Electrical, Plumbing) systems
        6. Final details and documentation
        
        OUTPUT FORMAT: Return JSON with step plan:
        {{
            "complexity_level": "{complexity_level}",
            "estimated_total_hours": 40,
            "prerequisites": [
                "Revit 2026 installed",
                "Project templates prepared",
                "Site survey completed"
            ],
            "steps": [
                {{
                    "step_number": 1,
                    "title": "Create New Project",
                    "description": "Set up new Revit project using residential template",
                    "category": "setup",
                    "estimated_hours": 0.5,
                    "revit_commands": [
                        "File > New > Project",
                        "Select Architectural Template"
                    ],
                    "dependencies": [],
                    "deliverables": ["New .rvt file with template"]
                }}
            ],
            "quality_checkpoints": [
                {{
                    "after_step": 10,
                    "checkpoint_name": "Foundation Review",
                    "validation_criteria": ["All levels created", "Grid lines positioned"]
                }}
            ],
            "estimated_timeline": "2-3 weeks",
            "confidence": 0.9
        }}
        """
    
    async def generate_analysis(self, 
                              prompt: str, 
                              correlation_id: str) -> Dict[str, Any]:
        """Generate project analysis using GitHub Models"""
        
        self.logger.info(
            "Generating project analysis",
            correlation_id=correlation_id,
            prompt_length=len(prompt)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert architectural analyst providing comprehensive project analysis and recommendations."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            
            # Try to parse as JSON, fallback to structured text
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                result = {
                    "analysis": content,
                    "recommendations": [],
                    "priority_issues": [],
                    "confidence": 0.8,
                    "requires_expert_review": True
                }
            
            self.logger.info(
                "Project analysis completed",
                correlation_id=correlation_id,
                has_recommendations=len(result.get("recommendations", [])) > 0
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to generate project analysis",
                correlation_id=correlation_id,
                error=str(e)
            )
            raise