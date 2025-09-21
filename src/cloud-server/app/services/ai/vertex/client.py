"""
Vertex AI Client for ArchBuilder.AI
Implements Google Cloud Vertex AI (Gemini-2.5-Flash-Lite) integration
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel

from ....core.config import get_settings
from ....core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VertexAIClient:
    """
    Vertex AI client for ArchBuilder.AI with Gemini-2.5-Flash-Lite integration
    Optimized for Turkish building codes and cost-effective architectural tasks
    """
    
    def __init__(self):
        self.project_id = settings.VERTEX_AI_PROJECT_ID
        self.location = settings.VERTEX_AI_LOCATION
        self.model_name = "gemini-2.5-flash-lite"
        
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        
        # Configure model parameters
        self.generation_config = {
            "max_output_tokens": 32768,
            "temperature": 0.1,  # Lower temperature for consistent architectural outputs
            "top_p": 0.8,
            "top_k": 40
        }
        
        # Safety settings for architectural content
        self.safety_settings = {
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
            "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE"
        }
        
        logger.info(
            "Vertex AI client initialized",
            project_id=self.project_id,
            location=self.location,
            model=self.model_name
        )
    
    async def generate_content(
        self,
        prompt: str,
        model: str = None,
        correlation_id: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """
        Generate content using Vertex AI Gemini model
        
        Args:
            prompt: Input prompt for the model
            model: Model name override (default: gemini-2.5-flash-lite)
            correlation_id: Request correlation ID for tracking
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Dict containing generated content and metadata
        """
        
        start_time = datetime.utcnow()
        
        logger.info(
            "Generating content with Vertex AI",
            correlation_id=correlation_id,
            model=model or self.model_name,
            prompt_length=len(prompt)
        )
        
        try:
            # Override generation config if specified
            config = self.generation_config.copy()
            if temperature is not None:
                config["temperature"] = temperature
            if max_tokens is not None:
                config["max_output_tokens"] = max_tokens
            
            # Initialize model
            generative_model = GenerativeModel(
                model_name=model or self.model_name,
                generation_config=config,
                safety_settings=self.safety_settings
            )
            
            # Generate content
            response = await self._generate_async(generative_model, prompt)
            
            # Parse response
            content = response.text if response.text else ""
            
            # Extract JSON if response contains structured data
            structured_data = self._extract_json_content(content)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                "Vertex AI content generation completed",
                correlation_id=correlation_id,
                response_length=len(content),
                processing_time_seconds=processing_time,
                has_structured_data=structured_data is not None
            )
            
            return {
                "content": content,
                "structured_data": structured_data,
                "model_used": model or self.model_name,
                "processing_time_seconds": processing_time,
                "token_usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                },
                "finish_reason": response.candidates[0].finish_reason if response.candidates else "unknown",
                "safety_ratings": [
                    {
                        "category": rating.category.name,
                        "probability": rating.probability.name
                    }
                    for rating in response.candidates[0].safety_ratings
                ] if response.candidates and response.candidates[0].safety_ratings else []
            }
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.error(
                "Vertex AI content generation failed",
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
    
    async def generate_architectural_layout(
        self,
        prompt: str,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate architectural layout using specialized prompting
        """
        
        logger.info(
            "Generating architectural layout",
            correlation_id=correlation_id
        )
        
        # Use specialized architectural prompt structure
        architectural_prompt = f"""
        As an architectural AI assistant, analyze the following request and generate a detailed layout specification.

        Request: {prompt}

        Please provide your response in the following JSON format:
        {{
            "layout": {{
                "total_area_m2": <number>,
                "rooms": [
                    {{
                        "name": "<room_name>",
                        "type": "<room_type>",
                        "area_m2": <number>,
                        "dimensions": {{"width_m": <number>, "length_m": <number>}},
                        "position": {{"x": <number>, "y": <number>}},
                        "requirements": ["<requirement1>", "<requirement2>"]
                    }}
                ],
                "walls": [
                    {{
                        "start_point": {{"x": <number>, "y": <number>, "z": 0}},
                        "end_point": {{"x": <number>, "y": <number>, "z": 0}},
                        "thickness_mm": <number>,
                        "height_mm": <number>,
                        "wall_type": "<type>"
                    }}
                ],
                "doors": [
                    {{
                        "wall_index": <number>,
                        "position_on_wall": <number>,
                        "width_mm": <number>,
                        "height_mm": <number>,
                        "door_type": "<type>"
                    }}
                ],
                "windows": [
                    {{
                        "wall_index": <number>,
                        "position_on_wall": <number>,
                        "width_mm": <number>,
                        "height_mm": <number>,
                        "sill_height_mm": <number>,
                        "window_type": "<type>"
                    }}
                ]
            }},
            "compliance": {{
                "building_codes_checked": ["<code1>", "<code2>"],
                "compliance_score": <0.0-1.0>,
                "issues": ["<issue1>", "<issue2>"],
                "recommendations": ["<rec1>", "<rec2>"]
            }},
            "confidence": <0.0-1.0>,
            "requires_human_review": <boolean>
        }}
        
        Ensure all dimensions are realistic and comply with standard building codes.
        """
        
        return await self.generate_content(
            prompt=architectural_prompt,
            correlation_id=correlation_id,
            temperature=0.1  # Low temperature for consistent architectural outputs
        )
    
    async def analyze_building_codes(
        self,
        building_description: str,
        region: str,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze building compliance with regional codes
        """
        
        logger.info(
            "Analyzing building code compliance",
            correlation_id=correlation_id,
            region=region
        )
        
        compliance_prompt = f"""
        As a building code compliance expert for {region}, analyze the following building description for compliance issues:

        Building Description: {building_description}
        Region: {region}

        Please provide a comprehensive compliance analysis in JSON format:
        {{
            "compliance_analysis": {{
                "overall_score": <0.0-1.0>,
                "compliant": <boolean>,
                "violations": [
                    {{
                        "code": "<code_reference>",
                        "violation": "<description>",
                        "severity": "<low|medium|high|critical>",
                        "resolution": "<recommended_fix>"
                    }}
                ],
                "warnings": [
                    {{
                        "code": "<code_reference>",
                        "warning": "<description>",
                        "recommendation": "<suggestion>"
                    }}
                ],
                "approvals_required": ["<approval1>", "<approval2>"],
                "estimated_approval_time": "<timeframe>",
                "next_steps": ["<step1>", "<step2>"]
            }},
            "confidence": <0.0-1.0>,
            "requires_expert_review": <boolean>
        }}
        """
        
        return await self.generate_content(
            prompt=compliance_prompt,
            correlation_id=correlation_id,
            temperature=0.1
        )
    
    async def _generate_async(self, model: GenerativeModel, prompt: str):
        """Async wrapper for Vertex AI generation"""
        
        # Vertex AI doesn't have native async support, so we use asyncio
        loop = asyncio.get_event_loop()
        
        def _generate_sync():
            return model.generate_content(prompt)
        
        return await loop.run_in_executor(None, _generate_sync)
    
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
        """Get information about available Vertex AI models"""
        
        return {
            "provider": "vertex_ai",
            "available_models": [
                {
                    "name": "gemini-2.5-flash-lite",
                    "max_tokens": 32768,
                    "languages": ["en", "tr", "de", "fr", "es"],
                    "specialties": ["cad_analysis", "building_codes", "architectural_prompts"],
                    "cost": "low"
                }
            ],
            "default_model": self.model_name,
            "project_id": self.project_id,
            "location": self.location
        }