---
applyTo: "src/mcp-server/**/*.py,src/ai-models/**/*.cs,**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.md"
description: AI Prompt Standards — structured prompt engineering for OpenAI, Claude, and Gemini integrations.
---
As AI Prompt Engineer:
- Design consistent prompt templates for architectural AI tasks
- Implement structured prompting with chain-of-thought reasoning
- Create model-specific optimizations for OpenAI, Claude, and Gemini
- Establish prompt versioning and A/B testing frameworks
- Ensure reliable JSON output through proper prompt engineering

## Base Prompt Template Structure

### Master Prompt Framework
```python
class PromptTemplate:
    def __init__(self):
        self.system_prompt = ""
        self.user_prompt_template = ""
        self.json_schema = {}
        self.examples = []
        self.constraints = []
        
    def format(self, **kwargs) -> str:
        return self.user_prompt_template.format(**kwargs)

# Architectural Layout Generation Template
ARCHITECTURAL_LAYOUT_PROMPT = PromptTemplate()
ARCHITECTURAL_LAYOUT_PROMPT.system_prompt = """
You are an expert architect and BIM specialist with deep knowledge of:
- Autodesk Revit API and data structures
- Architectural space planning and building codes
- Geometric relationships and spatial constraints
- Turkish building regulations (İmar Yönetmeliği)

Your ONLY task is to analyze user requirements and generate precise JSON responses 
that can be directly consumed by Revit API calls.

CRITICAL RULES:
1. ALWAYS respond with valid JSON matching the exact schema provided
2. ALL coordinates must be in millimeters
3. ALL geometric calculations must be accurate and buildable
4. Consider accessibility requirements and building codes
5. Flag any uncertainties with requiresHumanReview: true
"""

ARCHITECTURAL_LAYOUT_PROMPT.user_prompt_template = """
USER REQUIREMENTS:
{user_prompt}

CONTEXT:
- Building Type: {building_type}
- Total Area: {total_area_m2} m²
- Number of Rooms: {room_count}
- Style Preference: {style_preference}
- Accessibility Required: {accessibility_required}

THINK STEP BY STEP:
1. First, analyze the spatial requirements and create a logical room adjacency matrix
2. Calculate approximate room dimensions based on area requirements
3. Determine the overall building envelope (exterior walls)
4. Plan interior walls to create the required rooms
5. Position doors for optimal circulation
6. Position windows for natural light and ventilation
7. Validate that all constraints are met

RESPONSE FORMAT:
Generate a JSON response following this EXACT schema:

```json
{{
  "thinking": {{
    "analysis": "Brief explanation of your spatial analysis",
    "adjacency_decisions": "Why you placed rooms where you did",
    "geometric_reasoning": "Key geometric decisions and calculations"
  }},
  "layout": {{
    "walls": [
      {{
        "id": "unique_wall_id",
        "startPoint": {{"x": 0, "y": 0, "z": 0}},
        "endPoint": {{"x": 5000, "y": 0, "z": 0}},
        "heightMm": 2700,
        "wallTypeName": "Generic - 200mm",
        "levelName": "Level 1",
        "isExterior": true
      }}
    ],
    "doors": [
      {{
        "id": "unique_door_id", 
        "hostWallId": "wall_id_reference",
        "positionRatio": 0.5,
        "familyName": "Single-Flush",
        "typeName": "0915 x 2134mm",
        "widthMm": 915,
        "heightMm": 2134
      }}
    ],
    "windows": [
      {{
        "id": "unique_window_id",
        "hostWallId": "wall_id_reference", 
        "positionRatio": 0.5,
        "familyName": "Fixed",
        "typeName": "1220 x 1830mm",
        "widthMm": 1220,
        "heightMm": 1830
      }}
    ],
    "rooms": [
      {{
        "id": "unique_room_id",
        "name": "Living Room",
        "area": 25.5,
        "function": "living",
        "accessibilityCompliant": true
      }}
    ]
  }},
  "metadata": {{
    "confidence": 0.85,
    "requiresHumanReview": false,
    "geometricComplexity": "simple",
    "estimatedBuildTime": "2 hours",
    "potentialIssues": ["List any concerns or limitations"]
  }}
}}
```

CONSTRAINTS:
- Minimum room area: 5.0 m²
- Standard ceiling height: 2700mm
- Door width range: 700-1000mm
- Window width range: 600-2000mm
- Wall thickness: 200mm (interior), 300mm (exterior)
- Minimum corridor width: 1200mm
- All coordinates must form closed room boundaries
"""
```

