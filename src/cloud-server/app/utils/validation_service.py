"""
ArchBuilder.AI - Advanced Validation Service
Comprehensive input validation, data sanitization, and security validation for all system inputs.
"""

import re
import json
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass
from enum import Enum
import structlog
from pydantic import BaseModel, validator
from datetime import datetime
import uuid

class ValidationSeverity(Enum):
    """Validation error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationCategory(Enum):
    """Categories of validation errors."""
    INPUT_FORMAT = "input_format"
    BUSINESS_LOGIC = "business_logic"
    SECURITY = "security"
    GEOMETRY = "geometry"
    BUILDING_CODE = "building_code"
    PERFORMANCE = "performance"

@dataclass
class ValidationError:
    """Validation error details."""
    code: str
    message: str
    field: Optional[str] = None
    category: ValidationCategory = ValidationCategory.INPUT_FORMAT
    severity: ValidationSeverity = ValidationSeverity.ERROR
    suggested_fix: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ValidationResult:
    """Validation result container."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    info: List[ValidationError]
    correlation_id: str
    validation_time: datetime
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    @property
    def critical_errors(self) -> List[ValidationError]:
        """Get critical errors only."""
        return [e for e in self.errors if e.severity == ValidationSeverity.CRITICAL]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "is_valid": self.is_valid,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "field": e.field,
                    "category": e.category.value,
                    "severity": e.severity.value,
                    "suggested_fix": e.suggested_fix,
                    "metadata": e.metadata
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "field": w.field,
                    "category": w.category.value,
                    "severity": w.severity.value,
                    "suggested_fix": w.suggested_fix,
                    "metadata": w.metadata
                }
                for w in self.warnings
            ],
            "info": [
                {
                    "code": i.code,
                    "message": i.message,
                    "field": i.field,
                    "category": i.category.value,
                    "severity": i.severity.value,
                    "suggested_fix": i.suggested_fix,
                    "metadata": i.metadata
                }
                for i in self.info
            ],
            "correlation_id": self.correlation_id,
            "validation_time": self.validation_time.isoformat()
        }

class BaseValidator:
    """Base class for all validators."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.logger = structlog.get_logger(__name__)
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.info: List[ValidationError] = []
    
    def add_error(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        category: ValidationCategory = ValidationCategory.INPUT_FORMAT,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        suggested_fix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add validation error."""
        error = ValidationError(
            code=code,
            message=message,
            field=field,
            category=category,
            severity=severity,
            suggested_fix=suggested_fix,
            metadata=metadata
        )
        
        if severity == ValidationSeverity.ERROR or severity == ValidationSeverity.CRITICAL:
            self.errors.append(error)
        elif severity == ValidationSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.info.append(error)
    
    def get_result(self) -> ValidationResult:
        """Get validation result."""
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info,
            correlation_id=self.correlation_id,
            validation_time=datetime.utcnow()
        )

