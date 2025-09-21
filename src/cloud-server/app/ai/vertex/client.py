"""
Vertex AI Client for ArchBuilder.AI
Handles Google Cloud Vertex AI Gemini-2.5-Flash-Lite integration
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import structlog
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic as aip
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class VertexAIClient:
    """Client for Google Cloud Vertex AI Gemini models"""
    
    def __init__(self, 
                 project_id: str,
                 location: str = "us-central1",
                 credentials_path: Optional[str] = None):
        self.project_id = project_id
        self.location = location
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Vertex AI
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            aiplatform.init(
                project=project_id,
                location=location,
                credentials=credentials
            )
        else:
            aiplatform.init(project=project_id, location=location)
        
        self.logger.info(
            "Vertex AI client initialized",
            project_id=project_id,
            location=location
        )
    
    async def generate_content(self,
                             prompt: str,
                             model: str = "gemini-2.5-flash-lite",
                             temperature: float = 0.1,
                             max_tokens: int = 8192,
                             correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate content using Vertex AI Gemini models"""
        
        start_time = time.time()
        
        self.logger.info(
            "Generating content with Vertex AI",
            correlation_id=correlation_id,
            model=model,
            prompt_length=len(prompt)
        )
        
        try:
            # Initialize the Gemini model
            model_instance = GenerativeModel(model)
            
            # Configure generation parameters
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json"
            )
            
            # Generate content asynchronously
            response = await asyncio.to_thread(
                model_instance.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            processing_time = time.time() - start_time
            
            # Extract response content
            content = response.text if response.text else "{}"
            
            try:
                # Parse JSON response
                result = json.loads(content)
                confidence = result.get("confidence", 0.8)
            except json.JSONDecodeError:
                # Fallback if response is not JSON
                result = {"content": content, "confidence": 0.7}
                confidence = 0.7
            
            self.logger.info(
                "Vertex AI content generated successfully",
                correlation_id=correlation_id,
                confidence=confidence,
                processing_time_ms=int(processing_time * 1000),
                response_tokens=len(content.split())
            )
            
            return {
                "content": result,
                "confidence": confidence,
                "model_used": model,
                "processing_time": processing_time,
                "token_count": len(content.split()),
                "provider": "vertex_ai"
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            self.logger.error(
                "Vertex AI content generation failed",
                correlation_id=correlation_id,
                error=str(e),
                processing_time_ms=int(processing_time * 1000)
            )
            
            raise Exception(f"Vertex AI generation failed: {str(e)}")
    
    async def generate_layout(self,
                            room_program: Dict[str, Any],
                            building_codes: List[str],
                            correlation_id: str) -> Dict[str, Any]:
        """Generate architectural layout using Vertex AI"""
        
        prompt = self._create_layout_prompt(room_program, building_codes)
        
        return await self.generate_content(
            prompt=prompt,
            model="gemini-2.5-flash-lite",
            temperature=0.1,
            correlation_id=correlation_id
        )
    
    async def analyze_building_codes(self,
                                   document_content: str,
                                   region: str,
                                   correlation_id: str) -> Dict[str, Any]:
        """Analyze building code documents using Vertex AI"""
        
        prompt = self._create_building_code_prompt(document_content, region)
        
        return await self.generate_content(
            prompt=prompt,
            model="gemini-2.5-flash-lite",
            temperature=0.0,  # Deterministic for code analysis
            correlation_id=correlation_id
        )
    
    def _create_layout_prompt(self, 
                            room_program: Dict[str, Any], 
                            building_codes: List[str]) -> str:
        """Create structured prompt for layout generation"""
        
        return f"""
        You are an expert architect creating Revit-compatible layouts.
        
        ROOM PROGRAM:
        {json.dumps(room_program, indent=2)}
        
        APPLICABLE BUILDING CODES:
        {', '.join(building_codes)}
        
        TASK: Generate a JSON response with exact coordinates for:
        1. Wall lines (start/end points in millimeters)
        2. Door positions (wall location + offset)
        3. Window positions (wall location + offset)
        
        CONSTRAINTS:
        - All coordinates in millimeters
        - Minimum room size: 5m²
        - Standard door width: 800-1000mm
        - Standard window width: 1000-2000mm
        - Comply with Turkish building codes for residential buildings
        
        OUTPUT FORMAT: Return ONLY valid JSON matching this schema:
        {{
            "walls": [
                {{
                    "start_point": {{"x": 0, "y": 0, "z": 0}},
                    "end_point": {{"x": 5000, "y": 0, "z": 0}},
                    "height_mm": 2700,
                    "wall_type_name": "Generic - 200mm",
                    "level_name": "Level 1"
                }}
            ],
            "doors": [
                {{
                    "wall_index": 0,
                    "position_ratio": 0.5,
                    "width_mm": 900,
                    "height_mm": 2100,
                    "family_name": "Single-Flush",
                    "type_name": "0915 x 2134mm"
                }}
            ],
            "windows": [
                {{
                    "wall_index": 1,
                    "position_ratio": 0.5,
                    "width_mm": 1200,
                    "height_mm": 1200,
                    "family_name": "Fixed",
                    "type_name": "1220 x 1220mm"
                }}
            ],
            "rooms": [
                {{
                    "name": "Oturma Odası",
                    "area_m2": 25.0,
                    "boundary_walls": [0, 1, 2, 3]
                }}
            ],
            "confidence": 0.95,
            "requires_human_review": false
        }}
        """
    
    def _create_building_code_prompt(self, 
                                   document_content: str, 
                                   region: str) -> str:
        """Create prompt for building code analysis"""
        
        return f"""
        You are an expert building code analyst for {region} region.
        
        DOCUMENT CONTENT:
        {document_content}
        
        TASK: Extract key architectural requirements and constraints from this building code document.
        
        Focus on:
        1. Minimum room sizes and dimensions
        2. Door and window requirements
        3. Accessibility standards
        4. Fire safety requirements
        5. Structural requirements
        6. Energy efficiency standards
        
        OUTPUT FORMAT: Return JSON with extracted rules:
        {{
            "region": "{region}",
            "document_type": "building_code",
            "extracted_rules": [
                {{
                    "category": "room_sizes",
                    "rule": "Minimum bedroom size 9m²",
                    "numeric_value": 9.0,
                    "unit": "m2",
                    "applies_to": ["bedroom"]
                }}
            ],
            "accessibility_requirements": [],
            "fire_safety_requirements": [],
            "energy_efficiency_requirements": [],
            "confidence": 0.9
        }}
        """