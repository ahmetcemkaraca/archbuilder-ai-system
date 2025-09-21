"""
AI Service Implementation for ArchBuilder.AI
Handles Vertex AI (Gemini-2.5-Flash-Lite) and GitHub Models (GPT-4.1) integration
with comprehensive validation, fallback mechanisms, and performance optimization
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
import structlog
from pydantic import BaseModel, Field, ValidationError
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models.ai import (
    AICommandRequest,
    AICommandResponse, 
    AIProvider,
    AIProcessingStatus,
    AIModelConfig,
    AIValidationResult
)
from app.models.documents import DocumentType
from app.core.exceptions import (
    AIServiceException,
    AIModelUnavailableException,
    AIValidationFailedException,
    NetworkException
)
from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.validation_service import ValidationService
from app.utils.cache import AsyncCache
from app.utils.performance import PerformanceTracker

logger = structlog.get_logger(__name__)

class AIModelSelector:
    """Dynamic AI model selection for ArchBuilder.AI with Vertex AI and GitHub Models"""
    
    def __init__(self):
        self.model_config = {
            "vertex_ai": {
                "gemini-2.5-flash-lite": {
                    "languages": ["en", "tr", "de", "fr", "es"], 
                    "max_tokens": 32768,
                    "specialties": ["cad_analysis", "building_codes", "architectural_prompts"],
                    "cost": "low",
                    "recommended_for": ["simple_tasks", "prompt_generation", "turkish_codes"]
                }
            },
            "github_models": {
                "gpt-4.1": {
                    "languages": ["en", "tr", "de", "fr", "es"], 
                    "max_tokens": 128000,
                    "specialties": ["complex_reasoning", "multi_format_parsing", "revit_commands"],
                    "cost": "medium",
                    "recommended_for": ["complex_analysis", "multi_format_cad", "existing_project_analysis"]
                }
            }
        }
    
    def select_model(
        self,
        language: str = "en",
        document_type: Optional[str] = None,
        complexity: str = "medium",
        file_format: Optional[str] = None,
        analysis_type: str = "creation",
        user_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Select optimal AI model based on context for ArchBuilder.AI"""
        
        logger.info(
            "Selecting AI model",
            language=language,
            document_type=document_type,
            complexity=complexity,
            file_format=file_format,
            analysis_type=analysis_type
        )
        
        # Priority order based on task requirements  
        if analysis_type == "existing_project_analysis":
            # Existing project analysis - use GitHub Models for BIM intelligence
            return {
                "provider": "github_models",
                "model": "gpt-4.1",
                "reason": "Best for comprehensive BIM analysis and improvement recommendations",
                "confidence": 0.95
            }
        elif document_type == "building_code" and language == "tr":
            # Turkish building codes - use Vertex AI for regulatory documents
            return {
                "provider": "vertex_ai",
                "model": "gemini-2.5-flash-lite",
                "reason": "Optimized for Turkish regulatory documents and building codes",
                "confidence": 0.90
            }
        elif file_format in ["dwg", "dxf", "ifc"] or complexity == "high":
            # CAD file analysis and complex technical tasks - use GitHub Models
            return {
                "provider": "github_models", 
                "model": "gpt-4.1",
                "reason": "Superior for multi-format CAD parsing and complex reasoning",
                "confidence": 0.92
            }
        elif complexity == "simple" or document_type == "prompt_generation":
            # Simple tasks and prompt generation - use Vertex AI (cost-effective)
            return {
                "provider": "vertex_ai",
                "model": "gemini-2.5-flash-lite", 
                "reason": "Cost-effective for simple architectural tasks",
                "confidence": 0.85
            }
        elif user_preference:
            # Honor user preference if specified
            if user_preference in ["vertex_ai", "github_models"]:
                preferred_models = self.model_config.get(user_preference, {})
                if preferred_models:
                    model_name = list(preferred_models.keys())[0]
                    return {
                        "provider": user_preference,
                        "model": model_name,
                        "reason": f"User preferred {user_preference}",
                        "confidence": 0.80
                    }
        
        # Default to GitHub Models for comprehensive architectural reasoning
        return {
            "provider": "github_models",
            "model": "gpt-4.1",
            "reason": "Reliable for comprehensive architectural analysis",
            "confidence": 0.88
        }


