+-
---
applyTo: "src/cloud-server/**/*.py,src/desktop-app/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: AI Integration role — ArchBuilder.AI Vertex AI and GitHub Models integration, prompt engineering, validation patterns.
---
As AI Integration Developer:
- Design prompt engineering strategies for architectural tasks using Vertex AI (Gemini-2.5-Flash-Lite) and GitHub Models (GPT-4.1)
- Implement comprehensive AI output validation pipelines for multi-format CAD files (DWG/DXF, IFC, PDF)
- Create human-in-the-loop approval workflows with sandbox/dry-run testing
- Build fallback systems for AI failures with whitelisted command validation
- Ensure AI safety through validation layers and confidence scoring
- **AI PROCESSING**: All AI logic in Python Cloud Server with desktop app integration
- **EXISTING PROJECT ANALYSIS**: AI-powered analysis of existing Revit projects (.rvt files) for improvement recommendations
- **REVERSE ENGINEERING**: BIM intelligence and enhancement suggestions for existing architectural projects

AI Safety Principles:
- **Never Trust AI Outputs**: All AI responses must pass validation
- **Mandatory Human Review**: Every AI suggestion requires architect approval
- **Confidence Thresholds**: Low confidence outputs trigger human escalation
- **Graceful Degradation**: Always provide rule-based fallbacks
- **Audit Trail**: Log all AI interactions with correlation IDs

Multi-Language AI Processing:
- **Language Detection**: Automatic detection of user input language
- **Regional Models**: Use language-specific AI models and prompts
- **Model Selection**: Dynamic model selection based on region, language, and document type
- **Cultural Context**: Preserve region-specific architectural terminology

Model Selection Strategy:
```python
class AIModelSelector:
    """Dynamic AI model selection for ArchBuilder.AI with Vertex AI and GitHub Models"""
    
    def __init__(self):
        self.model_config = {
            "vertex_ai": {
                "gemini-2.5-flash-lite": {
                    "languages": ["en", "tr", "de", "fr", "es"], 
                    "max_tokens": 32768,
                    "specialties": ["cad_analysis", "building_codes", "architectural_prompts"],
                    "cost": "low"
                }
            },
            "github_models": {
                "gpt-4.1": {
                    "languages": ["en", "tr", "de", "fr", "es"], 
                    "max_tokens": 128000,
                    "specialties": ["complex_reasoning", "multi_format_parsing", "revit_commands"],
                    "cost": "medium"
                }
            }
        }
    
    def select_model(self, 
                    language: str,
                    document_type: str,
                    complexity: str,
                    file_format: str = None,
                    analysis_type: str = "creation",
                    user_preference: str = None) -> dict:
        """Select optimal AI model based on context for ArchBuilder.AI"""
        
        # Priority order based on task requirements  
        if analysis_type == "existing_project_analysis":
            # Existing project analysis - use GitHub Models for BIM intelligence
            return {
                "provider": "github_models",
                "model": "gpt-4.1",
                "reason": "Best for comprehensive BIM analysis and improvement recommendations"
            }
        elif document_type == "building_code" and language == "tr":
            # Turkish building codes - use Vertex AI for regulatory documents
            return {
                "provider": "vertex_ai",
                "model": "gemini-2.5-flash-lite",
                "reason": "Optimized for Turkish regulatory documents and building codes"
            }
        elif file_format in ["dwg", "dxf", "ifc"] or complexity == "high":
            # CAD file analysis and complex technical tasks - use GitHub Models
            return {
                "provider": "github_models", 
                "model": "gpt-4.1",
                "reason": "Superior for multi-format CAD parsing and complex reasoning"
            }
        elif complexity == "simple" or document_type == "prompt_generation":
            # Simple tasks and prompt generation - use Vertex AI (cost-effective)
            return {
                "provider": "vertex_ai",
                "model": "gemini-2.5-flash-lite", 
                "reason": "Cost-effective for simple architectural tasks"
            }
        else:
            # Default to GitHub Models for complex architectural reasoning
            return {
                "provider": "github_models",
                "model": "gpt-4.1",
                "reason": "Reliable for comprehensive architectural analysis"
            }
```

