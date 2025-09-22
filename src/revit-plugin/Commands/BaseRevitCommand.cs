using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.Commands
{
    /// <summary>
    /// Base class for all ArchBuilder AI commands providing common functionality.
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    public abstract class BaseRevitCommand : IExternalCommand
    {
        protected ILogger Logger { get; private set; }

        /// <summary>
        /// Executes the Revit command.
        /// </summary>
        /// <param name="commandData">The command data.</param>
        /// <param name="message">Output message for errors.</param>
        /// <param name="elements">Elements related to the command.</param>
        /// <returns>The execution result.</returns>
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                // Initialize logger for this command
                Logger = GetLogger();

                var correlationId = Guid.NewGuid().ToString("N")[..8];
                Logger.LogInformation("Command started: {CommandType}", GetType().Name, correlationId);

                var result = ExecuteCommand(commandData, correlationId);

                Logger.LogInformation("Command completed: {CommandType} with result: {Result}", 
                    GetType().Name, result, correlationId);

                return result;
            }
            catch (OperationCanceledException)
            {
                Logger?.LogInformation("Command cancelled by user: {CommandType}", GetType().Name);
                message = "Operation cancelled by user.";
                return Result.Cancelled;
            }
            catch (RevitApiException ex)
            {
                Logger?.LogError(ex, "Revit API error in command: {CommandType}", GetType().Name);
                message = $"Revit API error: {ex.Message}";
                return Result.Failed;
            }
            catch (Exception ex)
            {
                Logger?.LogError(ex, "Unexpected error in command: {CommandType}", GetType().Name);
                message = $"Unexpected error: {ex.Message}";
                return Result.Failed;
            }
        }

        /// <summary>
        /// Executes the specific command implementation.
        /// </summary>
        /// <param name="commandData">The command data.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>The execution result.</returns>
        protected abstract Result ExecuteCommand(ExternalCommandData commandData, string correlationId);

        /// <summary>
        /// Gets the logger for this command type.
        /// </summary>
        /// <returns>The logger instance.</returns>
        protected virtual ILogger GetLogger()
        {
            // Use a factory pattern or service locator to get the appropriate logger
            return Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance;
        }

        /// <summary>
        /// Validates that the document is available and not read-only.
        /// </summary>
        /// <param name="doc">The document to validate.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <exception cref="InvalidOperationException">Thrown when document validation fails.</exception>
        protected void ValidateDocument(Document doc, string correlationId)
        {
            if (doc == null)
            {
                Logger.LogError("Document is null", correlationId);
                throw new InvalidOperationException("No active document available.");
            }

            if (doc.IsReadOnly)
            {
                Logger.LogError("Document is read-only", correlationId);
                throw new InvalidOperationException("Document is read-only and cannot be modified.");
            }

            if (doc.IsFamilyDocument)
            {
                Logger.LogError("Command not supported in family documents", correlationId);
                throw new InvalidOperationException("This command is not supported in family documents.");
            }
        }

        /// <summary>
        /// Gets the active level from the document.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <returns>The active level.</returns>
        /// <exception cref="InvalidOperationException">Thrown when no active level is found.</exception>
        protected Level GetActiveLevel(Document doc)
        {
            var collector = new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .OfType<Level>()
                .OrderBy(l => l.Elevation);

            return collector.FirstOrDefault() 
                ?? throw new InvalidOperationException("No levels found in the document.");
        }

        /// <summary>
        /// Executes an operation within a Revit transaction with proper error handling.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="transactionName">The name of the transaction.</param>
        /// <param name="operation">The operation to execute.</param>
        /// <param name="correlationId">The correlation ID for tracking.</param>
        /// <returns>True if the operation succeeded; otherwise, false.</returns>
        protected bool ExecuteInTransaction(Document doc, string transactionName, 
            Action<Transaction> operation, string correlationId)
        {
            using var transaction = new Transaction(doc, transactionName);
            
            try
            {
                Logger.LogDebug("Starting transaction: {TransactionName}", transactionName, correlationId);
                
                var status = transaction.Start();
                if (status != TransactionStatus.Started)
                {
                    Logger.LogError("Failed to start transaction: {TransactionName}, Status: {Status}", 
                        transactionName, status, correlationId);
                    return false;
                }

                operation(transaction);

                status = transaction.Commit();
                if (status == TransactionStatus.Committed)
                {
                    Logger.LogDebug("Transaction committed successfully: {TransactionName}", 
                        transactionName, correlationId);
                    return true;
                }
                else
                {
                    Logger.LogError("Failed to commit transaction: {TransactionName}, Status: {Status}", 
                        transactionName, status, correlationId);
                    return false;
                }
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Exception in transaction: {TransactionName}", transactionName, correlationId);
                
                if (transaction.GetStatus() == TransactionStatus.Started)
                {
                    transaction.RollBack();
                    Logger.LogDebug("Transaction rolled back: {TransactionName}", transactionName, correlationId);
                }
                
                throw;
            }
        }

        /// <summary>
        /// Shows a user-friendly error message.
        /// </summary>
        /// <param name="title">The error title.</param>
        /// <param name="message">The error message.</param>
        protected void ShowError(string title, string message)
        {
            TaskDialog.Show(title, message);
        }

        /// <summary>
        /// Shows a user-friendly information message.
        /// </summary>
        /// <param name="title">The information title.</param>
        /// <param name="message">The information message.</param>
        protected void ShowInfo(string title, string message)
        {
            TaskDialog.Show(title, message);
        }

        /// <summary>
        /// Shows a confirmation dialog.
        /// </summary>
        /// <param name="title">The dialog title.</param>
        /// <param name="message">The confirmation message.</param>
        /// <returns>True if user confirmed; otherwise, false.</returns>
        protected bool ShowConfirmation(string title, string message)
        {
            var dialog = new TaskDialog(title)
            {
                MainContent = message,
                CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No,
                DefaultButton = TaskDialogResult.No
            };

            return dialog.Show() == TaskDialogResult.Yes;
        }
    }

    /// <summary>
    /// Custom exception for Revit API related errors.
    /// </summary>
    public class RevitApiException : Exception
    {
        /// <summary>
        /// Gets the Revit error code if available.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="RevitApiException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public RevitApiException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="RevitApiException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public RevitApiException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="RevitApiException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The Revit error code.</param>
        public RevitApiException(string message, string errorCode) : base(message)
        {
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="RevitApiException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The Revit error code.</param>
        /// <param name="innerException">The inner exception.</param>
        public RevitApiException(string message, string errorCode, Exception innerException) 
            : base(message, innerException)
        {
            ErrorCode = errorCode;
        }
    }

    /// <summary>
    /// Helper class for common Revit operations.
    /// </summary>
    public static class RevitHelpers
    {
        /// <summary>
        /// Converts millimeters to Revit internal units (feet).
        /// </summary>
        /// <param name="millimeters">The value in millimeters.</param>
        /// <returns>The value in Revit internal units.</returns>
        public static double MillimetersToFeet(double millimeters)
        {
            return UnitUtils.ConvertToInternalUnits(millimeters, UnitTypeId.Millimeters);
        }

        /// <summary>
        /// Converts Revit internal units (feet) to millimeters.
        /// </summary>
        /// <param name="feet">The value in Revit internal units.</param>
        /// <returns>The value in millimeters.</returns>
        public static double FeetToMillimeters(double feet)
        {
            return UnitUtils.ConvertFromInternalUnits(feet, UnitTypeId.Millimeters);
        }

        /// <summary>
        /// Gets the default wall type from the document.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <returns>The default wall type.</returns>
        /// <exception cref="InvalidOperationException">Thrown when no wall type is found.</exception>
        public static WallType GetDefaultWallType(Document doc)
        {
            var wallType = new FilteredElementCollector(doc)
                .OfClass(typeof(WallType))
                .OfType<WallType>()
                .FirstOrDefault(wt => wt.Kind == WallKind.Basic);

            return wallType ?? throw new InvalidOperationException("No basic wall type found in document.");
        }

        /// <summary>
        /// Gets a door family symbol from the document.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="familyName">The family name (optional).</param>
        /// <returns>A door family symbol.</returns>
        /// <exception cref="InvalidOperationException">Thrown when no door family is found.</exception>
        public static FamilySymbol GetDoorFamilySymbol(Document doc, string familyName = null)
        {
            var doorSymbols = new FilteredElementCollector(doc)
                .OfClass(typeof(FamilySymbol))
                .OfCategory(BuiltInCategory.OST_Doors)
                .OfType<FamilySymbol>();

            FamilySymbol symbol = null;

            if (!string.IsNullOrEmpty(familyName))
            {
                symbol = doorSymbols.FirstOrDefault(s => 
                    s.FamilyName.Equals(familyName, StringComparison.OrdinalIgnoreCase));
            }

            symbol ??= doorSymbols.FirstOrDefault();

            if (symbol == null)
            {
                throw new InvalidOperationException("No door family found in document.");
            }

            if (!symbol.IsActive)
            {
                symbol.Activate();
            }

            return symbol;
        }

        /// <summary>
        /// Gets a window family symbol from the document.
        /// </summary>
        /// <param name="doc">The document.</param>
        /// <param name="familyName">The family name (optional).</param>
        /// <returns>A window family symbol.</returns>
        /// <exception cref="InvalidOperationException">Thrown when no window family is found.</exception>
        public static FamilySymbol GetWindowFamilySymbol(Document doc, string familyName = null)
        {
            var windowSymbols = new FilteredElementCollector(doc)
                .OfClass(typeof(FamilySymbol))
                .OfCategory(BuiltInCategory.OST_Windows)
                .OfType<FamilySymbol>();

            FamilySymbol symbol = null;

            if (!string.IsNullOrEmpty(familyName))
            {
                symbol = windowSymbols.FirstOrDefault(s => 
                    s.FamilyName.Equals(familyName, StringComparison.OrdinalIgnoreCase));
            }

            symbol ??= windowSymbols.FirstOrDefault();

            if (symbol == null)
            {
                throw new InvalidOperationException("No window family found in document.");
            }

            if (!symbol.IsActive)
            {
                symbol.Activate();
            }

            return symbol;
        }

        /// <summary>
        /// Validates that a point is within acceptable coordinates.
        /// </summary>
        /// <param name="point">The point to validate.</param>
        /// <param name="parameterName">The parameter name for error reporting.</param>
        /// <exception cref="ArgumentException">Thrown when the point has invalid coordinates.</exception>
        public static void ValidatePoint(XYZ point, string parameterName = "point")
        {
            if (point == null)
                throw new ArgumentNullException(parameterName);

            const double maxCoordinate = 100000; // 100,000 feet limit

            if (Math.Abs(point.X) > maxCoordinate || 
                Math.Abs(point.Y) > maxCoordinate || 
                Math.Abs(point.Z) > maxCoordinate)
            {
                throw new ArgumentException($"Point coordinates are out of acceptable range: {point}", parameterName);
            }
        }

        /// <summary>
        /// Creates a line between two points with validation.
        /// </summary>
        /// <param name="start">The start point.</param>
        /// <param name="end">The end point.</param>
        /// <returns>The created line.</returns>
        /// <exception cref="ArgumentException">Thrown when points are invalid or identical.</exception>
        public static Line CreateValidatedLine(XYZ start, XYZ end)
        {
            ValidatePoint(start, nameof(start));
            ValidatePoint(end, nameof(end));

            if (start.IsAlmostEqualTo(end))
            {
                throw new ArgumentException("Start and end points cannot be identical.");
            }

            return Line.CreateBound(start, end);
        }
    }
}