class ArchitecturalPromptEngine:
    """Structured prompt engineering for architectural AI tasks with multi-language support"""
    
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, Dict[str, str]]:
        """Load localized prompt templates"""
        return {
            "layout_generation": {
                "en": """You are an expert architect creating Revit-compatible layouts.
                
REQUIREMENTS:
- Total area: {total_area} m²
- Building type: {building_type}
- Rooms: {room_requirements}
- Style: {style_preferences}
- Regional context: {region}

THINK STEP BY STEP:
1. Analyze spatial requirements and create logical room adjacency matrix
2. Calculate room dimensions based on area requirements and building codes
3. Design building envelope with proper orientation
4. Plan interior walls for optimal circulation
5. Position doors for accessibility and flow
6. Position windows for natural light and ventilation
7. Validate against {region} building codes

CONSTRAINTS:
- All coordinates in millimeters
- Minimum room size: 5m² (or regional minimum)
- Door width: 800-1000mm (accessibility: min 900mm)
- Window area: minimum 1/8 of floor area
- Consider {climate_zone} climate requirements

OUTPUT FORMAT: Return ONLY valid JSON matching LayoutResult schema.""",
                
                "tr": """Revit uyumlu mimari plan tasarlayan uzman mimarsınız.

GEREKSİNİMLER:
- Toplam alan: {total_area} m²
- Yapı türü: {building_type}
- Odalar: {room_requirements}
- Stil: {style_preferences}
- Bölgesel bağlam: {region}

ADIM ADIM DÜŞÜNÜN:
1. Mekansal gereksinimleri analiz edin ve mantıklı oda komşuluk matrisi oluşturun
2. Alan gereksinimlerine ve yapı yönetmeliğine göre oda boyutlarını hesaplayın
3. Uygun yönelim ile yapı kabuğunu tasarlayın
4. Optimal sirkülasyon için iç duvarları planlayın
5. Erişilebilirlik ve akış için kapıları konumlandırın
6. Doğal ışık ve havalandırma için pencereleri konumlandırın
7. {region} yapı yönetmeliğine göre doğrulayın

KISITLAR:
- Tüm koordinatlar milimetre cinsinden
- Minimum oda alanı: 5m² (veya bölgesel minimum)
- Kapı genişliği: 800-1000mm (erişilebilirlik: min 900mm)
- Pencere alanı: kat alanının minimum 1/8'i
- {climate_zone} iklim gereksinimlerini dikkate alın

ÇIKTI FORMATI: Yalnızca LayoutResult şemasına uygun geçerli JSON döndürün."""
            },
            
            "validation": {
                "en": """Review this architectural layout for compliance and errors.

LAYOUT DATA:
{layout_data}

VALIDATION CHECKLIST:
1. Geometric validity (no overlapping walls, proper connections)
2. Spatial constraints (minimum room sizes, door clearances)
3. Building code compliance (fire exits, accessibility, {region} codes)
4. Architectural logic (room adjacencies, circulation patterns)
5. Revit API compatibility (valid element references)

REGIONAL CODES ({region}):
{regional_building_codes}

RESPOND WITH:
{{
  "is_valid": true/false,
  "confidence_score": 0.0-1.0,
  "errors": ["specific error descriptions"],
  "warnings": ["potential issues"],
  "suggestions": ["recommended improvements"],
  "code_compliance": {{
    "accessibility": true/false,
    "fire_egress": true/false,
    "spatial_requirements": true/false,
    "regional_compliance": true/false
  }}
}}""",
                
                "tr": """Bu mimari planı uygunluk ve hatalar açısından inceleyin.

PLAN VERİLERİ:
{layout_data}

DOĞRULAMA LİSTESİ:
1. Geometrik geçerlilik (çakışan duvarlar yok, doğru bağlantılar)
2. Mekansal kısıtlar (minimum oda boyutları, kapı boşlukları)
3. Yapı yönetmeliği uygunluğu (yangın çıkışları, erişilebilirlik, {region} kodları)
4. Mimari mantık (oda komşulukları, sirkülasyon desenleri)
5. Revit API uyumluluğu (geçerli eleman referansları)

BÖLGESEL KODLAR ({region}):
{regional_building_codes}

YANIT:
{{
  "is_valid": true/false,
  "confidence_score": 0.0-1.0,
  "errors": ["spesifik hata açıklamaları"],
  "warnings": ["potansiyel sorunlar"],
  "suggestions": ["önerilen iyileştirmeler"],
  "code_compliance": {{
    "accessibility": true/false,
    "fire_egress": true/false,
    "spatial_requirements": true/false,
    "regional_compliance": true/false
  }}
}}"""
            }
        }
    
    async def create_layout_prompt(
        self,
        request: Dict[str, Any],
        correlation_id: str,
        language: str = "en"
    ) -> str:
        """Generate optimized prompt for layout generation with RAG context"""
        
        # Get regional building codes through RAG
        regional_context = await self._get_regional_context(
            request.get("region", "Turkey"),
            language,
            correlation_id
        )
        
        # Detect language if not provided
        if language == "auto":
            language = self._detect_language(request.get("prompt", ""))
        
        template = self.prompt_templates["layout_generation"].get(language, 
                   self.prompt_templates["layout_generation"]["en"])
        
        return template.format(
            total_area=request.get("total_area_m2", 100),
            building_type=request.get("building_type", "residential"),
            room_requirements=request.get("room_requirements", []),
            style_preferences=request.get("style_preferences", "modern"),
            region=request.get("region", "Turkey"),
            climate_zone=request.get("climate_zone", "temperate"),
            regional_building_codes=regional_context
        )
    
    async def _get_regional_context(
        self,
        region: str,
        language: str,
        correlation_id: str
    ) -> str:
        """Get regional building codes and context through RAG"""
        
        try:
            # Query RAG for regional building codes
            rag_query = f"{region} building codes regulations {language}"
            rag_result = await self.rag_service.query_knowledge_base(
                query=rag_query,
                max_results=5,
                correlation_id=correlation_id
            )
            
            if rag_result and hasattr(rag_result, 'documents') and rag_result.documents:
                # Combine relevant building code documents
                context_parts = []
                for doc in rag_result.documents[:3]:  # Top 3 most relevant
                    content = getattr(doc, 'content', str(doc))
                    context_parts.append(f"- {content[:200]}...")
                
                return "\n".join(context_parts)
            
        except Exception as e:
            logger.warning(
                "Failed to get regional context from RAG",
                region=region,
                language=language,
                error=str(e),
                correlation_id=correlation_id
            )
        
        # Fallback to basic regional information
        return self._get_basic_regional_info(region, language)
    
    def _get_basic_regional_info(self, region: str, language: str) -> str:
        """Get basic regional building information as fallback"""
        
        basic_info = {
            "Turkey": {
                "en": "Turkish Building Regulations: Min ceiling height 2.4m residential, min room 9m² bedroom, fire exit max 30m travel distance",
                "tr": "Türkiye Yapı Yönetmeliği: Min tavan yüksekliği 2.4m konut, min oda 9m² yatak odası, yangın çıkışı max 30m yürüme mesafesi"
            },
            "Germany": {
                "en": "German DIN standards: Min ceiling height 2.4m, accessibility requirements DIN 18040",
                "de": "Deutsche DIN-Normen: Min Deckenhöhe 2.4m, Barrierefreiheit DIN 18040"
            }
        }
        
        return basic_info.get(region, {}).get(language, 
               "International building standards: Min ceiling height 2.4m, accessibility compliance required")
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection for user prompts"""
        
        # Turkish indicators
        turkish_words = ["oda", "salon", "mutfak", "banyo", "yatak", "daire", "ev", "bina"]
        if any(word in text.lower() for word in turkish_words):
            return "tr"
        
        # German indicators  
        german_words = ["zimmer", "wohnzimmer", "küche", "bad", "schlafzimmer", "wohnung", "haus"]
        if any(word in text.lower() for word in german_words):
            return "de"
        
        # Default to English
        return "en"


class AIFallbackService:
    """Rule-based fallback service when AI fails or produces invalid outputs"""
    
    def __init__(self, validation_service: Optional[ValidationService] = None):
        self.validation_service = validation_service
    
    async def generate_layout_fallback(
        self,
        request: Dict[str, Any],
        correlation_id: str,
        failure_reason: str
    ) -> Dict[str, Any]:
        """Generate layout using rule-based algorithms as fallback"""
        
        logger.info(
            "Using rule-based fallback for layout generation",
            failure_reason=failure_reason,
            correlation_id=correlation_id
        )
        
        try:
            # Extract basic requirements
            total_area = request.get("total_area_m2", 100)
            building_type = request.get("building_type", "residential")
            room_requirements = request.get("room_requirements", [])
            
            if not room_requirements:
                # Default room program for residential
                room_requirements = [
                    {"name": "Living Room", "area": total_area * 0.3},
                    {"name": "Kitchen", "area": total_area * 0.15},
                    {"name": "Bedroom", "area": total_area * 0.25},
                    {"name": "Bathroom", "area": total_area * 0.1}
                ]
            
            # Simple rectangular layout algorithm
            layout = await self._generate_rectangular_layout(
                total_area, room_requirements, correlation_id
            )
            
            # Validate fallback layout if validation service available
            validation_result = {"is_valid": True, "errors": [], "warnings": []}
            if self.validation_service:
                try:
                    validation_result = await self.validation_service.validate_layout(
                        layout, correlation_id
                    )
                except Exception as e:
                    logger.warning("Validation failed for fallback layout", error=str(e))
            
            return {
                "layout": layout,
                "metadata": {
                    "confidence": 0.7,  # Lower confidence for rule-based
                    "generated_by": "fallback",
                    "fallback_reason": failure_reason,
                    "requires_human_review": True,
                    "validation": validation_result
                }
            }
            
        except Exception as e:
            logger.error(
                "Fallback layout generation failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise Exception(
                f"Both AI and fallback layout generation failed: {str(e)}"
            )
    
    async def _generate_rectangular_layout(
        self,
        total_area: float,
        room_requirements: List[Dict[str, Any]],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Generate simple rectangular room layout"""
        
        import math
        
        room_count = len(room_requirements)
        
        # Calculate overall building dimensions
        # Assume roughly square building with 20% circulation
        usable_area = total_area * 0.8
        building_width = math.sqrt(usable_area * 1.2)  # Slightly rectangular
        building_length = usable_area / building_width
        
        # Convert to millimeters
        building_width_mm = building_width * 1000
        building_length_mm = building_length * 1000
        
        walls = []
        doors = []
        windows = []
        rooms = []
        
        # Create exterior walls
        exterior_walls = [
            # South wall
            {
                "id": "wall_exterior_south",
                "start_point": {"x": 0, "y": 0, "z": 0},
                "end_point": {"x": building_width_mm, "y": 0, "z": 0},
                "height_mm": 2700,
                "wall_type_name": "Generic - 300mm",
                "level_name": "Level 1",
                "is_exterior": True
            },
            # East wall
            {
                "id": "wall_exterior_east", 
                "start_point": {"x": building_width_mm, "y": 0, "z": 0},
                "end_point": {"x": building_width_mm, "y": building_length_mm, "z": 0},
                "height_mm": 2700,
                "wall_type_name": "Generic - 300mm",
                "level_name": "Level 1",
                "is_exterior": True
            },
            # North wall
            {
                "id": "wall_exterior_north",
                "start_point": {"x": building_width_mm, "y": building_length_mm, "z": 0},
                "end_point": {"x": 0, "y": building_length_mm, "z": 0},
                "height_mm": 2700,
                "wall_type_name": "Generic - 300mm",
                "level_name": "Level 1",
                "is_exterior": True
            },
            # West wall
            {
                "id": "wall_exterior_west",
                "start_point": {"x": 0, "y": building_length_mm, "z": 0},
                "end_point": {"x": 0, "y": 0, "z": 0},
                "height_mm": 2700,
                "wall_type_name": "Generic - 300mm",
                "level_name": "Level 1",
                "is_exterior": True
            }
        ]
        
        walls.extend(exterior_walls)
        
        # Add entrance door
        doors.append({
            "id": "door_entrance",
            "host_wall_id": "wall_exterior_south",
            "position_ratio": 0.1,  # Near the corner
            "family_name": "Single-Flush",
            "type_name": "0915 x 2134mm",
            "width_mm": 915,
            "height_mm": 2134
        })
        
        # Add windows to exterior walls
        for i, wall in enumerate(exterior_walls):
            if wall["id"] != "wall_exterior_south":  # Skip entrance wall
                windows.append({
                    "id": f"window_{wall['id']}",
                    "host_wall_id": wall["id"],
                    "position_ratio": 0.5,  # Center of wall
                    "family_name": "Fixed",
                    "type_name": "1220 x 1830mm",
                    "width_mm": 1220,
                    "height_mm": 1830
                })
        
        # Create grid layout for rooms
        grid_cols = math.ceil(math.sqrt(room_count))
        grid_rows = math.ceil(room_count / grid_cols)
        
        room_width = (building_width_mm - 400) / grid_cols  # 200mm walls
        room_height = (building_length_mm - 400) / grid_rows
        
        for i, room_req in enumerate(room_requirements):
            row = i // grid_cols
            col = i % grid_cols
            
            room_x = 200 + col * room_width  # 200mm offset for exterior wall
            room_y = 200 + row * room_height
            
            # Create room
            room = {
                "id": f"room_{i}",
                "name": room_req.get("name", f"Room {i+1}"),
                "area": (room_width * room_height) / 1_000_000,  # Convert to m²
                "function": self._infer_room_function(room_req.get("name", "")),
                "accessibility_compliant": True
            }
            rooms.append(room)
            
            # Add interior walls if not on grid boundary
            if col < grid_cols - 1:  # Vertical divider
                walls.append({
                    "id": f"wall_interior_v_{i}",
                    "start_point": {"x": room_x + room_width, "y": room_y, "z": 0},
                    "end_point": {"x": room_x + room_width, "y": room_y + room_height, "z": 0},
                    "height_mm": 2700,
                    "wall_type_name": "Generic - 200mm",
                    "level_name": "Level 1",
                    "is_exterior": False
                })
            
            if row < grid_rows - 1:  # Horizontal divider
                walls.append({
                    "id": f"wall_interior_h_{i}",
                    "start_point": {"x": room_x, "y": room_y + room_height, "z": 0},
                    "end_point": {"x": room_x + room_width, "y": room_y + room_height, "z": 0},
                    "height_mm": 2700,
                    "wall_type_name": "Generic - 200mm",
                    "level_name": "Level 1",
                    "is_exterior": False
                })
            
            # Add interior doors for circulation
            if col > 0:  # Door to left room
                doors.append({
                    "id": f"door_room_{i}_left",
                    "host_wall_id": f"wall_interior_v_{i-1}",
                    "position_ratio": 0.5,
                    "family_name": "Single-Flush",
                    "type_name": "0815 x 2134mm",
                    "width_mm": 815,
                    "height_mm": 2134
                })
        
        logger.info(
            "Generated fallback rectangular layout",
            room_count=len(rooms),
            wall_count=len(walls),
            door_count=len(doors),
            window_count=len(windows),
            correlation_id=correlation_id
        )
        
        return {
            "walls": walls,
            "doors": doors,
            "windows": windows,
            "rooms": rooms,
            "building_envelope": {
                "width_mm": building_width_mm,
                "length_mm": building_length_mm,
                "height_mm": 2700,
                "total_area_m2": total_area
            }
        }
    
    def _infer_room_function(self, room_name: str) -> str:
        """Infer room function from name for categorization"""
        
        name_lower = room_name.lower()
        
        if any(word in name_lower for word in ["living", "salon", "oturma"]):
            return "living"
        elif any(word in name_lower for word in ["kitchen", "mutfak"]):
            return "kitchen"
        elif any(word in name_lower for word in ["bedroom", "yatak", "oda"]):
            return "bedroom"
        elif any(word in name_lower for word in ["bathroom", "banyo", "wc"]):
            return "bathroom"
        elif any(word in name_lower for word in ["office", "ofis", "çalışma"]):
            return "office"
        else:
            return "general"


