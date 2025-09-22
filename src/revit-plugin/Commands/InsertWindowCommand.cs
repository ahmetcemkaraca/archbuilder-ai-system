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
    /// Command for inserting windows in Revit with AI-generated or user-specified parameters.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public class InsertWindowCommand : BaseRevitCommand
    {
        protected override Result ExecuteCommand(ExternalCommandData commandData, string correlationId)
        {
            var doc = commandData.Application.ActiveUIDocument.Document;
            var uidoc = commandData.Application.ActiveUIDocument;

            ValidateDocument(doc, correlationId);

            try
            {
                // Get window insertion parameters
                var windowParameters = GetWindowInsertionParameters(uidoc, correlationId);
                if (windowParameters == null)
                {
                    Logger.LogInformation("Window insertion cancelled by user", correlationId);
                    return Result.Cancelled;
                }

                // Insert window in transaction
                var success = ExecuteInTransaction(doc, "Insert AI Window", transaction =>
                {
                    var window = InsertWindow(doc, windowParameters, correlationId);
                    
                    if (window != null)
                    {
                        Logger.LogInformation("Window inserted successfully with ID: {WindowId}", 
                            window.Id.IntegerValue, correlationId);
                        ShowInfo("Window Inserted", "Window inserted successfully.");
                    }
                    else
                    {
                        throw new RevitApiException("Failed to insert window - null result");
                    }

                }, correlationId);

                return success ? Result.Succeeded : Result.Failed;
            }
            catch (OperationCanceledException)
            {
                Logger.LogInformation("Window insertion cancelled", correlationId);
                return Result.Cancelled;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to insert window", correlationId);
                ShowError("Window Insertion Failed", $"Failed to insert window: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Gets window insertion parameters from user selection or AI data.
        /// </summary>
        /// <param name="uidoc">The UI document.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>Window insertion parameters or null if cancelled.</returns>
        private WindowInsertionParameters GetWindowInsertionParameters(UIDocument uidoc, string correlationId)
        {
            try
            {
                // For now, implement wall selection and point picking
                // In future, this will integrate with AI-generated layout data
                
                Logger.LogDebug("Prompting user to select wall for window", correlationId);
                ShowInfo("Insert Window", "Select a wall to place the window on.");

                // Create wall selection filter
                var wallFilter = new WallSelectionFilter();
                var wallRef = uidoc.Selection.PickObject(ObjectType.Element, wallFilter, "Select wall for window insertion");
                
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

                // Get window location on wall
                ShowInfo("Insert Window", "Click on the wall to specify window location.");
                var windowLocation = uidoc.Selection.PickPoint("Pick window location on wall");
                RevitHelpers.ValidatePoint(windowLocation, "windowLocation");

                // Get window family symbol
                var windowSymbol = RevitHelpers.GetWindowFamilySymbol(uidoc.Document);
                var level = GetLevelFromWall(hostWall);

                var parameters = new WindowInsertionParameters
                {
                    HostWall = hostWall,
                    Location = windowLocation,
                    WindowSymbol = windowSymbol,
                    Level = level,
                    Width = RevitHelpers.MillimetersToFeet(1200), // 1200mm default width
                    Height = RevitHelpers.MillimetersToFeet(1400), // 1400mm default height
                    SillHeight = RevitHelpers.MillimetersToFeet(900) // 900mm default sill height
                };

                Logger.LogDebug("Window insertion parameters collected", correlationId);
                return parameters;
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                Logger.LogDebug("User cancelled window insertion", correlationId);
                return null;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error getting window insertion parameters", correlationId);
                throw new RevitApiException("Failed to get window insertion parameters", ex);
            }
        }

        /// <summary>
        /// Inserts a window based on the provided parameters.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="parameters">The window insertion parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The created window instance.</returns>
        private FamilyInstance InsertWindow(Document doc, WindowInsertionParameters parameters, string correlationId)
        {
            try
            {
                // Validate inputs
                if (parameters.HostWall == null)
                    throw new ArgumentNullException("HostWall in parameters");

                if (parameters.WindowSymbol == null)
                    throw new ArgumentNullException("WindowSymbol in parameters");

                if (parameters.Level == null)
                    throw new ArgumentNullException("Level in parameters");

                // Ensure window symbol is active
                if (!parameters.WindowSymbol.IsActive)
                {
                    parameters.WindowSymbol.Activate();
                }

                // Calculate the best insertion point on the wall
                var insertionPoint = CalculateInsertionPoint(parameters.HostWall, parameters.Location, correlationId);

                // Validate window placement on wall
                ValidateWindowPlacement(parameters.HostWall, insertionPoint, parameters, correlationId);

                Logger.LogDebug("Creating window at point: {Point}", insertionPoint, correlationId);

                // Create window instance
                var window = doc.Create.NewFamilyInstance(
                    insertionPoint,
                    parameters.WindowSymbol,
                    parameters.HostWall,
                    parameters.Level,
                    StructuralType.NonStructural);

                if (window == null)
                {
                    Logger.LogError("Window creation returned null", correlationId);
                    throw new RevitApiException("Failed to create window instance");
                }

                // Set window parameters
                SetWindowParameters(window, parameters, correlationId);

                Logger.LogDebug("Window inserted successfully", correlationId);
                return window;
            }
            catch (Autodesk.Revit.Exceptions.ArgumentException ex)
            {
                Logger.LogError(ex, "Invalid arguments for window insertion", correlationId);
                throw new RevitApiException("Invalid window insertion parameters", "INVALID_WINDOW_ARGS", ex);
            }
            catch (Autodesk.Revit.Exceptions.InvalidOperationException ex)
            {
                Logger.LogError(ex, "Invalid operation during window insertion", correlationId);
                throw new RevitApiException("Window insertion operation is invalid", "INVALID_WINDOW_OPERATION", ex);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Unexpected error during window insertion", correlationId);
                throw new RevitApiException("Unexpected error inserting window", ex);
            }
        }

        /// <summary>
        /// Calculates the optimal insertion point for the window on the wall.
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
                
                // Ensure the point is within the wall bounds with margin for window width
                var startParam = wallCurve.GetEndParameter(0);
                var endParam = wallCurve.GetEndParameter(1);
                var pointParam = projectedPoint.Parameter;
                
                // Add margins (window half-width + 100mm from each end)
                var paramRange = endParam - startParam;
                var wallLength = wallCurve.Length;
                var marginLength = RevitHelpers.MillimetersToFeet(600); // 600mm margin (300mm window half-width + 300mm clearance)
                var marginParam = (marginLength / wallLength) * paramRange;
                
                if (pointParam < startParam + marginParam)
                {
                    pointParam = startParam + marginParam;
                    insertionPoint = wallCurve.Evaluate(pointParam, false);
                    Logger.LogDebug("Adjusted window location to respect wall start margin", correlationId);
                }
                else if (pointParam > endParam - marginParam)
                {
                    pointParam = endParam - marginParam;
                    insertionPoint = wallCurve.Evaluate(pointParam, false);
                    Logger.LogDebug("Adjusted window location to respect wall end margin", correlationId);
                }

                Logger.LogDebug("Calculated window insertion point: {Point}", insertionPoint, correlationId);
                return insertionPoint;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error calculating window insertion point", correlationId);
                throw new RevitApiException("Failed to calculate window insertion point", ex);
            }
        }

        /// <summary>
        /// Validates window placement to ensure it doesn't conflict with other openings.
        /// </summary>
        /// <param name="wall">The host wall.</param>
        /// <param name="insertionPoint">The proposed insertion point.</param>
        /// <param name="parameters">The window parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void ValidateWindowPlacement(Wall wall, XYZ insertionPoint, WindowInsertionParameters parameters, string correlationId)
        {
            try
            {
                // Get existing openings in the wall
                var existingDoors = GetExistingOpenings(wall, BuiltInCategory.OST_Doors);
                var existingWindows = GetExistingOpenings(wall, BuiltInCategory.OST_Windows);

                var allOpenings = existingDoors.Concat(existingWindows);

                foreach (var opening in allOpenings)
                {
                    var openingLocation = ((LocationPoint)opening.Location).Point;
                    var distance = insertionPoint.DistanceTo(openingLocation);

                    // Check minimum distance (1m between openings)
                    var minimumDistance = RevitHelpers.MillimetersToFeet(1000);
                    
                    if (distance < minimumDistance)
                    {
                        Logger.LogWarning("Window placement too close to existing opening: {Distance}mm", 
                            RevitHelpers.FeetToMillimeters(distance), correlationId);
                        
                        throw new RevitApiException($"Window location conflicts with existing opening. " +
                            $"Minimum distance required: {RevitHelpers.FeetToMillimeters(minimumDistance):F0}mm, " +
                            $"actual distance: {RevitHelpers.FeetToMillimeters(distance):F0}mm");
                    }
                }

                Logger.LogDebug("Window placement validation passed", correlationId);
            }
            catch (RevitApiException)
            {
                throw; // Re-throw validation errors
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error during window placement validation", correlationId);
                // Continue with placement - validation is not critical
            }
        }

        /// <summary>
        /// Gets existing openings (doors/windows) in the specified wall.
        /// </summary>
        /// <param name="wall">The wall to check.</param>
        /// <param name="category">The category of openings to find.</param>
        /// <returns>Collection of existing openings.</returns>
        private System.Collections.Generic.IEnumerable<FamilyInstance> GetExistingOpenings(Wall wall, BuiltInCategory category)
        {
            return new FilteredElementCollector(wall.Document)
                .OfClass(typeof(FamilyInstance))
                .OfCategory(category)
                .OfType<FamilyInstance>()
                .Where(fi => fi.Host?.Id == wall.Id);
        }

        /// <summary>
        /// Sets parameters on the inserted window.
        /// </summary>
        /// <param name="window">The window instance.</param>
        /// <param name="parameters">The window insertion parameters.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        private void SetWindowParameters(FamilyInstance window, WindowInsertionParameters parameters, string correlationId)
        {
            try
            {
                // Set width if different from default
                var widthParam = window.LookupParameter("Width");
                if (widthParam != null && !widthParam.IsReadOnly && parameters.Width > 0)
                {
                    widthParam.Set(parameters.Width);
                    Logger.LogDebug("Set window width to {Width} feet", parameters.Width, correlationId);
                }

                // Set height if different from default
                var heightParam = window.LookupParameter("Height");
                if (heightParam != null && !heightParam.IsReadOnly && parameters.Height > 0)
                {
                    heightParam.Set(parameters.Height);
                    Logger.LogDebug("Set window height to {Height} feet", parameters.Height, correlationId);
                }

                // Set sill height
                var sillHeightParam = window.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM);
                if (sillHeightParam != null && !sillHeightParam.IsReadOnly && parameters.SillHeight > 0)
                {
                    sillHeightParam.Set(parameters.SillHeight);
                    Logger.LogDebug("Set window sill height to {SillHeight} feet", parameters.SillHeight, correlationId);
                }

                // Set comments if provided
                if (!string.IsNullOrEmpty(parameters.Comments))
                {
                    var commentsParam = window.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                    if (commentsParam != null && !commentsParam.IsReadOnly)
                    {
                        commentsParam.Set(parameters.Comments);
                        Logger.LogDebug("Set window comments", correlationId);
                    }
                }

                // Mark window as AI-generated if applicable
                if (parameters.IsAIGenerated)
                {
                    var markParam = window.get_Parameter(BuiltInParameter.ALL_MODEL_MARK);
                    if (markParam != null && !markParam.IsReadOnly)
                    {
                        markParam.Set("AI-Generated");
                        Logger.LogDebug("Marked window as AI-generated", correlationId);
                    }
                }

                // Set window type/function if specified
                if (!string.IsNullOrEmpty(parameters.WindowType))
                {
                    var typeParam = window.LookupParameter("Type");
                    if (typeParam != null && !typeParam.IsReadOnly)
                    {
                        typeParam.Set(parameters.WindowType);
                        Logger.LogDebug("Set window type to {Type}", parameters.WindowType, correlationId);
                    }
                }

                // Set operational status if specified
                if (parameters.IsOperable.HasValue)
                {
                    var operableParam = window.LookupParameter("Operable");
                    if (operableParam != null && !operableParam.IsReadOnly)
                    {
                        operableParam.Set(parameters.IsOperable.Value ? 1 : 0);
                        Logger.LogDebug("Set window operable status to {IsOperable}", parameters.IsOperable.Value, correlationId);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to set some window parameters", correlationId);
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
    /// Parameters for window insertion operations.
    /// </summary>
    public class WindowInsertionParameters
    {
        /// <summary>
        /// Gets or sets the host wall for the window.
        /// </summary>
        public Wall HostWall { get; set; }

        /// <summary>
        /// Gets or sets the window location.
        /// </summary>
        public XYZ Location { get; set; }

        /// <summary>
        /// Gets or sets the window family symbol.
        /// </summary>
        public FamilySymbol WindowSymbol { get; set; }

        /// <summary>
        /// Gets or sets the level for the window.
        /// </summary>
        public Level Level { get; set; }

        /// <summary>
        /// Gets or sets the window width in Revit internal units.
        /// </summary>
        public double Width { get; set; }

        /// <summary>
        /// Gets or sets the window height in Revit internal units.
        /// </summary>
        public double Height { get; set; }

        /// <summary>
        /// Gets or sets the sill height in Revit internal units.
        /// </summary>
        public double SillHeight { get; set; }

        /// <summary>
        /// Gets or sets the window type or function.
        /// </summary>
        public string WindowType { get; set; }

        /// <summary>
        /// Gets or sets whether the window is operable.
        /// </summary>
        public bool? IsOperable { get; set; }

        /// <summary>
        /// Gets or sets comments for the window.
        /// </summary>
        public string Comments { get; set; }

        /// <summary>
        /// Gets or sets whether this window was AI-generated.
        /// </summary>
        public bool IsAIGenerated { get; set; }

        /// <summary>
        /// Gets or sets the correlation ID for tracking.
        /// </summary>
        public string CorrelationId { get; set; }
    }
}