## Model-Specific Optimizations

### OpenAI GPT-4 Prompts
```python
class OpenAIPromptEngine:
    def __init__(self):
        self.base_config = {
            "model": "gpt-4",
            "temperature": 0.1,  # Low temperature for consistent architectural output
            "max_tokens": 4000,
            "response_format": {"type": "json_object"}  # Force JSON mode
        }
    
    def create_layout_prompt(self, user_requirements: dict) -> dict:
        """Optimized for GPT-4's reasoning capabilities"""
        
        return {
            **self.base_config,
            "messages": [
                {
                    "role": "system",
                    "content": ARCHITECTURAL_LAYOUT_PROMPT.system_prompt
                },
                {
                    "role": "user", 
                    "content": ARCHITECTURAL_LAYOUT_PROMPT.format(**user_requirements)
                },
                {
                    "role": "assistant",
                    "content": "I'll analyze your requirements step by step and generate a precise architectural layout. Let me think through this systematically:\n\n{"
                }
            ]
        }
    
    def create_validation_prompt(self, layout_data: dict) -> dict:
        """Prompt for validating AI-generated layouts"""
        
        validation_prompt = f"""
        Review this architectural layout for errors and compliance:

        LAYOUT DATA:
        {json.dumps(layout_data, indent=2)}

        VALIDATION CHECKLIST:
        1. Geometric validity (no overlapping walls, proper connections)
        2. Spatial constraints (minimum room sizes, door clearances)
        3. Building code compliance (fire exits, accessibility)
        4. Architectural logic (room adjacencies, circulation)
        5. Revit API compatibility (valid element references)

        Respond with JSON:
        {{
          "isValid": true/false,
          "confidenceScore": 0.0-1.0,
          "errors": ["specific error descriptions"],
          "warnings": ["potential issues"],
          "suggestions": ["recommended improvements"],
          "codeCompliance": {{
            "accessibility": true/false,
            "fireEgress": true/false,
            "spatialRequirements": true/false
          }}
        }}
        """
        
        return {
            **self.base_config,
            "messages": [
                {"role": "system", "content": "You are an expert architectural reviewer."},
                {"role": "user", "content": validation_prompt}
            ]
        }
```

### Claude 3.5 Sonnet Prompts  
```python
class ClaudePromptEngine:
    def __init__(self):
        self.base_config = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4000,
            "temperature": 0.1
        }
    
    def create_layout_prompt(self, user_requirements: dict) -> dict:
        """Optimized for Claude's analytical strengths"""
        
        # Claude responds well to structured thinking prompts
        enhanced_prompt = f"""
        <task>
        Generate an architectural layout from user requirements with step-by-step reasoning.
        </task>

        <user_requirements>
        {json.dumps(user_requirements, indent=2)}
        </user_requirements>

        <thinking_process>
        Before generating the JSON response, work through these steps:

        1. <spatial_analysis>
           - Analyze the functional relationships between rooms
           - Calculate optimal room proportions
           - Consider circulation patterns
        </spatial_analysis>

        2. <geometric_planning>
           - Design the building envelope
           - Plan interior wall positions
           - Ensure proper door and window placement
        </geometric_planning>

        3. <code_compliance>
           - Check minimum room areas (5m² minimum)
           - Verify accessibility requirements
           - Ensure fire egress compliance
        </code_compliance>
        </thinking_process>

        <output_format>
        Respond with valid JSON matching the architectural layout schema.
        Include your reasoning in the "thinking" section of the JSON.
        </output_format>

        {ARCHITECTURAL_LAYOUT_PROMPT.user_prompt_template.format(**user_requirements)}
        """
        
        return {
            **self.base_config,
            "messages": [
                {
                    "role": "user",
                    "content": enhanced_prompt
                }
            ]
        }
    
    def create_sketch_analysis_prompt(self, image_data: str) -> dict:
        """Claude excels at image analysis"""
        
        return {
            **self.base_config,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
                            Analyze this architectural sketch and extract:
                            1. Room layouts and approximate dimensions
                            2. Door and window positions
                            3. Spatial relationships and circulation
                            4. Any annotations or measurements
                            
                            Convert your analysis into structured JSON format for Revit API implementation.
                            """
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                }
            ]
        }
```

