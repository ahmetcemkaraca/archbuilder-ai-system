using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ArchBuilder.Desktop.Models;

namespace ArchBuilder.Desktop.Services
{
    /// <summary>
    /// Interface for application configuration management and lifecycle services.
    /// Handles application initialization, resource management, and system configuration.
    /// </summary>
    public interface IConfigurationService
    {
        /// <summary>
        /// Initializes the application configuration and dependencies.
        /// </summary>
        /// <param name="configurationPath">Optional path to configuration files</param>
        /// <returns>Initialization result with status and any issues</returns>
        Task<InitializationResult> InitializeAsync(string configurationPath = null);

        /// <summary>
        /// Gets the current application environment (Development, Staging, Production).
        /// </summary>
        /// <returns>Current application environment</returns>
        string GetEnvironment();

        /// <summary>
        /// Gets application version information.
        /// </summary>
        /// <returns>Version details including build number and date</returns>
        ApplicationVersion GetVersionInfo();

        /// <summary>
        /// Gets configuration value by key with type conversion.
        /// </summary>
        /// <typeparam name="T">Type to convert the value to</typeparam>
        /// <param name="key">Configuration key (supports nested keys with colon separator)</param>
        /// <param name="defaultValue">Default value if key is not found</param>
        /// <returns>Configuration value or default value</returns>
        T GetConfigValue<T>(string key, T defaultValue = default);

        /// <summary>
        /// Checks if a configuration key exists.
        /// </summary>
        /// <param name="key">Configuration key to check</param>
        /// <returns>True if key exists, false otherwise</returns>
        bool HasConfigValue(string key);

        /// <summary>
        /// Gets all configuration keys under a specific section.
        /// </summary>
        /// <param name="section">Configuration section name</param>
        /// <returns>List of keys in the section</returns>
        List<string> GetConfigSection(string section);

        /// <summary>
        /// Gets database connection configuration.
        /// </summary>
        /// <returns>Database connection settings</returns>
        DatabaseConfig GetDatabaseConfig();

        /// <summary>
        /// Gets logging configuration settings.
        /// </summary>
        /// <returns>Logging configuration</returns>
        LoggingConfig GetLoggingConfig();

        /// <summary>
        /// Gets cloud service integration configuration.
        /// </summary>
        /// <returns>Cloud service settings</returns>
        CloudIntegrationConfig GetCloudIntegrationConfig();

        /// <summary>
        /// Gets AI service configuration and model settings.
        /// </summary>
        /// <returns>AI service configuration</returns>
        AIServiceConfig GetAIServiceConfig();

        /// <summary>
        /// Gets security and encryption configuration.
        /// </summary>
        /// <returns>Security configuration settings</returns>
        SecurityConfig GetSecurityConfig();

        /// <summary>
        /// Gets Revit integration configuration.
        /// </summary>
        /// <returns>Revit plugin configuration</returns>
        RevitIntegrationConfig GetRevitIntegrationConfig();

        /// <summary>
        /// Gets file processing configuration for supported formats.
        /// </summary>
        /// <returns>File processing configuration</returns>
        FileProcessingConfig GetFileProcessingConfig();

        /// <summary>
        /// Gets regional building code configuration.
        /// </summary>
        /// <returns>Building code configuration by region</returns>
        BuildingCodeConfig GetBuildingCodeConfig();

        /// <summary>
        /// Validates the current configuration and reports any issues.
        /// </summary>
        /// <returns>Validation result with configuration status</returns>
        Task<ConfigValidationResult> ValidateConfigurationAsync();

        /// <summary>
        /// Reloads configuration from all sources.
        /// </summary>
        /// <returns>Task representing the reload operation</returns>
        Task ReloadConfigurationAsync();

        /// <summary>
        /// Gets feature flags configuration.
        /// </summary>
        /// <returns>Feature flags settings</returns>
        FeatureFlags GetFeatureFlags();

        /// <summary>
        /// Checks if a specific feature is enabled.
        /// </summary>
        /// <param name="featureName">Name of the feature to check</param>
        /// <returns>True if feature is enabled, false otherwise</returns>
        bool IsFeatureEnabled(string featureName);

        /// <summary>
        /// Gets performance monitoring configuration.
        /// </summary>
        /// <returns>Performance monitoring settings</returns>
        PerformanceConfig GetPerformanceConfig();

        /// <summary>
        /// Gets application telemetry configuration.
        /// </summary>
        /// <returns>Telemetry configuration settings</returns>
        TelemetryConfig GetTelemetryConfig();

        /// <summary>
        /// Gets user interface configuration and theme settings.
        /// </summary>
        /// <returns>UI configuration</returns>
        UIConfig GetUIConfig();

        /// <summary>
        /// Gets localization and internationalization configuration.
        /// </summary>
        /// <returns>Localization configuration</returns>
        LocalizationConfig GetLocalizationConfig();

        /// <summary>
        /// Event raised when configuration is reloaded or changed.
        /// </summary>
        event EventHandler<ConfigurationChangedEventArgs> ConfigurationChanged;

        /// <summary>
        /// Saves current configuration state to persistent storage.
        /// </summary>
        /// <param name="configSection">Specific section to save (null for all)</param>
        /// <returns>Task representing the save operation</returns>
        Task SaveConfigurationAsync(string configSection = null);

        /// <summary>
        /// Resets configuration section to default values.
        /// </summary>
        /// <param name="configSection">Section to reset</param>
        /// <returns>Task representing the reset operation</returns>
        Task ResetConfigurationSectionAsync(string configSection);

        /// <summary>
        /// Gets diagnostic information about configuration state.
        /// </summary>
        /// <returns>Configuration diagnostic data</returns>
        Task<ConfigurationDiagnostics> GetDiagnosticsAsync();
    }
}