class InputValidator(BaseValidator):
    """Input validation for user requests and API data."""
    
    def validate_user_prompt(self, prompt: str) -> ValidationResult:
        """
        Validate user prompt for AI processing.
        
        Args:
            prompt: User input prompt
            
        Returns:
            Validation result
        """
        # Length validation
        if not prompt or len(prompt.strip()) == 0:
            self.add_error(
                "PROMPT_001",
                "User prompt cannot be empty",
                "user_prompt",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR,
                "Please provide a description of what you want to create"
            )
        elif len(prompt) < 10:
            self.add_error(
                "PROMPT_002",
                "User prompt is too short (minimum 10 characters)",
                "user_prompt",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR,
                "Please provide more detail about your requirements"
            )
        elif len(prompt) > 5000:
            self.add_error(
                "PROMPT_003",
                "User prompt is too long (maximum 5000 characters)",
                "user_prompt",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR,
                "Please shorten your description"
            )
        
        # Content validation
        if prompt:
            # Check for potentially malicious content
            if self._contains_injection_attempt(prompt):
                self.add_error(
                    "PROMPT_004",
                    "Prompt contains potentially malicious content",
                    "user_prompt",
                    ValidationCategory.SECURITY,
                    ValidationSeverity.CRITICAL,
                    "Please remove any system commands or code from your description"
                )
            
            # Check for personal information
            if self._contains_personal_info(prompt):
                self.add_error(
                    "PROMPT_005",
                    "Prompt appears to contain personal information",
                    "user_prompt",
                    ValidationCategory.SECURITY,
                    ValidationSeverity.WARNING,
                    "Avoid including personal details like names, addresses, or phone numbers"
                )
            
            # Check language appropriateness
            if self._contains_inappropriate_language(prompt):
                self.add_error(
                    "PROMPT_006",
                    "Prompt contains inappropriate language",
                    "user_prompt",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.WARNING,
                    "Please use professional language in your descriptions"
                )
        
        return self.get_result()
    
    def validate_building_requirements(self, requirements: Dict[str, Any]) -> ValidationResult:
        """
        Validate building requirements data.
        
        Args:
            requirements: Building requirements dictionary
            
        Returns:
            Validation result
        """
        # Required fields
        required_fields = ["building_type", "total_area_m2", "rooms"]
        for field in required_fields:
            if field not in requirements:
                self.add_error(
                    f"REQ_001",
                    f"Required field '{field}' is missing",
                    field,
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.ERROR,
                    f"Please provide the {field.replace('_', ' ')}"
                )
        
        # Building type validation
        if "building_type" in requirements:
            valid_types = ["residential", "office", "retail", "industrial", "mixed_use"]
            if requirements["building_type"] not in valid_types:
                self.add_error(
                    "REQ_002",
                    f"Invalid building type: {requirements['building_type']}",
                    "building_type",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.ERROR,
                    f"Valid types are: {', '.join(valid_types)}"
                )
        
        # Area validation
        if "total_area_m2" in requirements:
            area = requirements["total_area_m2"]
            if not isinstance(area, (int, float)) or area <= 0:
                self.add_error(
                    "REQ_003",
                    "Total area must be a positive number",
                    "total_area_m2",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.ERROR,
                    "Please provide the total area in square meters"
                )
            elif area < 10:
                self.add_error(
                    "REQ_004",
                    "Total area seems too small (minimum 10 m²)",
                    "total_area_m2",
                    ValidationCategory.BUSINESS_LOGIC,
                    ValidationSeverity.WARNING,
                    "Please verify the area is correct"
                )
            elif area > 10000:
                self.add_error(
                    "REQ_005",
                    "Total area seems very large (over 10,000 m²)",
                    "total_area_m2",
                    ValidationCategory.BUSINESS_LOGIC,
                    ValidationSeverity.WARNING,
                    "Large buildings may require special considerations"
                )
        
        # Room requirements validation
        if "rooms" in requirements:
            rooms = requirements["rooms"]
            if not isinstance(rooms, list) or len(rooms) == 0:
                self.add_error(
                    "REQ_006",
                    "At least one room is required",
                    "rooms",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.ERROR,
                    "Please specify the rooms you need"
                )
            else:
                total_room_area = 0
                for i, room in enumerate(rooms):
                    if not isinstance(room, dict):
                        self.add_error(
                            "REQ_007",
                            f"Room {i+1} must be an object",
                            f"rooms[{i}]",
                            ValidationCategory.INPUT_FORMAT,
                            ValidationSeverity.ERROR
                        )
                        continue
                    
                    # Room name validation
                    if "name" not in room or not room["name"]:
                        self.add_error(
                            "REQ_008",
                            f"Room {i+1} must have a name",
                            f"rooms[{i}].name",
                            ValidationCategory.INPUT_FORMAT,
                            ValidationSeverity.ERROR
                        )
                    
                    # Room area validation
                    if "area_m2" in room:
                        room_area = room["area_m2"]
                        if not isinstance(room_area, (int, float)) or room_area <= 0:
                            self.add_error(
                                "REQ_009",
                                f"Room {i+1} area must be a positive number",
                                f"rooms[{i}].area_m2",
                                ValidationCategory.INPUT_FORMAT,
                                ValidationSeverity.ERROR
                            )
                        else:
                            total_room_area += room_area
                            
                            # Check minimum room sizes
                            min_sizes = {
                                "bedroom": 9.0,
                                "living room": 12.0,
                                "kitchen": 6.0,
                                "bathroom": 3.0,
                                "office": 8.0
                            }
                            
                            room_type = room.get("name", "").lower()
                            for room_name, min_size in min_sizes.items():
                                if room_name in room_type and room_area < min_size:
                                    self.add_error(
                                        "REQ_010",
                                        f"{room['name']} area ({room_area} m²) is below recommended minimum ({min_size} m²)",
                                        f"rooms[{i}].area_m2",
                                        ValidationCategory.BUILDING_CODE,
                                        ValidationSeverity.WARNING,
                                        f"Consider increasing to at least {min_size} m²"
                                    )
                
                # Check total room area vs building area
                if "total_area_m2" in requirements and total_room_area > 0:
                    building_area = requirements["total_area_m2"]
                    if total_room_area > building_area * 0.95:  # Allow 5% for walls/circulation
                        self.add_error(
                            "REQ_011",
                            f"Total room area ({total_room_area} m²) exceeds building area ({building_area} m²)",
                            "rooms",
                            ValidationCategory.BUSINESS_LOGIC,
                            ValidationSeverity.ERROR,
                            "Reduce room areas or increase building area"
                        )
                    elif total_room_area < building_area * 0.6:  # Rooms should be at least 60% of building
                        self.add_error(
                            "REQ_012",
                            f"Total room area ({total_room_area} m²) seems low for building area ({building_area} m²)",
                            "rooms",
                            ValidationCategory.BUSINESS_LOGIC,
                            ValidationSeverity.WARNING,
                            "Consider adding more rooms or increasing room sizes"
                        )
        
        return self.get_result()
    
    def validate_file_upload(
        self,
        filename: str,
        file_size: int,
        content_type: str,
        max_size_mb: int = 100
    ) -> ValidationResult:
        """
        Validate file upload.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            content_type: MIME type of the file
            max_size_mb: Maximum allowed file size in MB
            
        Returns:
            Validation result
        """
        # Filename validation
        if not filename:
            self.add_error(
                "FILE_001",
                "Filename cannot be empty",
                "filename",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR
            )
        elif len(filename) > 255:
            self.add_error(
                "FILE_002",
                "Filename is too long (maximum 255 characters)",
                "filename",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR
            )
        elif not self._is_safe_filename(filename):
            self.add_error(
                "FILE_003",
                "Filename contains unsafe characters",
                "filename",
                ValidationCategory.SECURITY,
                ValidationSeverity.ERROR,
                "Use only letters, numbers, spaces, dots, hyphens, and underscores"
            )
        
        # File extension validation
        if filename:
            allowed_extensions = ['.dwg', '.dxf', '.ifc', '.pdf', '.jpg', '.jpeg', '.png']
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if f'.{file_ext}' not in allowed_extensions:
                self.add_error(
                    "FILE_004",
                    f"File type '.{file_ext}' is not allowed",
                    "filename",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.ERROR,
                    f"Allowed types: {', '.join(allowed_extensions)}"
                )
        
        # File size validation
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            self.add_error(
                "FILE_005",
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds maximum ({max_size_mb} MB)",
                "file_size",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR,
                f"Please upload a file smaller than {max_size_mb} MB"
            )
        elif file_size == 0:
            self.add_error(
                "FILE_006",
                "File appears to be empty",
                "file_size",
                ValidationCategory.INPUT_FORMAT,
                ValidationSeverity.ERROR,
                "Please upload a valid file"
            )
        
        # Content type validation
        allowed_content_types = [
            'application/octet-stream',  # DWG/DXF files
            'application/pdf',
            'image/jpeg',
            'image/png',
            'text/plain'
        ]
        
        if content_type not in allowed_content_types:
            self.add_error(
                "FILE_007",
                f"Content type '{content_type}' is not allowed",
                "content_type",
                ValidationCategory.SECURITY,
                ValidationSeverity.WARNING,
                "File type detection will be performed on content"
            )
        
        return self.get_result()
    
    def _contains_injection_attempt(self, text: str) -> bool:
        """Check for potential injection attempts."""
        injection_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'subprocess\.',
            r'os\.',
            r'__import__',
            r'open\s*\(',
            r'file\s*\(',
            r'</?\w+[^>]*>',  # HTML tags
            r'SELECT\s+.*FROM',  # SQL injection
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*SET'
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in injection_patterns)
    
    def _contains_personal_info(self, text: str) -> bool:
        """Check for potential personal information."""
        personal_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{3}[.-]\d{3}[.-]\d{4}\b',  # Phone number
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
            r'\b\d{1,5}\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln)\b'  # Address
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in personal_patterns)
    
    def _contains_inappropriate_language(self, text: str) -> bool:
        """Check for inappropriate language (basic check)."""
        # This would typically use a more sophisticated filter
        inappropriate_words = [
            'fuck', 'shit', 'damn', 'ass', 'bitch', 'bastard'
        ]
        
        text_lower = text.lower()
        return any(word in text_lower for word in inappropriate_words)
    
    def _is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe."""
        # Allow letters, numbers, spaces, dots, hyphens, underscores, parentheses
        safe_pattern = r'^[a-zA-Z0-9\s._()-]+$'
        
        # Reject dangerous filenames
        dangerous_names = [
            'con', 'prn', 'aux', 'nul',
            'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
            'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
        ]
        
        base_name = filename.split('.')[0].lower()
        
        return (
            bool(re.match(safe_pattern, filename)) and
            base_name not in dangerous_names and
            not filename.startswith('.') and
            not filename.endswith('.') and
            '..' not in filename
        )

class GeometryValidator(BaseValidator):
    """Geometry validation for architectural elements."""
    
    def validate_wall_definition(self, wall: Dict[str, Any]) -> ValidationResult:
        """
        Validate wall definition.
        
        Args:
            wall: Wall definition dictionary
            
        Returns:
            Validation result
        """
        # Required fields
        required_fields = ["start_point", "end_point", "height_mm"]
        for field in required_fields:
            if field not in wall:
                self.add_error(
                    "WALL_001",
                    f"Required field '{field}' is missing",
                    field,
                    ValidationCategory.GEOMETRY,
                    ValidationSeverity.ERROR
                )
        
        # Point validation
        for point_field in ["start_point", "end_point"]:
            if point_field in wall:
                point = wall[point_field]
                if not isinstance(point, dict) or "x" not in point or "y" not in point:
                    self.add_error(
                        "WALL_002",
                        f"{point_field} must have x and y coordinates",
                        point_field,
                        ValidationCategory.GEOMETRY,
                        ValidationSeverity.ERROR
                    )
                else:
                    # Validate coordinate values
                    for coord in ["x", "y"]:
                        if not isinstance(point[coord], (int, float)):
                            self.add_error(
                                "WALL_003",
                                f"{point_field}.{coord} must be a number",
                                f"{point_field}.{coord}",
                                ValidationCategory.GEOMETRY,
                                ValidationSeverity.ERROR
                            )
        
        # Wall length validation
        if all(field in wall for field in ["start_point", "end_point"]):
            start = wall["start_point"]
            end = wall["end_point"]
            
            if all(coord in start for coord in ["x", "y"]) and all(coord in end for coord in ["x", "y"]):
                length = ((end["x"] - start["x"])**2 + (end["y"] - start["y"])**2)**0.5
                
                if length < 100:  # 100mm minimum
                    self.add_error(
                        "WALL_004",
                        f"Wall is too short ({length:.1f}mm, minimum 100mm)",
                        "length",
                        ValidationCategory.GEOMETRY,
                        ValidationSeverity.ERROR,
                        "Increase wall length or remove this wall"
                    )
                elif length > 50000:  # 50m maximum
                    self.add_error(
                        "WALL_005",
                        f"Wall is very long ({length:.1f}mm, over 50m)",
                        "length",
                        ValidationCategory.GEOMETRY,
                        ValidationSeverity.WARNING,
                        "Consider breaking into smaller segments"
                    )
        
        # Height validation
        if "height_mm" in wall:
            height = wall["height_mm"]
            if not isinstance(height, (int, float)) or height <= 0:
                self.add_error(
                    "WALL_006",
                    "Wall height must be a positive number",
                    "height_mm",
                    ValidationCategory.GEOMETRY,
                    ValidationSeverity.ERROR
                )
            elif height < 1000:  # 1m minimum
                self.add_error(
                    "WALL_007",
                    f"Wall height ({height}mm) is below minimum (1000mm)",
                    "height_mm",
                    ValidationCategory.BUILDING_CODE,
                    ValidationSeverity.WARNING,
                    "Standard wall heights are 2400-3000mm"
                )
            elif height > 5000:  # 5m maximum for typical buildings
                self.add_error(
                    "WALL_008",
                    f"Wall height ({height}mm) is very high (over 5m)",
                    "height_mm",
                    ValidationCategory.GEOMETRY,
                    ValidationSeverity.WARNING,
                    "Verify if this height is correct"
                )
        
        return self.get_result()
    
    def validate_room_definition(self, room: Dict[str, Any]) -> ValidationResult:
        """
        Validate room definition.
        
        Args:
            room: Room definition dictionary
            
        Returns:
            Validation result
        """
        # Required fields
        required_fields = ["name", "boundary_points"]
        for field in required_fields:
            if field not in room:
                self.add_error(
                    "ROOM_001",
                    f"Required field '{field}' is missing",
                    field,
                    ValidationCategory.GEOMETRY,
                    ValidationSeverity.ERROR
                )
        
        # Room name validation
        if "name" in room:
            name = room["name"]
            if not isinstance(name, str) or len(name.strip()) == 0:
                self.add_error(
                    "ROOM_002",
                    "Room name cannot be empty",
                    "name",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.ERROR
                )
            elif len(name) > 100:
                self.add_error(
                    "ROOM_003",
                    "Room name is too long (maximum 100 characters)",
                    "name",
                    ValidationCategory.INPUT_FORMAT,
                    ValidationSeverity.WARNING
                )
        
        # Boundary points validation
        if "boundary_points" in room:
            points = room["boundary_points"]
            if not isinstance(points, list) or len(points) < 3:
                self.add_error(
                    "ROOM_004",
                    "Room must have at least 3 boundary points",
                    "boundary_points",
                    ValidationCategory.GEOMETRY,
                    ValidationSeverity.ERROR
                )
            else:
                # Validate each point
                for i, point in enumerate(points):
                    if not isinstance(point, dict) or "x" not in point or "y" not in point:
                        self.add_error(
                            "ROOM_005",
                            f"Boundary point {i+1} must have x and y coordinates",
                            f"boundary_points[{i}]",
                            ValidationCategory.GEOMETRY,
                            ValidationSeverity.ERROR
                        )
                
                # Check for closed polygon
                if len(points) >= 3:
                    first_point = points[0]
                    last_point = points[-1]
                    
                    if (isinstance(first_point, dict) and isinstance(last_point, dict) and
                        "x" in first_point and "y" in first_point and
                        "x" in last_point and "y" in last_point):
                        
                        if (abs(first_point["x"] - last_point["x"]) > 1 or
                            abs(first_point["y"] - last_point["y"]) > 1):
                            self.add_error(
                                "ROOM_006",
                                "Room boundary is not closed (first and last points don't match)",
                                "boundary_points",
                                ValidationCategory.GEOMETRY,
                                ValidationSeverity.WARNING,
                                "Ensure the room boundary forms a closed polygon"
                            )
                
                # Calculate and validate area
                if len(points) >= 3:
                    area = self._calculate_polygon_area(points)
                    if area < 5:  # 5 m² minimum
                        self.add_error(
                            "ROOM_007",
                            f"Room area ({area:.1f} m²) is below minimum (5 m²)",
                            "area",
                            ValidationCategory.BUILDING_CODE,
                            ValidationSeverity.WARNING,
                            "Rooms should be at least 5 m² for practical use"
                        )
                    elif area > 1000:  # 1000 m² very large
                        self.add_error(
                            "ROOM_008",
                            f"Room area ({area:.1f} m²) is very large (over 1000 m²)",
                            "area",
                            ValidationCategory.GEOMETRY,
                            ValidationSeverity.WARNING,
                            "Verify if this area is correct"
                        )
        
        return self.get_result()
    
    def _calculate_polygon_area(self, points: List[Dict[str, float]]) -> float:
        """Calculate polygon area using shoelace formula."""
        if len(points) < 3:
            return 0.0
        
        try:
            area = 0.0
            n = len(points)
            
            for i in range(n):
                j = (i + 1) % n
                area += points[i]["x"] * points[j]["y"]
                area -= points[j]["x"] * points[i]["y"]
            
            return abs(area) / 2.0 / 1000000  # Convert mm² to m²
            
        except (KeyError, TypeError):
            return 0.0

class SecurityValidator(BaseValidator):
    """Security validation for system inputs."""
    
    def validate_api_request(
        self,
        headers: Dict[str, str],
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate API request for security issues.
        
        Args:
            headers: Request headers
            user_agent: User agent string
            ip_address: Client IP address
            
        Returns:
            Validation result
        """
        # Check for required security headers
        if "authorization" not in headers and "x-api-key" not in headers:
            self.add_error(
                "SEC_001",
                "No authentication provided",
                "authorization",
                ValidationCategory.SECURITY,
                ValidationSeverity.CRITICAL,
                "Provide valid authentication token or API key"
            )
        
        # Check for suspicious user agents
        if user_agent:
            suspicious_agents = [
                'curl', 'wget', 'python-requests', 'postman',
                'bot', 'crawler', 'spider', 'scraper'
            ]
            
            agent_lower = user_agent.lower()
            if any(suspicious in agent_lower for suspicious in suspicious_agents):
                self.add_error(
                    "SEC_002",
                    f"Suspicious user agent detected: {user_agent}",
                    "user_agent",
                    ValidationCategory.SECURITY,
                    ValidationSeverity.WARNING,
                    "Use a standard browser or identify your application"
                )
        
        # Check for rate limiting headers
        if "x-forwarded-for" in headers:
            forwarded_ips = headers["x-forwarded-for"].split(",")
            if len(forwarded_ips) > 5:
                self.add_error(
                    "SEC_003",
                    "Too many forwarded IPs in request",
                    "x_forwarded_for",
                    ValidationCategory.SECURITY,
                    ValidationSeverity.WARNING,
                    "Request may be going through multiple proxies"
                )
        
        return self.get_result()