### Gemini Pro Prompts
```python
class GeminiPromptEngine:
    def __init__(self):
        self.base_config = {
            "model": "gemini-pro",
            "temperature": 0.1,
            "candidate_count": 1
        }
    
    def create_layout_prompt(self, user_requirements: dict) -> dict:
        """Optimized for Gemini's multimodal capabilities"""
        
        # Gemini works well with structured, example-driven prompts
        prompt_with_examples = f"""
        **ROLE**: Expert Architect specializing in Revit BIM modeling

        **TASK**: Generate precise architectural layout from requirements

        **EXAMPLE INPUT/OUTPUT**:
        Input: "Create a 50m² apartment with 1 bedroom, 1 bathroom, kitchen, living room"
        Output: {{
          "thinking": {{"analysis": "Small apartment requires efficient space planning..."}},
          "layout": {{"walls": [...], "doors": [...], "windows": [...]}},
          "metadata": {{"confidence": 0.9, "requiresHumanReview": false}}
        }}

        **CURRENT REQUIREMENTS**:
        {json.dumps(user_requirements, indent=2)}

        **STEP-BY-STEP APPROACH**:
        1. 🏗️ Analyze spatial program and adjacencies
        2. 📐 Calculate building envelope dimensions  
        3. 🚪 Plan circulation and door positions
        4. 🪟 Optimize window placement for daylighting
        5. ✅ Validate against building codes

        **OUTPUT**: Valid JSON following the architectural layout schema

        {ARCHITECTURAL_LAYOUT_PROMPT.user_prompt_template.format(**user_requirements)}
        """
        
        return {
            **self.base_config,
            "contents": [{"parts": [{"text": prompt_with_examples}]}]
        }
```

## Prompt Testing and Validation Framework
```python
class PromptTestingFramework:
    def __init__(self):
        self.test_cases = []
        self.validation_schema = {}
        
    def add_test_case(self, name: str, inputs: dict, expected_outputs: dict):
        """Add test case for prompt validation"""
        self.test_cases.append({
            "name": name,
            "inputs": inputs,
            "expected": expected_outputs,
            "results": {}
        })
    
    async def run_prompt_tests(self, prompt_engine: Any) -> dict:
        """Test prompts against all models"""
        results = {
            "passed": 0,
            "failed": 0,
            "test_results": []
        }
        
        for test_case in self.test_cases:
            try:
                # Test with different AI models
                gpt_result = await self.test_with_openai(prompt_engine, test_case)
                claude_result = await self.test_with_claude(prompt_engine, test_case)
                gemini_result = await self.test_with_gemini(prompt_engine, test_case)
                
                # Validate outputs
                validation_results = {
                    "gpt": self.validate_output(gpt_result, test_case["expected"]),
                    "claude": self.validate_output(claude_result, test_case["expected"]),
                    "gemini": self.validate_output(gemini_result, test_case["expected"])
                }
                
                test_result = {
                    "name": test_case["name"],
                    "validation": validation_results,
                    "passed": all(validation_results.values())
                }
                
                results["test_results"].append(test_result)
                
                if test_result["passed"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["test_results"].append({
                    "name": test_case["name"],
                    "error": str(e),
                    "passed": False
                })
        
        return results
```

## Prompt Version Management
```python
class PromptVersionManager:
    def __init__(self):
        self.versions = {}
        self.active_version = "1.0"
        
    def register_prompt_version(self, name: str, version: str, prompt_template: PromptTemplate):
        """Register a new prompt version"""
        if name not in self.versions:
            self.versions[name] = {}
        
        self.versions[name][version] = {
            "template": prompt_template,
            "created_at": datetime.utcnow(),
            "performance_metrics": {},
            "usage_count": 0
        }
    
    def get_prompt(self, name: str, version: str = None) -> PromptTemplate:
        """Get prompt by name and version"""
        if version is None:
            version = self.active_version
            
        if name in self.versions and version in self.versions[name]:
            self.versions[name][version]["usage_count"] += 1
            return self.versions[name][version]["template"]
        
        raise ValueError(f"Prompt {name} version {version} not found")
    
    def update_performance_metrics(self, name: str, version: str, metrics: dict):
        """Update performance metrics for a prompt version"""
        if name in self.versions and version in self.versions[name]:
            self.versions[name][version]["performance_metrics"].update(metrics)
    
    def get_best_performing_version(self, name: str) -> str:
        """Get the best performing version based on metrics"""
        if name not in self.versions:
            return None
            
        best_version = None
        best_score = 0
        
        for version, data in self.versions[name].items():
            metrics = data["performance_metrics"]
            if "accuracy" in metrics and metrics["accuracy"] > best_score:
                best_score = metrics["accuracy"]
                best_version = version
        
        return best_version or self.active_version
```

