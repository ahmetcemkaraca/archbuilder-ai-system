---
applyTo: "src/revit-plugin/**/*.cs,src/desktop-app/**/*.cs,src/revit-plugin/**/*Service*.cs,src/revit-plugin/**/*Repository*.cs,src/revit-plugin/**/*Model*.cs"
description: Revit Architecture role — element creation, family management, BIM model structure, geometric operations for ArchBuilder.AI with multi-format CAD support.
---
As Revit Architecture Developer:
- Design efficient element creation patterns with proper transactions
- Implement family management and parameter handling systems
- Create geometric validation and constraint checking algorithms
- Build BIM model structure with proper element relationships
- Integrate Dynamo as geometric script engine for complex operations
- **NO AI PROCESSING**: Focus on executing validated layouts from Python MCP Server

Dynamo Integration for Complex Geometry:
```csharp
public class DynamoGeometryEngine
{
    private readonly ILogger<DynamoGeometryEngine> _logger;
    private readonly string _dynamoScriptsPath;
    
    public DynamoGeometryEngine(ILogger<DynamoGeometryEngine> logger, IConfiguration config)
    {
        _logger = logger;
        _dynamoScriptsPath = config.GetValue<string>("Dynamo:ScriptsPath");
    }
    
    public async Task<GeometryResult> ExecuteComplexGeometry(
        GeometryParameters parameters,
        string correlationId)
    {
        try
        {
            // Determine if geometry is complex enough for Dynamo
            if (parameters.ComplexityLevel == GeometryComplexity.Simple)
            {
                return await CreateSimpleGeometryWithRevitAPI(parameters);
            }
            
            // Generate Dynamo script for complex geometry
            var scriptPath = await GenerateDynamoScript(parameters, correlationId);
            
            _logger.LogInformation("Executing Dynamo script for complex geometry",
                correlation_id: correlationId,
                script_path: scriptPath,
                complexity: parameters.ComplexityLevel.ToString());
            
            // Execute Dynamo script
            var dynamoResult = await ExecuteDynamoScript(scriptPath, parameters);
            
            // Convert Dynamo output to Revit elements
            var revitElements = await ConvertDynamoToRevitElements(dynamoResult);
            
            return new GeometryResult
            {
                Elements = revitElements,
                GeneratedBy = "Dynamo",
                ScriptPath = scriptPath,
                ExecutionTime = dynamoResult.ExecutionTime
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Dynamo geometry execution failed", correlation_id: correlationId);
            
            // Fallback to simple Revit API geometry
            _logger.LogInformation("Falling back to simple Revit API geometry", correlation_id: correlationId);
            return await CreateSimpleGeometryWithRevitAPI(parameters);
        }
    }
    
    private async Task<string> GenerateDynamoScript(GeometryParameters parameters, string correlationId)
    {
        var scriptTemplate = parameters.ComplexityLevel switch
        {
            GeometryComplexity.CurvedWalls => await LoadTemplate("curved_walls.dyn"),
            GeometryComplexity.ComplexFacade => await LoadTemplate("parametric_facade.dyn"), 
            GeometryComplexity.OrganicShapes => await LoadTemplate("organic_geometry.dyn"),
            _ => await LoadTemplate("basic_geometry.dyn")
        };
        
        // Replace parameters in template
        var script = scriptTemplate
            .Replace("{{BuildingWidth}}", parameters.BuildingWidth.ToString())
            .Replace("{{BuildingLength}}", parameters.BuildingLength.ToString())
            .Replace("{{FloorHeight}}", parameters.FloorHeight.ToString())
            .Replace("{{CorrelationId}}", correlationId);
        
        var scriptPath = Path.Combine(_dynamoScriptsPath, $"generated_{correlationId}.dyn");
        await File.WriteAllTextAsync(scriptPath, script);
        
        return scriptPath;
    }
}

public enum GeometryComplexity
{
    Simple,        // Direct Revit API
    CurvedWalls,   // Dynamo required
    ComplexFacade, // Dynamo + custom nodes
    OrganicShapes  // Advanced Dynamo
}
```