Prompt Engineering Patterns:
```python
class ArchitecturalPromptEngine:
    """Structured prompt engineering for architectural AI tasks"""
    
    def create_layout_prompt(self, requirements: RoomProgram) -> str:
        return f"""
        You are an expert architect creating Revit-compatible layouts.
        
        REQUIREMENTS:
        - Total area: {requirements.total_area} m²
        - Rooms: {', '.join(requirements.rooms)}
        - Style: {requirements.style}
        - Constraints: {requirements.constraints}
        
        TASK: Generate a JSON response with exact coordinates for:
        1. Wall lines (start/end points)
        2. Door positions (wall location + offset)
        3. Window positions (wall location + offset)
        
        CONSTRAINTS:
        - All coordinates in millimeters
        - Minimum room size: 5m²
        - Door width: 800-1000mm
        - Window width: 1000-2000mm
        
        OUTPUT FORMAT: Return ONLY valid JSON matching this schema:
        {{
            "walls": [
                {{"start": {{"x": 0, "y": 0}}, "end": {{"x": 5000, "y": 0}}, "type": "interior"}}
            ],
            "doors": [
                {{"wall_index": 0, "position": 2500, "width": 900, "type": "single"}}
            ],
            "confidence": 0.95
        }}
        """

    def create_validation_prompt(self, layout: dict) -> str:
        return f"""
        Review this architectural layout for errors:
        
        LAYOUT: {json.dumps(layout)}
        
        CHECK FOR:
        1. Geometric validity (no overlapping walls)
        2. Spatial constraints (minimum room sizes)
        3. Accessibility (door clearances)
        4. Building codes (fire exits, corridor widths)
        
        RESPOND WITH:
        {{
            "is_valid": true/false,
            "errors": ["list of specific issues"],
            "confidence": 0.0-1.0
        }}
        """
```

AI Output Validation Pipeline:
```python
class ComprehensiveAIValidator:
    """Multi-layer validation for AI architectural outputs"""
    
    async def validate_layout(self, ai_output: dict) -> ValidationResult:
        """Comprehensive validation with human review flags"""
        
        # Layer 1: Schema validation
        schema_errors = self._validate_json_schema(ai_output)
        if schema_errors:
            return ValidationResult(
                status=ValidationStatus.REJECTED,
                errors=schema_errors,
                requires_human_review=False  # Auto-reject schema errors
            )
        
        # Layer 2: Geometric validation
        geo_errors = self._validate_geometry(ai_output)
        
        # Layer 3: Building code validation
        code_errors = await self._validate_building_codes(ai_output)
        
        # Layer 4: Spatial validation
        spatial_errors = self._validate_spatial_constraints(ai_output)
        
        # Layer 5: AI confidence check
        confidence = ai_output.get("confidence", 0.0)
        confidence_errors = []
        if confidence < 0.8:
            confidence_errors.append(f"Low AI confidence: {confidence}")
        
        all_errors = geo_errors + code_errors + spatial_errors + confidence_errors
        
        # Determine status and human review requirement
        if len(all_errors) > 3:
            status = ValidationStatus.REJECTED
            requires_review = True  # Human should see why it was rejected
        elif all_errors:
            status = ValidationStatus.REQUIRES_REVIEW
            requires_review = True
        else:
            status = ValidationStatus.REQUIRES_REVIEW  # Even valid outputs need review
            requires_review = True
        
        return ValidationResult(
            status=status,
            errors=all_errors,
            confidence=confidence,
            requires_human_review=requires_review
        )
    
    def _validate_geometry(self, layout: dict) -> List[str]:
        """Validate geometric constraints"""
        errors = []
        
        walls = layout.get("walls", [])
        for i, wall in enumerate(walls):
            # Check wall length
            start, end = wall["start"], wall["end"]
            length = ((end["x"] - start["x"])**2 + (end["y"] - start["y"])**2)**0.5
            if length < 100:  # 10cm minimum
                errors.append(f"Wall {i} too short: {length}mm")
            
            # Check for overlapping walls
            for j, other_wall in enumerate(walls[i+1:], i+1):
                if self._walls_overlap(wall, other_wall):
                    errors.append(f"Walls {i} and {j} overlap")
        
        return errors
    
    async def _validate_building_codes(self, layout: dict) -> List[str]:
        """Validate against Turkish building codes"""
        errors = []
        
        # Check corridor widths (min 1.2m for residential)
        corridors = self._extract_corridors(layout)
        for corridor in corridors:
            if corridor["width"] < 1200:
                errors.append(f"Corridor width {corridor['width']}mm below minimum 1200mm")
        
        # Check fire exit requirements
        rooms = self._extract_rooms(layout)
        for room in rooms:
            if not self._has_fire_exit_access(room, layout):
                errors.append(f"Room {room['name']} lacks fire exit access")
        
        return errors
```

Human Review Integration:
```python
class HumanReviewWorkflow:
    """Manage human review queue and approval workflows"""
    
    async def submit_for_review(self, ai_output: dict, validation: ValidationResult):
        """Submit AI output for mandatory human review"""
        
        review_item = ReviewItem(
            id=str(uuid.uuid4()),
            ai_output=ai_output,
            validation_result=validation,
            status=ReviewStatus.PENDING,
            created_at=datetime.utcnow(),
            requires_action=validation.status != ValidationStatus.VALID
        )
        
        # Store in review queue
        await self.review_repository.save(review_item)
        
        # Notify architect via UI
        await self.notification_service.notify_review_pending(review_item)
        
        # Log for audit trail
        logger.info("AI output submitted for human review", 
                   review_id=review_item.id,
                   validation_status=validation.status.value,
                   error_count=len(validation.errors))
        
        return review_item
    
    async def process_human_feedback(self, review_id: str, feedback: HumanFeedback):
        """Process architect feedback and learn from corrections"""
        
        review_item = await self.review_repository.get(review_id)
        
        # Update review status
        review_item.status = ReviewStatus.COMPLETED
        review_item.human_feedback = feedback
        review_item.completed_at = datetime.utcnow()
        
        # Learn from corrections for future prompts
        if feedback.has_corrections:
            await self.learning_service.update_prompts(
                original_output=review_item.ai_output,
                corrections=feedback.corrections,
                architect_notes=feedback.notes
            )
        
        # Store final decision
        await self.review_repository.save(review_item)
        
        logger.info("Human review completed",
                   review_id=review_id,
                   approved=feedback.approved,
                   corrections_count=len(feedback.corrections))
```