## Specialized Prompt Templates

### Turkish Building Code Compliance
```python
TURKISH_BUILDING_CODE_PROMPT = """
Additionally, ensure compliance with Turkish İmar Yönetmeliği:

TURKISH BUILDING REQUIREMENTS:
- Minimum room heights: 2.40m for residential, 2.70m for commercial
- Minimum room areas: Bedroom 9m², Living room 12m², Kitchen 6m²
- Fire escape requirements: Max 30m travel distance to exit
- Accessibility: 900mm minimum door width for accessible routes
- Natural lighting: Minimum 1/8 floor area as window area
- Ventilation: Minimum 1/20 floor area as openable window area

Include these constraints in your geometric calculations and flag any potential violations.
"""

ENERGY_OPTIMIZATION_PROMPT = """
Consider energy efficiency in your design:

ENERGY REQUIREMENTS:
- Optimize building orientation for solar gain
- Minimize thermal bridging in wall connections  
- Position windows to maximize daylight while minimizing heat loss
- Design for cross-ventilation where possible
- Consider shading requirements for summer comfort

Include energy considerations in your "thinking" analysis.
"""
```

## Revit API Integration Prompts

### Revit Family and Parameter Prompts
```python
REVIT_FAMILY_PROMPT = """
When generating Revit elements, ensure compatibility with Revit API:

REVIT API CONSTRAINTS:
- All coordinates in millimeters for internal conversion
- Use standard Revit family types: "Basic Wall", "Single-Flush", "Fixed"
- Wall creation requires: start point, end point, wall type, level
- Door/window placement requires: host wall reference, position ratio (0.0-1.0)
- Transaction management: All element creation must be wrapped in transactions

FAMILY NAMING CONVENTIONS:
- Walls: "Generic - 200mm", "Exterior - Brick on CMU", "Interior - Partition (92mm)"
- Doors: "Single-Flush", "Double-Flush", "Pocket Door"
- Windows: "Fixed", "Casement", "Double Hung"

REVIT API INTEGRATION:
- Element IDs are required for tracking and modification
- Level references must be valid in the current document
- Wall types must exist in the project before creation
- Use FilteredElementCollector for efficient element queries

Example Revit-compatible output:
{{
  "walls": [
    {{
      "id": "wall_exterior_south",
      "startPoint": {{"x": 0, "y": 0, "z": 0}},
      "endPoint": {{"x": 10000, "y": 0, "z": 0}},
      "wallTypeName": "Generic - 200mm",
      "levelName": "Level 1",
      "height": 2700,
      "isLoadBearing": false
    }}
  ],
  "doors": [
    {{
      "id": "door_entrance",
      "hostWallId": "wall_exterior_south",
      "positionRatio": 0.5,
      "familyName": "Single-Flush",
      "typeName": "0915 x 2134mm",
      "flipHand": false,
      "flipFacing": false
    }}
  ]
}}
"""

REVIT_TRANSACTION_PROMPT = """
Consider Revit API transaction requirements:

TRANSACTION GUIDELINES:
- Each element creation operation requires a Transaction
- Group related operations in single transactions for performance
- Provide rollback strategy for failed operations
- Include correlation IDs for tracking and debugging

MEMORY MANAGEMENT:
- Avoid memory leaks with proper disposal patterns
- Use using statements for IDisposable objects
- Consider performance for large element collections
- Implement progress reporting for long operations

ERROR RECOVERY:
- Validate element references before use
- Check for existing elements to avoid duplicates
- Provide fallback for missing family types
- Handle Revit API exceptions gracefully
"""
```

## Dynamo Integration Prompts

