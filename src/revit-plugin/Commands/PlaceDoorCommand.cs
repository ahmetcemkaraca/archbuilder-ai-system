using System;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.Commands
{
    /// <summary>
    /// Command for placing doors in Revit with AI-generated or user-specified parameters.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public class PlaceDoorCommand : BaseRevitCommand
    {
        protected override Result ExecuteCommand(ExternalCommandData commandData, string correlationId)
        {
            var doc = commandData.Application.ActiveUIDocument.Document;
            var uidoc = commandData.Application.ActiveUIDocument;

            ValidateDocument(doc, correlationId);

            try
            {
                // Get door placement parameters
                var doorParameters = GetDoorPlacementParameters(uidoc, correlationId);
                if (doorParameters == null)
                {
                    Logger.LogInformation("Door placement cancelled by user", correlationId);
                    return Result.Cancelled;
                }

                // Place door in transaction
                var success = ExecuteInTransaction(doc, "Place AI Door", transaction =>
                {
                    var door = PlaceDoor(doc, doorParameters, correlationId);
                    
                    if (door != null)
                    {
                        Logger.LogInformation("Door placed successfully with ID: {DoorId}", 
                            door.Id.IntegerValue, correlationId);
                        ShowInfo("Door Placed", "Door placed successfully.");
                    }
                    else
                    {
                        throw new RevitApiException("Failed to place door - null result");
                    }

                }, correlationId);

                return success ? Result.Succeeded : Result.Failed;
            }
            catch (OperationCanceledException)
            {
                Logger.LogInformation("Door placement cancelled", correlationId);
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to place door", correlationId);
                ShowError("Door Placement Failed", $"Failed to place door: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Gets door placement parameters from user selection or AI data.
        /// </summary>
        /// <param name="uidoc">The UI document.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>Door placement parameters or null if cancelled.</returns>
        private DoorPlacementParameters GetDoorPlacementParameters(UIDocument uidoc, string correlationId)
        {
            try
            {
                // For now, implement wall selection and point picking
                // In future, this will integrate with AI-generated layout data
                
                Logger.LogDebug("Prompting user to select wall for door", correlationId);
                ShowInfo("Place Door", "Select a wall to place the door on.");

                // Create wall selection filter
                var wallFilter = new WallSelectionFilter();
                var wallRef = uidoc.Selection.PickObject(ObjectType.Element, wallFilter, "Select wall for door placement");
                
                if (wallRef == null)
                {
                    Logger.LogDebug("No wall selected", correlationId);
                    return null;
                }

                var hostWall = uidoc.Document.GetElement(wallRef) as Wall;
                if (hostWall == null)
                {
                    throw new RevitApiException("Selected element is not a wall");
                }

                Logger.LogDebug("Wall selected: {WallId}", hostWall.Id.IntegerValue, correlationId);

                // Get door location on wall
                ShowInfo("Place Door", "Click on the wall to specify door location.");
                var doorLocation = uidoc.Selection.PickPoint("Pick door location on wall");
                RevitHelpers.ValidatePoint(doorLocation, "doorLocation");

                // Get door family symbol
                var doorSymbol = RevitHelpers.GetDoorFamilySymbol(uidoc.Document);
                var level = GetLevelFromWall(hostWall);

                var parameters = new DoorPlacementParameters
                {
                    HostWall = hostWall,
                    Location = doorLocation,
                    DoorSymbol = doorSymbol,
                    Level = level,
                    Width = RevitHelpers.MillimetersToFeet(900), // 900mm default width
                    Height = RevitHelpers.MillimetersToFeet(2100) // 2100mm default height
                };

                Logger.LogDebug("Door placement parameters collected", correlationId);
                return parameters;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                Logger.LogDebug("User cancelled door placement", correlationId);
                return null;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error getting door placement parameters", correlationId);
                throw new RevitApiException("Failed to get door placement parameters", ex);
            }
        }

        /// <summary>
        /// Places a door based on the provided parameters.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The door placement parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The created door instance.</returns>
        private FamilyInstance PlaceDoor(Document doc, DoorPlacementParameters parameters, string correlationId)
        {
            try
            {
                // Validate inputs
                if (parameters.HostWall == null)
                    throw new ArgumentNullException("HostWall in parameters");

                if (parameters.DoorSymbol == null)
                    throw new ArgumentNullException("DoorSymbol in parameters");

                if (parameters.Level == null)
                    throw new ArgumentNullException("Level in parameters");

                // Ensure door symbol is active
                if (!parameters.DoorSymbol.IsActive)
                {
                    parameters.DoorSymbol.Activate();
                }

                // Calculate the best insertion point on the wall
                var insertionPoint = CalculateInsertionPoint(parameters.HostWall, parameters.Location, correlationId);

                Logger.LogDebug("Creating door at point: {Point}", insertionPoint, correlationId);

                // Create door instance
                var door = doc.Create.NewFamilyInstance(
                    insertionPoint,
                    parameters.DoorSymbol,
                    parameters.HostWall,
                    parameters.Level,
                    StructuralType.NonStructural);

                if (door == null)
                {
                    Logger.LogError("Door creation returned null", correlationId);
                    throw new RevitApiException("Failed to create door instance");
                }

                // Set door parameters
                SetDoorParameters(door, parameters, correlationId);

                Logger.LogDebug("Door placed successfully", correlationId);
                return door;
            }
            catch (Autodesk.Revit.Exceptions.ArgumentException ex)
            {
                Logger.LogError(ex, "Invalid arguments for door placement", correlationId);
                throw new RevitApiException("Invalid door placement parameters", "INVALID_DOOR_ARGS", ex);
            }
            catch (Autodesk.Revit.Exceptions.InvalidOperationException ex)
            {
                Logger.LogError(ex, "Invalid operation during door placement", correlationId);
                throw new RevitApiException("Door placement operation is invalid", "INVALID_DOOR_OPERATION", ex);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Unexpected error during door placement", correlationId);
                throw new RevitApiException("Unexpected error placing door", ex);
            }
        }

        /// <summary>
        /// Calculates the optimal insertion point for the door on the wall.
        /// </summary>
        /// <param name="wall">The host wall.</param>
        /// <param name="userPoint">The user-specified point.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The calculated insertion point.</returns>
        private XYZ CalculateInsertionPoint(Wall wall, XYZ userPoint, string correlationId)
        {
            try
            {
                // Get wall curve (centerline)
                var wallCurve = ((LocationCurve)wall.Location).Curve;
                
                // Project user point onto wall centerline
                var projectedPoint = wallCurve.Project(userPoint);
                
                if (projectedPoint == null)
                {
                    Logger.LogWarning("Could not project point onto wall, using closest point", correlationId);
                    // Use closest point on curve
                    var parameter = wallCurve.Project(userPoint).Parameter;
                    return wallCurve.Evaluate(parameter, false);
                }

                var insertionPoint = projectedPoint.XYZPoint;
                
                // Ensure the point is within the wall bounds with some margin
                var startParam = wallCurve.GetEndParameter(0);
                var endParam = wallCurve.GetEndParameter(1);
                var pointParam = projectedPoint.Parameter;
                
                // Add margins (10% of wall length from each end)
                var paramRange = endParam - startParam;
                var margin = paramRange * 0.1;
                
                if (pointParam < startParam + margin)
                {
                    pointParam = startParam + margin;
                    insertionPoint = wallCurve.Evaluate(pointParam, false);
                    Logger.LogDebug("Adjusted door location to respect wall start margin", correlationId);
                }
                else if (pointParam > endParam - margin)
                {
                    pointParam = endParam - margin;
                    insertionPoint = wallCurve.Evaluate(pointParam, false);
                    Logger.LogDebug("Adjusted door location to respect wall end margin", correlationId);
                }

                Logger.LogDebug("Calculated door insertion point: {Point}", insertionPoint, correlationId);
                return insertionPoint;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error calculating door insertion point", correlationId);
                throw new RevitApiException("Failed to calculate door insertion point", ex);
            }
        }

        /// <summary>
        /// Sets parameters on the placed door.
        /// </summary>
        /// <param name="door">The door instance.</param>
        /// <param name="parameters">The door placement parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void SetDoorParameters(FamilyInstance door, DoorPlacementParameters parameters, string correlationId)
        {
            try
            {
                // Set width if different from default
                var widthParam = door.LookupParameter("Width");
                if (widthParam != null && !widthParam.IsReadOnly && parameters.Width > 0)
                {
                    widthParam.Set(parameters.Width);
                    Logger.LogDebug("Set door width to {Width} feet", parameters.Width, correlationId);
                }

                // Set height if different from default
                var heightParam = door.LookupParameter("Height");
                if (heightParam != null && !heightParam.IsReadOnly && parameters.Height > 0)
                {
                    heightParam.Set(parameters.Height);
                    Logger.LogDebug("Set door height to {Height} feet", parameters.Height, correlationId);
                }

                // Set comments if provided
                if (!string.IsNullOrEmpty(parameters.Comments))
                {
                    var commentsParam = door.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                    if (commentsParam != null && !commentsParam.IsReadOnly)
                    {
                        commentsParam.Set(parameters.Comments);
                        Logger.LogDebug("Set door comments", correlationId);
                    }
                }

                // Mark door as AI-generated if applicable
                if (parameters.IsAIGenerated)
                {
                    var markParam = door.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
                    if (markParam != null && !markParam.IsReadOnly)
                    {
                        markParam.Set("AI-Generated");
                        Logger.LogDebug("Marked door as AI-generated", correlationId);
                    }
                }

                // Set door type/function if specified
                if (!string.IsNullOrEmpty(parameters.DoorType))
                {
                    var typeParam = door.LookupParameter("Type");
                    if (typeParam != null && !typeParam.IsReadOnly)
                    {
                        typeParam.Set(parameters.DoorType);
                        Logger.LogDebug("Set door type to {Type}", parameters.DoorType, correlationId);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to set some door parameters", correlationId);
                // Continue execution - parameter setting is not critical
            }
        }

        /// <summary>
        /// Gets the level associated with a wall.
        /// </summary>
        /// <param name="wall">The wall.</param>
        /// <returns>The wall's level.</returns>
        private Level GetLevelFromWall(Wall wall)
        {
            var levelId = wall.LevelId;
            return wall.Document.GetElement(levelId) as Level;
        }
    }

    /// <summary>
    /// Selection filter for walls to ensure only walls can be selected for door placement.
    /// </summary>
    public class WallSelectionFilter : ISelectionFilter
    {
        public bool AllowElement(Element elem)
        {
            return elem is Wall;
        }

        public bool AllowReference(Reference reference, XYZ position)
        {
            return false;
        }
    }

    /// <summary>
    /// Parameters for door placement operations.
    /// </summary>
    public class DoorPlacementParameters
    {
        /// <summary>
        /// Gets or sets the host wall for the door.
        /// </summary>
        public Wall HostWall { get; set; }

        /// <summary>
        /// Gets or sets the door location.
        /// </summary>
        public XYZ Location { get; set; }

        /// <summary>
        /// Gets or sets the door family symbol.
        /// </summary>
        public FamilySymbol DoorSymbol { get; set; }

        /// <summary>
        /// Gets or sets the level for the door.
        /// </summary>
        public Level Level { get; set; }

        /// <summary>
        /// Gets or sets the door width in Revit internal units.
        /// </summary>
        public double Width { get; set; }

        /// <summary>
        /// Gets or sets the door height in Revit internal units.
        /// </summary>
        public double Height { get; set; }

        /// <summary>
        /// Gets or sets the door type or function.
        /// </summary>
        public string DoorType { get; set; }

        /// <summary>
        /// Gets or sets comments for the door.
        /// </summary>
        public string Comments { get; set; }

        /// <summary>
        /// Gets or sets whether this door was AI-generated.
        /// </summary>
        public bool IsAIGenerated { get; set; }

        /// <summary>
        /// Gets or sets the correlation ID for tracking.
        /// </summary>
        public string CorrelationId { get; set; }
    }
}