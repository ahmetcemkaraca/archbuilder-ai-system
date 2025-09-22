using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.Commands
{
    /// <summary>
    /// Command for performing geometric operations in Revit with AI-generated layouts.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public class GeometricOperationsCommand : BaseRevitCommand
    {
        protected override Result ExecuteCommand(ExternalCommandData commandData, string correlationId)
        {
            var doc = commandData.Application.ActiveUIDocument.Document;
            var uidoc = commandData.Application.ActiveUIDocument;

            ValidateDocument(doc, correlationId);

            try
            {
                // Get geometric operation parameters
                var operationParameters = GetGeometricOperationParameters(uidoc, correlationId);
                if (operationParameters == null)
                {
                    Logger.LogInformation("Geometric operation cancelled by user", correlationId);
                    return Result.Cancelled;
                }

                // Execute geometric operations in transaction
                var success = ExecuteInTransaction(doc, "Execute AI Geometric Operations", transaction =>
                {
                    var results = ExecuteGeometricOperations(doc, operationParameters, correlationId);
                    
                    if (results != null && results.Count > 0)
                    {
                        Logger.LogInformation("Geometric operations completed successfully. Created {Count} elements", 
                            results.Count, correlationId);
                        ShowInfo("Operations Complete", $"Geometric operations completed. Created {results.Count} elements.");
                    }
                    else
                    {
                        throw new RevitApiException("Failed to execute geometric operations - no results");
                    }

                }, correlationId);

                return success ? Result.Succeeded : Result.Failed;
            }
            catch (OperationCanceledException)
            {
                Logger.LogInformation("Geometric operations cancelled", correlationId);
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to execute geometric operations", correlationId);
                ShowError("Geometric Operations Failed", $"Failed to execute operations: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Gets geometric operation parameters from user input or AI data.
        /// </summary>
        /// <param name="uidoc">The UI document.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>Geometric operation parameters or null if cancelled.</returns>
        private GeometricOperationParameters GetGeometricOperationParameters(UIDocument uidoc, string correlationId)
        {
            try
            {
                // For now, implement simple geometric operations
                // In future, this will integrate with AI-generated layout data
                
                Logger.LogDebug("Getting geometric operation parameters", correlationId);
                
                // For demonstration, create a simple rectangular layout
                var parameters = new GeometricOperationParameters
                {
                    OperationType = GeometricOperationType.CreateRectangularLayout,
                    BasePoint = new XYZ(0, 0, 0),
                    Width = RevitHelpers.MillimetersToFeet(6000), // 6m
                    Height = RevitHelpers.MillimetersToFeet(4000), // 4m
                    WallHeight = RevitHelpers.MillimetersToFeet(3000), // 3m
                    Level = GetActiveLevel(uidoc.Document),
                    IncludeDoors = true,
                    IncludeWindows = true,
                    DoorWidth = RevitHelpers.MillimetersToFeet(900), // 900mm
                    WindowWidth = RevitHelpers.MillimetersToFeet(1200), // 1200mm
                    WindowHeight = RevitHelpers.MillimetersToFeet(1400), // 1400mm
                    WindowSillHeight = RevitHelpers.MillimetersToFeet(900), // 900mm
                    IsAIGenerated = false, // Set to true when called from AI workflow
                    CorrelationId = correlationId
                };

                Logger.LogDebug("Geometric operation parameters prepared", correlationId);
                return parameters;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error getting geometric operation parameters", correlationId);
                throw new RevitApiException("Failed to get geometric operation parameters", ex);
            }
        }

        /// <summary>
        /// Executes geometric operations based on the provided parameters.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The geometric operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created elements.</returns>
        private List<Element> ExecuteGeometricOperations(Document doc, GeometricOperationParameters parameters, string correlationId)
        {
            try
            {
                var createdElements = new List<Element>();

                switch (parameters.OperationType)
                {
                    case GeometricOperationType.CreateRectangularLayout:
                        createdElements.AddRange(CreateRectangularLayout(doc, parameters, correlationId));
                        break;

                    case GeometricOperationType.CreateLShapedLayout:
                        createdElements.AddRange(CreateLShapedLayout(doc, parameters, correlationId));
                        break;

                    case GeometricOperationType.CreateCustomPolygon:
                        createdElements.AddRange(CreateCustomPolygonLayout(doc, parameters, correlationId));
                        break;

                    case GeometricOperationType.ArrayElements:
                        createdElements.AddRange(CreateElementArray(doc, parameters, correlationId));
                        break;

                    default:
                        throw new RevitApiException($"Unsupported geometric operation type: {parameters.OperationType}");
                }

                // Add rooms if specified
                if (parameters.CreateRooms)
                {
                    var rooms = CreateRoomsInLayout(doc, parameters, createdElements, correlationId);
                    createdElements.AddRange(rooms);
                }

                Logger.LogDebug("Geometric operations completed. Created {Count} elements", createdElements.Count, correlationId);
                return createdElements;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error executing geometric operations", correlationId);
                throw new RevitApiException("Failed to execute geometric operations", ex);
            }
        }

        /// <summary>
        /// Creates a rectangular layout with walls, doors, and windows.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created elements.</returns>
        private List<Element> CreateRectangularLayout(Document doc, GeometricOperationParameters parameters, string correlationId)
        {
            var elements = new List<Element>();

            try
            {
                // Define the rectangle corners
                var p1 = parameters.BasePoint;
                var p2 = new XYZ(parameters.BasePoint.X + parameters.Width, parameters.BasePoint.Y, parameters.BasePoint.Z);
                var p3 = new XYZ(parameters.BasePoint.X + parameters.Width, parameters.BasePoint.Y + parameters.Height, parameters.BasePoint.Z);
                var p4 = new XYZ(parameters.BasePoint.X, parameters.BasePoint.Y + parameters.Height, parameters.BasePoint.Z);

                var wallType = RevitHelpers.GetDefaultWallType(doc);
                
                // Create walls
                var wall1 = CreateWallBetweenPoints(doc, p1, p2, wallType, parameters.Level, parameters.WallHeight);
                var wall2 = CreateWallBetweenPoints(doc, p2, p3, wallType, parameters.Level, parameters.WallHeight);
                var wall3 = CreateWallBetweenPoints(doc, p3, p4, wallType, parameters.Level, parameters.WallHeight);
                var wall4 = CreateWallBetweenPoints(doc, p4, p1, wallType, parameters.Level, parameters.WallHeight);

                elements.AddRange(new[] { wall1, wall2, wall3, wall4 });

                // Add door to the first wall (bottom wall)
                if (parameters.IncludeDoors)
                {
                    var doorLocation = new XYZ(p1.X + parameters.Width / 3, p1.Y, p1.Z);
                    var door = CreateDoorInWall(doc, wall1, doorLocation, parameters, correlationId);
                    if (door != null) elements.Add(door);
                }

                // Add windows to walls 2 and 4 (side walls)
                if (parameters.IncludeWindows)
                {
                    // Window in right wall
                    var window1Location = new XYZ(p2.X, p2.Y + parameters.Height / 2, p2.Z);
                    var window1 = CreateWindowInWall(doc, wall2, window1Location, parameters, correlationId);
                    if (window1 != null) elements.Add(window1);

                    // Window in left wall
                    var window2Location = new XYZ(p4.X, p4.Y - parameters.Height / 2, p4.Z);
                    var window2 = CreateWindowInWall(doc, wall4, window2Location, parameters, correlationId);
                    if (window2 != null) elements.Add(window2);
                }

                Logger.LogDebug("Created rectangular layout with {ElementCount} elements", elements.Count, correlationId);
                return elements;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error creating rectangular layout", correlationId);
                throw new RevitApiException("Failed to create rectangular layout", ex);
            }
        }

        /// <summary>
        /// Creates an L-shaped layout.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created elements.</returns>
        private List<Element> CreateLShapedLayout(Document doc, GeometricOperationParameters parameters, string correlationId)
        {
            var elements = new List<Element>();

            try
            {
                // Create L-shaped layout using two rectangles
                var wallType = RevitHelpers.GetDefaultWallType(doc);
                
                // Main rectangle
                var width1 = parameters.Width * 0.7;
                var height1 = parameters.Height;
                
                // Side rectangle
                var width2 = parameters.Width * 0.3;
                var height2 = parameters.Height * 0.6;

                // Points for main rectangle
                var mainP1 = parameters.BasePoint;
                var mainP2 = new XYZ(mainP1.X + width1, mainP1.Y, mainP1.Z);
                var mainP3 = new XYZ(mainP1.X + width1, mainP1.Y + height1, mainP1.Z);
                var mainP4 = new XYZ(mainP1.X, mainP1.Y + height1, mainP1.Z);

                // Points for side rectangle
                var sideP1 = new XYZ(mainP2.X, mainP2.Y, mainP2.Z);
                var sideP2 = new XYZ(sideP1.X + width2, sideP1.Y, sideP1.Z);
                var sideP3 = new XYZ(sideP2.X, sideP2.Y + height2, sideP2.Z);
                var sideP4 = new XYZ(sideP1.X, sideP1.Y + height2, sideP1.Z);

                // Create walls for main rectangle
                elements.Add(CreateWallBetweenPoints(doc, mainP1, mainP2, wallType, parameters.Level, parameters.WallHeight));
                elements.Add(CreateWallBetweenPoints(doc, mainP2, sideP4, wallType, parameters.Level, parameters.WallHeight)); // Partial wall
                elements.Add(CreateWallBetweenPoints(doc, sideP4, sideP3, wallType, parameters.Level, parameters.WallHeight));
                elements.Add(CreateWallBetweenPoints(doc, sideP3, sideP2, wallType, parameters.Level, parameters.WallHeight));
                elements.Add(CreateWallBetweenPoints(doc, sideP2, mainP3, wallType, parameters.Level, parameters.WallHeight)); // Connection
                elements.Add(CreateWallBetweenPoints(doc, mainP3, mainP4, wallType, parameters.Level, parameters.WallHeight));
                elements.Add(CreateWallBetweenPoints(doc, mainP4, mainP1, wallType, parameters.Level, parameters.WallHeight));

                Logger.LogDebug("Created L-shaped layout with {ElementCount} elements", elements.Count, correlationId);
                return elements;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error creating L-shaped layout", correlationId);
                throw new RevitApiException("Failed to create L-shaped layout", ex);
            }
        }

        /// <summary>
        /// Creates a custom polygon layout.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created elements.</returns>
        private List<Element> CreateCustomPolygonLayout(Document doc, GeometricOperationParameters parameters, string correlationId)
        {
            var elements = new List<Element>();

            try
            {
                // For demonstration, create a hexagonal layout
                var centerPoint = new XYZ(parameters.BasePoint.X + parameters.Width / 2, 
                                          parameters.BasePoint.Y + parameters.Height / 2, 
                                          parameters.BasePoint.Z);
                var radius = Math.Min(parameters.Width, parameters.Height) / 2 * 0.8;
                
                var points = new List<XYZ>();
                var angleStep = 2 * Math.PI / 6; // Hexagon

                for (int i = 0; i < 6; i++)
                {
                    var angle = i * angleStep;
                    var x = centerPoint.X + radius * Math.Cos(angle);
                    var y = centerPoint.Y + radius * Math.Sin(angle);
                    points.Add(new XYZ(x, y, centerPoint.Z));
                }

                var wallType = RevitHelpers.GetDefaultWallType(doc);

                // Create walls between consecutive points
                for (int i = 0; i < points.Count; i++)
                {
                    var startPoint = points[i];
                    var endPoint = points[(i + 1) % points.Count];
                    var wall = CreateWallBetweenPoints(doc, startPoint, endPoint, wallType, parameters.Level, parameters.WallHeight);
                    elements.Add(wall);
                }

                Logger.LogDebug("Created custom polygon layout with {ElementCount} elements", elements.Count, correlationId);
                return elements;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error creating custom polygon layout", correlationId);
                throw new RevitApiException("Failed to create custom polygon layout", ex);
            }
        }

        /// <summary>
        /// Creates an array of elements.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created elements.</returns>
        private List<Element> CreateElementArray(Document doc, GeometricOperationParameters parameters, string correlationId)
        {
            var elements = new List<Element>();

            try
            {
                // Create a simple array of columns or structural elements
                var spacing = parameters.Width / 5; // 5 columns across
                var wallType = RevitHelpers.GetDefaultWallType(doc);

                for (int i = 0; i < 5; i++)
                {
                    var columnLocation = new XYZ(parameters.BasePoint.X + i * spacing, 
                                                 parameters.BasePoint.Y + parameters.Height / 2, 
                                                 parameters.BasePoint.Z);
                    
                    // Create small wall as column placeholder
                    var columnEnd = new XYZ(columnLocation.X, columnLocation.Y + RevitHelpers.MillimetersToFeet(200), columnLocation.Z);
                    var column = CreateWallBetweenPoints(doc, columnLocation, columnEnd, wallType, parameters.Level, parameters.WallHeight);
                    elements.Add(column);
                }

                Logger.LogDebug("Created element array with {ElementCount} elements", elements.Count, correlationId);
                return elements;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error creating element array", correlationId);
                throw new RevitApiException("Failed to create element array", ex);
            }
        }

        /// <summary>
        /// Creates rooms within the layout.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="walls">The walls that define the layout.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created rooms.</returns>
        private List<Element> CreateRoomsInLayout(Document doc, GeometricOperationParameters parameters, List<Element> walls, string correlationId)
        {
            var rooms = new List<Element>();

            try
            {
                // Create a room in the center of the layout
                var roomLocation = new XYZ(parameters.BasePoint.X + parameters.Width / 2,
                                          parameters.BasePoint.Y + parameters.Height / 2,
                                          parameters.BasePoint.Z);

                var room = doc.Create.NewRoom(parameters.Level, new UV(roomLocation.X, roomLocation.Y));
                if (room != null)
                {
                    room.Name = "AI Generated Room";
                    room.Number = "001";
                    rooms.Add(room);
                    
                    Logger.LogDebug("Created room in layout", correlationId);
                }

                return rooms;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error creating rooms in layout", correlationId);
                return rooms; // Return empty list on error
            }
        }

        /// <summary>
        /// Creates a wall between two points.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="startPoint">The start point.</param>
        /// <param name="endPoint">The end point.</param>
        /// <param name="wallType">The wall type.</param>
        /// <param name="level">The level.</param>
        /// <param name="height">The wall height.</param>
        /// <returns>The created wall.</returns>
        private Wall CreateWallBetweenPoints(Document doc, XYZ startPoint, XYZ endPoint, WallType wallType, Level level, double height)
        {
            var line = Line.CreateBound(startPoint, endPoint);
            var wall = Wall.Create(doc, line, wallType.Id, level.Id, height, 0, false, false);
            return wall;
        }

        /// <summary>
        /// Creates a door in the specified wall.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="wall">The host wall.</param>
        /// <param name="location">The door location.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The created door.</returns>
        private FamilyInstance CreateDoorInWall(Document doc, Wall wall, XYZ location, GeometricOperationParameters parameters, string correlationId)
        {
            try
            {
                var doorSymbol = RevitHelpers.GetDoorFamilySymbol(doc);
                if (!doorSymbol.IsActive) doorSymbol.Activate();

                var door = doc.Create.NewFamilyInstance(location, doorSymbol, wall, parameters.Level, StructuralType.NonStructural);
                
                // Set door width if specified
                if (parameters.DoorWidth > 0)
                {
                    var widthParam = door.LookupParameter("Width");
                    if (widthParam != null && !widthParam.IsReadOnly)
                    {
                        widthParam.Set(parameters.DoorWidth);
                    }
                }

                return door;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to create door in wall", correlationId);
                return null;
            }
        }

        /// <summary>
        /// Creates a window in the specified wall.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="wall">The host wall.</param>
        /// <param name="location">The window location.</param>
        /// <param name="parameters">The operation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The created window.</returns>
        private FamilyInstance CreateWindowInWall(Document doc, Wall wall, XYZ location, GeometricOperationParameters parameters, string correlationId)
        {
            try
            {
                var windowSymbol = RevitHelpers.GetWindowFamilySymbol(doc);
                if (!windowSymbol.IsActive) windowSymbol.Activate();

                var window = doc.Create.NewFamilyInstance(location, windowSymbol, wall, parameters.Level, StructuralType.NonStructural);
                
                // Set window dimensions if specified
                if (parameters.WindowWidth > 0)
                {
                    var widthParam = window.LookupParameter("Width");
                    if (widthParam != null && !widthParam.IsReadOnly)
                    {
                        widthParam.Set(parameters.WindowWidth);
                    }
                }

                if (parameters.WindowHeight > 0)
                {
                    var heightParam = window.LookupParameter("Height");
                    if (heightParam != null && !heightParam.IsReadOnly)
                    {
                        heightParam.Set(parameters.WindowHeight);
                    }
                }

                if (parameters.WindowSillHeight > 0)
                {
                    var sillHeightParam = window.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM);
                    if (sillHeightParam != null && !sillHeightParam.IsReadOnly)
                    {
                        sillHeightParam.Set(parameters.WindowSillHeight);
                    }
                }

                return window;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to create window in wall", correlationId);
                return null;
            }
        }

        /// <summary>
        /// Gets the active level from the document.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <returns>The active level.</returns>
        private Level GetActiveLevel(Document doc)
        {
            var levels = new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .OfType<Level>()
                .OrderBy(l => l.Elevation)
                .ToList();

            return levels.FirstOrDefault();
        }
    }

    /// <summary>
    /// Types of geometric operations.
    /// </summary>
    public enum GeometricOperationType
    {
        CreateRectangularLayout,
        CreateLShapedLayout,
        CreateCustomPolygon,
        ArrayElements
    }

    /// <summary>
    /// Parameters for geometric operations.
    /// </summary>
    public class GeometricOperationParameters
    {
        /// <summary>
        /// Gets or sets the type of geometric operation.
        /// </summary>
        public GeometricOperationType OperationType { get; set; }

        /// <summary>
        /// Gets or sets the base point for the operation.
        /// </summary>
        public XYZ BasePoint { get; set; }

        /// <summary>
        /// Gets or sets the width of the layout.
        /// </summary>
        public double Width { get; set; }

        /// <summary>
        /// Gets or sets the height of the layout.
        /// </summary>
        public double Height { get; set; }

        /// <summary>
        /// Gets or sets the wall height.
        /// </summary>
        public double WallHeight { get; set; }

        /// <summary>
        /// Gets or sets the level for the operation.
        /// </summary>
        public Level Level { get; set; }

        /// <summary>
        /// Gets or sets whether to include doors.
        /// </summary>
        public bool IncludeDoors { get; set; }

        /// <summary>
        /// Gets or sets whether to include windows.
        /// </summary>
        public bool IncludeWindows { get; set; }

        /// <summary>
        /// Gets or sets whether to create rooms.
        /// </summary>
        public bool CreateRooms { get; set; }

        /// <summary>
        /// Gets or sets the door width.
        /// </summary>
        public double DoorWidth { get; set; }

        /// <summary>
        /// Gets or sets the window width.
        /// </summary>
        public double WindowWidth { get; set; }

        /// <summary>
        /// Gets or sets the window height.
        /// </summary>
        public double WindowHeight { get; set; }

        /// <summary>
        /// Gets or sets the window sill height.
        /// </summary>
        public double WindowSillHeight { get; set; }

        /// <summary>
        /// Gets or sets whether this operation was AI-generated.
        /// </summary>
        public bool IsAIGenerated { get; set; }

        /// <summary>
        /// Gets or sets the correlation ID for tracking.
        /// </summary>
        public string CorrelationId { get; set; }
    }
}