### Dynamo Geometric Script Generation
```python
DYNAMO_GEOMETRY_PROMPT = """
When generating complex geometry, consider Dynamo script integration:

DYNAMO CAPABILITIES:
- Parametric geometry generation with live updates
- Complex mathematical operations and transformations
- Visual scripting interface for architects
- Direct integration with Revit elements

GEOMETRIC COMPLEXITY THRESHOLDS:
- Simple geometry: Direct Revit API (rectangles, basic shapes)
- Medium complexity: Dynamo scripts (curved walls, complex forms)
- High complexity: Dynamo + custom nodes (parametric facades)

DYNAMO SCRIPT STRUCTURE:
1. Input parameters (dimensions, constraints)
2. Geometric generation nodes
3. Revit element creation nodes
4. Output validation and error handling

Example Dynamo integration decision:
{{
  "geometryComplexity": "medium",
  "requiresDynamo": true,
  "dynamoScript": {{
    "inputParameters": [
      {{"name": "buildingWidth", "type": "number", "default": 20000}},
      {{"name": "buildingLength", "type": "number", "default": 30000}},
      {{"name": "floorHeight", "type": "number", "default": 3000}}
    ],
    "outputElements": ["walls", "floors", "rooms"],
    "scriptPath": "scripts/curved_building_envelope.dyn"
  }}
}}
"""

DYNAMO_PARAMETER_PROMPT = """
For parametric design with Dynamo:

PARAMETER MANAGEMENT:
- Use stable parameter names for consistency
- Provide reasonable default values
- Include parameter validation ranges
- Support metric/imperial unit conversion

SCRIPT EXECUTION:
- Design for Dynamo Player compatibility
- Include progress indicators for long operations
- Handle script failures gracefully
- Provide user-friendly parameter interfaces

REVIT INTEGRATION:
- Map Dynamo outputs to Revit elements
- Maintain element tracking for updates
- Support incremental modifications
- Preserve user customizations
"""
```

## Turkish Building Code Integration

### Turkish Regulatory Compliance Prompts
```python
TURKISH_BUILDING_CODE_PROMPT = """
Additionally, ensure compliance with Turkish İmar Yönetmeliği and building codes:

TURKISH BUILDING REQUIREMENTS:
- Minimum room heights: 2.40m for residential, 2.70m for commercial
- Minimum room areas: Bedroom 9m², Living room 12m², Kitchen 6m²
- Fire escape requirements: Max 30m travel distance to exit
- Accessibility: 900mm minimum door width for accessible routes
- Natural lighting: Minimum 1/8 floor area as window area
- Ventilation: Minimum 1/20 floor area as openable window area
- TAKS (building coverage ratio): Typically 0.30-0.40 depending on zone
- KAKS (floor area ratio): Varies by zoning district

ZONING COMPLIANCE:
- Setback requirements from property boundaries
- Building height restrictions based on zone type
- Parking requirements based on building use
- Landscape requirements (minimum green area ratios)

STRUCTURAL REQUIREMENTS:
- Earthquake resistance (Turkey is in seismic zone)
- Foundation depth based on soil type
- Thermal insulation requirements
- Sound insulation between units

Include these constraints in your geometric calculations and flag any potential violations.

Example compliance check:
{{
  "turkishBuildingCodeCheck": {{
    "taksCompliance": true,
    "taksRatio": 0.35,
    "fireEgressCompliance": true,
    "maxTravelDistance": 25,
    "accessibilityCompliance": true,
    "naturalLightingRatio": 0.15,
    "potentialViolations": []
  }}
}}
"""

MULTI_LANGUAGE_DOCUMENT_PROMPT = """
For processing building codes in multiple languages:

LANGUAGE-SPECIFIC PROCESSING:
- Turkish: Use tr_core_news_sm model for Turkish regulations
- German: Use de_core_news_sm for German DIN standards  
- English: Use en_core_web_sm for international codes
- French: Use fr_core_news_sm for French regulations

CULTURAL CONTEXT PRESERVATION:
- Maintain original terminology where applicable
- Note regional measurement preferences (metric vs imperial)
- Preserve cultural architectural concepts
- Include local material and construction practices

REGULATORY EXTRACTION:
- Identify measurement units and convert appropriately
- Extract minimum/maximum constraints
- Note exceptions and special conditions
- Flag unclear or ambiguous requirements for human review

Example multi-language output:
{{
  "detectedLanguage": "tr",
  "originalTerminology": {{
    "imar_yonetmeligi": "zoning_regulation",
    "taks": "building_coverage_ratio",
    "kaks": "floor_area_ratio"
  }},
  "extractedRules": [
    {{
      "rule": "minimum_room_height",
      "value": 2400,
      "unit": "mm",
      "applicability": "residential",
      "source": "İmar Yönetmeliği Madde 15"
    }}
  ]
}}
"""
```
