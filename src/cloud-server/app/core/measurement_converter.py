"""
Regional Measurement Conversion Service
Handles conversion between metric, imperial, and mixed measurement systems
for international ArchBuilder.AI users.

This module provides comprehensive measurement conversion capabilities
with proper localization and regional preferences.
"""

from typing import Tuple, Dict, Optional, Union, Any
from enum import Enum
from dataclasses import dataclass
import structlog
from babel import Locale, numbers
from babel.core import UnknownLocaleError

logger = structlog.get_logger(__name__)


class MeasurementUnit(str, Enum):
    """Supported measurement units."""
    # Length units
    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    INCH = "in"
    FOOT = "ft"
    YARD = "yd"
    
    # Area units
    SQUARE_MILLIMETER = "mm²"
    SQUARE_CENTIMETER = "cm²"
    SQUARE_METER = "m²"
    SQUARE_INCH = "in²"
    SQUARE_FOOT = "ft²"
    SQUARE_YARD = "yd²"
    
    # Volume units
    CUBIC_METER = "m³"
    CUBIC_FOOT = "ft³"
    LITER = "L"
    GALLON = "gal"
    
    # Temperature units
    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


class MeasurementSystem(str, Enum):
    """Measurement systems for different regions."""
    METRIC = "metric"
    IMPERIAL = "imperial"
    MIXED = "mixed"


@dataclass
class MeasurementPreferences:
    """Regional measurement preferences."""
    system: MeasurementSystem
    length_unit: MeasurementUnit
    area_unit: MeasurementUnit
    volume_unit: MeasurementUnit
    temperature_unit: MeasurementUnit
    precision: int = 2  # Decimal places for display
    use_fractions: bool = False  # Use fractions instead of decimals for imperial