class ComprehensiveValidator:
    """Main validator that orchestrates all validation types."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.logger = structlog.get_logger(__name__)
    
    def validate_ai_request(
        self,
        user_prompt: str,
        building_requirements: Dict[str, Any],
        files: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Comprehensive validation for AI processing requests.
        
        Args:
            user_prompt: User input prompt
            building_requirements: Building requirements data
            files: List of uploaded files (optional)
            headers: Request headers (optional)
            
        Returns:
            Combined validation result
        """
        all_errors = []
        all_warnings = []
        all_info = []
        
        # Input validation
        input_validator = InputValidator(self.correlation_id)
        
        # Validate user prompt
        prompt_result = input_validator.validate_user_prompt(user_prompt)
        all_errors.extend(prompt_result.errors)
        all_warnings.extend(prompt_result.warnings)
        all_info.extend(prompt_result.info)
        
        # Validate building requirements
        req_result = input_validator.validate_building_requirements(building_requirements)
        all_errors.extend(req_result.errors)
        all_warnings.extend(req_result.warnings)
        all_info.extend(req_result.info)
        
        # Validate files if provided
        if files:
            for file_info in files:
                file_result = input_validator.validate_file_upload(
                    file_info.get("filename", ""),
                    file_info.get("size", 0),
                    file_info.get("content_type", ""),
                    file_info.get("max_size_mb", 100)
                )
                all_errors.extend(file_result.errors)
                all_warnings.extend(file_result.warnings)
                all_info.extend(file_result.info)
        
        # Security validation
        if headers:
            security_validator = SecurityValidator(self.correlation_id)
            user_agent = headers.get("user-agent")
            real_ip = headers.get("x-real-ip")
            security_result = security_validator.validate_api_request(
                headers,
                user_agent,
                real_ip
            )
            all_errors.extend(security_result.errors)
            all_warnings.extend(security_result.warnings)
            all_info.extend(security_result.info)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            info=all_info,
            correlation_id=self.correlation_id,
            validation_time=datetime.utcnow()
        )
    
    def validate_ai_output(
        self,
        layout_result: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate AI-generated layout output.
        
        Args:
            layout_result: AI-generated layout data
            
        Returns:
            Validation result
        """
        all_errors = []
        all_warnings = []
        all_info = []
        
        geometry_validator = GeometryValidator(self.correlation_id)
        
        # Validate walls
        if "walls" in layout_result:
            for i, wall in enumerate(layout_result["walls"]):
                wall_result = geometry_validator.validate_wall_definition(wall)
                # Prefix error fields with wall index
                for error in wall_result.errors:
                    error.field = f"walls[{i}].{error.field}" if error.field else f"walls[{i}]"
                all_errors.extend(wall_result.errors)
                all_warnings.extend(wall_result.warnings)
                all_info.extend(wall_result.info)
        
        # Validate rooms
        if "rooms" in layout_result:
            for i, room in enumerate(layout_result["rooms"]):
                room_result = geometry_validator.validate_room_definition(room)
                # Prefix error fields with room index
                for error in room_result.errors:
                    error.field = f"rooms[{i}].{error.field}" if error.field else f"rooms[{i}]"
                all_errors.extend(room_result.errors)
                all_warnings.extend(room_result.warnings)
                all_info.extend(room_result.info)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            info=all_info,
            correlation_id=self.correlation_id,
            validation_time=datetime.utcnow()
        )