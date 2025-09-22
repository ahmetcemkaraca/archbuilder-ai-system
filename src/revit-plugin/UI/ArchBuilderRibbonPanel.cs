using System;
using System.Reflection;
using Autodesk.Revit.UI;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.UI
{
    /// <summary>
    /// Creates and manages the ArchBuilder.AI ribbon panel in Revit.
    /// Implements Apple-vari design principles with clean, professional UI.
    /// </summary>
    public class ArchBuilderRibbonPanel
    {
        private static readonly ILogger Logger = LoggerFactory.Create(builder => builder.AddConsole()).CreateLogger<ArchBuilderRibbonPanel>();
        private const string PANEL_NAME = "ArchBuilder.AI";

        /// <summary>
        /// Creates the main ArchBuilder.AI ribbon panel with AI-powered commands.
        /// </summary>
        /// <param name="application">The UI controlled application.</param>
        /// <returns>The created ribbon panel.</returns>
        public static RibbonPanel CreateRibbonPanel(UIControlledApplication application)
        {
            try
            {
                Logger.LogDebug("Creating ArchBuilder.AI ribbon panel");

                // Create the main panel
                var ribbonPanel = application.CreateRibbonPanel(PANEL_NAME);

                // Add main AI commands group
                AddAICommandsGroup(ribbonPanel);

                // Add separator
                ribbonPanel.AddSeparator();

                // Add analysis and review tools
                AddAnalysisToolsGroup(ribbonPanel);

                // Add separator
                ribbonPanel.AddSeparator();

                // Add settings and help
                AddSettingsGroup(ribbonPanel);

                Logger.LogInformation("ArchBuilder.AI ribbon panel created successfully");
                return ribbonPanel;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to create ArchBuilder.AI ribbon panel");
                throw new InvalidOperationException("Failed to create ribbon panel", ex);
            }
        }

        /// <summary>
        /// Adds the main AI commands group with split button design.
        /// </summary>
        /// <param name="ribbonPanel">The ribbon panel.</param>
        private static void AddAICommandsGroup(RibbonPanel ribbonPanel)
        {
            try
            {
                // Main AI Layout Generation split button
                var splitButtonData = new SplitButtonData("aiCommands", "AI Commands");
                var splitButton = ribbonPanel.AddItem(splitButtonData) as SplitButton;

                // Main AI layout command (primary action)
                var aiLayoutButtonData = new PushButtonData(
                    "aiLayout",
                    "Generate\nLayout",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.AILayoutCommand")
                {
                    LargeImage = GetEmbeddedImage("Icons.ai_layout_32.png"),
                    Image = GetEmbeddedImage("Icons.ai_layout_16.png"),
                    ToolTip = "Generate room layout using AI",
                    LongDescription = "Uses artificial intelligence to automatically generate optimized room layouts based on your requirements. " +
                                      "All AI outputs are validated for building code compliance and require professional review before implementation.",
                    AvailabilityClassName = "ArchBuilder.Revit.UI.Availability.DocumentAvailability"
                };
                splitButton.AddPushButton(aiLayoutButtonData);

                // Room creation command
                var createRoomButtonData = new PushButtonData(
                    "createRoom",
                    "Create Room",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.CreateRoomCommand")
                {
                    LargeImage = GetEmbeddedImage("Icons.room_32.png"),
                    ToolTip = "Create rooms with AI assistance",
                    LongDescription = "Create rooms in enclosed spaces with intelligent naming and property assignment."
                };
                splitButton.AddPushButton(createRoomButtonData);

                // Quick geometric operations
                var geometricOpsButtonData = new PushButtonData(
                    "geometricOps",
                    "Geometric\nOperations",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.GeometricOperationsCommand")
                {
                    LargeImage = GetEmbeddedImage("Icons.geometry_32.png"),
                    ToolTip = "Execute geometric layout operations",
                    LongDescription = "Perform complex geometric operations for layout generation including arrays, patterns, and custom shapes."
                };
                splitButton.AddPushButton(geometricOpsButtonData);

                Logger.LogDebug("AI commands group added to ribbon");
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to add AI commands group");
                throw;
            }
        }

        /// <summary>
        /// Adds analysis and review tools group.
        /// </summary>
        /// <param name="ribbonPanel">The ribbon panel.</param>
        private static void AddAnalysisToolsGroup(RibbonPanel ribbonPanel)
        {
            try
            {
                // Project Analysis button
                var analysisButtonData = new PushButtonData(
                    "projectAnalysis",
                    "Analyze\nProject",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.ProjectAnalysisCommand")
                {
                    LargeImage = GetEmbeddedImage("Icons.analysis_32.png"),
                    Image = GetEmbeddedImage("Icons.analysis_16.png"),
                    ToolTip = "Analyze existing Revit project",
                    LongDescription = "Comprehensive analysis of existing Revit projects including performance issues, " +
                                      "clash detection, building code compliance, and AI-powered improvement recommendations.",
                    AvailabilityClassName = "ArchBuilder.Revit.UI.Availability.DocumentAvailability"
                };
                ribbonPanel.AddItem(analysisButtonData);

                // AI Review Queue
                var reviewQueueButtonData = new PushButtonData(
                    "reviewQueue",
                    "Review\nQueue",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.AIReviewQueueCommand")
                {
                    Image = GetEmbeddedImage("Icons.review_16.png"),
                    ToolTip = "View pending AI outputs requiring review",
                    LongDescription = "Access the queue of AI-generated layouts and modifications awaiting professional review and approval."
                };
                ribbonPanel.AddItem(reviewQueueButtonData);

                Logger.LogDebug("Analysis tools group added to ribbon");
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to add analysis tools group");
                throw;
            }
        }

        /// <summary>
        /// Adds settings and help group.
        /// </summary>
        /// <param name="ribbonPanel">The ribbon panel.</param>
        private static void AddSettingsGroup(RibbonPanel ribbonPanel)
        {
            try
            {
                // Stack panel for settings and help
                var stackedItems = new StackedButtonData("settingsStack");
                
                // AI Settings
                var settingsButtonData = new PushButtonData(
                    "aiSettings",
                    "Settings",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.AISettingsCommand")
                {
                    Image = GetEmbeddedImage("Icons.settings_16.png"),
                    ToolTip = "Configure ArchBuilder.AI settings",
                    LongDescription = "Configure AI integration settings, cloud connectivity, regional building codes, and user preferences."
                };

                // Help and Documentation
                var helpButtonData = new PushButtonData(
                    "help",
                    "Help",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.HelpCommand")
                {
                    Image = GetEmbeddedImage("Icons.help_16.png"),
                    ToolTip = "ArchBuilder.AI help and documentation",
                    LongDescription = "Access comprehensive help documentation, tutorials, and troubleshooting guides for ArchBuilder.AI."
                };

                // About
                var aboutButtonData = new PushButtonData(
                    "about",
                    "About",
                    Assembly.GetExecutingAssembly().Location,
                    "ArchBuilder.Revit.Commands.AboutCommand")
                {
                    Image = GetEmbeddedImage("Icons.about_16.png"),
                    ToolTip = "About ArchBuilder.AI",
                    LongDescription = "Version information, licensing details, and credits for ArchBuilder.AI."
                };

                // Add stacked buttons
                var stackedButtons = ribbonPanel.AddStackedItems(settingsButtonData, helpButtonData, aboutButtonData);

                Logger.LogDebug("Settings group added to ribbon");
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to add settings group");
                throw;
            }
        }

        /// <summary>
        /// Gets an embedded image resource for ribbon icons.
        /// </summary>
        /// <param name="imageName">The image resource name.</param>
        /// <returns>The image source or null if not found.</returns>
        private static System.Windows.Media.ImageSource GetEmbeddedImage(string imageName)
        {
            try
            {
                // Try to load embedded resource
                var assembly = Assembly.GetExecutingAssembly();
                var resourceName = $"ArchBuilder.Revit.Resources.{imageName}";
                
                using (var stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream == null)
                    {
                        Logger.LogWarning("Embedded image not found: {ImageName}", imageName);
                        return null;
                    }

                    var bitmap = new System.Windows.Media.Imaging.BitmapImage();
                    bitmap.BeginInit();
                    bitmap.StreamSource = stream;
                    bitmap.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                    bitmap.EndInit();
                    bitmap.Freeze();

                    return bitmap;
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to load embedded image: {ImageName}", imageName);
                return null;
            }
        }

        /// <summary>
        /// Updates ribbon button states based on document context.
        /// </summary>
        /// <param name="hasActiveDocument">Whether there is an active document.</param>
        /// <param name="hasSelection">Whether there are selected elements.</param>
        public static void UpdateRibbonState(bool hasActiveDocument, bool hasSelection)
        {
            try
            {
                // This would be called from document events to update button availability
                // Implementation depends on maintaining references to ribbon buttons
                Logger.LogDebug("Updating ribbon state - Document: {HasDocument}, Selection: {HasSelection}", 
                    hasActiveDocument, hasSelection);
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to update ribbon state");
            }
        }
    }
}