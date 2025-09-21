"""
Architectural Fallback Service for ArchBuilder.AI
Implements rule-based fallback systems when AI fails or produces invalid outputs
"""

import math
from typing import Dict, List, Any, Optional
from enum import Enum

from ....core.logging import get_logger

logger = get_logger(__name__)


class RoomType(str, Enum):
    """Standard room types for fallback generation"""
    BEDROOM = "bedroom"
    LIVING_ROOM = "living_room"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    DINING_ROOM = "dining_room"
    OFFICE = "office"
    CORRIDOR = "corridor"
    STORAGE = "storage"


class ArchitecturalFallbackService:
    """
    Rule-based fallback service for architectural tasks
    Provides reliable alternatives when AI processing fails
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Standard room dimensions (width x length in meters)
        self.standard_room_dimensions = {
            RoomType.BEDROOM: {"min": (3.0, 3.0), "standard": (3.5, 4.0), "large": (4.0, 5.0)},
            RoomType.LIVING_ROOM: {"min": (3.5, 4.0), "standard": (4.5, 5.5), "large": (6.0, 7.0)},
            RoomType.KITCHEN: {"min": (2.5, 3.0), "standard": (3.0, 4.0), "large": (3.5, 5.0)},
            RoomType.BATHROOM: {"min": (1.8, 2.0), "standard": (2.2, 2.5), "large": (2.5, 3.0)},
            RoomType.DINING_ROOM: {"min": (3.0, 3.5), "standard": (3.5, 4.5), "large": (4.0, 5.5)},
            RoomType.OFFICE: {"min": (2.5, 3.0), "standard": (3.0, 3.5), "large": (3.5, 4.5)},
            RoomType.CORRIDOR: {"min": (1.2, 3.0), "standard": (1.5, 5.0), "large": (2.0, 8.0)},
            RoomType.STORAGE: {"min": (1.5, 2.0), "standard": (2.0, 2.5), "large": (2.5, 3.0)}
        }
        
        # Standard wall types
        self.standard_wall_types = {
            "exterior": {"thickness_mm": 300, "material": "concrete", "fire_rating_hours": 2},
            "interior_load_bearing": {"thickness_mm": 200, "material": "concrete", "fire_rating_hours": 1},
            "interior_partition": {"thickness_mm": 100, "material": "drywall", "fire_rating_hours": 0.5},
            "bathroom": {"thickness_mm": 150, "material": "masonry", "fire_rating_hours": 1}
        }
        
        # Standard door and window sizes
        self.standard_openings = {
            "doors": {
                "single": {"width_mm": 900, "height_mm": 2100},
                "double": {"width_mm": 1800, "height_mm": 2100},
                "accessible": {"width_mm": 950, "height_mm": 2100}
            },
            "windows": {
                "standard": {"width_mm": 1200, "height_mm": 1200, "sill_height_mm": 900},
                "large": {"width_mm": 1800, "height_mm": 1500, "sill_height_mm": 900},
                "floor_to_ceiling": {"width_mm": 2400, "height_mm": 2400, "sill_height_mm": 0}
            }
        }
    
    async def process_command_fallback(self, request: Any) -> Dict[str, Any]:
        """
        Process AI command using rule-based fallback
        
        Args:
            request: AI command request that failed
            
        Returns:
            Dict containing fallback result
        """
        
        command_type = getattr(request, 'command_type', 'general')
        
        self.logger.info(
            "Processing command with fallback",
            command_type=command_type
        )
        
        if command_type == "layout_generation":
            return await self.generate_layout_fallback(request)
        elif command_type == "room_generation":
            return await self.generate_room_fallback(request)
        elif command_type == "building_code_compliance":
            return await self.check_compliance_fallback(request)
        else:
            return self._generate_generic_fallback(request)
    
    async def generate_layout_fallback(self, request: Any) -> Dict[str, Any]:
        """
        Generate layout using rule-based algorithms
        
        Args:
            request: Layout generation request
            
        Returns:
            Dict containing fallback layout
        """
        
        # Extract requirements
        total_area = getattr(request, 'total_area', 100)  # Default 100m²
        rooms = getattr(request, 'rooms', [])
        
        self.logger.info(
            "Generating fallback layout",
            total_area=total_area,
            room_count=len(rooms)
        )
        
        if len(rooms) == 0:
            # Create default room layout
            rooms = [
                {"type": "living_room", "area_m2": total_area * 0.35},
                {"type": "bedroom", "area_m2": total_area * 0.25},
                {"type": "kitchen", "area_m2": total_area * 0.15},
                {"type": "bathroom", "area_m2": total_area * 0.10},
                {"type": "corridor", "area_m2": total_area * 0.15}
            ]
        
        # Generate rectangular layout
        layout = self._generate_rectangular_layout(rooms, total_area)
        
        return {
            "layout": layout,
            "confidence": 0.7,  # Lower confidence for rule-based
            "generated_by": "fallback",
            "requires_human_review": True,
            "fallback_reason": "AI processing failed, using rule-based layout generation",
            "optimization_score": 0.6,  # Basic optimization
            "compliance_status": "requires_review"
        }
    
    async def generate_room_fallback(self, request: Any) -> Dict[str, Any]:
        """
        Generate room design using standard patterns
        """
        
        room_type = getattr(request, 'room_type', 'bedroom')
        area_m2 = getattr(request, 'area_m2', 12)
        
        self.logger.info(
            "Generating fallback room design",
            room_type=room_type,
            area_m2=area_m2
        )
        
        # Get standard dimensions for room type
        room_enum = self._get_room_enum(room_type)
        dimensions = self._calculate_room_dimensions(room_enum, area_m2)
        
        # Generate standard furniture layout
        furniture = self._generate_standard_furniture(room_enum, dimensions)
        
        return {
            "room_design": {
                "type": room_type,
                "dimensions": dimensions,
                "furniture": furniture,
                "lighting": self._generate_standard_lighting(room_enum, dimensions),
                "materials": self._generate_standard_materials(room_enum)
            },
            "confidence": 0.6,
            "generated_by": "fallback",
            "requires_human_review": True
        }
    
    async def check_compliance_fallback(self, request: Any) -> Dict[str, Any]:
        """
        Perform basic compliance check using rule-based system
        """
        
        design_data = getattr(request, 'design_data', {})
        region = getattr(request, 'region', 'international')
        
        self.logger.info(
            "Performing fallback compliance check",
            region=region
        )
        
        # Basic rule-based compliance checks
        compliance_results = self._perform_basic_compliance_check(design_data, region)
        
        return {
            "compliance_analysis": compliance_results,
            "confidence": 0.5,  # Low confidence for basic checks
            "generated_by": "fallback",
            "requires_expert_review": True,
            "recommendation": "Professional review required for comprehensive compliance assessment"
        }
    
    def _generate_rectangular_layout(self, rooms: List[Dict[str, Any]], total_area: float) -> Dict[str, Any]:
        """Generate rectangular grid layout"""
        
        room_count = len(rooms)
        
        # Calculate building dimensions
        aspect_ratio = 1.4  # Typical building aspect ratio
        building_width = math.sqrt(total_area / aspect_ratio)
        building_length = total_area / building_width
        
        # Calculate grid dimensions
        grid_cols = math.ceil(math.sqrt(room_count))
        grid_rows = math.ceil(room_count / grid_cols)
        
        # Calculate cell dimensions
        cell_width = building_width / grid_cols
        cell_length = building_length / grid_rows
        
        layout_rooms = []
        walls = []
        doors = []
        windows = []
        
        # Generate rooms in grid
        for i, room in enumerate(rooms):
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate room position
            x = col * cell_width
            y = row * cell_length
            
            # Adjust room size based on specified area
            target_area = room.get("area_m2", cell_width * cell_length)
            room_width = min(cell_width, math.sqrt(target_area))
            room_length = target_area / room_width
            
            # Create room
            layout_room = {
                "id": f"room_{i+1}",
                "name": room.get("name", f"{room.get('type', 'room')}_{i+1}"),
                "type": room.get("type", "room"),
                "area_m2": room_width * room_length,
                "dimensions": {
                    "width_m": room_width,
                    "length_m": room_length,
                    "height_m": 2.7  # Standard ceiling height
                },
                "position": {
                    "x_mm": x * 1000,
                    "y_mm": y * 1000
                }
            }
            layout_rooms.append(layout_room)
            
            # Create walls for room
            room_walls = self._create_room_walls(
                x * 1000, y * 1000, 
                room_width * 1000, room_length * 1000,
                room.get("type", "room")
            )
            walls.extend(room_walls)
            
            # Add doors (except for perimeter rooms or specific room types)
            if col > 0 and room.get("type") != "bathroom":  # Door to left neighbor
                door = {
                    "id": f"door_{len(doors)+1}",
                    "wall_id": f"wall_{len(walls)-4}",  # Left wall
                    "position_on_wall_mm": room_length * 500,  # Center of wall
                    "width_mm": self.standard_openings["doors"]["single"]["width_mm"],
                    "height_mm": self.standard_openings["doors"]["single"]["height_mm"],
                    "door_type": "single",
                    "accessibility_compliant": True
                }
                doors.append(door)
            
            # Add windows for exterior walls
            if col == 0 or col == grid_cols - 1 or row == 0 or row == grid_rows - 1:
                window = {
                    "id": f"window_{len(windows)+1}",
                    "wall_id": f"wall_{len(walls)-1}",  # Exterior wall
                    "position_on_wall_mm": room_width * 500,  # Center of wall
                    "width_mm": self.standard_openings["windows"]["standard"]["width_mm"],
                    "height_mm": self.standard_openings["windows"]["standard"]["height_mm"],
                    "sill_height_mm": self.standard_openings["windows"]["standard"]["sill_height_mm"],
                    "window_type": "casement"
                }
                windows.append(window)
        
        return {
            "total_area_m2": total_area,
            "building_dimensions": {
                "width_m": building_width,
                "length_m": building_length,
                "height_m": 2.7
            },
            "rooms": layout_rooms,
            "walls": walls,
            "doors": doors,
            "windows": windows,
            "circulation": {
                "corridors": self._generate_corridor_system(layout_rooms),
                "accessibility_compliant": True
            }
        }
    
    def _create_room_walls(self, x: float, y: float, width: float, height: float, room_type: str) -> List[Dict[str, Any]]:
        """Create walls for a rectangular room"""
        
        # Select appropriate wall type
        if room_type == "bathroom":
            wall_spec = self.standard_wall_types["bathroom"]
        else:
            wall_spec = self.standard_wall_types["interior_partition"]
        
        return [
            # Bottom wall
            {
                "id": f"wall_b_{x}_{y}",
                "type": "interior",
                "start_point": {"x_mm": x, "y_mm": y, "z_mm": 0},
                "end_point": {"x_mm": x + width, "y_mm": y, "z_mm": 0},
                "thickness_mm": wall_spec["thickness_mm"],
                "height_mm": 2700,
                "material": wall_spec["material"],
                "fire_rating_hours": wall_spec["fire_rating_hours"]
            },
            # Right wall
            {
                "id": f"wall_r_{x}_{y}",
                "type": "interior",
                "start_point": {"x_mm": x + width, "y_mm": y, "z_mm": 0},
                "end_point": {"x_mm": x + width, "y_mm": y + height, "z_mm": 0},
                "thickness_mm": wall_spec["thickness_mm"],
                "height_mm": 2700,
                "material": wall_spec["material"],
                "fire_rating_hours": wall_spec["fire_rating_hours"]
            },
            # Top wall
            {
                "id": f"wall_t_{x}_{y}",
                "type": "interior",
                "start_point": {"x_mm": x + width, "y_mm": y + height, "z_mm": 0},
                "end_point": {"x_mm": x, "y_mm": y + height, "z_mm": 0},
                "thickness_mm": wall_spec["thickness_mm"],
                "height_mm": 2700,
                "material": wall_spec["material"],
                "fire_rating_hours": wall_spec["fire_rating_hours"]
            },
            # Left wall
            {
                "id": f"wall_l_{x}_{y}",
                "type": "interior",
                "start_point": {"x_mm": x, "y_mm": y + height, "z_mm": 0},
                "end_point": {"x_mm": x, "y_mm": y, "z_mm": 0},
                "thickness_mm": wall_spec["thickness_mm"],
                "height_mm": 2700,
                "material": wall_spec["material"],
                "fire_rating_hours": wall_spec["fire_rating_hours"]
            }
        ]
    
    def _generate_corridor_system(self, rooms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate basic corridor system"""
        
        corridors = []
        
        # Simple corridor connecting all rooms
        if len(rooms) > 1:
            corridor = {
                "id": "main_corridor",
                "width_mm": 1500,  # Accessible width
                "connects": [room["id"] for room in rooms],
                "accessibility_compliant": True,
                "emergency_route": True
            }
            corridors.append(corridor)
        
        return corridors
    
    def _get_room_enum(self, room_type: str) -> RoomType:
        """Convert string room type to enum"""
        
        try:
            return RoomType(room_type.lower())
        except ValueError:
            return RoomType.BEDROOM  # Default fallback
    
    def _calculate_room_dimensions(self, room_type: RoomType, area_m2: float) -> Dict[str, float]:
        """Calculate room dimensions based on type and area"""
        
        dimensions_config = self.standard_room_dimensions.get(room_type, self.standard_room_dimensions[RoomType.BEDROOM])
        
        # Choose appropriate size category
        if area_m2 < 10:
            width, length = dimensions_config["min"]
        elif area_m2 < 20:
            width, length = dimensions_config["standard"]
        else:
            width, length = dimensions_config["large"]
        
        # Adjust to match target area
        scale_factor = math.sqrt(area_m2 / (width * length))
        
        return {
            "width_m": width * scale_factor,
            "length_m": length * scale_factor,
            "height_m": 2.7
        }
    
    def _generate_standard_furniture(self, room_type: RoomType, dimensions: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate standard furniture layout for room type"""
        
        furniture = []
        
        if room_type == RoomType.BEDROOM:
            furniture = [
                {"type": "bed", "position": {"x_mm": 1000, "y_mm": 1000}, "size": "queen"},
                {"type": "nightstand", "position": {"x_mm": 2500, "y_mm": 1000}, "size": "standard"},
                {"type": "wardrobe", "position": {"x_mm": 500, "y_mm": 3000}, "size": "large"}
            ]
        elif room_type == RoomType.LIVING_ROOM:
            furniture = [
                {"type": "sofa", "position": {"x_mm": 2000, "y_mm": 2000}, "size": "3_seater"},
                {"type": "coffee_table", "position": {"x_mm": 2000, "y_mm": 3000}, "size": "standard"},
                {"type": "tv_stand", "position": {"x_mm": 500, "y_mm": 2000}, "size": "standard"}
            ]
        elif room_type == RoomType.KITCHEN:
            furniture = [
                {"type": "cabinets", "position": {"x_mm": 500, "y_mm": 500}, "size": "linear"},
                {"type": "refrigerator", "position": {"x_mm": 500, "y_mm": 1500}, "size": "standard"},
                {"type": "stove", "position": {"x_mm": 1500, "y_mm": 500}, "size": "standard"}
            ]
        elif room_type == RoomType.BATHROOM:
            furniture = [
                {"type": "toilet", "position": {"x_mm": 500, "y_mm": 1500}, "size": "standard"},
                {"type": "sink", "position": {"x_mm": 1000, "y_mm": 500}, "size": "standard"},
                {"type": "shower", "position": {"x_mm": 1500, "y_mm": 1500}, "size": "standard"}
            ]
        
        return furniture
    
    def _generate_standard_lighting(self, room_type: RoomType, dimensions: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate standard lighting layout"""
        
        lighting = [
            {
                "type": "ceiling_fixture",
                "position": {
                    "x_mm": dimensions["width_m"] * 500,  # Center
                    "y_mm": dimensions["length_m"] * 500  # Center
                },
                "fixture_type": "LED",
                "wattage": 15
            }
        ]
        
        return lighting
    
    def _generate_standard_materials(self, room_type: RoomType) -> List[Dict[str, Any]]:
        """Generate standard material specifications"""
        
        if room_type == RoomType.BATHROOM:
            return [
                {"surface": "floor", "material": "ceramic_tile", "color": "white"},
                {"surface": "walls", "material": "ceramic_tile", "color": "light_gray"},
                {"surface": "ceiling", "material": "moisture_resistant_paint", "color": "white"}
            ]
        else:
            return [
                {"surface": "floor", "material": "hardwood", "color": "natural"},
                {"surface": "walls", "material": "paint", "color": "white"},
                {"surface": "ceiling", "material": "paint", "color": "white"}
            ]
    
    def _perform_basic_compliance_check(self, design_data: Dict[str, Any], region: str) -> Dict[str, Any]:
        """Perform basic rule-based compliance check"""
        
        violations = []
        warnings = []
        
        # Basic area checks
        rooms = design_data.get("rooms", [])
        for room in rooms:
            area = room.get("area_m2", 0)
            room_type = room.get("type", "")
            
            if room_type in ["bedroom", "living_room"] and area < 7.0:
                violations.append({
                    "code": "MINIMUM_ROOM_AREA",
                    "violation": f"Room '{room.get('name', 'Unknown')}' area below minimum 7m²",
                    "severity": "high"
                })
        
        # Basic door width checks
        doors = design_data.get("doors", [])
        for door in doors:
            width = door.get("width_mm", 0)
            if width < 800:
                warnings.append({
                    "code": "DOOR_WIDTH",
                    "warning": f"Door width {width}mm may not meet accessibility requirements",
                    "recommendation": "Consider increasing to 900mm minimum"
                })
        
        return {
            "overall_score": 0.6,
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "region": region,
            "checked_codes": ["basic_area_requirements", "basic_accessibility"],
            "requires_professional_review": True
        }
    
    def _generate_generic_fallback(self, request: Any) -> Dict[str, Any]:
        """Generate generic fallback response"""
        
        return {
            "message": "AI processing failed. Please try again or contact support for assistance.",
            "confidence": 0.0,
            "generated_by": "fallback",
            "requires_human_review": True,
            "recommendations": [
                "Simplify your request",
                "Provide more specific requirements",
                "Contact technical support"
            ]
        }