"""
Comprehensive AI Validator for ArchBuilder.AI
Implements multi-layer validation for AI outputs including building code compliance,
safety checks, and human review workflows
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

import structlog

from .....core.logging import get_logger
from .....models.ai import ValidationResult, ValidationStatus, ReviewStatus

logger = get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Validation issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationCategory(str, Enum):
    """Validation categories for architectural outputs"""
    BUILDING_CODE = "building_code"
    SAFETY = "safety"
    ACCESSIBILITY = "accessibility"
    STRUCTURAL = "structural"
    MEP = "mep"  # Mechanical, Electrical, Plumbing
    SUSTAINABILITY = "sustainability"
    COST = "cost"
    FEASIBILITY = "feasibility"


class ComprehensiveAIValidator:
    """
    Comprehensive validation system for AI-generated architectural content
    Implements multi-layer validation with building code compliance
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Validation rules by category
        self.validation_rules = {
            ValidationCategory.BUILDING_CODE: {
                "min_room_area_m2": 7.0,  # Minimum habitable room area
                "min_corridor_width_mm": 1200,  # Minimum corridor width
                "max_travel_distance_m": 45,  # Maximum travel distance to exit
                "min_ceiling_height_mm": 2400,  # Minimum ceiling height
                "min_stair_width_mm": 1000,  # Minimum stair width
                "max_ramp_slope_percent": 8.33,  # Maximum ramp slope (1:12)
            },
            ValidationCategory.ACCESSIBILITY: {
                "min_door_width_mm": 850,  # Accessible door width
                "max_door_threshold_mm": 12,  # Maximum door threshold
                "min_accessible_route_width_mm": 1200,  # Accessible route width
                "elevator_required_floors": 3,  # Elevator required for 3+ floors
            },
            ValidationCategory.SAFETY: {
                "fire_exit_spacing_m": 30,  # Maximum spacing between fire exits
                "emergency_lighting_required": True,
                "smoke_detector_spacing_m": 15,  # Maximum smoke detector spacing
                "fire_rated_corridor_width_mm": 1800,  # Fire-rated corridor minimum width
            }
        }
        
        # Confidence thresholds
        self.confidence_thresholds = {
            "auto_approve": 0.95,  # Auto-approve if confidence > 95%
            "requires_review": 0.80,  # Human review if confidence < 80%
            "requires_expert": 0.60,  # Expert review if confidence < 60%
        }
    
    async def validate_layout(self, ai_output: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive validation of AI-generated layout
        
        Args:
            ai_output: AI-generated layout data
            
        Returns:
            ValidationResult with validation status and details
        """
        
        self.logger.info(
            "Starting comprehensive layout validation",
            output_keys=list(ai_output.keys())
        )
        
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Extract layout data
            layout_data = ai_output.get("layout", ai_output)
            
            # 1. Validate structure and required fields
            structure_errors = self._validate_structure(layout_data)
            errors.extend(structure_errors)
            
            # 2. Validate building code compliance
            code_errors, code_warnings = self._validate_building_codes(layout_data)
            errors.extend(code_errors)
            warnings.extend(code_warnings)
            
            # 3. Validate accessibility compliance
            accessibility_errors, accessibility_warnings = self._validate_accessibility(layout_data)
            errors.extend(accessibility_errors)
            warnings.extend(accessibility_warnings)
            
            # 4. Validate safety requirements
            safety_errors, safety_warnings = self._validate_safety(layout_data)
            errors.extend(safety_errors)
            warnings.extend(safety_warnings)
            
            # 5. Validate spatial relationships
            spatial_warnings = self._validate_spatial_relationships(layout_data)
            warnings.extend(spatial_warnings)
            
            # 6. Generate improvement suggestions
            suggestions = self._generate_suggestions(layout_data, errors, warnings)
            
            # 7. Calculate overall confidence and compliance score
            confidence = self._calculate_confidence(ai_output, errors, warnings)
            compliance_score = self._calculate_compliance_score(errors, warnings)
            
            # 8. Determine validation status
            status = self._determine_validation_status(errors, warnings, confidence)
            
            # 9. Determine if human review is required
            requires_human_review = self._requires_human_review(confidence, errors, warnings)
            
            self.logger.info(
                "Layout validation completed",
                status=status,
                confidence=confidence,
                compliance_score=compliance_score,
                error_count=len(errors),
                warning_count=len(warnings),
                requires_review=requires_human_review
            )
            
            return ValidationResult(
                status=status,
                is_valid=status == ValidationStatus.VALID,
                confidence=confidence,
                compliance_score=compliance_score,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                requires_human_review=requires_human_review,
                validation_timestamp=datetime.utcnow(),
                categories_checked=[
                    ValidationCategory.BUILDING_CODE,
                    ValidationCategory.ACCESSIBILITY,
                    ValidationCategory.SAFETY,
                    ValidationCategory.FEASIBILITY
                ]
            )
            
        except Exception as e:
            self.logger.error(
                "Layout validation failed",
                error=str(e),
                error_type=type(e).__name__
            )
            
            return ValidationResult(
                status=ValidationStatus.ERROR,
                is_valid=False,
                confidence=0.0,
                compliance_score=0.0,
                errors=[{
                    "category": "system",
                    "severity": ValidationSeverity.CRITICAL,
                    "message": f"Validation system error: {str(e)}",
                    "code": "VALIDATION_SYSTEM_ERROR"
                }],
                warnings=[],
                suggestions=[],
                requires_human_review=True,
                validation_timestamp=datetime.utcnow()
            )
    
    async def validate_command_output(
        self,
        ai_output: Dict[str, Any],
        command_type: str
    ) -> ValidationResult:
        """
        Validate specific AI command output based on command type
        """
        
        self.logger.info(
            "Validating command output",
            command_type=command_type
        )
        
        if command_type in ["layout_generation", "room_generation"]:
            return await self.validate_layout(ai_output)
        elif command_type == "existing_project_analysis":
            return await self.validate_project_analysis(ai_output)
        elif command_type == "building_code_compliance":
            return await self.validate_compliance_check(ai_output)
        else:
            # Generic validation for other command types
            return await self.validate_generic_output(ai_output)
    
    async def validate_project_analysis(
        self,
        analysis_output: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate AI-generated project analysis
        """
        
        self.logger.info("Validating project analysis output")
        
        errors = []
        warnings = []
        suggestions = []
        
        # Check for required analysis components
        required_sections = [
            "project_analysis",
            "performance_issues",
            "design_improvements",
            "compliance_issues"
        ]
        
        for section in required_sections:
            if section not in analysis_output:
                errors.append({
                    "category": "structure",
                    "severity": ValidationSeverity.HIGH,
                    "message": f"Missing required analysis section: {section}",
                    "code": "MISSING_ANALYSIS_SECTION"
                })
        
        # Validate analysis completeness
        project_analysis = analysis_output.get("project_analysis", {})
        if not project_analysis.get("overall_score"):
            warnings.append({
                "category": "completeness",
                "severity": ValidationSeverity.MEDIUM,
                "message": "Missing overall project score",
                "code": "MISSING_PROJECT_SCORE"
            })
        
        # Check confidence levels
        confidence = analysis_output.get("confidence", 0.0)
        if confidence < 0.7:
            warnings.append({
                "category": "confidence",
                "severity": ValidationSeverity.MEDIUM,
                "message": f"Low analysis confidence: {confidence}",
                "code": "LOW_ANALYSIS_CONFIDENCE"
            })
        
        compliance_score = len([e for e in errors if e["severity"] in [ValidationSeverity.HIGH, ValidationSeverity.CRITICAL]]) / max(1, len(errors) + len(warnings))
        
        return ValidationResult(
            status=ValidationStatus.VALID if len(errors) == 0 else ValidationStatus.REQUIRES_REVIEW,
            is_valid=len(errors) == 0,
            confidence=confidence,
            compliance_score=1.0 - compliance_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            requires_human_review=confidence < 0.8 or len(errors) > 0,
            validation_timestamp=datetime.utcnow()
        )
    
    async def validate_compliance_check(
        self,
        compliance_output: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate building code compliance check output
        """
        
        self.logger.info("Validating compliance check output")
        
        errors = []
        warnings = []
        
        # Check for required compliance components
        if "compliance_analysis" not in compliance_output:
            errors.append({
                "category": "structure",
                "severity": ValidationSeverity.CRITICAL,
                "message": "Missing compliance analysis section",
                "code": "MISSING_COMPLIANCE_ANALYSIS"
            })
        
        compliance_analysis = compliance_output.get("compliance_analysis", {})
        
        # Validate compliance score
        compliance_score = compliance_analysis.get("overall_score", 0.0)
        if compliance_score < 0.6:
            errors.append({
                "category": "compliance",
                "severity": ValidationSeverity.HIGH,
                "message": f"Low compliance score: {compliance_score}",
                "code": "LOW_COMPLIANCE_SCORE"
            })
        
        confidence = compliance_output.get("confidence", 0.0)
        
        return ValidationResult(
            status=ValidationStatus.VALID if len(errors) == 0 else ValidationStatus.REQUIRES_REVIEW,
            is_valid=len(errors) == 0,
            confidence=confidence,
            compliance_score=compliance_score,
            errors=errors,
            warnings=warnings,
            suggestions=[],
            requires_human_review=confidence < 0.9 or compliance_score < 0.8,
            validation_timestamp=datetime.utcnow()
        )
    
    async def validate_generic_output(
        self,
        ai_output: Dict[str, Any]
    ) -> ValidationResult:
        """
        Generic validation for AI outputs
        """
        
        self.logger.info("Performing generic output validation")
        
        errors = []
        warnings = []
        
        # Basic structure validation
        if not isinstance(ai_output, dict):
            errors.append({
                "category": "structure",
                "severity": ValidationSeverity.CRITICAL,
                "message": "AI output must be a dictionary",
                "code": "INVALID_OUTPUT_STRUCTURE"
            })
        
        # Check for confidence score
        confidence = ai_output.get("confidence", 0.5)  # Default to medium confidence
        if confidence < 0.3:
            errors.append({
                "category": "confidence",
                "severity": ValidationSeverity.HIGH,
                "message": f"Very low confidence score: {confidence}",
                "code": "VERY_LOW_CONFIDENCE"
            })
        
        return ValidationResult(
            status=ValidationStatus.VALID if len(errors) == 0 else ValidationStatus.REQUIRES_REVIEW,
            is_valid=len(errors) == 0,
            confidence=confidence,
            compliance_score=1.0 if len(errors) == 0 else 0.5,
            errors=errors,
            warnings=warnings,
            suggestions=[],
            requires_human_review=confidence < 0.8,
            validation_timestamp=datetime.utcnow()
        )
    
    def _validate_structure(self, layout_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate basic structure of layout data"""
        
        errors = []
        
        # Check for required fields
        required_fields = ["rooms", "walls"]
        for field in required_fields:
            if field not in layout_data:
                errors.append({
                    "category": "structure",
                    "severity": ValidationSeverity.HIGH,
                    "message": f"Missing required field: {field}",
                    "code": f"MISSING_{field.upper()}"
                })
        
        # Validate rooms structure
        rooms = layout_data.get("rooms", [])
        if not isinstance(rooms, list):
            errors.append({
                "category": "structure",
                "severity": ValidationSeverity.HIGH,
                "message": "Rooms must be a list",
                "code": "INVALID_ROOMS_STRUCTURE"
            })
        elif len(rooms) == 0:
            errors.append({
                "category": "structure",
                "severity": ValidationSeverity.MEDIUM,
                "message": "No rooms defined in layout",
                "code": "NO_ROOMS_DEFINED"
            })
        
        return errors
    
    def _validate_building_codes(self, layout_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate building code compliance"""
        
        errors = []
        warnings = []
        
        rules = self.validation_rules[ValidationCategory.BUILDING_CODE]
        rooms = layout_data.get("rooms", [])
        
        for room in rooms:
            room_name = room.get("name", "Unknown")
            area_m2 = room.get("area_m2", 0)
            
            # Check minimum room area for habitable spaces
            if room.get("type") in ["bedroom", "living_room", "office"] and area_m2 < rules["min_room_area_m2"]:
                errors.append({
                    "category": ValidationCategory.BUILDING_CODE,
                    "severity": ValidationSeverity.HIGH,
                    "message": f"Room '{room_name}' area ({area_m2}m²) below minimum ({rules['min_room_area_m2']}m²)",
                    "code": "ROOM_AREA_TOO_SMALL",
                    "element": room_name
                })
            
            # Check ceiling height
            dimensions = room.get("dimensions", {})
            height_m = dimensions.get("height_m", 2.4)
            if height_m * 1000 < rules["min_ceiling_height_mm"]:
                warnings.append({
                    "category": ValidationCategory.BUILDING_CODE,
                    "severity": ValidationSeverity.MEDIUM,
                    "message": f"Room '{room_name}' ceiling height ({height_m}m) below recommended minimum",
                    "code": "LOW_CEILING_HEIGHT",
                    "element": room_name
                })
        
        return errors, warnings
    
    def _validate_accessibility(self, layout_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate accessibility compliance"""
        
        errors = []
        warnings = []
        
        rules = self.validation_rules[ValidationCategory.ACCESSIBILITY]
        doors = layout_data.get("doors", [])
        
        for i, door in enumerate(doors):
            door_width = door.get("width_mm", 0)
            
            if door_width < rules["min_door_width_mm"]:
                errors.append({
                    "category": ValidationCategory.ACCESSIBILITY,
                    "severity": ValidationSeverity.HIGH,
                    "message": f"Door {i+1} width ({door_width}mm) below accessible minimum ({rules['min_door_width_mm']}mm)",
                    "code": "DOOR_WIDTH_INACCESSIBLE",
                    "element": f"Door {i+1}"
                })
        
        return errors, warnings
    
    def _validate_safety(self, layout_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate safety requirements"""
        
        errors = []
        warnings = []
        
        # Check for adequate exit routes
        doors = layout_data.get("doors", [])
        exit_doors = [d for d in doors if d.get("door_type") == "exit" or d.get("is_exit", False)]
        
        if len(exit_doors) < 2:
            warnings.append({
                "category": ValidationCategory.SAFETY,
                "severity": ValidationSeverity.HIGH,
                "message": "Consider adding secondary exit for improved safety",
                "code": "INSUFFICIENT_EXITS"
            })
        
        return errors, warnings
    
    def _validate_spatial_relationships(self, layout_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate spatial relationships and adjacencies"""
        
        warnings = []
        
        rooms = layout_data.get("rooms", [])
        
        # Check for logical room adjacencies
        for room in rooms:
            room_type = room.get("type", "")
            adjacencies = room.get("adjacencies", [])
            
            if room_type == "bathroom" and "bedroom" not in adjacencies:
                warnings.append({
                    "category": "spatial",
                    "severity": ValidationSeverity.LOW,
                    "message": f"Bathroom '{room.get('name')}' not adjacent to bedroom - consider proximity",
                    "code": "SUBOPTIMAL_ADJACENCY",
                    "element": room.get("name")
                })
        
        return warnings
    
    def _generate_suggestions(
        self,
        layout_data: Dict[str, Any],
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate improvement suggestions"""
        
        suggestions = []
        
        # Suggest improvements based on errors and warnings
        if any(e["code"] == "ROOM_AREA_TOO_SMALL" for e in errors):
            suggestions.append({
                "category": "optimization",
                "suggestion": "Consider increasing room dimensions or combining adjacent spaces",
                "priority": "high",
                "implementation": "Modify room boundaries in layout"
            })
        
        if any(w["code"] == "INSUFFICIENT_EXITS" for w in warnings):
            suggestions.append({
                "category": "safety",
                "suggestion": "Add secondary exit or emergency window for improved safety",
                "priority": "medium",
                "implementation": "Add exit door or modify window to egress window"
            })
        
        return suggestions
    
    def _calculate_confidence(
        self,
        ai_output: Dict[str, Any],
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence score"""
        
        # Start with AI-reported confidence
        base_confidence = ai_output.get("confidence", 0.8)
        
        # Reduce confidence based on validation issues
        critical_errors = len([e for e in errors if e.get("severity") == ValidationSeverity.CRITICAL])
        high_errors = len([e for e in errors if e.get("severity") == ValidationSeverity.HIGH])
        medium_warnings = len([w for w in warnings if w.get("severity") == ValidationSeverity.MEDIUM])
        
        confidence_penalty = (critical_errors * 0.3) + (high_errors * 0.15) + (medium_warnings * 0.05)
        
        return max(0.0, min(1.0, base_confidence - confidence_penalty))
    
    def _calculate_compliance_score(
        self,
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]]
    ) -> float:
        """Calculate building code compliance score"""
        
        if len(errors) == 0 and len(warnings) == 0:
            return 1.0
        
        total_issues = len(errors) + len(warnings)
        critical_weight = len([e for e in errors if e.get("severity") == ValidationSeverity.CRITICAL]) * 1.0
        high_weight = len([e for e in errors if e.get("severity") == ValidationSeverity.HIGH]) * 0.7
        medium_weight = len([w for w in warnings if w.get("severity") == ValidationSeverity.MEDIUM]) * 0.3
        low_weight = len([w for w in warnings if w.get("severity") == ValidationSeverity.LOW]) * 0.1
        
        total_weight = critical_weight + high_weight + medium_weight + low_weight
        
        # Score decreases with weighted issue count
        return max(0.0, 1.0 - (total_weight / max(1, total_issues * 1.5)))
    
    def _determine_validation_status(
        self,
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        confidence: float
    ) -> ValidationStatus:
        """Determine overall validation status"""
        
        critical_errors = len([e for e in errors if e.get("severity") == ValidationSeverity.CRITICAL])
        high_errors = len([e for e in errors if e.get("severity") == ValidationSeverity.HIGH])
        
        if critical_errors > 0:
            return ValidationStatus.INVALID
        elif high_errors > 0 or confidence < self.confidence_thresholds["requires_review"]:
            return ValidationStatus.REQUIRES_REVIEW
        elif len(warnings) > 3 or confidence < self.confidence_thresholds["auto_approve"]:
            return ValidationStatus.REQUIRES_REVIEW
        else:
            return ValidationStatus.VALID
    
    def _requires_human_review(
        self,
        confidence: float,
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]]
    ) -> bool:
        """Determine if human review is required"""
        
        # Always require review for critical errors
        if any(e.get("severity") == ValidationSeverity.CRITICAL for e in errors):
            return True
        
        # Require review for low confidence
        if confidence < self.confidence_thresholds["requires_review"]:
            return True
        
        # Require review for multiple high-severity issues
        high_severity_count = len([e for e in errors if e.get("severity") == ValidationSeverity.HIGH])
        if high_severity_count >= 2:
            return True
        
        # Require expert review for very low confidence
        if confidence < self.confidence_thresholds["requires_expert"]:
            return True
        
        return False