"""
Regional and Localization API Endpoints
FastAPI endpoints for multi-language support, regional building codes,
cultural preferences, and measurement systems.

Provides comprehensive regional adaptation capabilities for international users.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import structlog
from enum import Enum

from ..core.localization import (
    LocalizationService, 
    SupportedRegion, 
    SupportedLanguage,
    CulturalPreferences,
    RegionalBuildingCodes,
    localization_service
)
from ..core.measurement_converter import (
    RegionalMeasurementConverter, 
    MeasurementSystem, 
    MeasurementUnit,
    create_converter
)
from ..core.global_prompt_engine import (
    GlobalPromptTemplateEngine,
    AIModelType,
    PromptType,
    AIPromptRequest,
    create_prompt_engine
)
from ..models.auth import User
from ..api.auth import get_current_user
from ..core.performance import track_operation

logger = structlog.get_logger(__name__)

# Create router for regional endpoints
router = APIRouter(prefix="/v1/regional", tags=["regional-localization"])


# Pydantic models for API requests/responses
class LocaleInfoRequest(BaseModel):
    """Request model for locale information."""
    locale: str = Field(..., description="Locale string (e.g., 'en-US', 'tr-TR')")


class LocaleInfoResponse(BaseModel):
    """Response model for locale information."""
    locale: str
    region: str
    country: str
    measurement_system: str
    language: str
    supported: bool


class CulturalPreferencesResponse(BaseModel):
    """Response model for cultural preferences."""
    region: str
    privacy_level: float = Field(..., ge=0.0, le=1.0)
    family_structure: str
    entertainment_style: str
    outdoor_connection: str
    religious_considerations: List[str]
    dining_traditions: str
    work_from_home: bool
    multi_generational_living: bool


class BuildingCodesResponse(BaseModel):
    """Response model for regional building codes."""
    region: str
    primary_codes: List[str]
    secondary_codes: List[str]
    accessibility_standard: str
    energy_standard: str
    seismic_requirements: bool
    climate_adaptations: List[str]
    max_occupancy_ratios: Dict[str, float]
    minimum_room_sizes: Dict[str, float]
    setback_requirements: Dict[str, float]
    height_restrictions: Dict[str, float]


class MeasurementConversionRequest(BaseModel):
    """Request model for measurement conversion."""
    value: float = Field(..., gt=0)
    from_unit: str
    to_unit: Optional[str] = None
    region: Optional[str] = None


class MeasurementConversionResponse(BaseModel):
    """Response model for measurement conversion."""
    original_value: float
    original_unit: str
    converted_value: float
    converted_unit: str
    region: str
    measurement_system: str


class AIPromptGenerationRequest(BaseModel):
    """Request model for AI prompt generation."""
    model_type: str = Field(..., description="AI model type (e.g., 'openai_gpt4')")
    prompt_type: str = Field(default="layout_generation", description="Type of prompt")
    locale: str = Field(..., description="User locale")
    building_type: str = Field(default="residential")
    total_area_m2: float = Field(..., gt=0)
    floor_count: int = Field(default=1, ge=1)
    room_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    style_preferences: Dict[str, Any] = Field(default_factory=dict)
    budget_range: Optional[str] = None
    special_requirements: List[str] = Field(default_factory=list)
    accessibility_required: bool = False
    energy_efficiency_target: str = "standard"
    user_prompt: str = ""


class AIPromptGenerationResponse(BaseModel):
    """Response model for AI prompt generation."""
    generated_prompt: str
    model_type: str
    prompt_type: str
    region: str
    locale: str
    measurement_system: str
    cultural_context: Dict[str, Any]
    building_codes: List[str]


class LocalizedRoomTypesResponse(BaseModel):
    """Response model for localized room types."""
    region: str
    language: str
    room_types: Dict[str, str]


class TranslationRequest(BaseModel):
    """Request model for translations."""
    language: str
    keys: List[str]


class TranslationResponse(BaseModel):
    """Response model for translations."""
    language: str
    translations: Dict[str, str]


class RegionalConfigResponse(BaseModel):
    """Response model for regional configuration."""
    supported_regions: List[str]
    supported_languages: List[str]
    default_measurement_systems: Dict[str, str]
    locale_mappings: Dict[str, str]


# API Endpoints

@router.get("/config", response_model=RegionalConfigResponse)
async def get_regional_config():
    """
    Get comprehensive regional configuration information.
    
    Returns supported regions, languages, and default measurement systems.
    """
    try:
        return RegionalConfigResponse(
            supported_regions=[region.value for region in SupportedRegion],
            supported_languages=[lang.value for lang in SupportedLanguage],
            default_measurement_systems={
                SupportedRegion.NORTH_AMERICA.value: MeasurementSystem.IMPERIAL.value,
                SupportedRegion.EUROPE.value: MeasurementSystem.METRIC.value,
                SupportedRegion.ASIA_PACIFIC.value: MeasurementSystem.METRIC.value,
                SupportedRegion.MIDDLE_EAST.value: MeasurementSystem.METRIC.value,
                SupportedRegion.AFRICA.value: MeasurementSystem.METRIC.value,
                SupportedRegion.SOUTH_AMERICA.value: MeasurementSystem.METRIC.value,
            },
            locale_mappings={
                "en-US": SupportedRegion.NORTH_AMERICA.value,
                "en-CA": SupportedRegion.NORTH_AMERICA.value,
                "en-GB": SupportedRegion.EUROPE.value,
                "tr-TR": SupportedRegion.MIDDLE_EAST.value,
                "de-DE": SupportedRegion.EUROPE.value,
                "fr-FR": SupportedRegion.EUROPE.value,
                "es-ES": SupportedRegion.EUROPE.value,
                "ja-JP": SupportedRegion.ASIA_PACIFIC.value,
                "ar-SA": SupportedRegion.MIDDLE_EAST.value,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get regional config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve regional configuration"
        )


@router.post("/locale-info", response_model=LocaleInfoResponse)
@track_operation("regional_locale_info")
async def get_locale_info(request: LocaleInfoRequest):
    """
    Get detailed information about a specific locale.
    
    Returns region, country, measurement system, and language information.
    """
    try:
        region, country, measurement_system = localization_service.get_locale_info(request.locale)
        language = request.locale.split('-')[0]
        
        # Check if locale is supported
        supported = request.locale in localization_service.supported_locales
        
        return LocaleInfoResponse(
            locale=request.locale,
            region=region.value,
            country=country,
            measurement_system=measurement_system.value,
            language=language,
            supported=supported
        )
    except Exception as e:
        logger.error(f"Failed to get locale info for {request.locale}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unsupported locale: {request.locale}"
        )


@router.get("/{region}/cultural-preferences", response_model=CulturalPreferencesResponse)
@track_operation("regional_cultural_preferences")
async def get_cultural_preferences(region: str):
    """
    Get cultural preferences for a specific region.
    
    Returns cultural design preferences including privacy levels,
    family structures, and entertainment styles.
    """
    try:
        region_enum = SupportedRegion(region)
        preferences = localization_service.get_cultural_preferences(region_enum)
        
        return CulturalPreferencesResponse(
            region=region,
            privacy_level=preferences.privacy_level,
            family_structure=preferences.family_structure,
            entertainment_style=preferences.entertainment_style,
            outdoor_connection=preferences.outdoor_connection,
            religious_considerations=preferences.religious_considerations,
            dining_traditions=preferences.dining_traditions,
            work_from_home=preferences.work_from_home,
            multi_generational_living=preferences.multi_generational_living
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported region: {region}"
        )
    except Exception as e:
        logger.error(f"Failed to get cultural preferences for {region}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cultural preferences"
        )


@router.get("/{region}/building-codes", response_model=BuildingCodesResponse)
@track_operation("regional_building_codes")
async def get_building_codes(region: str):
    """
    Get building codes and compliance requirements for a specific region.
    
    Returns regional building codes, accessibility standards,
    and compliance requirements.
    """
    try:
        region_enum = SupportedRegion(region)
        codes = localization_service.get_building_codes(region_enum)
        
        return BuildingCodesResponse(
            region=region,
            primary_codes=codes.primary_codes,
            secondary_codes=codes.secondary_codes,
            accessibility_standard=codes.accessibility_standard,
            energy_standard=codes.energy_standard,
            seismic_requirements=codes.seismic_requirements,
            climate_adaptations=codes.climate_adaptations,
            max_occupancy_ratios=codes.max_occupancy_ratios,
            minimum_room_sizes=codes.minimum_room_sizes,
            setback_requirements=codes.setback_requirements,
            height_restrictions=codes.height_restrictions
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported region: {region}"
        )
    except Exception as e:
        logger.error(f"Failed to get building codes for {region}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve building codes"
        )


@router.get("/{region}/{language}/room-types", response_model=LocalizedRoomTypesResponse)
@track_operation("regional_room_types")
async def get_localized_room_types(region: str, language: str):
    """
    Get localized room type names for a specific region and language.
    
    Returns room types with names translated to the specified language
    and cultural variants for the region.
    """
    try:
        region_enum = SupportedRegion(region)
        room_types = localization_service.get_localized_room_types(region_enum, language)
        
        return LocalizedRoomTypesResponse(
            region=region,
            language=language,
            room_types=room_types
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported region or language: {region}, {language}"
        )
    except Exception as e:
        logger.error(f"Failed to get room types for {region}/{language}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve localized room types"
        )


@router.post("/convert-measurement", response_model=MeasurementConversionResponse)
@track_operation("measurement_conversion")
async def convert_measurement(request: MeasurementConversionRequest):
    """
    Convert measurements between different units and systems.
    
    Supports length, area, volume, and temperature conversions
    with regional preferences.
    """
    try:
        # Determine region and create converter
        region = request.region or "north_america"
        converter = create_converter(region)
        
        # Parse units
        try:
            from_unit = MeasurementUnit(request.from_unit)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported measurement unit: {request.from_unit}"
            )
        
        to_unit = None
        if request.to_unit:
            try:
                to_unit = MeasurementUnit(request.to_unit)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported measurement unit: {request.to_unit}"
                )
        
        # Perform conversion based on unit type
        if from_unit in [MeasurementUnit.METER, MeasurementUnit.FOOT, MeasurementUnit.CENTIMETER, 
                        MeasurementUnit.MILLIMETER, MeasurementUnit.INCH, MeasurementUnit.YARD]:
            converted_value, target_unit = converter.convert_length(request.value, from_unit, to_unit)
        elif from_unit in [MeasurementUnit.SQUARE_METER, MeasurementUnit.SQUARE_FOOT, 
                          MeasurementUnit.SQUARE_CENTIMETER, MeasurementUnit.SQUARE_MILLIMETER,
                          MeasurementUnit.SQUARE_INCH, MeasurementUnit.SQUARE_YARD]:
            converted_value, target_unit = converter.convert_area(request.value, from_unit, to_unit)
        elif from_unit in [MeasurementUnit.CUBIC_METER, MeasurementUnit.CUBIC_FOOT, 
                          MeasurementUnit.LITER, MeasurementUnit.GALLON]:
            converted_value, target_unit = converter.convert_volume(request.value, from_unit, to_unit)
        elif from_unit in [MeasurementUnit.CELSIUS, MeasurementUnit.FAHRENHEIT, MeasurementUnit.KELVIN]:
            converted_value, target_unit = converter.convert_temperature(request.value, from_unit, to_unit)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conversion not supported for unit type: {request.from_unit}"
            )
        
        return MeasurementConversionResponse(
            original_value=request.value,
            original_unit=from_unit.value,
            converted_value=converted_value,
            converted_unit=target_unit.value,
            region=region,
            measurement_system=converter.system.value
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to convert measurement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert measurement"
        )


@router.post("/generate-prompt", response_model=AIPromptGenerationResponse)
@track_operation("ai_prompt_generation", cost_units=5)
async def generate_ai_prompt(
    request: AIPromptGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate culturally-appropriate and regionally-compliant AI prompts.
    
    Creates optimized prompts for different AI models while incorporating
    regional building codes, cultural preferences, and measurement systems.
    """
    try:
        # Parse and validate inputs
        try:
            model_type = AIModelType(request.model_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported AI model type: {request.model_type}"
            )
        
        try:
            prompt_type = PromptType(request.prompt_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported prompt type: {request.prompt_type}"
            )
        
        # Get locale information
        region, country, measurement_system = localization_service.get_locale_info(request.locale)
        
        # Create prompt engine
        prompt_engine = create_prompt_engine(
            region=region.value,
            country=country,
            locale=request.locale,
            localization_service=localization_service
        )
        
        # Initialize if not already done
        await prompt_engine.initialize()
        
        # Prepare AI prompt request
        ai_request = AIPromptRequest(
            building_type=request.building_type,
            total_area_m2=request.total_area_m2,
            floor_count=request.floor_count,
            room_requirements=request.room_requirements,
            style_preferences=request.style_preferences,
            budget_range=request.budget_range,
            special_requirements=request.special_requirements,
            accessibility_required=request.accessibility_required,
            energy_efficiency_target=request.energy_efficiency_target,
            user_prompt=request.user_prompt
        )
        
        # Generate prompt
        generated_prompt = await prompt_engine.generate_prompt(
            model_type=model_type,
            prompt_type=prompt_type,
            request_data=ai_request
        )
        
        # Get cultural context and building codes for response
        cultural_preferences = localization_service.get_cultural_preferences(region)
        building_codes = localization_service.get_building_codes(region)
        
        cultural_context = {
            "privacy_level": cultural_preferences.privacy_level,
            "family_structure": cultural_preferences.family_structure,
            "entertainment_style": cultural_preferences.entertainment_style,
            "outdoor_connection": cultural_preferences.outdoor_connection,
            "religious_considerations": cultural_preferences.religious_considerations,
            "dining_traditions": cultural_preferences.dining_traditions,
        }
        
        return AIPromptGenerationResponse(
            generated_prompt=generated_prompt,
            model_type=model_type.value,
            prompt_type=prompt_type.value,
            region=region.value,
            locale=request.locale,
            measurement_system=measurement_system.value,
            cultural_context=cultural_context,
            building_codes=building_codes.primary_codes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate AI prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI prompt"
        )


@router.post("/translations", response_model=TranslationResponse)
@track_operation("get_translations")
async def get_translations(request: TranslationRequest):
    """
    Get UI translations for specific keys and language.
    
    Returns translated strings for the specified language,
    with fallback to English if translations are not available.
    """
    try:
        translations = {}
        
        for key in request.keys:
            translation = localization_service.get_translation(
                request.language, 
                key, 
                default=key  # Use key as fallback
            )
            translations[key] = translation
        
        return TranslationResponse(
            language=request.language,
            translations=translations
        )
    except Exception as e:
        logger.error(f"Failed to get translations for {request.language}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve translations"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for regional services."""
    try:
        # Test localization service
        region, country, system = localization_service.get_locale_info("en-US")
        
        return {
            "status": "healthy",
            "service": "regional-localization",
            "localization_service": "operational",
            "supported_regions": len(SupportedRegion),
            "supported_languages": len(SupportedLanguage),
            "test_locale_parsing": "passed"
        }
    except Exception as e:
        logger.error(f"Regional service health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "regional-localization",
                "error": str(e)
            }
        )