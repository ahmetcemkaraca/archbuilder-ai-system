using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.Commands
{
    /// <summary>
    /// Command for creating rooms in Revit with AI-generated or user-specified parameters.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public class CreateRoomCommand : BaseRevitCommand
    {
        protected override Result ExecuteCommand(ExternalCommandData commandData, string correlationId)
        {
            var doc = commandData.Application.ActiveUIDocument.Document;
            var uidoc = commandData.Application.ActiveUIDocument;

            ValidateDocument(doc, correlationId);

            try
            {
                // Get room creation parameters
                var roomParameters = GetRoomCreationParameters(uidoc, correlationId);
                if (roomParameters == null)
                {
                    Logger.LogInformation("Room creation cancelled by user", correlationId);
                    return Result.Cancelled;
                }

                // Create room in transaction
                var success = ExecuteInTransaction(doc, "Create AI Room", transaction =>
                {
                    var room = CreateRoom(doc, roomParameters, correlationId);
                    
                    if (room != null)
                    {
                        Logger.LogInformation("Room created successfully with ID: {RoomId}, Name: {RoomName}", 
                            room.Id.IntegerValue, room.Name, correlationId);
                        ShowInfo("Room Created", $"Room '{roomParameters.RoomName}' created successfully.");
                    }
                    else
                    {
                        throw new RevitApiException("Failed to create room - null result");
                    }

                }, correlationId);

                return success ? Result.Succeeded : Result.Failed;
            }
            catch (OperationCanceledException)
            {
                Logger.LogInformation("Room creation cancelled", correlationId);
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to create room", correlationId);
                ShowError("Room Creation Failed", $"Failed to create room: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Gets room creation parameters from user input or AI data.
        /// </summary>
        /// <param name="uidoc">The UI document.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>Room creation parameters or null if cancelled.</returns>
        private RoomCreationParameters GetRoomCreationParameters(UIDocument uidoc, string correlationId)
        {
            try
            {
                // For now, implement point picking for room location
                // In future, this will integrate with AI-generated layout data
                
                Logger.LogDebug("Prompting user to select room location", correlationId);
                ShowInfo("Create Room", "Click in the enclosed space to create a room.");

                // Get room location
                var roomLocation = uidoc.Selection.PickPoint("Pick room location");
                RevitHelpers.ValidatePoint(roomLocation, "roomLocation");

                // Get the appropriate level for the room
                var level = GetLevelForPoint(uidoc.Document, roomLocation);
                if (level == null)
                {
                    throw new RevitApiException("Cannot determine level for room location");
                }

                // For now, use default room properties
                // In production, these would come from AI analysis or user input
                var parameters = new RoomCreationParameters
                {
                    Location = roomLocation,
                    Level = level,
                    RoomName = "Room", // Will be auto-numbered by Revit
                    RoomNumber = "", // Will be auto-numbered by Revit
                    Department = "General",
                    Comments = "",
                    Phase = GetDefaultPhase(uidoc.Document),
                    IsAIGenerated = false, // Set to true when called from AI workflow
                    CorrelationId = correlationId
                };

                Logger.LogDebug("Room creation parameters collected for level: {LevelName}", 
                    level.Name, correlationId);
                return parameters;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                Logger.LogDebug("User cancelled room creation", correlationId);
                return null;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error getting room creation parameters", correlationId);
                throw new RevitApiException("Failed to get room creation parameters", ex);
            }
        }

        /// <summary>
        /// Creates a room based on the provided parameters.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The room creation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The created room.</returns>
        private Room CreateRoom(Document doc, RoomCreationParameters parameters, string correlationId)
        {
            try
            {
                // Validate inputs
                if (parameters.Level == null)
                    throw new ArgumentNullException("Level in parameters");

                if (parameters.Location == null)
                    throw new ArgumentNullException("Location in parameters");

                if (parameters.Phase == null)
                    throw new ArgumentNullException("Phase in parameters");

                Logger.LogDebug("Creating room at point: {Point} on level: {Level}", 
                    parameters.Location, parameters.Level.Name, correlationId);

                // Check if the location is in an enclosed space
                if (!IsLocationEnclosed(doc, parameters.Location, parameters.Level, correlationId))
                {
                    Logger.LogWarning("Room location may not be in an enclosed space", correlationId);
                    // Continue with creation - Revit will handle unplaced rooms
                }

                // Create the room
                var room = doc.Create.NewRoom(parameters.Level, new UV(parameters.Location.X, parameters.Location.Y));

                if (room == null)
                {
                    Logger.LogError("Room creation returned null", correlationId);
                    throw new RevitApiException("Failed to create room instance");
                }

                // Set room properties
                SetRoomProperties(room, parameters, correlationId);

                // Verify room placement
                ValidateRoomPlacement(room, correlationId);

                Logger.LogDebug("Room created successfully: {RoomId}", room.Id.IntegerValue, correlationId);
                return room;
            }
            catch (Autodesk.Revit.Exceptions.ArgumentException ex)
            {
                Logger.LogError(ex, "Invalid arguments for room creation", correlationId);
                throw new RevitApiException("Invalid room creation parameters", "INVALID_ROOM_ARGS", ex);
            }
            catch (Autodesk.Revit.Exceptions.InvalidOperationException ex)
            {
                Logger.LogError(ex, "Invalid operation during room creation", correlationId);
                throw new RevitApiException("Room creation operation is invalid", "INVALID_ROOM_OPERATION", ex);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Unexpected error during room creation", correlationId);
                throw new RevitApiException("Unexpected error creating room", ex);
            }
        }

        /// <summary>
        /// Checks if the specified location is in an enclosed space.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="location">The location to check.</param>
        /// <param name="level">The level to check on.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>True if the location appears to be enclosed.</returns>
        private bool IsLocationEnclosed(Document doc, XYZ location, Level level, string correlationId)
        {
            try
            {
                // Perform basic ray-casting to check for enclosure
                // This is a simplified check - Revit will provide more accurate validation
                
                var directions = new[]
                {
                    XYZ.BasisX,
                    XYZ.BasisX.Negate(),
                    XYZ.BasisY,
                    XYZ.BasisY.Negate()
                };

                var intersectionCount = 0;

                foreach (var direction in directions)
                {
                    if (HasWallInDirection(doc, location, direction, level, correlationId))
                    {
                        intersectionCount++;
                    }
                }

                // Consider enclosed if walls found in most directions
                var isEnclosed = intersectionCount >= 3;
                
                Logger.LogDebug("Enclosure check: {IntersectionCount}/4 directions have walls, Enclosed: {IsEnclosed}", 
                    intersectionCount, isEnclosed, correlationId);
                
                return isEnclosed;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error checking room enclosure", correlationId);
                return true; // Assume enclosed if check fails
            }
        }

        /// <summary>
        /// Checks if there's a wall in the specified direction from the location.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="location">The starting location.</param>
        /// <param name="direction">The direction to check.</param>
        /// <param name="level">The level to check on.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>True if a wall is found in the direction.</returns>
        private bool HasWallInDirection(Document doc, XYZ location, XYZ direction, Level level, string correlationId)
        {
            try
            {
                // Create a ray from the location in the specified direction
                var rayLength = RevitHelpers.MillimetersToFeet(10000); // 10m search distance
                var endPoint = location + (direction * rayLength);
                
                // Create a line for intersection testing
                var searchLine = Line.CreateBound(location, endPoint);

                // Get walls on the same level
                var walls = new FilteredElementCollector(doc)
                    .OfClass(typeof(Wall))
                    .OfType<Wall>()
                    .Where(w => w.LevelId == level.Id);

                foreach (var wall in walls)
                {
                    var wallCurve = ((LocationCurve)wall.Location)?.Curve;
                    if (wallCurve != null)
                    {
                        var intersection = wallCurve.Intersect(searchLine);
                        if (intersection == SetComparisonResult.Overlap || intersection == SetComparisonResult.Subset)
                        {
                            return true;
                        }
                    }
                }

                return false;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error checking wall in direction", correlationId);
                return false;
            }
        }

        /// <summary>
        /// Sets properties on the created room.
        /// </summary>
        /// <param name="room">The room instance.</param>
        /// <param name="parameters">The room creation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void SetRoomProperties(Room room, RoomCreationParameters parameters, string correlationId)
        {
            try
            {
                // Set room name if provided
                if (!string.IsNullOrEmpty(parameters.RoomName) && parameters.RoomName != "Room")
                {
                    room.Name = parameters.RoomName;
                    Logger.LogDebug("Set room name to {RoomName}", parameters.RoomName, correlationId);
                }

                // Set room number if provided
                if (!string.IsNullOrEmpty(parameters.RoomNumber))
                {
                    room.Number = parameters.RoomNumber;
                    Logger.LogDebug("Set room number to {RoomNumber}", parameters.RoomNumber, correlationId);
                }

                // Set department if provided
                if (!string.IsNullOrEmpty(parameters.Department))
                {
                    var deptParam = room.get_Parameter(BuiltInParameter.ROOM_DEPARTMENT);
                    if (deptParam != null && !deptParam.IsReadOnly)
                    {
                        deptParam.Set(parameters.Department);
                        Logger.LogDebug("Set room department to {Department}", parameters.Department, correlationId);
                    }
                }

                // Set comments if provided
                if (!string.IsNullOrEmpty(parameters.Comments))
                {
                    var commentsParam = room.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                    if (commentsParam != null && !commentsParam.IsReadOnly)
                    {
                        commentsParam.Set(parameters.Comments);
                        Logger.LogDebug("Set room comments", correlationId);
                    }
                }

                // Set occupancy if provided
                if (!string.IsNullOrEmpty(parameters.Occupancy))
                {
                    var occupancyParam = room.get_Parameter(BuiltInParameter.ROOM_OCCUPANCY);
                    if (occupancyParam != null && !occupancyParam.IsReadOnly)
                    {
                        occupancyParam.Set(parameters.Occupancy);
                        Logger.LogDebug("Set room occupancy to {Occupancy}", parameters.Occupancy, correlationId);
                    }
                }

                // Set area per person if provided
                if (parameters.AreaPerPerson > 0)
                {
                    var areaParam = room.LookupParameter("Area per Person");
                    if (areaParam != null && !areaParam.IsReadOnly)
                    {
                        areaParam.Set(parameters.AreaPerPerson);
                        Logger.LogDebug("Set room area per person to {AreaPerPerson}", parameters.AreaPerPerson, correlationId);
                    }
                }

                // Mark room as AI-generated if applicable
                if (parameters.IsAIGenerated)
                {
                    var markParam = room.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
                    if (markParam != null && !markParam.IsReadOnly)
                    {
                        markParam.Set("AI-Generated");
                        Logger.LogDebug("Marked room as AI-generated", correlationId);
                    }
                }

                // Set finish information if provided
                SetRoomFinishes(room, parameters, correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to set some room properties", correlationId);
                // Continue execution - property setting is not critical
            }
        }

        /// <summary>
        /// Sets room finish information.
        /// </summary>
        /// <param name="room">The room instance.</param>
        /// <param name="parameters">The room creation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void SetRoomFinishes(Room room, RoomCreationParameters parameters, string correlationId)
        {
            try
            {
                // Set floor finish
                if (!string.IsNullOrEmpty(parameters.FloorFinish))
                {
                    var floorFinishParam = room.get_Parameter(BuiltInParameter.ROOM_FINISH_FLOOR);
                    if (floorFinishParam != null && !floorFinishParam.IsReadOnly)
                    {
                        floorFinishParam.Set(parameters.FloorFinish);
                        Logger.LogDebug("Set floor finish to {FloorFinish}", parameters.FloorFinish, correlationId);
                    }
                }

                // Set wall finish
                if (!string.IsNullOrEmpty(parameters.WallFinish))
                {
                    var wallFinishParam = room.get_Parameter(BuiltInParameter.ROOM_FINISH_WALL);
                    if (wallFinishParam != null && !wallFinishParam.IsReadOnly)
                    {
                        wallFinishParam.Set(parameters.WallFinish);
                        Logger.LogDebug("Set wall finish to {WallFinish}", parameters.WallFinish, correlationId);
                    }
                }

                // Set ceiling finish
                if (!string.IsNullOrEmpty(parameters.CeilingFinish))
                {
                    var ceilingFinishParam = room.get_Parameter(BuiltInParameter.ROOM_FINISH_CEILING);
                    if (ceilingFinishParam != null && !ceilingFinishParam.IsReadOnly)
                    {
                        ceilingFinishParam.Set(parameters.CeilingFinish);
                        Logger.LogDebug("Set ceiling finish to {CeilingFinish}", parameters.CeilingFinish, correlationId);
                    }
                }

                // Set base finish
                if (!string.IsNullOrEmpty(parameters.BaseFinish))
                {
                    var baseFinishParam = room.get_Parameter(BuiltInParameter.ROOM_FINISH_BASE);
                    if (baseFinishParam != null && !baseFinishParam.IsReadOnly)
                    {
                        baseFinishParam.Set(parameters.BaseFinish);
                        Logger.LogDebug("Set base finish to {BaseFinish}", parameters.BaseFinish, correlationId);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to set room finish properties", correlationId);
            }
        }

        /// <summary>
        /// Validates room placement and provides feedback.
        /// </summary>
        /// <param name="room">The created room.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void ValidateRoomPlacement(Room room, string correlationId)
        {
            try
            {
                // Check if room is placed (has area > 0)
                var area = room.Area;
                
                if (area > 0)
                {
                    var areaM2 = RevitHelpers.FeetToMillimeters(Math.Sqrt(area)) / 1000.0 * RevitHelpers.FeetToMillimeters(Math.Sqrt(area)) / 1000.0;
                    Logger.LogDebug("Room placed successfully with area: {Area} m²", areaM2, correlationId);
                }
                else
                {
                    Logger.LogWarning("Room created but not placed (area = 0). Location may not be enclosed.", correlationId);
                    ShowInfo("Room Created", "Room was created but may need to be placed manually. The location might not be fully enclosed.");
                }

                // Check room boundaries
                var boundarySegments = room.GetBoundarySegments(new SpatialElementBoundaryOptions());
                if (boundarySegments?.Count > 0)
                {
                    Logger.LogDebug("Room has {BoundaryCount} boundary loops", boundarySegments.Count, correlationId);
                }
                else
                {
                    Logger.LogWarning("Room has no boundary segments", correlationId);
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error validating room placement", correlationId);
            }
        }

        /// <summary>
        /// Gets the appropriate level for a given point.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="point">The point to find level for.</param>
        /// <returns>The appropriate level.</returns>
        private Level GetLevelForPoint(Document doc, XYZ point)
        {
            var levels = new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .OfType<Level>()
                .OrderBy(l => l.Elevation)
                .ToList();

            // Find the level closest to and below the point elevation
            Level selectedLevel = null;
            
            foreach (var level in levels)
            {
                if (level.Elevation <= point.Z)
                {
                    selectedLevel = level;
                }
                else
                {
                    break;
                }
            }

            // If no level found below, use the lowest level
            return selectedLevel ?? levels.FirstOrDefault();
        }

        /// <summary>
        /// Gets the default phase from the document.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <returns>The default phase.</returns>
        private Phase GetDefaultPhase(Document doc)
        {
            var phases = new FilteredElementCollector(doc)
                .OfClass(typeof(Phase))
                .OfType<Phase>()
                .ToList();

            // Return the first phase (usually "New Construction")
            return phases.FirstOrDefault();
        }
    }

    /// <summary>
    /// Parameters for room creation operations.
    /// </summary>
    public class RoomCreationParameters
    {
        /// <summary>
        /// Gets or sets the room location.
        /// </summary>
        public XYZ Location { get; set; }

        /// <summary>
        /// Gets or sets the level for the room.
        /// </summary>
        public Level Level { get; set; }

        /// <summary>
        /// Gets or sets the room name.
        /// </summary>
        public string RoomName { get; set; }

        /// <summary>
        /// Gets or sets the room number.
        /// </summary>
        public string RoomNumber { get; set; }

        /// <summary>
        /// Gets or sets the room department.
        /// </summary>
        public string Department { get; set; }

        /// <summary>
        /// Gets or sets the room occupancy.
        /// </summary>
        public string Occupancy { get; set; }

        /// <summary>
        /// Gets or sets the area per person in square feet.
        /// </summary>
        public double AreaPerPerson { get; set; }

        /// <summary>
        /// Gets or sets comments for the room.
        /// </summary>
        public string Comments { get; set; }

        /// <summary>
        /// Gets or sets the floor finish.
        /// </summary>
        public string FloorFinish { get; set; }

        /// <summary>
        /// Gets or sets the wall finish.
        /// </summary>
        public string WallFinish { get; set; }

        /// <summary>
        /// Gets or sets the ceiling finish.
        /// </summary>
        public string CeilingFinish { get; set; }

        /// <summary>
        /// Gets or sets the base finish.
        /// </summary>
        public string BaseFinish { get; set; }

        /// <summary>
        /// Gets or sets the phase for the room.
        /// </summary>
        public Phase Phase { get; set; }

        /// <summary>
        /// Gets or sets whether this room was AI-generated.
        /// </summary>
        public bool IsAIGenerated { get; set; }

        /// <summary>
        /// Gets or sets the correlation ID for tracking.
        /// </summary>
        public string CorrelationId { get; set; }
    }
}