class AIService:
    """Comprehensive AI service with dual provider support, caching, and fallback mechanisms"""
    
    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        validation_service: Optional[ValidationService] = None,
        cache: Optional[AsyncCache] = None,
        performance_tracker: Optional[PerformanceTracker] = None
    ):
        self.rag_service = rag_service
        self.validation_service = validation_service
        self.cache = cache
        self.performance_tracker = performance_tracker
        
        # Initialize AI components
        self.model_selector = AIModelSelector()
        self.prompt_engine = ArchitecturalPromptEngine(rag_service) if rag_service else None
        self.fallback_service = AIFallbackService(validation_service)
        
        # HTTP clients for AI providers
        self.vertex_client = None
        self.github_client = None
        
        # Initialize clients if settings available
        try:
            if hasattr(settings, 'VERTEX_AI_BASE_URL'):
                self.vertex_client = httpx.AsyncClient(
                    base_url=settings.VERTEX_AI_BASE_URL,
                    headers={"Authorization": f"Bearer {settings.VERTEX_AI_API_KEY}"},
                    timeout=30.0
                )
        except:
            logger.warning("Vertex AI client initialization failed")
        
        try:
            if hasattr(settings, 'GITHUB_MODELS_BASE_URL'):
                self.github_client = httpx.AsyncClient(
                    base_url=settings.GITHUB_MODELS_BASE_URL,
                    headers={"Authorization": f"Bearer {settings.GITHUB_MODELS_API_KEY}"},
                    timeout=30.0
                )
        except:
            logger.warning("GitHub Models client initialization failed")
        
        logger.info("AI Service initialized with dual provider support")
    
    async def process_command(
        self,
        request: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Process AI command with comprehensive error handling and fallback"""
        
        start_time = time.time()
        
        logger.info(
            "Starting AI command processing",
            command_type=request.get("command_type", "unknown"),
            correlation_id=correlation_id
        )
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_result = None
            
            if self.cache:
                try:
                    cached_result = await self.cache.get(cache_key)
                except Exception as e:
                    logger.warning("Cache retrieval failed", error=str(e))
            
            if cached_result:
                logger.info("AI command result served from cache", correlation_id=correlation_id)
                return cached_result
            
            # Select appropriate AI model
            model_selection = self.model_selector.select_model(
                language=request.get("language", "en"),
                document_type=request.get("document_type"),
                complexity=request.get("complexity", "medium"),
                file_format=request.get("file_format"),
                analysis_type=request.get("analysis_type", "creation")
            )
            
            logger.info(
                "AI model selected",
                provider=model_selection["provider"],
                model=model_selection["model"],
                reason=model_selection["reason"],
                correlation_id=correlation_id
            )
            
            # Generate optimized prompt
            prompt = "Default prompt"
            if self.prompt_engine:
                try:
                    prompt = await self.prompt_engine.create_layout_prompt(
                        request,
                        correlation_id,
                        language=request.get("language", "en")
                    )
                except Exception as e:
                    logger.warning("Prompt generation failed, using basic prompt", error=str(e))
                    prompt = f"Create architectural layout: {request.get('prompt', 'Default request')}"
            
            # Process with selected AI model
            ai_result = await self._process_with_ai_model(
                prompt,
                model_selection,
                correlation_id
            )
            
            # Validate AI output
            validation_result = {"is_valid": True, "requires_human_review": False}
            if self.validation_service:
                try:
                    validation_result = await self.validation_service.validate_ai_output(
                        ai_result,
                        correlation_id
                    )
                except Exception as e:
                    logger.warning("AI output validation failed", error=str(e))
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Create response
            response = {
                "correlation_id": correlation_id,
                "status": "completed",
                "generated_content": ai_result,
                "model_used": model_selection["model"],
                "provider": model_selection["provider"],
                "confidence_score": ai_result.get("confidence", model_selection.get("confidence", 0.8)),
                "validation_result": validation_result,
                "requires_human_review": validation_result.get("requires_human_review", False),
                "processing_time_ms": processing_time_ms
            }
            
            # Cache successful results
            if self.cache and validation_result.get("is_valid", True):
                try:
                    await self.cache.set(
                        cache_key,
                        response,
                        ttl=3600  # Cache for 1 hour
                    )
                except Exception as e:
                    logger.warning("Cache storage failed", error=str(e))
            
            logger.info(
                "AI command processing completed successfully",
                confidence=response["confidence_score"],
                requires_review=response["requires_human_review"],
                correlation_id=correlation_id
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "AI command processing failed, attempting fallback",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            # Attempt fallback
            try:
                fallback_result = await self.fallback_service.generate_layout_fallback(
                    request,
                    correlation_id,
                    f"AI processing failed: {str(e)}"
                )
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "correlation_id": correlation_id,
                    "status": "completed",
                    "generated_content": fallback_result["layout"],
                    "model_used": "fallback",
                    "provider": "fallback",
                    "confidence_score": fallback_result["metadata"]["confidence"],
                    "validation_result": fallback_result["metadata"]["validation"],
                    "requires_human_review": True,
                    "processing_time_ms": processing_time_ms,
                    "fallback_used": True,
                    "fallback_reason": str(e)
                }
                
            except Exception as fallback_error:
                logger.error(
                    "Both AI and fallback processing failed",
                    ai_error=str(e),
                    fallback_error=str(fallback_error),
                    correlation_id=correlation_id,
                    exc_info=True
                )
                
                return {
                    "correlation_id": correlation_id,
                    "status": "failed",
                    "error_message": f"AI processing failed: {str(e)}. Fallback also failed: {str(fallback_error)}",
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
    
    async def _process_with_ai_model(
        self,
        prompt: str,
        model_selection: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Process prompt with selected AI model with basic retry logic"""
        
        provider = model_selection["provider"]
        model_name = model_selection["model"]
        
        if provider == "vertex_ai" and self.vertex_client:
            return await self._call_vertex_ai(prompt, model_name, correlation_id)
        elif provider == "github_models" and self.github_client:
            return await self._call_github_models(prompt, model_name, correlation_id)
        else:
            logger.warning(f"AI provider {provider} not available, using mock response")
            # Mock response for testing
            return {
                "walls": [],
                "doors": [],
                "windows": [],
                "rooms": [{"name": "Mock Room", "area": 20}],
                "confidence": 0.5,
                "mock_response": True
            }
    
    async def _call_vertex_ai(
        self,
        prompt: str,
        model_name: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Call Vertex AI Gemini-2.5-Flash-Lite model"""
        
        logger.info(
            "Calling Vertex AI",
            model=model_name,
            correlation_id=correlation_id
        )
        
        try:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 4000,
                    "responseMimeType": "application/json"
                }
            }
            
            response = await self.vertex_client.post(
                f"/v1/projects/{settings.VERTEX_AI_PROJECT_ID}/locations/{settings.VERTEX_AI_LOCATION}/publishers/google/models/{model_name}:generateContent",
                json=payload,
                headers={"X-Correlation-ID": correlation_id}
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract content from Vertex AI response
            if "candidates" in result and result["candidates"]:
                content_text = result["candidates"][0]["content"]["parts"][0]["text"]
                ai_output = json.loads(content_text)
                
                logger.info(
                    "Vertex AI call successful",
                    model=model_name,
                    correlation_id=correlation_id
                )
                
                return ai_output
            else:
                raise Exception("Empty response from Vertex AI")
                
        except Exception as e:
            logger.error(
                "Vertex AI call failed",
                model=model_name,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def _call_github_models(
        self,
        prompt: str,
        model_name: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Call GitHub Models GPT-4.1"""
        
        logger.info(
            "Calling GitHub Models",
            model=model_name,
            correlation_id=correlation_id
        )
        
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert architect specializing in BIM and Revit. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"}
            }
            
            response = await self.github_client.post(
                "/chat/completions",
                json=payload,
                headers={"X-Correlation-ID": correlation_id}
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract content from GitHub Models response
            if "choices" in result and result["choices"]:
                content_text = result["choices"][0]["message"]["content"]
                ai_output = json.loads(content_text)
                
                logger.info(
                    "GitHub Models call successful",
                    model=model_name,
                    correlation_id=correlation_id
                )
                
                return ai_output
            else:
                raise Exception("Empty response from GitHub Models")
                
        except Exception as e:
            logger.error(
                "GitHub Models call failed",
                model=model_name,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    def _generate_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate cache key for AI request"""
        
        # Create stable hash from request content
        cache_data = {
            "prompt": request.get("prompt", ""),
            "command_type": request.get("command_type", ""),
            "context": {k: v for k, v in (request.get("context", {})).items() 
                       if k not in ["correlation_id", "timestamp"]}
        }
        
        cache_json = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_json.encode()).hexdigest()
        
        return f"ai_command:{cache_hash[:16]}"
    
    async def analyze_existing_project(
        self,
        project_data: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Analyze existing Revit project and provide improvement recommendations"""
        
        logger.info(
            "Starting existing project analysis",
            project_element_count=project_data.get("total_elements", 0),
            correlation_id=correlation_id
        )
        
        # Use GitHub Models for comprehensive BIM analysis
        model_selection = {
            "provider": "github_models",
            "model": "gpt-4.1",
            "reason": "Best for comprehensive BIM analysis"
        }
        
        # Create specialized prompt for project analysis
        analysis_prompt = f"""
        Analyze this existing Revit project and provide improvement recommendations:

        PROJECT DATA:
        {json.dumps(project_data, indent=2)}

        ANALYSIS CATEGORIES:
        1. BIM Model Optimization (file size, performance, organization)
        2. Design Improvements (spatial layout, accessibility, code compliance)
        3. Technical Enhancements (MEP integration, structural optimization)
        4. Energy Performance (thermal, lighting, HVAC efficiency)

        For each recommendation, provide:
        - Priority (High/Medium/Low)
        - Implementation effort (Hours/Days/Weeks)
        - Expected impact (Performance/Cost/Quality improvement)
        - Specific Revit implementation steps

        Respond with structured JSON format.
        """
        
        try:
            ai_result = await self._process_with_ai_model(
                analysis_prompt,
                model_selection,
                correlation_id
            )
            
            logger.info(
                "Existing project analysis completed",
                recommendation_count=len(ai_result.get("recommendations", [])),
                correlation_id=correlation_id
            )
            
            return ai_result
        except Exception as e:
            logger.error(
                "Project analysis failed",
                error=str(e),
                correlation_id=correlation_id
            )
            
            # Return basic analysis structure
            return {
                "analysis": "Basic analysis unavailable due to AI service error",
                "recommendations": [],
                "error": str(e),
                "confidence": 0.0
            }
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get status of all AI models"""
        
        status = {}
        
        # Check Vertex AI
        if self.vertex_client:
            try:
                health_response = await self.vertex_client.get("/health", timeout=5.0)
                status["vertex_ai"] = {
                    "status": "healthy" if health_response.status_code == 200 else "unhealthy",
                    "response_time_ms": health_response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                status["vertex_ai"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            status["vertex_ai"] = {"status": "not_configured"}
        
        # Check GitHub Models
        if self.github_client:
            try:
                health_response = await self.github_client.get("/health", timeout=5.0)
                status["github_models"] = {
                    "status": "healthy" if health_response.status_code == 200 else "unhealthy",
                    "response_time_ms": health_response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                status["github_models"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            status["github_models"] = {"status": "not_configured"}
        
        return status
    
    async def shutdown(self):
        """Cleanup resources on shutdown"""
        
        logger.info("Shutting down AI Service")
        
        if self.vertex_client:
            await self.vertex_client.aclose()
        
        if self.github_client:
            await self.github_client.aclose()
        
        logger.info("AI Service shutdown complete")