Enhanced Element Creation with Dynamo Support:
```csharp
public class LayoutExecutor
{
    private readonly Document document;
    private readonly ILogger logger;
    private readonly DynamoGeometryEngine dynamoEngine;
    
    public LayoutExecutor(Document document, DynamoGeometryEngine dynamoEngine)
    {
        this.document = document;
        this.logger = Log.ForContext<LayoutExecutor>();
        this.dynamoEngine = dynamoEngine;
    }
    
    public async Task CreateLayoutAsync(LayoutResult layout, string correlationId)
    {
        using (var transaction = new Transaction(document, "Create AI Layout"))
        {
            transaction.Start();
            
            try
            {
                // Analyze geometry complexity
                var complexityAnalysis = AnalyzeGeometryComplexity(layout);
                
                if (complexityAnalysis.RequiresDynamo)
                {
                    _logger.LogInformation("Complex geometry detected, using Dynamo",
                        correlation_id: correlationId,
                        complexity: complexityAnalysis.ComplexityLevel.ToString());
                    
                    // Use Dynamo for complex geometry
                    var geometryParams = CreateGeometryParameters(layout);
                    var geometryResult = await dynamoEngine.ExecuteComplexGeometry(geometryParams, correlationId);
                    
                    // Apply Dynamo-generated elements
                    ApplyDynamoElements(geometryResult.Elements);
                }
                else
                {
                    // Use direct Revit API for simple geometry
                    _logger.LogInformation("Simple geometry, using direct Revit API", correlation_id: correlationId);
                    await CreateElementsWithRevitAPI(layout);
                }
                
                // Create rooms and spaces
                CreateRooms(layout.Rooms);
                
                // Apply AI-generated parameters and metadata
                ApplyLayoutMetadata(layout, correlationId);
                
                // Validate geometric relationships
                ValidateElementRelationships();
                
                transaction.Commit();
                
                _logger.LogInformation("Layout created successfully",
                    correlation_id: correlationId,
                    wall_count: layout.Walls?.Count ?? 0,
                    door_count: layout.Doors?.Count ?? 0,
                    used_dynamo: complexityAnalysis.RequiresDynamo);
            }
            catch (Exception ex)
            {
                transaction.RollBack();
                _logger.LogError(ex, "Failed to create layout", correlation_id: correlationId);
                throw;
            }
        }
    }
    
    private ComplexityAnalysis AnalyzeGeometryComplexity(LayoutResult layout)
    {
        var analysis = new ComplexityAnalysis();
        
        // Check for curved walls
        var curvedWalls = layout.Walls?.Where(w => w.IsCurved).Count() ?? 0;
        if (curvedWalls > 0)
        {
            analysis.ComplexityLevel = GeometryComplexity.CurvedWalls;
            analysis.RequiresDynamo = true;
        }
        
        // Check for complex facade patterns
        var complexWindows = layout.Windows?.Where(w => w.IsParametric).Count() ?? 0;
        if (complexWindows > 5)
        {
            analysis.ComplexityLevel = GeometryComplexity.ComplexFacade;
            analysis.RequiresDynamo = true;
        }
        
        // Check for organic or complex shapes
        if (layout.CustomGeometry?.Any() == true)
        {
            analysis.ComplexityLevel = GeometryComplexity.OrganicShapes;
            analysis.RequiresDynamo = true;
        }
        
        analysis.ReasonForComplexity = GenerateComplexityReason(analysis);
        
        return analysis;
    }
}

public class ComplexityAnalysis
{
    public GeometryComplexity ComplexityLevel { get; set; } = GeometryComplexity.Simple;
    public bool RequiresDynamo { get; set; } = false;
    public string ReasonForComplexity { get; set; } = "";
    public List<string> DynamoNodes { get; set; } = new();
}
```
                logger.Information("Layout successfully created", 
                    wall_count = layout.Walls.Count,
                    door_count = layout.Doors.Count,
                    room_count = layout.Rooms.Count);
            }
            catch (Exception ex)
            {
                transaction.RollBack();
                logger.Error(ex, "Failed to create layout");
                throw;
            }
        }
    }
    
    private List<ElementId> CreateWalls(List<WallDefinition> wallDefinitions)
    {
        var wallIds = new List<ElementId>();
        var wallType = GetDefaultWallType();
        var level = GetActiveLevel();
        
        foreach (var wallDef in wallDefinitions)
        {
            try
            {
                // Convert AI coordinates to Revit units
                var startPoint = new XYZ(
                    UnitUtils.ConvertToInternalUnits(wallDef.Start.X, UnitTypeId.Millimeters),
                    UnitUtils.ConvertToInternalUnits(wallDef.Start.Y, UnitTypeId.Millimeters),
                    0);
                var endPoint = new XYZ(
                    UnitUtils.ConvertToInternalUnits(wallDef.End.X, UnitTypeId.Millimeters),
                    UnitUtils.ConvertToInternalUnits(wallDef.End.Y, UnitTypeId.Millimeters),
                    0);
                
                var line = Line.CreateBound(startPoint, endPoint);
                var wall = Wall.Create(document, line, wallType.Id, level.Id, 
                                     UnitUtils.ConvertToInternalUnits(wallDef.Height, UnitTypeId.Millimeters), 
                                     0, false, false);
                
                // Set AI-generated parameters
                if (wallDef.Parameters != null)
                {
                    SetElementParameters(wall, wallDef.Parameters);
                }
                
                wallIds.Add(wall.Id);
                logger.Debug("Wall created", wall_id = wall.Id.IntegerValue);
            }
            catch (Exception ex)
            {
                logger.Warning(ex, "Failed to create wall", wall_definition = wallDef);
                throw;
            }
        }
        
        return wallIds;
    }
    
    private void CreateDoors(List<DoorDefinition> doorDefinitions, List<ElementId> wallIds)
    {
        var doorFamilySymbol = GetDoorFamilySymbol("Standard Door");
        
        foreach (var doorDef in doorDefinitions)
        {
            try
            {
                var hostWall = document.GetElement(wallIds[doorDef.WallIndex]) as Wall;
                if (hostWall == null)
                {
                    logger.Warning("Invalid wall index for door", wall_index = doorDef.WallIndex);
                    continue;
                }
                
                // Calculate door position on wall
                var wallCurve = (hostWall.Location as LocationCurve).Curve;
                var doorPoint = wallCurve.Evaluate(doorDef.PositionRatio, false);
                
                // Create door instance
                var door = document.Create.NewFamilyInstance(
                    doorPoint, doorFamilySymbol, hostWall, 
                    document.ActiveView.GenLevel, StructuralType.NonStructural);
                
                // Set door width from AI
                var widthParam = door.LookupParameter("Width");
                if (widthParam != null && !widthParam.IsReadOnly)
                {
                    var widthInFeet = UnitUtils.ConvertToInternalUnits(doorDef.Width, UnitTypeId.Millimeters);
                    widthParam.Set(widthInFeet);
                }
                
                logger.Debug("Door created", door_id = door.Id.IntegerValue, wall_id = hostWall.Id.IntegerValue);
            }
            catch (Exception ex)
            {
                logger.Warning(ex, "Failed to create door", door_definition = doorDef);
            }
        }
    }
}
```

Family Management System:
```csharp
public class FamilyManager
{
    private readonly Document document;
    private readonly Dictionary<string, FamilySymbol> familyCache;
    
