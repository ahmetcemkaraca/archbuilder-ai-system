using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ArchBuilder.Desktop.Models;

namespace ArchBuilder.Desktop.Services
{
    /// <summary>
    /// Interface for application settings management and configuration services.
    /// Handles user preferences, application state, and configuration persistence.
    /// </summary>
    public interface ISettingsService
    {
        /// <summary>
        /// Gets application settings with optional default values.
        /// </summary>
        /// <typeparam name="T">Type of the setting value</typeparam>
        /// <param name="key">Setting key identifier</param>
        /// <param name="defaultValue">Default value if setting doesn't exist</param>
        /// <returns>Setting value or default value</returns>
        Task<T> GetSettingAsync<T>(string key, T defaultValue = default);

        /// <summary>
        /// Sets an application setting value.
        /// </summary>
        /// <typeparam name="T">Type of the setting value</typeparam>
        /// <param name="key">Setting key identifier</param>
        /// <param name="value">Value to store</param>
        /// <returns>Task representing the operation</returns>
        Task SetSettingAsync<T>(string key, T value);

        /// <summary>
        /// Removes a setting from storage.
        /// </summary>
        /// <param name="key">Setting key to remove</param>
        /// <returns>True if setting was removed, false if it didn't exist</returns>
        Task<bool> RemoveSettingAsync(string key);

        /// <summary>
        /// Gets all settings keys that match the specified prefix.
        /// </summary>
        /// <param name="prefix">Key prefix to search for</param>
        /// <returns>List of matching setting keys</returns>
        Task<List<string>> GetSettingKeysAsync(string prefix = null);

        /// <summary>
        /// Loads user preferences for the application.
        /// </summary>
        /// <returns>Current user preferences</returns>
        Task<UserPreferences> LoadUserPreferencesAsync();

        /// <summary>
        /// Saves user preferences to persistent storage.
        /// </summary>
        /// <param name="preferences">User preferences to save</param>
        /// <returns>Task representing the save operation</returns>
        Task SaveUserPreferencesAsync(UserPreferences preferences);

        /// <summary>
        /// Resets user preferences to default values.
        /// </summary>
        /// <returns>Default user preferences</returns>
        Task<UserPreferences> ResetUserPreferencesToDefaultAsync();

        /// <summary>
        /// Gets the current application configuration.
        /// </summary>
        /// <returns>Application configuration settings</returns>
        Task<ApplicationConfig> GetApplicationConfigAsync();

        /// <summary>
        /// Updates application configuration settings.
        /// </summary>
        /// <param name="config">New configuration to apply</param>
        /// <returns>Task representing the update operation</returns>
        Task UpdateApplicationConfigAsync(ApplicationConfig config);

        /// <summary>
        /// Gets regional settings based on user location and preferences.
        /// </summary>
        /// <returns>Regional configuration settings</returns>
        Task<RegionalSettings> GetRegionalSettingsAsync();

        /// <summary>
        /// Sets regional settings for localization and measurement units.
        /// </summary>
        /// <param name="settings">Regional settings to apply</param>
        /// <returns>Task representing the operation</returns>
        Task SetRegionalSettingsAsync(RegionalSettings settings);

        /// <summary>
        /// Gets cloud service connection settings.
        /// </summary>
        /// <returns>Cloud service configuration</returns>
        Task<CloudServiceSettings> GetCloudServiceSettingsAsync();

        /// <summary>
        /// Updates cloud service connection settings.
        /// </summary>
        /// <param name="settings">Cloud service settings to save</param>
        /// <returns>Task representing the update operation</returns>
        Task SetCloudServiceSettingsAsync(CloudServiceSettings settings);

        /// <summary>
        /// Exports all settings to a backup file.
        /// </summary>
        /// <param name="filePath">Path to save the settings backup</param>
        /// <returns>True if export was successful</returns>
        Task<bool> ExportSettingsAsync(string filePath);

        /// <summary>
        /// Imports settings from a backup file.
        /// </summary>
        /// <param name="filePath">Path to the settings backup file</param>
        /// <param name="overwriteExisting">Whether to overwrite existing settings</param>
        /// <returns>Import result with details</returns>
        Task<ImportResult> ImportSettingsAsync(string filePath, bool overwriteExisting = false);

        /// <summary>
        /// Validates settings configuration and reports any issues.
        /// </summary>
        /// <returns>Validation result with any configuration issues</returns>
        Task<SettingsValidationResult> ValidateSettingsAsync();

        /// <summary>
        /// Gets the application theme settings.
        /// </summary>
        /// <returns>Current theme configuration</returns>
        Task<ThemeSettings> GetThemeSettingsAsync();

        /// <summary>
        /// Sets the application theme settings.
        /// </summary>
        /// <param name="themeSettings">Theme configuration to apply</param>
        /// <returns>Task representing the operation</returns>
        Task SetThemeSettingsAsync(ThemeSettings themeSettings);

        /// <summary>
        /// Event raised when settings are changed.
        /// </summary>
        event EventHandler<SettingsChangedEventArgs> SettingsChanged;

        /// <summary>
        /// Gets performance optimization settings.
        /// </summary>
        /// <returns>Performance settings configuration</returns>
        Task<PerformanceSettings> GetPerformanceSettingsAsync();

        /// <summary>
        /// Updates performance optimization settings.
        /// </summary>
        /// <param name="settings">Performance settings to apply</param>
        /// <returns>Task representing the operation</returns>
        Task SetPerformanceSettingsAsync(PerformanceSettings settings);
    }
}