"""
Regional and Localization Core Module
Multi-language support, regional building codes, cultural preferences, measurement systems

This module provides comprehensive localization and regional adaptation capabilities
for ArchBuilder.AI, supporting international users with their local building codes,
cultural preferences, and measurement systems.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import structlog
from babel import Locale, numbers, dates
from babel.core import UnknownLocaleError

logger = structlog.get_logger(__name__)


class SupportedRegion(str, Enum):
    """Supported geographical regions with their building code systems."""
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    ASIA_PACIFIC = "asia_pacific"
    MIDDLE_EAST = "middle_east"
    AFRICA = "africa"
    SOUTH_AMERICA = "south_america"


class SupportedLanguage(str, Enum):
    """Supported languages for localization."""
    ENGLISH = "en"
    TURKISH = "tr"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
    JAPANESE = "ja"
    ARABIC = "ar"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    RUSSIAN = "ru"


class MeasurementSystem(str, Enum):
    """Measurement systems for different regions."""
    METRIC = "metric"
    IMPERIAL = "imperial"
    MIXED = "mixed"


@dataclass
class CulturalPreferences:
    """Cultural design preferences for different regions."""
    privacy_level: float = 0.5  # 0.0 = open, 1.0 = very private
    family_structure: str = "nuclear"  # nuclear, extended, multi_generational
    entertainment_style: str = "mixed"  # formal, casual, mixed
    outdoor_connection: str = "medium"  # high, medium, low
    religious_considerations: List[str] = field(default_factory=list)
    dining_traditions: str = "western"  # western, eastern, traditional
    work_from_home: bool = True
    multi_generational_living: bool = False


@dataclass
class RegionalBuildingCodes:
    """Regional building codes and compliance requirements."""
    primary_codes: List[str] = field(default_factory=list)
    secondary_codes: List[str] = field(default_factory=list)
    accessibility_standard: str = "international"
    energy_standard: str = "basic"
    seismic_requirements: bool = False
    climate_adaptations: List[str] = field(default_factory=list)
    max_occupancy_ratios: Dict[str, float] = field(default_factory=dict)
    minimum_room_sizes: Dict[str, float] = field(default_factory=dict)  # in m²
    setback_requirements: Dict[str, float] = field(default_factory=dict)  # in meters
    height_restrictions: Dict[str, float] = field(default_factory=dict)  # in meters


@dataclass
class LocalizedRoomType:
    """Room type with localized names and cultural variants."""
    standard_type: str
    localized_names: Dict[str, str] = field(default_factory=dict)
    cultural_variants: Dict[str, List[str]] = field(default_factory=dict)
    typical_sizes: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # (min, max) in m²
    cultural_requirements: List[str] = field(default_factory=list)


class LocalizationService:
    """
    Comprehensive localization service for ArchBuilder.AI.
    
    Handles multi-language support, regional building codes, cultural preferences,
    and measurement systems for international users.
    """
    
    def __init__(self, configs_path: Optional[Path] = None):
        """Initialize localization service with configuration paths."""
        self.configs_path = configs_path or Path(__file__).parent.parent.parent.parent / "configs"
        self.supported_locales: Dict[str, Locale] = {}
        self.regional_data: Dict[str, Dict[str, Any]] = {}
        self.cultural_preferences: Dict[str, CulturalPreferences] = {}
        self.building_codes: Dict[str, RegionalBuildingCodes] = {}
        self.room_types: Dict[str, Dict[str, LocalizedRoomType]] = {}
        self.translations: Dict[str, Dict[str, str]] = {}
        
        # Initialize default locale mappings
        self._initialize_locale_mappings()
        
    def _initialize_locale_mappings(self):
        """Initialize supported locales and their mappings."""
        locale_mappings = {
            "en_US": SupportedRegion.NORTH_AMERICA,
            "en_CA": SupportedRegion.NORTH_AMERICA,
            "en_GB": SupportedRegion.EUROPE,
            "en_AU": SupportedRegion.ASIA_PACIFIC,
            "tr_TR": SupportedRegion.MIDDLE_EAST,
            "de_DE": SupportedRegion.EUROPE,
            "de_AT": SupportedRegion.EUROPE,
            "de_CH": SupportedRegion.EUROPE,
            "fr_FR": SupportedRegion.EUROPE,
            "fr_CA": SupportedRegion.NORTH_AMERICA,
            "es_ES": SupportedRegion.EUROPE,
            "es_MX": SupportedRegion.NORTH_AMERICA,
            "es_AR": SupportedRegion.SOUTH_AMERICA,
            "ja_JP": SupportedRegion.ASIA_PACIFIC,
            "ar_SA": SupportedRegion.MIDDLE_EAST,
            "ar_AE": SupportedRegion.MIDDLE_EAST,
            "pt_BR": SupportedRegion.SOUTH_AMERICA,
            "pt_PT": SupportedRegion.EUROPE,
            "it_IT": SupportedRegion.EUROPE,
            "ru_RU": SupportedRegion.EUROPE,
        }
        
        for locale_str, region in locale_mappings.items():
            try:
                locale_obj = Locale.parse(locale_str)
                self.supported_locales[locale_str] = locale_obj
                # Also support dash format for compatibility
                dash_format = locale_str.replace('_', '-')
                self.supported_locales[dash_format] = locale_obj
            except UnknownLocaleError:
                logger.warning(f"Unknown locale: {locale_str}")
    
    async def initialize(self):
        """Asynchronously initialize all localization data."""
        logger.info("Initializing localization service")
        
        try:
            await asyncio.gather(
                self._load_regional_data(),
                self._load_cultural_preferences(),
                self._load_building_codes(),
                self._load_room_types(),
                self._load_translations()
            )
            logger.info("Localization service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize localization service: {e}")
            raise
    
    async def _load_regional_data(self):
        """Load regional configuration data."""
        regional_config_path = self.configs_path / "app-settings" / "regional-config.json"
        
        if regional_config_path.exists():
            with open(regional_config_path, 'r', encoding='utf-8') as f:
                self.regional_data = json.load(f)
        else:
            # Create default regional data
            self.regional_data = await self._create_default_regional_data()
            await self._save_regional_data()
    
    async def _load_cultural_preferences(self):
        """Load cultural preferences for different regions."""
        cultural_config_path = self.configs_path / "app-settings" / "cultural-preferences.json"
        
        if cultural_config_path.exists():
            with open(cultural_config_path, 'r', encoding='utf-8') as f:
                cultural_data = json.load(f)
                
                for region, prefs in cultural_data.items():
                    self.cultural_preferences[region] = CulturalPreferences(**prefs)
        else:
            # Create default cultural preferences
            self.cultural_preferences = await self._create_default_cultural_preferences()
            await self._save_cultural_preferences()
    
    async def _load_building_codes(self):
        """Load regional building codes and compliance requirements."""
        building_codes_path = self.configs_path / "building-codes" / "regional-codes.json"
        
        if building_codes_path.exists():
            with open(building_codes_path, 'r', encoding='utf-8') as f:
                codes_data = json.load(f)
                
                for region, codes in codes_data.items():
                    self.building_codes[region] = RegionalBuildingCodes(**codes)
        else:
            # Create default building codes
            self.building_codes = await self._create_default_building_codes()
            await self._save_building_codes()
    
    async def _load_room_types(self):
        """Load localized room types with cultural variants."""
        room_types_path = self.configs_path / "app-settings" / "room-types.json"
        
        if room_types_path.exists():
            with open(room_types_path, 'r', encoding='utf-8') as f:
                room_data = json.load(f)
                
                for region, types in room_data.items():
                    self.room_types[region] = {}
                    for type_key, type_data in types.items():
                        self.room_types[region][type_key] = LocalizedRoomType(**type_data)
        else:
            # Create default room types
            self.room_types = await self._create_default_room_types()
            await self._save_room_types()
    
    async def _load_translations(self):
        """Load UI translations for supported languages."""
        for language in SupportedLanguage:
            translation_path = self.configs_path / "ai-prompts" / language.value / "translations.json"
            
            if translation_path.exists():
                with open(translation_path, 'r', encoding='utf-8') as f:
                    self.translations[language.value] = json.load(f)
            else:
                # Create default translations
                self.translations[language.value] = await self._create_default_translations(language.value)
                # Save translations
                translation_path.parent.mkdir(parents=True, exist_ok=True)
                with open(translation_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translations[language.value], f, ensure_ascii=False, indent=2)
    
    def get_locale_info(self, locale_str: str) -> Tuple[SupportedRegion, str, MeasurementSystem]:
        """
        Get region, country, and measurement system for a given locale.
        
        Args:
            locale_str: Locale string (e.g., "en-US", "tr-TR")
            
        Returns:
            Tuple of (region, country, measurement_system)
        """
        try:
            # Convert dash to underscore for Babel compatibility
            normalized_locale = locale_str.replace('-', '_')
            locale_obj = Locale.parse(normalized_locale)
            country = locale_obj.territory or "Unknown"
            
            # Determine region based on locale
            if locale_str.startswith("en-US") or locale_str.startswith("en_US") or locale_str.startswith("en-CA") or locale_str.startswith("en_CA") or locale_str.startswith("fr-CA") or locale_str.startswith("fr_CA"):
                region = SupportedRegion.NORTH_AMERICA
                measurement_system = MeasurementSystem.IMPERIAL if locale_str.startswith("en-US") or locale_str.startswith("en_US") else MeasurementSystem.MIXED
            elif locale_str.startswith("tr-") or locale_str.startswith("tr_"):
                region = SupportedRegion.MIDDLE_EAST
                measurement_system = MeasurementSystem.METRIC
            elif locale_str.startswith(("de-", "de_", "fr-FR", "fr_FR", "es-ES", "es_ES", "it-", "it_", "pt-PT", "pt_PT")):
                region = SupportedRegion.EUROPE
                measurement_system = MeasurementSystem.METRIC
            elif locale_str.startswith(("ja-", "ja_", "ko-", "ko_", "zh-", "zh_", "en-AU", "en_AU")):
                region = SupportedRegion.ASIA_PACIFIC
                measurement_system = MeasurementSystem.METRIC
            elif locale_str.startswith(("ar-", "ar_", "fa-", "fa_", "he-", "he_")):
                region = SupportedRegion.MIDDLE_EAST
                measurement_system = MeasurementSystem.METRIC
            elif (locale_str.startswith(("es-", "es_", "pt-BR", "pt_BR")) and 
                  not locale_str.startswith("es-ES") and not locale_str.startswith("es_ES")):
                region = SupportedRegion.SOUTH_AMERICA
                measurement_system = MeasurementSystem.METRIC
            else:
                region = SupportedRegion.NORTH_AMERICA  # Default
                measurement_system = MeasurementSystem.METRIC
                
            return region, country, measurement_system
            
        except UnknownLocaleError:
            logger.warning(f"Unknown locale: {locale_str}, using defaults")
            return SupportedRegion.NORTH_AMERICA, "Unknown", MeasurementSystem.METRIC
    
    def get_cultural_preferences(self, region: SupportedRegion) -> CulturalPreferences:
        """Get cultural preferences for a specific region."""
        return self.cultural_preferences.get(region.value, CulturalPreferences())
    
    def get_building_codes(self, region: SupportedRegion) -> RegionalBuildingCodes:
        """Get building codes for a specific region."""
        return self.building_codes.get(region.value, RegionalBuildingCodes())
    
    def get_localized_room_types(self, region: SupportedRegion, language: str) -> Dict[str, str]:
        """Get localized room type names for a region and language."""
        room_types = self.room_types.get(region.value, {})
        localized_types = {}
        
        for type_key, room_type in room_types.items():
            if language in room_type.localized_names:
                localized_types[type_key] = room_type.localized_names[language]
            else:
                # Fallback to English or standard type
                localized_types[type_key] = room_type.localized_names.get("en", room_type.standard_type)
        
        return localized_types
    
    def get_translation(self, language: str, key: str, default: Optional[str] = None) -> str:
        """Get translation for a specific key and language."""
        language_translations = self.translations.get(language, {})
        return language_translations.get(key, default or key)
    
    def format_area(self, area_m2: float, measurement_system: MeasurementSystem, locale_str: str) -> str:
        """Format area value according to regional preferences."""
        try:
            locale_obj = Locale.parse(locale_str)
            
            if measurement_system == MeasurementSystem.IMPERIAL:
                # Convert to square feet
                area_sqft = area_m2 * 10.764
                formatted = numbers.format_decimal(area_sqft, locale=locale_obj)
                return f"{formatted} sq ft"
            else:
                # Use square meters
                formatted = numbers.format_decimal(area_m2, locale=locale_obj)
                return f"{formatted} m²"
                
        except (UnknownLocaleError, Exception) as e:
            logger.warning(f"Error formatting area: {e}")
            return f"{area_m2:.1f} m²"
    
    def format_currency(self, amount: float, currency: str, locale_str: str) -> str:
        """Format currency according to regional preferences."""
        try:
            locale_obj = Locale.parse(locale_str)
            return numbers.format_currency(amount, currency, locale=locale_obj)
        except (UnknownLocaleError, Exception) as e:
            logger.warning(f"Error formatting currency: {e}")
            return f"{amount:.2f} {currency}"
    
    def format_datetime(self, dt: datetime, locale_str: str) -> str:
        """Format datetime according to regional preferences."""
        try:
            locale_obj = Locale.parse(locale_str)
            return dates.format_datetime(dt, locale=locale_obj)
        except (UnknownLocaleError, Exception) as e:
            logger.warning(f"Error formatting datetime: {e}")
            return dt.isoformat()
    
    async def _create_default_regional_data(self) -> Dict[str, Any]:
        """Create default regional configuration data."""
        return {
            "supported_regions": [region.value for region in SupportedRegion],
            "supported_languages": [lang.value for lang in SupportedLanguage],
            "default_measurement_systems": {
                SupportedRegion.NORTH_AMERICA.value: MeasurementSystem.IMPERIAL.value,
                SupportedRegion.EUROPE.value: MeasurementSystem.METRIC.value,
                SupportedRegion.ASIA_PACIFIC.value: MeasurementSystem.METRIC.value,
                SupportedRegion.MIDDLE_EAST.value: MeasurementSystem.METRIC.value,
                SupportedRegion.AFRICA.value: MeasurementSystem.METRIC.value,
                SupportedRegion.SOUTH_AMERICA.value: MeasurementSystem.METRIC.value,
            }
        }
    
    async def _create_default_cultural_preferences(self) -> Dict[str, CulturalPreferences]:
        """Create default cultural preferences for each region."""
        return {
            SupportedRegion.NORTH_AMERICA.value: CulturalPreferences(
                privacy_level=0.4,
                family_structure="nuclear",
                entertainment_style="casual",
                outdoor_connection="medium",
                dining_traditions="western",
                work_from_home=True
            ),
            SupportedRegion.EUROPE.value: CulturalPreferences(
                privacy_level=0.6,
                family_structure="nuclear",
                entertainment_style="formal",
                outdoor_connection="high",
                dining_traditions="western",
                work_from_home=True
            ),
            SupportedRegion.ASIA_PACIFIC.value: CulturalPreferences(
                privacy_level=0.7,
                family_structure="extended",
                entertainment_style="formal",
                outdoor_connection="medium",
                dining_traditions="eastern",
                multi_generational_living=True
            ),
            SupportedRegion.MIDDLE_EAST.value: CulturalPreferences(
                privacy_level=0.8,
                family_structure="extended",
                entertainment_style="formal",
                outdoor_connection="low",
                religious_considerations=["prayer_space", "gender_separation"],
                dining_traditions="traditional",
                multi_generational_living=True
            ),
            SupportedRegion.AFRICA.value: CulturalPreferences(
                privacy_level=0.5,
                family_structure="extended",
                entertainment_style="mixed",
                outdoor_connection="high",
                dining_traditions="traditional",
                multi_generational_living=True
            ),
            SupportedRegion.SOUTH_AMERICA.value: CulturalPreferences(
                privacy_level=0.4,
                family_structure="extended",
                entertainment_style="casual",
                outdoor_connection="high",
                dining_traditions="western",
                multi_generational_living=False
            ),
        }
    
    async def _create_default_building_codes(self) -> Dict[str, RegionalBuildingCodes]:
        """Create default building codes for each region."""
        return {
            SupportedRegion.NORTH_AMERICA.value: RegionalBuildingCodes(
                primary_codes=["IBC", "IRC", "Local Zoning"],
                accessibility_standard="ADA",
                energy_standard="IECC",
                seismic_requirements=True,
                climate_adaptations=["hurricane", "tornado", "wildfire"],
                max_occupancy_ratios={"residential": 0.5, "commercial": 0.7},
                minimum_room_sizes={"bedroom": 6.5, "living_room": 13.9, "kitchen": 7.4},  # m²
                setback_requirements={"front": 7.6, "side": 3.0, "rear": 7.6},  # meters
                height_restrictions={"residential": 10.7, "commercial": 30.5}  # meters
            ),
            SupportedRegion.EUROPE.value: RegionalBuildingCodes(
                primary_codes=["Eurocode", "National Building Regulations"],
                accessibility_standard="European Accessibility Act",
                energy_standard="EU Energy Performance Directive",
                seismic_requirements=True,
                climate_adaptations=["flood", "heat_wave", "snow_load"],
                max_occupancy_ratios={"residential": 0.4, "commercial": 0.6},
                minimum_room_sizes={"bedroom": 9.0, "living_room": 16.0, "kitchen": 6.0},  # m²
                setback_requirements={"front": 5.0, "side": 3.0, "rear": 5.0},  # meters
                height_restrictions={"residential": 12.0, "commercial": 50.0}  # meters
            ),
            SupportedRegion.MIDDLE_EAST.value: RegionalBuildingCodes(
                primary_codes=["National Building Code", "Municipal Regulations"],
                accessibility_standard="International Accessibility Standards",
                energy_standard="Regional Energy Code",
                seismic_requirements=True,
                climate_adaptations=["extreme_heat", "dust_storms", "earthquake"],
                max_occupancy_ratios={"residential": 0.4, "commercial": 0.6},
                minimum_room_sizes={"bedroom": 9.0, "living_room": 12.0, "kitchen": 6.0},  # m²
                setback_requirements={"front": 6.0, "side": 3.0, "rear": 6.0},  # meters
                height_restrictions={"residential": 15.0, "commercial": 100.0}  # meters
            ),
            SupportedRegion.ASIA_PACIFIC.value: RegionalBuildingCodes(
                primary_codes=["National Building Code", "Local Regulations"],
                accessibility_standard="Regional Accessibility Standards",
                energy_standard="National Energy Code",
                seismic_requirements=True,
                climate_adaptations=["typhoon", "earthquake", "humidity", "flood"],
                max_occupancy_ratios={"residential": 0.6, "commercial": 0.8},
                minimum_room_sizes={"bedroom": 8.0, "living_room": 14.0, "kitchen": 5.0},  # m²
                setback_requirements={"front": 4.0, "side": 2.0, "rear": 4.0},  # meters
                height_restrictions={"residential": 20.0, "commercial": 200.0}  # meters
            ),
            SupportedRegion.AFRICA.value: RegionalBuildingCodes(
                primary_codes=["National Building Code"],
                accessibility_standard="International Standards",
                energy_standard="Basic Energy Requirements",
                climate_adaptations=["extreme_heat", "drought", "flood"],
                max_occupancy_ratios={"residential": 0.5, "commercial": 0.7},
                minimum_room_sizes={"bedroom": 7.0, "living_room": 12.0, "kitchen": 5.0},  # m²
                setback_requirements={"front": 5.0, "side": 2.5, "rear": 5.0},  # meters
                height_restrictions={"residential": 15.0, "commercial": 50.0}  # meters
            ),
            SupportedRegion.SOUTH_AMERICA.value: RegionalBuildingCodes(
                primary_codes=["National Building Code", "Regional Standards"],
                accessibility_standard="Regional Accessibility Requirements",
                energy_standard="Energy Efficiency Standards",
                seismic_requirements=True,
                climate_adaptations=["earthquake", "flood", "hurricane"],
                max_occupancy_ratios={"residential": 0.5, "commercial": 0.7},
                minimum_room_sizes={"bedroom": 8.0, "living_room": 15.0, "kitchen": 6.0},  # m²
                setback_requirements={"front": 6.0, "side": 3.0, "rear": 6.0},  # meters
                height_restrictions={"residential": 12.0, "commercial": 80.0}  # meters
            ),
        }
    
    async def _create_default_room_types(self) -> Dict[str, Dict[str, LocalizedRoomType]]:
        """Create default room types with localized names."""
        common_room_types = {
            "bedroom": LocalizedRoomType(
                standard_type="bedroom",
                localized_names={
                    "en": "Bedroom",
                    "tr": "Yatak Odası",
                    "de": "Schlafzimmer",
                    "fr": "Chambre",
                    "es": "Dormitorio",
                    "ja": "寝室",
                    "ar": "غرفة النوم"
                },
                typical_sizes={"min": (9.0, 25.0), "max": (9.0, 25.0)},
                cultural_requirements=["privacy", "natural_light"]
            ),
            "living_room": LocalizedRoomType(
                standard_type="living_room",
                localized_names={
                    "en": "Living Room",
                    "tr": "Oturma Odası",
                    "de": "Wohnzimmer",
                    "fr": "Salon",
                    "es": "Sala de Estar",
                    "ja": "居間",
                    "ar": "غرفة المعيشة"
                },
                typical_sizes={"min": (12.0, 50.0), "max": (12.0, 50.0)},
                cultural_requirements=["family_gathering", "entertainment"]
            ),
            "kitchen": LocalizedRoomType(
                standard_type="kitchen",
                localized_names={
                    "en": "Kitchen",
                    "tr": "Mutfak",
                    "de": "Küche",
                    "fr": "Cuisine",
                    "es": "Cocina",
                    "ja": "台所",
                    "ar": "مطبخ"
                },
                typical_sizes={"min": (6.0, 20.0), "max": (6.0, 20.0)},
                cultural_requirements=["ventilation", "water_access"]
            ),
            "bathroom": LocalizedRoomType(
                standard_type="bathroom",
                localized_names={
                    "en": "Bathroom",
                    "tr": "Banyo",
                    "de": "Badezimmer",
                    "fr": "Salle de bain",
                    "es": "Baño",
                    "ja": "浴室",
                    "ar": "حمام"
                },
                typical_sizes={"min": (3.0, 15.0), "max": (3.0, 15.0)},
                cultural_requirements=["privacy", "ventilation", "water_access"]
            )
        }
        
        # All regions use the same basic room types
        return {region.value: common_room_types.copy() for region in SupportedRegion}
    
    async def _create_default_translations(self, language: str) -> Dict[str, str]:
        """Create default UI translations for a language."""
        translations = {
            "en": {
                "app_name": "ArchBuilder.AI",
                "welcome": "Welcome to ArchBuilder.AI",
                "generate_layout": "Generate Layout",
                "building_type": "Building Type",
                "total_area": "Total Area",
                "room_requirements": "Room Requirements",
                "cultural_preferences": "Cultural Preferences",
                "generate": "Generate",
                "cancel": "Cancel",
                "success": "Success",
                "error": "Error",
                "loading": "Loading...",
                "residential": "Residential",
                "commercial": "Commercial",
                "mixed_use": "Mixed Use"
            },
            "tr": {
                "app_name": "ArchBuilder.AI",
                "welcome": "ArchBuilder.AI'ye Hoş Geldiniz",
                "generate_layout": "Düzen Oluştur",
                "building_type": "Bina Türü",
                "total_area": "Toplam Alan",
                "room_requirements": "Oda Gereksinimleri",
                "cultural_preferences": "Kültürel Tercihler",
                "generate": "Oluştur",
                "cancel": "İptal",
                "success": "Başarılı",
                "error": "Hata",
                "loading": "Yükleniyor...",
                "residential": "Konut",
                "commercial": "Ticari",
                "mixed_use": "Karma Kullanım"
            },
            "de": {
                "app_name": "ArchBuilder.AI",
                "welcome": "Willkommen bei ArchBuilder.AI",
                "generate_layout": "Layout Generieren",
                "building_type": "Gebäudetyp",
                "total_area": "Gesamtfläche",
                "room_requirements": "Raumanforderungen",
                "cultural_preferences": "Kulturelle Präferenzen",
                "generate": "Generieren",
                "cancel": "Abbrechen",
                "success": "Erfolg",
                "error": "Fehler",
                "loading": "Wird geladen...",
                "residential": "Wohngebäude",
                "commercial": "Gewerbegebäude",
                "mixed_use": "Mischnutzung"
            }
        }
        
        return translations.get(language, translations["en"])
    
    async def _save_regional_data(self):
        """Save regional data to configuration file."""
        regional_config_path = self.configs_path / "app-settings" / "regional-config.json"
        regional_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(regional_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.regional_data, f, ensure_ascii=False, indent=2)
    
    async def _save_cultural_preferences(self):
        """Save cultural preferences to configuration file."""
        cultural_config_path = self.configs_path / "app-settings" / "cultural-preferences.json"
        cultural_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dict for JSON serialization
        cultural_data = {}
        for region, prefs in self.cultural_preferences.items():
            cultural_data[region] = {
                "privacy_level": prefs.privacy_level,
                "family_structure": prefs.family_structure,
                "entertainment_style": prefs.entertainment_style,
                "outdoor_connection": prefs.outdoor_connection,
                "religious_considerations": prefs.religious_considerations,
                "dining_traditions": prefs.dining_traditions,
                "work_from_home": prefs.work_from_home,
                "multi_generational_living": prefs.multi_generational_living
            }
        
        with open(cultural_config_path, 'w', encoding='utf-8') as f:
            json.dump(cultural_data, f, ensure_ascii=False, indent=2)
    
    async def _save_building_codes(self):
        """Save building codes to configuration file."""
        building_codes_path = self.configs_path / "building-codes" / "regional-codes.json"
        building_codes_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dict for JSON serialization
        codes_data = {}
        for region, codes in self.building_codes.items():
            codes_data[region] = {
                "primary_codes": codes.primary_codes,
                "secondary_codes": codes.secondary_codes,
                "accessibility_standard": codes.accessibility_standard,
                "energy_standard": codes.energy_standard,
                "seismic_requirements": codes.seismic_requirements,
                "climate_adaptations": codes.climate_adaptations,
                "max_occupancy_ratios": codes.max_occupancy_ratios,
                "minimum_room_sizes": codes.minimum_room_sizes,
                "setback_requirements": codes.setback_requirements,
                "height_restrictions": codes.height_restrictions
            }
        
        with open(building_codes_path, 'w', encoding='utf-8') as f:
            json.dump(codes_data, f, ensure_ascii=False, indent=2)
    
    async def _save_room_types(self):
        """Save room types to configuration file."""
        room_types_path = self.configs_path / "app-settings" / "room-types.json"
        room_types_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dict for JSON serialization
        room_data = {}
        for region, types in self.room_types.items():
            room_data[region] = {}
            for type_key, room_type in types.items():
                room_data[region][type_key] = {
                    "standard_type": room_type.standard_type,
                    "localized_names": room_type.localized_names,
                    "cultural_variants": room_type.cultural_variants,
                    "typical_sizes": room_type.typical_sizes,
                    "cultural_requirements": room_type.cultural_requirements
                }
        
        with open(room_types_path, 'w', encoding='utf-8') as f:
            json.dump(room_data, f, ensure_ascii=False, indent=2)


# Global localization service instance
localization_service = LocalizationService()