    public FamilyManager(Document document)
    {
        this.document = document;
        this.familyCache = new Dictionary<string, FamilySymbol>();
        CacheFamilySymbols();
    }
    
    public FamilySymbol GetFamilySymbol(string familyName, string typeName = null)
    {
        var key = $"{familyName}_{typeName ?? "Default"}";
        
        if (familyCache.TryGetValue(key, out var cachedSymbol))
        {
            return cachedSymbol;
        }
        
        // Search for family in document
        var familySymbol = new FilteredElementCollector(document)
            .OfClass(typeof(FamilySymbol))
            .Cast<FamilySymbol>()
            .FirstOrDefault(fs => fs.FamilyName.Equals(familyName, StringComparison.OrdinalIgnoreCase) &&
                                 (typeName == null || fs.Name.Equals(typeName, StringComparison.OrdinalIgnoreCase)));
        
        if (familySymbol == null)
        {
            // Try to load family from library
            familySymbol = LoadFamilyFromLibrary(familyName, typeName);
        }
        
        if (familySymbol != null && !familySymbol.IsActive)
        {
            familySymbol.Activate();
        }
        
        familyCache[key] = familySymbol;
        return familySymbol;
    }
    
    private FamilySymbol LoadFamilyFromLibrary(string familyName, string typeName)
    {
        try
        {
            var familyPath = GetFamilyPath(familyName);
            if (string.IsNullOrEmpty(familyPath) || !File.Exists(familyPath))
            {
                logger.Warning("Family file not found", family_name = familyName);
                return null;
            }
            
            Family family;
            if (document.LoadFamily(familyPath, out family))
            {
                var symbolIds = family.GetFamilySymbolIds();
                foreach (var symbolId in symbolIds)
                {
                    var symbol = document.GetElement(symbolId) as FamilySymbol;
                    if (typeName == null || symbol.Name.Equals(typeName, StringComparison.OrdinalIgnoreCase))
                    {
                        return symbol;
                    }
                }
            }
        }
        catch (Exception ex)
        {
            logger.Warning(ex, "Failed to load family", family_name = familyName);
        }
        
        return null;
    }
    
