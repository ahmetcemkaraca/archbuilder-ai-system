"""
AI Output Validation Service for ArchBuilder.AI
Validates AI-generated architectural content for safety and compliance
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger(__name__)


class ValidationResult(BaseModel):
    """Result of AI output validation"""
    is_valid: bool
    confidence_score: float
    validation_errors: List[str]
    warnings: List[str]
    safe_to_execute: bool
    requires_human_review: bool
    metadata: Dict[str, Any]


class AIOutputValidator:
    """Validates AI-generated outputs for architectural design"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        
        # Minimum safety thresholds
        self.min_confidence_threshold = 0.7
        self.min_room_area_m2 = 3.0  # Minimum usable room area
        self.max_room_area_m2 = 500.0  # Maximum reasonable room area
        self.min_ceiling_height_mm = 2100  # Minimum ceiling height
        self.max_ceiling_height_mm = 6000  # Maximum reasonable ceiling height
        
        # Building code constraints
        self.building_constraints = {
            "min_door_width_mm": 700,
            "max_door_width_mm": 1200,
            "min_window_width_mm": 600,
            "max_window_width_mm": 3000,
            "min_wall_thickness_mm": 100,
            "max_wall_thickness_mm": 400
        }
        
        self.logger.info("AI Output Validator initialized with safety constraints")
    
    async def validate_layout_output(self, 
                                   ai_output: Dict[str, Any],
                                   correlation_id: str) -> ValidationResult:
        """Validate AI-generated layout output"""
        
        self.logger.info(
            "Starting layout validation",
            correlation_id=correlation_id
        )
        
        errors = []
        warnings = []
        safe_to_execute = True
        requires_human_review = False
        
        try:
            # Extract confidence score
            confidence = ai_output.get("confidence", 0.0)
            
            # Validate confidence threshold
            if confidence < self.min_confidence_threshold:
                errors.append(f"AI confidence ({confidence}) below minimum threshold ({self.min_confidence_threshold})")
                requires_human_review = True
            
            # Validate required structure
            required_fields = ["walls", "doors", "windows", "rooms"]
            for field in required_fields:
                if field not in ai_output:
                    errors.append(f"Missing required field: {field}")
                    safe_to_execute = False
            
            if safe_to_execute:
                # Validate walls
                wall_errors = self._validate_walls(ai_output.get("walls", []))
                errors.extend(wall_errors)
                
                # Validate doors
                door_errors = self._validate_doors(ai_output.get("doors", []), ai_output.get("walls", []))
                errors.extend(door_errors)
                
                # Validate windows
                window_errors = self._validate_windows(ai_output.get("windows", []), ai_output.get("walls", []))
                errors.extend(window_errors)
                
                # Validate rooms
                room_errors, room_warnings = self._validate_rooms(ai_output.get("rooms", []))
                errors.extend(room_errors)
                warnings.extend(room_warnings)
                
                # Check for geometric consistency
                geometry_errors = self._validate_geometry_consistency(ai_output)
                errors.extend(geometry_errors)
            
            # Determine final safety status
            if errors:
                safe_to_execute = False
            
            if confidence < 0.85 or warnings:
                requires_human_review = True
            
            is_valid = len(errors) == 0
            
            result = ValidationResult(
                is_valid=is_valid,
                confidence_score=confidence,
                validation_errors=errors,
                warnings=warnings,
                safe_to_execute=safe_to_execute,
                requires_human_review=requires_human_review,
                metadata={
                    "validation_timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": correlation_id,
                    "ai_provider": ai_output.get("provider", "unknown"),
                    "model_used": ai_output.get("model_used", "unknown")
                }
            )
            
            self.logger.info(
                "Layout validation completed",
                correlation_id=correlation_id,
                is_valid=is_valid,
                errors_count=len(errors),
                warnings_count=len(warnings),
                safe_to_execute=safe_to_execute
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Layout validation failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                validation_errors=[f"Validation process failed: {str(e)}"],
                warnings=[],
                safe_to_execute=False,
                requires_human_review=True,
                metadata={"error": str(e)}
            )
    
    def _validate_walls(self, walls: List[Dict[str, Any]]) -> List[str]:
        """Validate wall definitions"""
        errors = []
        
        if not walls:
            errors.append("No walls defined in layout")
            return errors
        
        for i, wall in enumerate(walls):
            # Check required fields
            if not all(field in wall for field in ["start_point", "end_point", "height_mm"]):
                errors.append(f"Wall {i}: Missing required fields")
                continue
            
            try:
                # Validate coordinates
                start = wall["start_point"]
                end = wall["end_point"]
                
                if not all(coord in start for coord in ["x", "y", "z"]):
                    errors.append(f"Wall {i}: Invalid start_point coordinates")
                
                if not all(coord in end for coord in ["x", "y", "z"]):
                    errors.append(f"Wall {i}: Invalid end_point coordinates")
                
                # Check wall length
                import math
                length = math.sqrt((end["x"] - start["x"])**2 + (end["y"] - start["y"])**2)
                if length < 100:  # Minimum 100mm wall length
                    errors.append(f"Wall {i}: Wall too short ({length:.0f}mm)")
                
                # Check height
                height = wall["height_mm"]
                if height < self.min_ceiling_height_mm or height > self.max_ceiling_height_mm:
                    errors.append(f"Wall {i}: Invalid height ({height}mm)")
                
            except (KeyError, TypeError, ValueError) as e:
                errors.append(f"Wall {i}: Invalid data format - {str(e)}")
        
        return errors
    
    def _validate_doors(self, doors: List[Dict[str, Any]], walls: List[Dict[str, Any]]) -> List[str]:
        """Validate door definitions"""
        errors = []
        
        for i, door in enumerate(doors):
            try:
                # Check required fields
                if not all(field in door for field in ["wall_index", "position_ratio", "width_mm"]):
                    errors.append(f"Door {i}: Missing required fields")
                    continue
                
                # Validate wall reference
                wall_index = door["wall_index"]
                if wall_index >= len(walls) or wall_index < 0:
                    errors.append(f"Door {i}: Invalid wall_index ({wall_index})")
                    continue
                
                # Validate dimensions
                width = door["width_mm"]
                if width < self.building_constraints["min_door_width_mm"] or width > self.building_constraints["max_door_width_mm"]:
                    errors.append(f"Door {i}: Invalid width ({width}mm)")
                
                # Validate position
                position_ratio = door["position_ratio"]
                if position_ratio < 0.1 or position_ratio > 0.9:
                    errors.append(f"Door {i}: Position ratio out of safe range ({position_ratio})")
                
            except (KeyError, TypeError, ValueError) as e:
                errors.append(f"Door {i}: Invalid data format - {str(e)}")
        
        return errors
    
    def _validate_windows(self, windows: List[Dict[str, Any]], walls: List[Dict[str, Any]]) -> List[str]:
        """Validate window definitions"""
        errors = []
        
        for i, window in enumerate(windows):
            try:
                # Check required fields
                if not all(field in window for field in ["wall_index", "position_ratio", "width_mm"]):
                    errors.append(f"Window {i}: Missing required fields")
                    continue
                
                # Validate wall reference
                wall_index = window["wall_index"]
                if wall_index >= len(walls) or wall_index < 0:
                    errors.append(f"Window {i}: Invalid wall_index ({wall_index})")
                    continue
                
                # Validate dimensions
                width = window["width_mm"]
                if width < self.building_constraints["min_window_width_mm"] or width > self.building_constraints["max_window_width_mm"]:
                    errors.append(f"Window {i}: Invalid width ({width}mm)")
                
                # Validate position
                position_ratio = window["position_ratio"]
                if position_ratio < 0.1 or position_ratio > 0.9:
                    errors.append(f"Window {i}: Position ratio out of safe range ({position_ratio})")
                
            except (KeyError, TypeError, ValueError) as e:
                errors.append(f"Window {i}: Invalid data format - {str(e)}")
        
        return errors
    
    def _validate_rooms(self, rooms: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        """Validate room definitions"""
        errors = []
        warnings = []
        
        if not rooms:
            errors.append("No rooms defined in layout")
            return errors, warnings
        
        for i, room in enumerate(rooms):
            try:
                # Check required fields
                if not all(field in room for field in ["name", "area_m2"]):
                    errors.append(f"Room {i}: Missing required fields")
                    continue
                
                # Validate area
                area = room["area_m2"]
                if area < self.min_room_area_m2:
                    errors.append(f"Room {i} ({room['name']}): Area too small ({area}m²)")
                elif area > self.max_room_area_m2:
                    warnings.append(f"Room {i} ({room['name']}): Large area ({area}m²) - verify calculation")
                
                # Validate room name
                name = room["name"]
                if not name or not isinstance(name, str):
                    errors.append(f"Room {i}: Invalid or missing name")
                
            except (KeyError, TypeError, ValueError) as e:
                errors.append(f"Room {i}: Invalid data format - {str(e)}")
        
        return errors, warnings
    
    def _validate_geometry_consistency(self, layout_data: Dict[str, Any]) -> List[str]:
        """Validate geometric consistency of the layout"""
        errors = []
        
        try:
            walls = layout_data.get("walls", [])
            doors = layout_data.get("doors", [])
            windows = layout_data.get("windows", [])
            
            # Check for overlapping openings on same wall
            wall_openings = {}
            
            for door in doors:
                wall_idx = door.get("wall_index")
                if wall_idx is not None:
                    if wall_idx not in wall_openings:
                        wall_openings[wall_idx] = []
                    wall_openings[wall_idx].append({
                        "type": "door",
                        "position": door.get("position_ratio", 0),
                        "width_mm": door.get("width_mm", 0)
                    })
            
            for window in windows:
                wall_idx = window.get("wall_index")
                if wall_idx is not None:
                    if wall_idx not in wall_openings:
                        wall_openings[wall_idx] = []
                    wall_openings[wall_idx].append({
                        "type": "window",
                        "position": window.get("position_ratio", 0),
                        "width_mm": window.get("width_mm", 0)
                    })
            
            # Check for conflicts
            for wall_idx, openings in wall_openings.items():
                if len(openings) > 1:
                    # Sort by position
                    openings.sort(key=lambda x: x["position"])
                    
                    for j in range(len(openings) - 1):
                        current = openings[j]
                        next_opening = openings[j + 1]
                        
                        # Simple overlap check (should be more sophisticated)
                        pos_diff = abs(next_opening["position"] - current["position"])
                        if pos_diff < 0.2:  # Less than 20% of wall length apart
                            errors.append(f"Wall {wall_idx}: Potential opening overlap between {current['type']} and {next_opening['type']}")
            
        except Exception as e:
            errors.append(f"Geometry validation failed: {str(e)}")
        
        return errors
    
    async def validate_building_code_output(self,
                                          ai_output: Dict[str, Any],
                                          correlation_id: str) -> ValidationResult:
        """Validate AI-generated building code analysis"""
        
        self.logger.info(
            "Starting building code validation",
            correlation_id=correlation_id
        )
        
        errors = []
        warnings = []
        
        try:
            # Check required structure for building code analysis
            required_fields = ["region", "document_type", "extracted_rules"]
            for field in required_fields:
                if field not in ai_output:
                    errors.append(f"Missing required field: {field}")
            
            # Validate extracted rules format
            rules = ai_output.get("extracted_rules", [])
            for i, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    errors.append(f"Rule {i}: Invalid format")
                    continue
                
                required_rule_fields = ["category", "rule", "numeric_value"]
                for field in required_rule_fields:
                    if field not in rule:
                        warnings.append(f"Rule {i}: Missing field '{field}'")
            
            confidence = ai_output.get("confidence", 0.0)
            
            result = ValidationResult(
                is_valid=len(errors) == 0,
                confidence_score=confidence,
                validation_errors=errors,
                warnings=warnings,
                safe_to_execute=len(errors) == 0,
                requires_human_review=confidence < 0.8 or len(warnings) > 0,
                metadata={
                    "validation_timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": correlation_id,
                    "validation_type": "building_code"
                }
            )
            
            self.logger.info(
                "Building code validation completed",
                correlation_id=correlation_id,
                is_valid=result.is_valid,
                requires_review=result.requires_human_review
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Building code validation failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            
            return ValidationResult(
                is_valid=False,
                confidence_score=0.0,
                validation_errors=[f"Validation failed: {str(e)}"],
                warnings=[],
                safe_to_execute=False,
                requires_human_review=True,
                metadata={"error": str(e)}
            )