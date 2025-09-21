"""
Unit tests for AI Service functionality
Tests individual AI service methods and validation
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
from datetime import datetime
import uuid

from app.services.ai_service import AIService, AIModelSelector, AIFallbackService
from app.models.ai import (
    AIProcessingRequest, AIProcessingResponse, AIProcessingStatus, 
    AIProvider, AIModelConfig, PromptContext
)


class TestAIModelSelector:
    """Test AI model selection logic"""
    
    def test_select_model_simple_task_turkish(self):
        """Test model selection for simple Turkish task"""
        selector = AIModelSelector()
        
        result = selector.select_model(
            language="tr",
            document_type="prompt_generation",
            complexity="simple",
            analysis_type="creation"
        )
        
        assert result["provider"] == "vertex_ai"
        assert result["model"] == "gemini-2.5-flash-lite"
        assert "cost-effective" in result["reason"]
    
    def test_select_model_complex_task_english(self):
        """Test model selection for complex English task"""
        selector = AIModelSelector()
        
        result = selector.select_model(
            language="en",
            document_type="general",
            complexity="high",
            file_format="ifc",
            analysis_type="creation"
        )
        
        assert result["provider"] == "github_models"
        assert result["model"] == "gpt-4.1"
        assert "CAD parsing" in result["reason"]
    
    def test_select_model_existing_project_analysis(self):
        """Test model selection for existing project analysis"""
        selector = AIModelSelector()
        
        result = selector.select_model(
            language="en",
            document_type="general",
            complexity="medium",
            analysis_type="existing_project_analysis"
        )
        
        assert result["provider"] == "github_models"
        assert result["model"] == "gpt-4.1"
        assert "BIM analysis" in result["reason"]
    
    def test_select_model_building_codes_turkish(self):
        """Test model selection for Turkish building codes"""
        selector = AIModelSelector()
        
        result = selector.select_model(
            language="tr",
            document_type="building_code",
            complexity="medium"
        )
        
        assert result["provider"] == "vertex_ai"
        assert result["model"] == "gemini-2.5-flash-lite"
        assert "Turkish regulatory" in result["reason"]
    
    def test_select_model_dwg_file_analysis(self):
        """Test model selection for DWG file analysis"""
        selector = AIModelSelector()
        
        result = selector.select_model(
            language="en",
            document_type="general",
            complexity="medium",
            file_format="dwg"
        )
        
        assert result["provider"] == "github_models"
        assert result["model"] == "gpt-4.1"
        assert "multi-format CAD" in result["reason"]


@pytest.mark.asyncio
class TestAIService:
    """Test AI Service main functionality"""
    
    async def test_process_command_success(self):
        """Test successful command processing"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_vertex_client.generate_content = AsyncMock(return_value={
            "content": "Generated layout successfully",
            "confidence": 0.95,
            "processing_time_ms": 1500
        })
        
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_validator.validate_layout_output = AsyncMock(return_value=Mock(
            is_valid=True,
            confidence_score=0.95,
            validation_errors=[],
            requires_human_review=False
        ))
        
        mock_prompt_engine = Mock()
        mock_prompt_engine.get_layout_generation_prompt = Mock(return_value="Generated prompt")
        
        # Create AI service with mocked dependencies
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        # Create test request
        request = AIProcessingRequest(
            correlation_id="test-123",
            prompt="Create a simple room layout",
            ai_model_config=AIModelConfig(
                provider=AIProvider.VERTEX_AI,
                model_name="gemini-2.5-flash-lite"
            ),
            confidence_threshold=0.7,
            context=PromptContext(language="en")
        )
        
        # Process command
        result = await ai_service.process_command(request, "user123", "test-123")
        
        # Assertions
        assert result.status == AIProcessingStatus.COMPLETED
        assert result.confidence_score == 0.95
        assert result.validation_passed is True
        assert len(result.validation_errors) == 0
    
    async def test_process_command_validation_failure(self):
        """Test command processing with validation failure"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_vertex_client.generate_content = AsyncMock(return_value={
            "content": "Invalid layout generated",
            "confidence": 0.95,
            "processing_time_ms": 1500
        })
        
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_validator.validate_layout_output = AsyncMock(return_value=Mock(
            is_valid=False,
            confidence_score=0.3,
            validation_errors=["Ceiling height too low"],
            requires_human_review=True
        ))
        
        mock_prompt_engine = Mock()
        mock_prompt_engine.get_layout_generation_prompt = Mock(return_value="Generated prompt")
        
        # Create AI service with mocked dependencies
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        # Create test request
        request = AIProcessingRequest(
            correlation_id="test-123",
            prompt="Create an invalid room layout",
            ai_model_config=AIModelConfig(
                provider=AIProvider.VERTEX_AI,
                model_name="gemini-2.5-flash-lite"
            ),
            confidence_threshold=0.7,
            context=PromptContext(language="en")
        )
        
        # Process command
        result = await ai_service.process_command(request, "user123", "test-123")
        
        # Assertions
        assert result.status == AIProcessingStatus.COMPLETED
        assert result.confidence_score == 0.3
        assert result.validation_passed is False
        assert "Ceiling height too low" in result.validation_errors
    
    async def test_process_command_ai_error(self):
        """Test command processing with AI service error"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_vertex_client.generate_content = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
        
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_prompt_engine = Mock()
        mock_prompt_engine.get_layout_generation_prompt = Mock(return_value="Generated prompt")
        
        # Create AI service with mocked dependencies
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        # Create test request
        request = AIProcessingRequest(
            correlation_id="test-123",
            prompt="Create a room layout",
            ai_model_config=AIModelConfig(
                provider=AIProvider.VERTEX_AI,
                model_name="gemini-2.5-flash-lite"
            ),
            confidence_threshold=0.7,
            context=PromptContext(language="en")
        )
        
        # Process command
        result = await ai_service.process_command(request, "user123", "test-123")
        
        # Assertions
        assert result.status == AIProcessingStatus.FAILED
        assert result.confidence_score == 0.0
        assert result.validation_passed is False
        assert len(result.validation_errors) > 0
    
    async def test_analyze_existing_project(self):
        """Test existing project analysis functionality"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_github_client = Mock()
        mock_github_client.generate_analysis = AsyncMock(return_value={
            "analysis": "Comprehensive BIM analysis completed",
            "recommendations": ["Improve circulation", "Optimize room sizes"],
            "priority_issues": ["Fire safety compliance"],
            "confidence": 0.92
        })
        
        mock_validator = Mock()
        mock_prompt_engine = Mock()
        mock_prompt_engine.get_project_analysis_prompt = Mock(return_value="Analysis prompt")
        
        # Create AI service with mocked dependencies
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        # Test project data
        project_data = {
            "total_elements": 1500,
            "rooms": ["Living Room", "Kitchen", "Bedroom"],
            "area_m2": 120
        }
        
        # Analyze project
        result = await ai_service.analyze_existing_project(project_data, "test-123")
        
        # Assertions
        assert "analysis" in result
        assert len(result["recommendations"]) == 2
        assert len(result["priority_issues"]) == 1
        assert result["confidence"] == 0.92
        assert result["requires_expert_review"] is False  # confidence > 0.9
    
    def test_assess_complexity_simple(self):
        """Test complexity assessment for simple prompts"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_prompt_engine = Mock()
        
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        complexity = ai_service._assess_complexity("Create a simple room")
        assert complexity == "simple"
    
    def test_assess_complexity_high(self):
        """Test complexity assessment for complex prompts"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_prompt_engine = Mock()
        
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        complexity = ai_service._assess_complexity(
            "Create a multi-story complex building with irregular shape and custom analysis"
        )
        assert complexity == "high"
    
    def test_assess_complexity_medium_default(self):
        """Test complexity assessment defaults to medium"""
        # Create mock dependencies
        mock_vertex_client = Mock()
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_prompt_engine = Mock()
        
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        complexity = ai_service._assess_complexity("Create some architectural layout")
        assert complexity == "medium"


class TestAIFallbackService:
    """Test AI Fallback Service functionality"""
    
    def test_generate_layout_fallback_success(self):
        """Test successful fallback layout generation"""
        fallback_service = AIFallbackService()
        
        requirements = {
            "total_area_m2": 100,
            "rooms": ["Living Room", "Kitchen", "Bedroom", "Bathroom"]
        }
        
        result = fallback_service.generate_layout_fallback(requirements)
        
        # Assertions
        assert "walls" in result
        assert "doors" in result
        assert result["confidence"] == 0.7
        assert result["generated_by"] == "fallback"
        assert result["requires_human_review"] is True
        assert len(result["walls"]) > 0  # Should have walls for each room
    
    def test_generate_layout_fallback_no_rooms(self):
        """Test fallback generation with no rooms specified"""
        fallback_service = AIFallbackService()
        
        requirements = {
            "total_area_m2": 100,
            "rooms": []
        }
        
        with pytest.raises(ValueError, match="No rooms specified"):
            fallback_service.generate_layout_fallback(requirements)
    
    def test_create_room_walls(self):
        """Test room wall creation functionality"""
        fallback_service = AIFallbackService()
        
        walls = fallback_service._create_room_walls(0, 0, 5000, 4000)  # 5m x 4m room
        
        # Should create 4 walls (bottom, right, top, left)
        assert len(walls) == 4
        
        # Check wall properties
        for wall in walls:
            assert "start_point" in wall
            assert "end_point" in wall
            assert wall["height_mm"] == 2700
            assert wall["wall_type_name"] == "Generic - 200mm"
        
        # Check wall coordinates form a rectangle
        bottom_wall = walls[0]
        assert bottom_wall["start_point"]["x"] == 0
        assert bottom_wall["start_point"]["y"] == 0
        assert bottom_wall["end_point"]["x"] == 5000
        assert bottom_wall["end_point"]["y"] == 0


@pytest.mark.asyncio
class TestAIServiceIntegration:
    """Integration tests for AI Service with real-like scenarios"""
    
    async def test_complete_workflow_residential_layout(self):
        """Test complete workflow for residential layout generation"""
        # Create comprehensive mock setup
        mock_vertex_client = Mock()
        mock_vertex_client.generate_content = AsyncMock(return_value={
            "content": "Generated comprehensive 3-bedroom layout with optimized flow",
            "confidence": 0.92,
            "processing_time_ms": 2200
        })
        
        mock_github_client = Mock()
        mock_validator = Mock()
        mock_validator.validate_layout_output = AsyncMock(return_value=Mock(
            is_valid=True,
            confidence_score=0.92,
            validation_errors=[],
            requires_human_review=False
        ))
        
        mock_prompt_engine = Mock()
        mock_prompt_engine.get_layout_generation_prompt = Mock(
            return_value="Create a 3-bedroom residential layout..."
        )
        
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        request = AIProcessingRequest(
            correlation_id="test-residential",
            prompt="3 bedroom residential house layout with living room and kitchen",
            ai_model_config=AIModelConfig(
                provider=AIProvider.VERTEX_AI,
                model_name="gemini-2.5-flash-lite"
            ),
            confidence_threshold=0.7,
            context=PromptContext(
                language="en",
                region="Turkey",
                variables={
                    "building_type": "residential",
                    "include_furniture": True,
                    "optimize_layout": True,
                    "accessibility_compliance": True
                }
            )
        )
        
        result = await ai_service.process_command(request, "user123", "test-residential")
        
        # Comprehensive assertions
        assert result.status == AIProcessingStatus.COMPLETED
        assert result.confidence_score == 0.92
        assert result.validation_passed is True
        assert result.processing_time_ms > 0
        assert result.model_used in ["gemini-2.5-flash-lite", "gpt-4.1"]
    
    async def test_workflow_with_github_models_selection(self):
        """Test workflow that should use GitHub Models"""
        # Create mock setup for GitHub Models
        mock_vertex_client = Mock()
        mock_github_client = Mock()
        mock_github_client.generate_content = AsyncMock(return_value={
            "content": "Generated office layout with comprehensive fire safety measures",
            "confidence": 0.88,
            "processing_time_ms": 3500
        })
        
        mock_validator = Mock()
        mock_validator.validate_layout_output = AsyncMock(return_value=Mock(
            is_valid=True,
            confidence_score=0.88,
            validation_errors=[],
            requires_human_review=False
        ))
        
        mock_prompt_engine = Mock()
        mock_prompt_engine.get_layout_generation_prompt = Mock(
            return_value="Create office layout with fire safety compliance..."
        )
        
        ai_service = AIService(
            vertex_client=mock_vertex_client,
            github_client=mock_github_client,
            validator=mock_validator,
            prompt_engine=mock_prompt_engine
        )
        
        # Request that should trigger GitHub Models selection (high complexity)
        request = AIProcessingRequest(
            correlation_id="test-office",
            prompt="Office building layout with fire safety compliance and complex irregular shapes",
            ai_model_config=AIModelConfig(
                provider=AIProvider.GITHUB_MODELS,
                model_name="gpt-4.1"
            ),
            confidence_threshold=0.7,
            context=PromptContext(
                language="en",
                region="Turkey",
                variables={
                    "building_type": "commercial",
                    "fire_safety_analysis": True,
                    "evacuation_routes": True
                }
            )
        )
        
        result = await ai_service.process_command(request, "user123", "test-office")
        
        assert result.status == AIProcessingStatus.COMPLETED
        assert result.provider == AIProvider.GITHUB_MODELS
        assert result.confidence_score == 0.88
        
        # Verify GitHub client was called
        mock_github_client.generate_content.assert_called_once()