    public void ConfigureFamilyForAI(FamilySymbol familySymbol, Dictionary<string, object> aiParameters)
    {
        """Configure family parameters based on AI requirements"""
        
        foreach (var paramPair in aiParameters)
        {
            var parameter = familySymbol.LookupParameter(paramPair.Key);
            if (parameter != null && !parameter.IsReadOnly)
            {
                SetParameterValue(parameter, paramPair.Value);
            }
        }
    }
}
```

Dynamo Integration as Script Engine:
```csharp
public class DynamoScriptEngine
{
    private readonly ILogger logger;
    private DynamoModel dynamoModel;
    
    public DynamoScriptEngine()
    {
        this.logger = Log.ForContext<DynamoScriptEngine>();
        InitializeDynamo();
    }
    
    public GeometryResult ExecuteGeometricOperation(GeometryScript script, GeometryParameters parameters)
    {
        """Execute complex geometric operations using Dynamo as script engine"""
        
        try
        {
            logger.Information("Executing Dynamo geometric operation", script_type = script.Type);
            
            // Generate Dynamo script from AI parameters
            var dynamoScript = GenerateDynamoScript(script, parameters);
            
            // Execute script in Dynamo engine
            var workspace = WorkspaceModel.FromXmlDocument(dynamoScript);
            dynamoModel.OpenWorkspace(workspace);
            
            // Run and get results
            var runner = new DynamoRunner(dynamoModel);
            var results = runner.Execute();
            
            // Convert Dynamo geometry to Revit geometry
            var revitGeometry = ConvertDynamoToRevitGeometry(results);
            
            return new GeometryResult
            {
                Geometry = revitGeometry,
                Success = true,
                ExecutionTime = runner.ExecutionTime
            };
        }
        catch (Exception ex)
        {
            logger.Error(ex, "Dynamo script execution failed");
            return new GeometryResult { Success = false, Error = ex.Message };
        }
    }
    
    private XmlDocument GenerateDynamoScript(GeometryScript script, GeometryParameters parameters)
    {
        """Generate Dynamo script XML from AI geometric requirements"""
        
        var scriptBuilder = new DynamoScriptBuilder();
        
        switch (script.Type)
        {
            case GeometryScriptType.ComplexCurtainWall:
                return scriptBuilder.CreateCurtainWallScript(parameters);
                
            case GeometryScriptType.ParametricStair:
                return scriptBuilder.CreateStairScript(parameters);
                
            case GeometryScriptType.AdaptiveRoof:
                return scriptBuilder.CreateRoofScript(parameters);
                
            case GeometryScriptType.CustomMassing:
                return scriptBuilder.CreateMassingScript(parameters);
                
            default:
                throw new NotSupportedException($"Script type {script.Type} not supported");
        }
    }
    
    public void CreateAdaptiveFamily(AdaptiveFamilyDefinition definition)
    {
        """Create adaptive families using Dynamo for complex AI-generated geometries"""
        
        var scriptTemplate = @"
        // Dynamo script for adaptive family creation
        import('ProtoGeometry.dll');
        import('DSCoreNodes.dll');
        
        // Create adaptive points from AI coordinates
        points = List.Create(
            {0}, {1}, {2}, {3}  // AI-generated points
        );
        
        // Generate adaptive surface
        surface = NurbsSurface.ByPoints(points);
        
        // Apply AI parameters
        surface = surface.Scale({4}); // AI scale factor
        
        return surface;
        ";
        
        var formattedScript = string.Format(scriptTemplate,
            definition.AdaptivePoints[0],
            definition.AdaptivePoints[1], 
            definition.AdaptivePoints[2],
            definition.AdaptivePoints[3],
            definition.ScaleFactor);
        
        ExecuteScript(formattedScript);
    }
}
```

Geometric Validation and Constraints:
```csharp
public class GeometricValidator
{
    public ValidationResult ValidateLayout(LayoutResult layout)
    {
        var errors = new List<string>();
        
        // Validate wall intersections
        var wallIntersectionErrors = ValidateWallIntersections(layout.Walls);
        errors.AddRange(wallIntersectionErrors);
        
        // Validate room areas and adjacencies
        var roomErrors = ValidateRoomGeometry(layout.Rooms);
        errors.AddRange(roomErrors);
        
        // Validate door and window placement
        var openingErrors = ValidateOpenings(layout.Doors, layout.Windows, layout.Walls);
        errors.AddRange(openingErrors);
        
        // Validate accessibility requirements
        var accessibilityErrors = ValidateAccessibility(layout);
        errors.AddRange(accessibilityErrors);
        
        return new ValidationResult
        {
            IsValid = errors.Count == 0,
            Errors = errors,
            Confidence = CalculateGeometricConfidence(layout)
        };
    }
    