Fallback System Architecture:
```python
class ArchitecturalFallbackService:
    """Rule-based fallback when AI fails or produces invalid outputs"""
    
    def generate_layout_fallback(self, requirements: RoomProgram) -> LayoutResult:
        """Generate layout using rule-based algorithms"""
        
        logger.info("Using rule-based fallback for layout generation")
        
        # Simple rectangular room layout algorithm
        total_area = requirements.total_area
        room_count = len(requirements.rooms)
        avg_room_size = total_area / room_count
        
        # Calculate grid layout
        grid_size = math.ceil(math.sqrt(room_count))
        room_width = math.sqrt(avg_room_size)
        room_height = room_width
        
        walls = []
        doors = []
        
        # Generate grid of rooms
        for i, room_name in enumerate(requirements.rooms):
            row = i // grid_size
            col = i % grid_size
            
            x = col * room_width * 1000  # Convert to mm
            y = row * room_height * 1000
            
            # Add room walls
            room_walls = self._create_room_walls(x, y, room_width * 1000, room_height * 1000)
            walls.extend(room_walls)
            
            # Add door if not on perimeter
            if col > 0:  # Add door to left wall
                doors.append({
                    "wall_index": len(walls) - 4,  # Left wall
                    "position": room_height * 500,  # Center of wall
                    "width": 900,
                    "type": "single"
                })
        
        return LayoutResult(
            walls=walls,
            doors=doors,
            confidence=0.7,  # Lower confidence for rule-based
            generated_by="fallback",
            requires_human_review=True
        )

## Existing Project Analysis AI Prompts

Specialized prompts for analyzing existing Revit projects:

### Project Analysis Prompt Template:
```python
PROJECT_ANALYSIS_PROMPT = """
You are an expert BIM consultant analyzing an existing Revit project. Based on the provided project data, generate comprehensive improvement recommendations.

PROJECT DATA:
{project_summary}

ELEMENT ANALYSIS:
- Total Elements: {total_elements}
- Walls: {wall_count} ({wall_types})
- Doors: {door_count}
- Windows: {window_count}
- Families: {family_count}

PERFORMANCE METRICS:
- File Size: {file_size}MB
- Complex Families: {complex_families}
- Unused Elements: {unused_elements}

COMPLIANCE ISSUES DETECTED:
{compliance_issues}

TASK: Provide detailed analysis and improvement recommendations in the following categories:

1. **BIM OPTIMIZATION**
   - Model organization improvements
   - Family optimization suggestions
   - Performance enhancement recommendations

2. **DESIGN IMPROVEMENTS**
   - Spatial layout optimization
   - Accessibility compliance fixes
   - Building code violation corrections

3. **TECHNICAL ENHANCEMENTS**
   - MEP system improvements
   - Structural optimization
   - Energy performance upgrades

4. **WORKFLOW OPTIMIZATION**
   - Collaboration improvements
   - Documentation enhancements
   - Standard compliance

For each recommendation, provide:
- Priority level (High/Medium/Low)
- Estimated implementation time
- Expected impact
- Specific Revit commands or steps

Format response as structured JSON with Turkish descriptions.
"""

CLASH_DETECTION_PROMPT = """
Analyze the provided clash detection results from Revit project and suggest resolution strategies.

DETECTED CLASHES:
{clash_data}

For each clash, provide:
1. Root cause analysis
2. Resolution strategy
3. Prevention methods for future
4. Priority ranking

Focus on architectural, structural, and MEP conflicts. Provide Turkish explanations with technical English terms.
"""

BUILDING_CODE_ANALYSIS_PROMPT = """
Analyze this Revit project against Turkish Building Code requirements.

PROJECT CONTEXT:
- Building Type: {building_type}
- Total Area: {total_area}m²
- Floor Count: {floor_count}
- Occupancy: {occupancy_type}

SPECIFIC CHECKS REQUIRED:
1. Door width accessibility (min 80cm)
2. Stair dimensions and safety
3. Fire escape routes
4. Natural lighting requirements
5. Ventilation standards
6. Parking space requirements

Provide detailed compliance report with:
- Violations found
- Correction recommendations
- Relevant code article references
- Implementation priorities

Use Turkish descriptions with code article numbers.
"""
```
```

Always implement multi-layer validation, require human review, and provide fallbacks.
Log all AI interactions with correlation IDs for debugging and learning.