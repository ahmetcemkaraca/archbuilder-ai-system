using Autodesk.Revit.UI;
using Serilog;
using System;
using System.Reflection;

namespace ArchBuilderRevit;

/// <summary>
/// Main application class for ArchBuilder.AI Revit Plugin
/// Implements IExternalApplication for Revit plugin lifecycle management
/// </summary>
public class Program : IExternalApplication
{
    private static readonly string AssemblyPath = Assembly.GetExecutingAssembly().Location;
    private static readonly string AssemblyDirectory = System.IO.Path.GetDirectoryName(AssemblyPath) ?? "";

    /// <summary>
    /// Called when Revit starts up
    /// </summary>
    public Result OnStartup(UIControlledApplication application)
    {
        try
        {
            // Initialize logging
            InitializeLogging();
            
            Log.Information("ArchBuilder.AI Plugin starting up");
            
            // Create ribbon panel
            CreateRibbonPanel(application);
            
            Log.Information("ArchBuilder.AI Plugin started successfully");
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Failed to start ArchBuilder.AI Plugin");
            return Result.Failed;
        }
    }

    /// <summary>
    /// Called when Revit shuts down
    /// </summary>
    public Result OnShutdown(UIControlledApplication application)
    {
        try
        {
            Log.Information("ArchBuilder.AI Plugin shutting down");
            Log.CloseAndFlush();
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Error during ArchBuilder.AI Plugin shutdown");
            return Result.Failed;
        }
    }

    /// <summary>
    /// Initialize Serilog logging
    /// </summary>
    private static void InitializeLogging()
    {
        var logPath = System.IO.Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "ArchBuilder.AI", 
            "Logs", 
            "revit-plugin-.txt"
        );

        Log.Logger = new LoggerConfiguration()
            .WriteTo.File(
                logPath, 
                rollingInterval: RollingInterval.Day,
                retainedFileCountLimit: 30,
                fileSizeLimitBytes: 10_000_000,
                rollOnFileSizeLimit: true
            )
            .CreateLogger();
    }

    /// <summary>
    /// Create ArchBuilder.AI ribbon panel with commands
    /// </summary>
    private static void CreateRibbonPanel(UIControlledApplication application)
    {
        // Create ribbon panel
        var ribbonPanel = application.CreateRibbonPanel("ArchBuilder.AI");

        // Create AI Design button
        var aiDesignButton = new PushButtonData(
            "ArchBuilder_AIDesign",
            "AI Design",
            AssemblyPath,
            "ArchBuilderRevit.Commands.AIDesignCommand"
        );
        
        aiDesignButton.ToolTip = "Generate architectural designs using AI";
        aiDesignButton.LongDescription = "Transform natural language descriptions into detailed architectural layouts using AI-powered automation.";
        
        var aiDesignPushButton = ribbonPanel.AddItem(aiDesignButton) as PushButton;

        // Create Project Analysis button
        var projectAnalysisButton = new PushButtonData(
            "ArchBuilder_ProjectAnalysis",
            "Project Analysis",
            AssemblyPath,
            "ArchBuilderRevit.Commands.ProjectAnalysisCommand"
        );
        
        projectAnalysisButton.ToolTip = "Analyze existing Revit projects";
        projectAnalysisButton.LongDescription = "Analyze current Revit project and get AI-powered improvement recommendations.";
        
        var projectAnalysisPushButton = ribbonPanel.AddItem(projectAnalysisButton) as PushButton;

        // Create Settings button
        var settingsButton = new PushButtonData(
            "ArchBuilder_Settings",
            "Settings",
            AssemblyPath,
            "ArchBuilderRevit.Commands.SettingsCommand"
        );
        
        settingsButton.ToolTip = "ArchBuilder.AI Settings";
        settingsButton.LongDescription = "Configure ArchBuilder.AI preferences, cloud connection, and regional settings.";
        
        var settingsPushButton = ribbonPanel.AddItem(settingsButton) as PushButton;

        Log.Information("ArchBuilder.AI ribbon panel created with {ButtonCount} buttons", 3);
    }
}