    private List<string> ValidateWallIntersections(List<WallDefinition> walls)
    {
        var errors = new List<string>();
        
        for (int i = 0; i < walls.Count; i++)
        {
            for (int j = i + 1; j < walls.Count; j++)
            {
                var wall1 = walls[i];
                var wall2 = walls[j];
                
                // Check for overlapping walls
                if (WallsOverlap(wall1, wall2))
                {
                    errors.Add($"Walls {i} and {j} overlap");
                }
                
                // Check for T-junctions and proper connections
                if (!WallsProperlyConnected(wall1, wall2))
                {
                    var intersection = GetWallIntersection(wall1, wall2);
                    if (intersection.HasValue && !IsValidIntersection(intersection.Value))
                    {
                        errors.Add($"Invalid wall connection between walls {i} and {j}");
                    }
                }
            }
        }
        
        return errors;
    }
    
    private List<string> ValidateRoomGeometry(List<RoomDefinition> rooms)
    {
        var errors = new List<string>();
        
        foreach (var room in rooms)
        {
            // Check minimum room area
            if (room.Area < 5.0) // 5 m² minimum
            {
                errors.Add($"Room '{room.Name}' area ({room.Area:F1} m²) below minimum 5 m²");
            }
            
            // Check room proportions (not too narrow)
            var aspectRatio = Math.Max(room.Width, room.Height) / Math.Min(room.Width, room.Height);
            if (aspectRatio > 4.0)
            {
                errors.Add($"Room '{room.Name}' has extreme proportions (aspect ratio: {aspectRatio:F1})");
            }
            
            // Check for room overlaps
            foreach (var otherRoom in rooms.Where(r => r != room))
            {
                if (RoomsOverlap(room, otherRoom))
                {
                    errors.Add($"Rooms '{room.Name}' and '{otherRoom.Name}' overlap");
                }
            }
        }
        
        return errors;
    }
    
    private bool IsValidIntersection(XYZ intersection)
    {
        // Implement geometric validation logic
        // Check if intersection point is within tolerance
        // Validate that intersection creates proper joints
        return true; // Simplified for example
    }
}
```

BIM Model Structure and Relationships:
```csharp
public class BIMModelBuilder
{
    public void EstablishElementRelationships(LayoutResult layout)
    {
        """Create proper BIM relationships between AI-generated elements"""
        
        // Create spatial hierarchy
        EstablishSpatialHierarchy(layout.Rooms);
        
        // Link hosted elements to hosts
        LinkDoorsToWalls(layout.Doors, layout.Walls);
        LinkWindowsToWalls(layout.Windows, layout.Walls);
        
        // Create room boundaries
        CreateRoomBoundaries(layout.Rooms, layout.Walls);
        
        // Establish MEP connections (if AI generated)
        if (layout.MEPSystems != null)
        {
            EstablishMEPConnections(layout.MEPSystems);
        }
    }
    
    private void EstablishSpatialHierarchy(List<RoomDefinition> rooms)
    {
        foreach (var room in rooms)
        {
            // Create room element if it doesn't exist
            var roomElement = CreateOrUpdateRoom(room);
            
            // Set room properties from AI
            SetRoomProperties(roomElement, room.AIProperties);
            
            // Establish department/zone relationships
            if (!string.IsNullOrEmpty(room.Department))
            {
                CreateDepartmentRelationship(roomElement, room.Department);
            }
        }
    }
}
```

Always validate geometry, establish proper BIM relationships, and use Dynamo for complex operations.