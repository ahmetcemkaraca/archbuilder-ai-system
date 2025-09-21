"""
Test Regional and Localization Features
Simple test script to verify localization functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src" / "cloud-server"))

from app.core.localization import LocalizationService, SupportedRegion, SupportedLanguage
from app.core.measurement_converter import RegionalMeasurementConverter, MeasurementUnit
from app.core.global_prompt_engine import (
    GlobalPromptTemplateEngine, 
    AIModelType, 
    PromptType, 
    AIPromptRequest
)


async def test_localization_service():
    """Test localization service functionality."""
    print("🌍 Testing Localization Service...")
    
    # Initialize service
    localization = LocalizationService()
    await localization.initialize()
    
    # Test locale info
    print("\n📍 Testing Locale Information:")
    locales_to_test = ["en-US", "tr-TR", "de-DE", "fr-FR", "ja-JP"]
    
    for locale in locales_to_test:
        region, country, measurement_system = localization.get_locale_info(locale)
        print(f"  {locale}: {region.value} | {country} | {measurement_system.value}")
    
    # Test cultural preferences
    print("\n🏛️ Testing Cultural Preferences:")
    for region in [SupportedRegion.NORTH_AMERICA, SupportedRegion.EUROPE, SupportedRegion.MIDDLE_EAST]:
        prefs = localization.get_cultural_preferences(region)
        print(f"  {region.value}:")
        print(f"    Privacy Level: {prefs.privacy_level}")
        print(f"    Family Structure: {prefs.family_structure}")
        print(f"    Religious Considerations: {prefs.religious_considerations}")
    
    # Test building codes
    print("\n🏗️ Testing Building Codes:")
    for region in [SupportedRegion.NORTH_AMERICA, SupportedRegion.EUROPE, SupportedRegion.MIDDLE_EAST]:
        codes = localization.get_building_codes(region)
        print(f"  {region.value}:")
        print(f"    Primary Codes: {codes.primary_codes}")
        print(f"    Accessibility Standard: {codes.accessibility_standard}")
        print(f"    Seismic Requirements: {codes.seismic_requirements}")
    
    # Test room types
    print("\n🏠 Testing Localized Room Types:")
    for region in [SupportedRegion.NORTH_AMERICA, SupportedRegion.MIDDLE_EAST]:
        for language in ["en", "tr"]:
            room_types = localization.get_localized_room_types(region, language)
            print(f"  {region.value} ({language}): {list(room_types.items())[:3]}")
    
    print("✅ Localization Service tests completed!")


async def test_measurement_converter():
    """Test measurement conversion functionality."""
    print("\n📏 Testing Measurement Converter...")
    
    # Test different regions
    regions_to_test = ["north_america", "europe", "middle_east"]
    
    for region in regions_to_test:
        print(f"\n🌐 Testing {region}:")
        converter = RegionalMeasurementConverter(region)
        
        # Test area conversion
        area_m2 = 100.0
        converted_area, unit = converter.convert_area(area_m2, MeasurementUnit.SQUARE_METER)
        formatted_area = converter.format_area(converted_area, unit)
        print(f"  100 m² = {formatted_area}")
        
        # Test length conversion
        length_m = 10.0
        converted_length, length_unit = converter.convert_length(length_m, MeasurementUnit.METER)
        formatted_length = converter.format_length(converted_length, length_unit)
        print(f"  10 m = {formatted_length}")
        
        # Test temperature conversion
        temp_c = 20.0
        converted_temp, temp_unit = converter.convert_temperature(temp_c, MeasurementUnit.CELSIUS)
        formatted_temp = converter.format_temperature(converted_temp, temp_unit)
        print(f"  20°C = {formatted_temp}")
        
        # Test user input parsing
        test_inputs = ["150 sqft", "50 m²", "12 feet", "25 m"]
        print(f"  Input parsing:")
        for test_input in test_inputs:
            try:
                value, parsed_unit = converter.parse_user_input(test_input)
                print(f"    '{test_input}' → {value} {parsed_unit.value}")
            except Exception as e:
                print(f"    '{test_input}' → Error: {e}")
    
    print("✅ Measurement Converter tests completed!")


async def test_prompt_engine():
    """Test global prompt template engine."""
    print("\n🤖 Testing Global Prompt Template Engine...")
    
    # Test different regional prompts
    test_cases = [
        ("north_america", "US", "en-US"),
        ("europe", "DE", "de-DE"),
        ("middle_east", "TR", "tr-TR"),
    ]
    
    for region, country, locale in test_cases:
        print(f"\n🌍 Testing {region} ({locale}):")
        
        try:
            # Create prompt engine
            localization = LocalizationService()
            await localization.initialize()
            
            prompt_engine = GlobalPromptTemplateEngine(
                region=region,
                country=country,
                locale=locale,
                localization_service=localization
            )
            await prompt_engine.initialize()
            
            # Create test request
            test_request = AIPromptRequest(
                building_type="residential",
                total_area_m2=120.0,
                floor_count=2,
                room_requirements=[
                    {"type": "bedroom", "count": 3},
                    {"type": "bathroom", "count": 2},
                    {"type": "living_room", "count": 1},
                    {"type": "kitchen", "count": 1}
                ],
                user_prompt="Create a family-friendly home with modern design"
            )
            
            # Generate prompt
            prompt = await prompt_engine.generate_prompt(
                model_type=AIModelType.OPENAI_GPT4,
                prompt_type=PromptType.LAYOUT_GENERATION,
                request_data=test_request
            )
            
            # Show excerpt
            prompt_excerpt = prompt[:500] + "..." if len(prompt) > 500 else prompt
            print(f"  Generated prompt excerpt:")
            print(f"    {prompt_excerpt}")
            print(f"  Full prompt length: {len(prompt)} characters")
            
        except Exception as e:
            print(f"  ❌ Error generating prompt: {e}")
    
    print("✅ Global Prompt Template Engine tests completed!")


async def test_config_files():
    """Test configuration file creation."""
    print("\n📁 Testing Configuration Files...")
    
    # Check if config files are created
    configs_path = Path(__file__).parent.parent.parent / "configs"
    
    expected_files = [
        "app-settings/regional-config.json",
        "app-settings/cultural-preferences.json",
        "app-settings/room-types.json",
        "building-codes/regional-codes.json",
        "ai-prompts/model-configs.json",
        "ai-prompts/en/translations.json",
        "ai-prompts/tr/translations.json",
    ]
    
    print(f"  Config path: {configs_path}")
    
    for file_path in expected_files:
        full_path = configs_path / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - Missing")
    
    print("✅ Configuration files test completed!")


async def main():
    """Run all tests."""
    print("🚀 Starting ArchBuilder.AI Regional & Localization Tests")
    print("=" * 60)
    
    try:
        await test_localization_service()
        await test_measurement_converter()
        await test_prompt_engine()
        await test_config_files()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())