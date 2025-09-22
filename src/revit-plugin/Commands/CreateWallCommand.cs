using System;
using System.Collections.Generic;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.Commands
{
    /// <summary>
    /// Command for creating walls in Revit with AI-generated or user-specified parameters.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public class CreateWallCommand : BaseRevitCommand
    {
        protected override Result ExecuteCommand(ExternalCommandData commandData, string correlationId)
        {
            var doc = commandData.Application.ActiveUIDocument.Document;
            var uidoc = commandData.Application.ActiveUIDocument;

            ValidateDocument(doc, correlationId);

            try
            {
                // Get wall creation parameters from user or AI data
                var wallParameters = GetWallCreationParameters(uidoc, correlationId);
                if (wallParameters == null)
                {
                    Logger.LogInformation("Wall creation cancelled by user", correlationId);
                    return Result.Cancelled;
                }

                // Create walls in transaction
                var success = ExecuteInTransaction(doc, "Create AI Walls", transaction =>
                {
                    var createdWalls = CreateWalls(doc, wallParameters, correlationId);
                    
                    Logger.LogInformation("Created {WallCount} walls successfully", 
                        createdWalls.Count, correlationId);

                    if (createdWalls.Count > 0)
                    {
                        ShowInfo("Walls Created", 
                            $"Successfully created {createdWalls.Count} wall(s).");
                    }

                }, correlationId);

                return success ? Result.Succeeded : Result.Failed;
            }
            catch (OperationCanceledException)
            {
                Logger.LogInformation("Wall creation cancelled", correlationId);
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to create walls", correlationId);
                ShowError("Wall Creation Failed", $"Failed to create walls: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Gets wall creation parameters from user input or AI data.
        /// </summary>
        /// <param name="uidoc">The UI document.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>Wall creation parameters or null if cancelled.</returns>
        private WallCreationParameters GetWallCreationParameters(UIDocument uidoc, string correlationId)
        {
            try
            {
                // For now, implement simple two-point wall creation
                // In future, this will integrate with AI-generated layout data
                
                Logger.LogDebug("Prompting user for wall start point", correlationId);
                ShowInfo("Create Wall", "Click to specify the start point of the wall.");

                var startPoint = uidoc.Selection.PickPoint("Pick start point for wall");
                RevitHelpers.ValidatePoint(startPoint, "startPoint");

                Logger.LogDebug("Prompting user for wall end point", correlationId);
                ShowInfo("Create Wall", "Click to specify the end point of the wall.");

                var endPoint = uidoc.Selection.PickPoint("Pick end point for wall");
                RevitHelpers.ValidatePoint(endPoint, "endPoint");

                // Create line for wall
                var wallLine = RevitHelpers.CreateValidatedLine(startPoint, endPoint);

                // Get wall parameters
                var wallType = RevitHelpers.GetDefaultWallType(uidoc.Document);
                var level = GetActiveLevel(uidoc.Document);

                var parameters = new WallCreationParameters
                {
                    WallLines = new List<Line> { wallLine },
                    WallType = wallType,
                    Level = level,
                    Height = RevitHelpers.MillimetersToFeet(3000), // 3m default height
                    IsStructural = false
                };

                Logger.LogDebug("Wall creation parameters collected", correlationId);
                return parameters;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                Logger.LogDebug("User cancelled wall point selection", correlationId);
                return null;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error getting wall creation parameters", correlationId);
                throw new RevitApiException("Failed to get wall creation parameters", ex);
            }
        }

        /// <summary>
        /// Creates walls based on the provided parameters.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The wall creation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>List of created walls.</returns>
        private List<Wall> CreateWalls(Document doc, WallCreationParameters parameters, string correlationId)
        {
            var createdWalls = new List<Wall>();

            try
            {
                foreach (var wallLine in parameters.WallLines)
                {
                    Logger.LogDebug("Creating wall from line: {StartPoint} to {EndPoint}", 
                        wallLine.GetEndPoint(0), wallLine.GetEndPoint(1), correlationId);

                    var wall = CreateSingleWall(doc, wallLine, parameters, correlationId);
                    if (wall != null)
                    {
                        createdWalls.Add(wall);
                        Logger.LogDebug("Wall created with ID: {WallId}", wall.Id.IntegerValue, correlationId);
                    }
                }

                return createdWalls;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error creating walls", correlationId);
                
                // Clean up any partially created walls
                if (createdWalls.Count > 0)
                {
                    try
                    {
                        var wallIds = createdWalls.ConvertAll(w => w.Id);
                        doc.Delete(wallIds);
                        Logger.LogDebug("Cleaned up {WallCount} partially created walls", 
                            createdWalls.Count, correlationId);
                    }
                    catch (Exception cleanupEx)
                    {
                        Logger.LogError(cleanupEx, "Failed to cleanup partially created walls", correlationId);
                    }
                }

                throw;
            }
        }

        /// <summary>
        /// Creates a single wall from the specified parameters.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="wallLine">The wall centerline.</param>
        /// <param name="parameters">The wall creation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The created wall or null if creation failed.</returns>
        private Wall CreateSingleWall(Document doc, Line wallLine, WallCreationParameters parameters, string correlationId)
        {
            try
            {
                // Validate inputs
                if (wallLine == null)
                    throw new ArgumentNullException(nameof(wallLine));

                if (parameters.WallType == null)
                    throw new ArgumentNullException("WallType in parameters");

                if (parameters.Level == null)
                    throw new ArgumentNullException("Level in parameters");

                // Create wall
                var wall = Wall.Create(
                    doc,
                    wallLine,
                    parameters.WallType.Id,
                    parameters.Level.Id,
                    parameters.Height,
                    0.0, // offset
                    false, // flip
                    parameters.IsStructural);

                if (wall == null)
                {
                    Logger.LogError("Wall.Create returned null", correlationId);
                    return null;
                }

                // Set additional parameters if specified
                SetWallParameters(wall, parameters, correlationId);

                Logger.LogDebug("Single wall created successfully", correlationId);
                return wall;
            }
            catch (Autodesk.Revit.Exceptions.ArgumentException ex)
            {
                Logger.LogError(ex, "Invalid arguments for wall creation", correlationId);
                throw new RevitApiException("Invalid wall creation parameters", "INVALID_WALL_ARGS", ex);
            }
            catch (Autodesk.Revit.Exceptions.InvalidOperationException ex)
            {
                Logger.LogError(ex, "Invalid operation during wall creation", correlationId);
                throw new RevitApiException("Wall creation operation is invalid", "INVALID_WALL_OPERATION", ex);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Unexpected error during wall creation", correlationId);
                throw new RevitApiException("Unexpected error creating wall", ex);
            }
        }

        /// <summary>
        /// Sets additional parameters on the created wall.
        /// </summary>
        /// <param name="wall">The wall to configure.</param>
        /// <param name="parameters">The wall creation parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void SetWallParameters(Wall wall, WallCreationParameters parameters, string correlationId)
        {
            try
            {
                // Set wall function if specified
                if (parameters.WallFunction.HasValue)
                {
                    var functionParam = wall.get_Parameter(BuiltInParameter.FUNCTION_PARAM);
                    if (functionParam != null && !functionParam.IsReadOnly)
                    {
                        functionParam.Set((int)parameters.WallFunction.Value);
                        Logger.LogDebug("Set wall function to {Function}", parameters.WallFunction.Value, correlationId);
                    }
                }

                // Set structural parameter
                var structuralParam = wall.get_Parameter(BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT);
                if (structuralParam != null && !structuralParam.IsReadOnly)
                {
                    structuralParam.Set(parameters.IsStructural ? 1 : 0);
                    Logger.LogDebug("Set wall structural parameter to {IsStructural}", parameters.IsStructural, correlationId);
                }

                // Set comments if provided
                if (!string.IsNullOrEmpty(parameters.Comments))
                {
                    var commentsParam = wall.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                    if (commentsParam != null && !commentsParam.IsReadOnly)
                    {
                        commentsParam.Set(parameters.Comments);
                        Logger.LogDebug("Set wall comments", correlationId);
                    }
                }

                // Mark wall as AI-generated if applicable
                if (parameters.IsAIGenerated)
                {
                    // Add custom parameter or comment to identify AI-generated walls
                    var markParam = wall.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
                    if (markParam != null && !markParam.IsReadOnly)
                    {
                        markParam.Set("AI-Generated");
                        Logger.LogDebug("Marked wall as AI-generated", correlationId);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to set some wall parameters", correlationId);
                // Continue execution - parameter setting is not critical
            }
        }
    }

    /// <summary>
    /// Parameters for wall creation operations.
    /// </summary>
    public class WallCreationParameters
    {
        /// <summary>
        /// Gets or sets the wall centerlines.
        /// </summary>
        public List<Line> WallLines { get; set; } = new List<Line>();

        /// <summary>
        /// Gets or sets the wall type to use.
        /// </summary>
        public WallType WallType { get; set; }

        /// <summary>
        /// Gets or sets the level for the wall base.
        /// </summary>
        public Level Level { get; set; }

        /// <summary>
        /// Gets or sets the wall height in Revit internal units.
        /// </summary>
        public double Height { get; set; }

        /// <summary>
        /// Gets or sets whether the wall is structural.
        /// </summary>
        public bool IsStructural { get; set; }

        /// <summary>
        /// Gets or sets the wall function.
        /// </summary>
        public WallFunction? WallFunction { get; set; }

        /// <summary>
        /// Gets or sets comments for the wall.
        /// </summary>
        public string Comments { get; set; }

        /// <summary>
        /// Gets or sets whether this wall was AI-generated.
        /// </summary>
        public bool IsAIGenerated { get; set; }

        /// <summary>
        /// Gets or sets the correlation ID for tracking.
        /// </summary>
        public string CorrelationId { get; set; }
    }
}