class RegionalMeasurementConverter:
    """
    Comprehensive measurement conversion service for ArchBuilder.AI.
    
    Handles conversion between different measurement systems based on
    regional preferences and cultural conventions.
    """
    
    def __init__(self, region: str, system: Optional[MeasurementSystem] = None):
        """
        Initialize measurement converter for a specific region.
        
        Args:
            region: Geographic region (e.g., "north_america", "europe")
            system: Override measurement system (optional)
        """
        self.region = region
        self.system = system or self._get_default_system(region)
        self.preferences = self._get_regional_preferences()
        
        # Conversion factors to base units (meters for length, square meters for area)
        self.length_conversions = {
            MeasurementUnit.MILLIMETER: 0.001,
            MeasurementUnit.CENTIMETER: 0.01,
            MeasurementUnit.METER: 1.0,
            MeasurementUnit.INCH: 0.0254,
            MeasurementUnit.FOOT: 0.3048,
            MeasurementUnit.YARD: 0.9144,
        }
        
        self.area_conversions = {
            MeasurementUnit.SQUARE_MILLIMETER: 0.000001,
            MeasurementUnit.SQUARE_CENTIMETER: 0.0001,
            MeasurementUnit.SQUARE_METER: 1.0,
            MeasurementUnit.SQUARE_INCH: 0.00064516,
            MeasurementUnit.SQUARE_FOOT: 0.092903,
            MeasurementUnit.SQUARE_YARD: 0.836127,
        }
        
        self.volume_conversions = {
            MeasurementUnit.CUBIC_METER: 1.0,
            MeasurementUnit.CUBIC_FOOT: 0.0283168,
            MeasurementUnit.LITER: 0.001,
            MeasurementUnit.GALLON: 0.00378541,  # US gallon
        }
    
    def _get_default_system(self, region: str) -> MeasurementSystem:
        """Get default measurement system for a region."""
        metric_regions = ["europe", "asia_pacific", "middle_east", "africa", "south_america"]
        
        if region == "north_america":
            return MeasurementSystem.IMPERIAL
        elif region in metric_regions:
            return MeasurementSystem.METRIC
        else:
            return MeasurementSystem.MIXED
    
    def _get_regional_preferences(self) -> MeasurementPreferences:
        """Get measurement preferences for the current region and system."""
        if self.system == MeasurementSystem.METRIC:
            return MeasurementPreferences(
                system=MeasurementSystem.METRIC,
                length_unit=MeasurementUnit.METER,
                area_unit=MeasurementUnit.SQUARE_METER,
                volume_unit=MeasurementUnit.CUBIC_METER,
                temperature_unit=MeasurementUnit.CELSIUS,
                precision=2,
                use_fractions=False
            )
        elif self.system == MeasurementSystem.IMPERIAL:
            return MeasurementPreferences(
                system=MeasurementSystem.IMPERIAL,
                length_unit=MeasurementUnit.FOOT,
                area_unit=MeasurementUnit.SQUARE_FOOT,
                volume_unit=MeasurementUnit.CUBIC_FOOT,
                temperature_unit=MeasurementUnit.FAHRENHEIT,
                precision=1,
                use_fractions=True
            )
        else:  # MIXED
            return MeasurementPreferences(
                system=MeasurementSystem.MIXED,
                length_unit=MeasurementUnit.METER,
                area_unit=MeasurementUnit.SQUARE_METER,
                volume_unit=MeasurementUnit.CUBIC_METER,
                temperature_unit=MeasurementUnit.CELSIUS,
                precision=2,
                use_fractions=False
            )
    
    def convert_length(self, value: float, from_unit: MeasurementUnit, 
                      to_unit: Optional[MeasurementUnit] = None) -> Tuple[float, MeasurementUnit]:
        """
        Convert length value between units.
        
        Args:
            value: Length value to convert
            from_unit: Source unit
            to_unit: Target unit (uses regional preference if None)
            
        Returns:
            Tuple of (converted_value, target_unit)
        """
        if to_unit is None:
            to_unit = self.preferences.length_unit
        
        if from_unit == to_unit:
            return value, to_unit
        
        # Convert to meters first, then to target unit
        meters = value * self.length_conversions[from_unit]
        converted_value = meters / self.length_conversions[to_unit]
        
        # Round to regional precision
        converted_value = round(converted_value, self.preferences.precision)
        
        return converted_value, to_unit
    
    def convert_area(self, value: float, from_unit: MeasurementUnit = MeasurementUnit.SQUARE_METER,
                    to_unit: Optional[MeasurementUnit] = None) -> Tuple[float, MeasurementUnit]:
        """
        Convert area value between units.
        
        Args:
            value: Area value to convert (default assumes square meters)
            from_unit: Source unit (default: square meters)
            to_unit: Target unit (uses regional preference if None)
            
        Returns:
            Tuple of (converted_value, target_unit)
        """
        if to_unit is None:
            to_unit = self.preferences.area_unit
        
        if from_unit == to_unit:
            return value, to_unit
        
        # Convert to square meters first, then to target unit
        square_meters = value * self.area_conversions[from_unit]
        converted_value = square_meters / self.area_conversions[to_unit]
        
        # Round to regional precision
        converted_value = round(converted_value, self.preferences.precision)
        
        return converted_value, to_unit
    
    def convert_volume(self, value: float, from_unit: MeasurementUnit,
                      to_unit: Optional[MeasurementUnit] = None) -> Tuple[float, MeasurementUnit]:
        """
        Convert volume value between units.
        
        Args:
            value: Volume value to convert
            from_unit: Source unit
            to_unit: Target unit (uses regional preference if None)
            
        Returns:
            Tuple of (converted_value, target_unit)
        """
        if to_unit is None:
            to_unit = self.preferences.volume_unit
        
        if from_unit == to_unit:
            return value, to_unit
        
        # Convert to cubic meters first, then to target unit
        cubic_meters = value * self.volume_conversions[from_unit]
        converted_value = cubic_meters / self.volume_conversions[to_unit]
        
        # Round to regional precision
        converted_value = round(converted_value, self.preferences.precision)
        
        return converted_value, to_unit
    
    def convert_temperature(self, value: float, from_unit: MeasurementUnit,
                           to_unit: Optional[MeasurementUnit] = None) -> Tuple[float, MeasurementUnit]:
        """
        Convert temperature value between units.
        
        Args:
            value: Temperature value to convert
            from_unit: Source unit
            to_unit: Target unit (uses regional preference if None)
            
        Returns:
            Tuple of (converted_value, target_unit)
        """
        if to_unit is None:
            to_unit = self.preferences.temperature_unit
        
        if from_unit == to_unit:
            return value, to_unit
        
        # Convert to Celsius first, then to target unit
        if from_unit == MeasurementUnit.FAHRENHEIT:
            celsius = (value - 32) * 5/9
        elif from_unit == MeasurementUnit.KELVIN:
            celsius = value - 273.15
        else:  # Already Celsius
            celsius = value
        
        # Convert from Celsius to target unit
        if to_unit == MeasurementUnit.FAHRENHEIT:
            converted_value = celsius * 9/5 + 32
        elif to_unit == MeasurementUnit.KELVIN:
            converted_value = celsius + 273.15
        else:  # Celsius
            converted_value = celsius
        
        # Round to regional precision
        converted_value = round(converted_value, self.preferences.precision)
        
        return converted_value, to_unit
    
    def format_length(self, value: float, unit: MeasurementUnit, 
                     locale_str: Optional[str] = None) -> str:
        """
        Format length value with proper localization.
        
        Args:
            value: Length value
            unit: Measurement unit
            locale_str: Locale for number formatting
            
        Returns:
            Formatted length string
        """
        try:
            if locale_str:
                locale_obj = Locale.parse(locale_str)
                formatted_value = numbers.format_decimal(value, locale=locale_obj)
            else:
                formatted_value = f"{value:.{self.preferences.precision}f}"
            
            # Handle imperial fractions if preferred
            if self.preferences.use_fractions and unit in [MeasurementUnit.FOOT, MeasurementUnit.INCH]:
                # Convert decimal to fraction (simplified implementation)
                if unit == MeasurementUnit.FOOT:
                    feet = int(value)
                    inches = (value - feet) * 12
                    if inches > 0:
                        return f"{feet}' {inches:.0f}\""
                    else:
                        return f"{feet}'"
            
            return f"{formatted_value} {unit.value}"
            
        except (UnknownLocaleError, Exception) as e:
            logger.warning(f"Error formatting length: {e}")
            return f"{value:.{self.preferences.precision}f} {unit.value}"
    
    def format_area(self, value: float, unit: MeasurementUnit,
                   locale_str: Optional[str] = None) -> str:
        """
        Format area value with proper localization.
        
        Args:
            value: Area value
            unit: Measurement unit
            locale_str: Locale for number formatting
            
        Returns:
            Formatted area string
        """
        try:
            if locale_str:
                locale_obj = Locale.parse(locale_str)
                formatted_value = numbers.format_decimal(value, locale=locale_obj)
            else:
                formatted_value = f"{value:.{self.preferences.precision}f}"
            
            return f"{formatted_value} {unit.value}"
            
        except (UnknownLocaleError, Exception) as e:
            logger.warning(f"Error formatting area: {e}")
            return f"{value:.{self.preferences.precision}f} {unit.value}"
    
    def format_temperature(self, value: float, unit: MeasurementUnit,
                          locale_str: Optional[str] = None) -> str:
        """
        Format temperature value with proper localization.
        
        Args:
            value: Temperature value
            unit: Measurement unit
            locale_str: Locale for number formatting
            
        Returns:
            Formatted temperature string
        """
        try:
            if locale_str:
                locale_obj = Locale.parse(locale_str)
                formatted_value = numbers.format_decimal(value, locale=locale_obj)
            else:
                formatted_value = f"{value:.{self.preferences.precision}f}"
            
            return f"{formatted_value}{unit.value}"
            
        except (UnknownLocaleError, Exception) as e:
            logger.warning(f"Error formatting temperature: {e}")
            return f"{value:.{self.preferences.precision}f}{unit.value}"
    
    def get_regional_room_dimensions(self, room_type: str) -> Dict[str, Tuple[float, MeasurementUnit]]:
        """
        Get typical room dimensions for the region in regional units.
        
        Args:
            room_type: Type of room (e.g., "bedroom", "living_room")
            
        Returns:
            Dictionary with min/max dimensions in regional units
        """
        # Standard dimensions in square meters
        standard_dimensions = {
            "bedroom": {"min": 9.0, "max": 25.0},
            "living_room": {"min": 12.0, "max": 50.0},
            "kitchen": {"min": 6.0, "max": 20.0},
            "bathroom": {"min": 3.0, "max": 15.0},
            "dining_room": {"min": 8.0, "max": 30.0},
            "office": {"min": 5.0, "max": 20.0},
            "laundry": {"min": 3.0, "max": 10.0},
            "storage": {"min": 2.0, "max": 15.0},
        }
        
        dimensions = standard_dimensions.get(room_type, {"min": 5.0, "max": 20.0})
        
        # Convert to regional units
        min_converted, unit = self.convert_area(dimensions["min"], MeasurementUnit.SQUARE_METER)
        max_converted, _ = self.convert_area(dimensions["max"], MeasurementUnit.SQUARE_METER)
        
        return {
            "min": (min_converted, unit),
            "max": (max_converted, unit)
        }
    
    def parse_user_input(self, input_str: str) -> Tuple[float, MeasurementUnit]:
        """
        Parse user input string to extract value and unit.
        
        Args:
            input_str: User input string (e.g., "150 sqft", "50 m²")
            
        Returns:
            Tuple of (value, unit)
        """
        input_str = input_str.strip().lower()
        
        # Common patterns to match
        patterns = {
            "sqft": MeasurementUnit.SQUARE_FOOT,
            "sq ft": MeasurementUnit.SQUARE_FOOT,
            "square feet": MeasurementUnit.SQUARE_FOOT,
            "ft²": MeasurementUnit.SQUARE_FOOT,
            "m²": MeasurementUnit.SQUARE_METER,
            "sqm": MeasurementUnit.SQUARE_METER,
            "sq m": MeasurementUnit.SQUARE_METER,
            "square meters": MeasurementUnit.SQUARE_METER,
            "square metres": MeasurementUnit.SQUARE_METER,
            "ft": MeasurementUnit.FOOT,
            "feet": MeasurementUnit.FOOT,
            "m": MeasurementUnit.METER,
            "meters": MeasurementUnit.METER,
            "metres": MeasurementUnit.METER,
            "in": MeasurementUnit.INCH,
            "inches": MeasurementUnit.INCH,
            "cm": MeasurementUnit.CENTIMETER,
            "mm": MeasurementUnit.MILLIMETER,
        }
        
        # Try to extract number and unit
        import re
        
        # Pattern to match number followed by optional unit
        pattern = r'(\d+(?:\.\d+)?)\s*([a-zA-Z²°\s]+)?'
        match = re.search(pattern, input_str)
        
        if match:
            value = float(match.group(1))
            unit_str = match.group(2).strip() if match.group(2) else ""
            
            # Find matching unit
            for pattern_str, unit in patterns.items():
                if pattern_str in unit_str:
                    return value, unit
            
            # If no unit found, use regional default
            if "²" in input_str or "sq" in input_str:
                return value, self.preferences.area_unit
            else:
                return value, self.preferences.length_unit
        
        # Fallback: try to parse as just a number
        try:
            value = float(input_str)
            return value, self.preferences.area_unit  # Assume area for building context
        except ValueError:
            raise ValueError(f"Could not parse measurement input: {input_str}")
    
    def get_conversion_info(self) -> Dict[str, Any]:
        """
        Get conversion information for the current region.
        
        Returns:
            Dictionary with conversion factors and preferences
        """
        return {
            "region": self.region,
            "system": self.system.value,
            "preferences": {
                "length_unit": self.preferences.length_unit.value,
                "area_unit": self.preferences.area_unit.value,
                "volume_unit": self.preferences.volume_unit.value,
                "temperature_unit": self.preferences.temperature_unit.value,
                "precision": self.preferences.precision,
                "use_fractions": self.preferences.use_fractions,
            },
            "common_conversions": {
                "1_sqm_to_sqft": round(1.0 / self.area_conversions[MeasurementUnit.SQUARE_FOOT], 4),
                "1_meter_to_feet": round(1.0 / self.length_conversions[MeasurementUnit.FOOT], 4),
                "celsius_to_fahrenheit": "°F = °C × 9/5 + 32",
                "fahrenheit_to_celsius": "°C = (°F - 32) × 5/9",
            }
        }


def create_converter(region: str, system: Optional[MeasurementSystem] = None) -> RegionalMeasurementConverter:
    """
    Factory function to create a measurement converter for a specific region.
    
    Args:
        region: Geographic region
        system: Override measurement system (optional)
        
    Returns:
        Configured RegionalMeasurementConverter instance
    """
    return RegionalMeasurementConverter(region, system)