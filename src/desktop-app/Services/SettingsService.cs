using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using ArchBuilder.Desktop.Models;
using ArchBuilder.Desktop.Core.Exceptions;

namespace ArchBuilder.Desktop.Services
{
    /// <summary>
    /// Service implementation for application settings management and configuration.
    /// Handles user preferences, application state, and configuration persistence with validation.
    /// </summary>
    public class SettingsService : ISettingsService
    {
        #region Private Fields

        private readonly ILogger<SettingsService> _logger;
        private readonly IConfigurationService _configurationService;
        private readonly string _settingsDirectory;
        private readonly string _userPreferencesFile;
        private readonly string _applicationConfigFile;
        private readonly JsonSerializerOptions _jsonOptions;
        private readonly Dictionary<string, object> _settingsCache;
        private UserPreferences _userPreferences;
        private ApplicationConfig _applicationConfig;

        #endregion

        #region Events

        /// <summary>
        /// Event raised when settings are changed.
        /// </summary>
        public event EventHandler<SettingsChangedEventArgs> SettingsChanged;

        #endregion

        #region Constructor

        /// <summary>
        /// Initializes a new instance of the SettingsService.
        /// </summary>
        /// <param name="logger">Logger instance for tracking operations</param>
        /// <param name="configurationService">Configuration service for application settings</param>
        public SettingsService(
            ILogger<SettingsService> logger,
            IConfigurationService configurationService)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _configurationService = configurationService ?? throw new ArgumentNullException(nameof(configurationService));

            // Initialize settings storage
            _settingsDirectory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "ArchBuilder", "Settings");
            
            _userPreferencesFile = Path.Combine(_settingsDirectory, "user-preferences.json");
            _applicationConfigFile = Path.Combine(_settingsDirectory, "application-config.json");

            // Ensure settings directory exists
            Directory.CreateDirectory(_settingsDirectory);

            // Configure JSON serialization
            _jsonOptions = new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                PropertyNameCaseInsensitive = true
            };

            // Initialize in-memory cache
            _settingsCache = new Dictionary<string, object>();

            _logger.LogInformation("SettingsService initialized with settings directory: {SettingsDirectory}", _settingsDirectory);

            // Load initial settings
            Task.Run(async () =>
            {
                try
                {
                    _userPreferences = await LoadUserPreferencesAsync();
                    _applicationConfig = await GetApplicationConfigAsync();
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to load initial settings");
                }
            });
        }

        #endregion

        #region Public Methods

        /// <summary>
        /// Gets application settings with optional default values.
        /// </summary>
        public async Task<T> GetSettingAsync<T>(string key, T defaultValue = default)
        {
            if (string.IsNullOrWhiteSpace(key))
                throw new ArgumentException("Setting key cannot be null or empty", nameof(key));

            try
            {
                _logger.LogDebug("Getting setting: {Key}", key);

                // Check cache first
                if (_settingsCache.TryGetValue(key, out var cachedValue) && cachedValue is T typedValue)
                {
                    return typedValue;
                }

                // Load from persistent storage
                var settingsFile = GetSettingsFilePath(key);
                if (File.Exists(settingsFile))
                {
                    var jsonContent = await File.ReadAllTextAsync(settingsFile);
                    var settings = JsonSerializer.Deserialize<Dictionary<string, object>>(jsonContent, _jsonOptions);

                    if (settings.TryGetValue(key, out var value))
                    {
                        var convertedValue = ConvertValue<T>(value);
                        _settingsCache[key] = convertedValue;
                        return convertedValue;
                    }
                }

                // Return default value if setting not found
                _logger.LogDebug("Setting not found, returning default value: {Key}", key);
                return defaultValue;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get setting: {Key}", key);
                return defaultValue;
            }
        }

        /// <summary>
        /// Sets an application setting value.
        /// </summary>
        public async Task SetSettingAsync<T>(string key, T value)
        {
            if (string.IsNullOrWhiteSpace(key))
                throw new ArgumentException("Setting key cannot be null or empty", nameof(key));

            try
            {
                _logger.LogDebug("Setting value: {Key}", key);

                // Update cache
                _settingsCache[key] = value;

                // Save to persistent storage
                var settingsFile = GetSettingsFilePath(key);
                var settings = new Dictionary<string, object>();

                // Load existing settings
                if (File.Exists(settingsFile))
                {
                    var jsonContent = await File.ReadAllTextAsync(settingsFile);
                    settings = JsonSerializer.Deserialize<Dictionary<string, object>>(jsonContent, _jsonOptions) ?? new Dictionary<string, object>();
                }

                // Update setting
                settings[key] = value;

                // Save to file
                var updatedJson = JsonSerializer.Serialize(settings, _jsonOptions);
                await File.WriteAllTextAsync(settingsFile, updatedJson);

                // Raise settings changed event
                OnSettingsChanged(new SettingsChangedEventArgs { Key = key, NewValue = value });

                _logger.LogDebug("Setting saved successfully: {Key}", key);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to set setting: {Key}", key);
                throw new SettingsException($"Failed to set setting '{key}': {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Removes a setting from storage.
        /// </summary>
        public async Task<bool> RemoveSettingAsync(string key)
        {
            if (string.IsNullOrWhiteSpace(key))
                throw new ArgumentException("Setting key cannot be null or empty", nameof(key));

            try
            {
                _logger.LogDebug("Removing setting: {Key}", key);

                // Remove from cache
                var removedFromCache = _settingsCache.Remove(key);

                // Remove from persistent storage
                var settingsFile = GetSettingsFilePath(key);
                if (File.Exists(settingsFile))
                {
                    var jsonContent = await File.ReadAllTextAsync(settingsFile);
                    var settings = JsonSerializer.Deserialize<Dictionary<string, object>>(jsonContent, _jsonOptions);

                    if (settings?.Remove(key) == true)
                    {
                        var updatedJson = JsonSerializer.Serialize(settings, _jsonOptions);
                        await File.WriteAllTextAsync(settingsFile, updatedJson);

                        // Raise settings changed event
                        OnSettingsChanged(new SettingsChangedEventArgs { Key = key, NewValue = null });

                        _logger.LogDebug("Setting removed successfully: {Key}", key);
                        return true;
                    }
                }

                return removedFromCache;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to remove setting: {Key}", key);
                throw new SettingsException($"Failed to remove setting '{key}': {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets all settings keys that match the specified prefix.
        /// </summary>
        public async Task<List<string>> GetSettingKeysAsync(string prefix = null)
        {
            try
            {
                _logger.LogDebug("Getting setting keys with prefix: {Prefix}", prefix ?? "all");

                var keys = new HashSet<string>();

                // Get keys from cache
                foreach (var key in _settingsCache.Keys)
                {
                    if (prefix == null || key.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    {
                        keys.Add(key);
                    }
                }

                // Get keys from persistent storage
                var settingsFiles = Directory.GetFiles(_settingsDirectory, "*.json");
                foreach (var file in settingsFiles)
                {
                    try
                    {
                        var jsonContent = await File.ReadAllTextAsync(file);
                        var settings = JsonSerializer.Deserialize<Dictionary<string, object>>(jsonContent, _jsonOptions);

                        if (settings != null)
                        {
                            foreach (var key in settings.Keys)
                            {
                                if (prefix == null || key.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                                {
                                    keys.Add(key);
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, "Failed to load settings from file: {File}", file);
                    }
                }

                return new List<string>(keys);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get setting keys");
                throw new SettingsException($"Failed to get setting keys: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Loads user preferences for the application.
        /// </summary>
        public async Task<UserPreferences> LoadUserPreferencesAsync()
        {
            try
            {
                if (_userPreferences != null)
                    return _userPreferences;

                _logger.LogDebug("Loading user preferences");

                if (File.Exists(_userPreferencesFile))
                {
                    var jsonContent = await File.ReadAllTextAsync(_userPreferencesFile);
                    _userPreferences = JsonSerializer.Deserialize<UserPreferences>(jsonContent, _jsonOptions);
                }

                if (_userPreferences == null)
                {
                    _userPreferences = CreateDefaultUserPreferences();
                    await SaveUserPreferencesAsync(_userPreferences);
                }

                _logger.LogDebug("User preferences loaded successfully");
                return _userPreferences;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load user preferences");
                _userPreferences = CreateDefaultUserPreferences();
                return _userPreferences;
            }
        }

        /// <summary>
        /// Saves user preferences to persistent storage.
        /// </summary>
        public async Task SaveUserPreferencesAsync(UserPreferences preferences)
        {
            if (preferences == null)
                throw new ArgumentNullException(nameof(preferences));

            try
            {
                _logger.LogDebug("Saving user preferences");

                preferences.UpdatedAt = DateTime.UtcNow;
                _userPreferences = preferences;

                var jsonContent = JsonSerializer.Serialize(preferences, _jsonOptions);
                await File.WriteAllTextAsync(_userPreferencesFile, jsonContent);

                // Raise settings changed event
                OnSettingsChanged(new SettingsChangedEventArgs 
                { 
                    Key = "UserPreferences", 
                    NewValue = preferences 
                });

                _logger.LogDebug("User preferences saved successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to save user preferences");
                throw new SettingsException($"Failed to save user preferences: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Resets user preferences to default values.
        /// </summary>
        public async Task<UserPreferences> ResetUserPreferencesToDefaultAsync()
        {
            try
            {
                _logger.LogInformation("Resetting user preferences to default");

                _userPreferences = CreateDefaultUserPreferences();
                await SaveUserPreferencesAsync(_userPreferences);

                _logger.LogInformation("User preferences reset successfully");
                return _userPreferences;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to reset user preferences");
                throw new SettingsException($"Failed to reset user preferences: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets the current application configuration.
        /// </summary>
        public async Task<ApplicationConfig> GetApplicationConfigAsync()
        {
            try
            {
                if (_applicationConfig != null)
                    return _applicationConfig;

                _logger.LogDebug("Loading application configuration");

                if (File.Exists(_applicationConfigFile))
                {
                    var jsonContent = await File.ReadAllTextAsync(_applicationConfigFile);
                    _applicationConfig = JsonSerializer.Deserialize<ApplicationConfig>(jsonContent, _jsonOptions);
                }

                if (_applicationConfig == null)
                {
                    _applicationConfig = CreateDefaultApplicationConfig();
                    await UpdateApplicationConfigAsync(_applicationConfig);
                }

                _logger.LogDebug("Application configuration loaded successfully");
                return _applicationConfig;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load application configuration");
                _applicationConfig = CreateDefaultApplicationConfig();
                return _applicationConfig;
            }
        }

        /// <summary>
        /// Updates application configuration settings.
        /// </summary>
        public async Task UpdateApplicationConfigAsync(ApplicationConfig config)
        {
            if (config == null)
                throw new ArgumentNullException(nameof(config));

            try
            {
                _logger.LogDebug("Updating application configuration");

                config.UpdatedAt = DateTime.UtcNow;
                _applicationConfig = config;

                var jsonContent = JsonSerializer.Serialize(config, _jsonOptions);
                await File.WriteAllTextAsync(_applicationConfigFile, jsonContent);

                // Raise settings changed event
                OnSettingsChanged(new SettingsChangedEventArgs 
                { 
                    Key = "ApplicationConfig", 
                    NewValue = config 
                });

                _logger.LogDebug("Application configuration updated successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to update application configuration");
                throw new SettingsException($"Failed to update application configuration: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets regional settings based on user location and preferences.
        /// </summary>
        public async Task<RegionalSettings> GetRegionalSettingsAsync()
        {
            try
            {
                var preferences = await LoadUserPreferencesAsync();
                return preferences.RegionalSettings ?? CreateDefaultRegionalSettings();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get regional settings");
                return CreateDefaultRegionalSettings();
            }
        }

        /// <summary>
        /// Sets regional settings for localization and measurement units.
        /// </summary>
        public async Task SetRegionalSettingsAsync(RegionalSettings settings)
        {
            if (settings == null)
                throw new ArgumentNullException(nameof(settings));

            try
            {
                var preferences = await LoadUserPreferencesAsync();
                preferences.RegionalSettings = settings;
                await SaveUserPreferencesAsync(preferences);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to set regional settings");
                throw new SettingsException($"Failed to set regional settings: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets cloud service connection settings.
        /// </summary>
        public async Task<CloudServiceSettings> GetCloudServiceSettingsAsync()
        {
            try
            {
                var config = await GetApplicationConfigAsync();
                return config.CloudServiceSettings ?? CreateDefaultCloudServiceSettings();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get cloud service settings");
                return CreateDefaultCloudServiceSettings();
            }
        }

        /// <summary>
        /// Updates cloud service connection settings.
        /// </summary>
        public async Task SetCloudServiceSettingsAsync(CloudServiceSettings settings)
        {
            if (settings == null)
                throw new ArgumentNullException(nameof(settings));

            try
            {
                var config = await GetApplicationConfigAsync();
                config.CloudServiceSettings = settings;
                await UpdateApplicationConfigAsync(config);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to set cloud service settings");
                throw new SettingsException($"Failed to set cloud service settings: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Exports all settings to a backup file.
        /// </summary>
        public async Task<bool> ExportSettingsAsync(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath))
                throw new ArgumentException("File path cannot be null or empty", nameof(filePath));

            try
            {
                _logger.LogInformation("Exporting settings to: {FilePath}", filePath);

                var allSettings = new
                {
                    UserPreferences = await LoadUserPreferencesAsync(),
                    ApplicationConfig = await GetApplicationConfigAsync(),
                    CustomSettings = _settingsCache,
                    ExportedAt = DateTime.UtcNow,
                    Version = _configurationService.GetVersionInfo().Version
                };

                var jsonContent = JsonSerializer.Serialize(allSettings, _jsonOptions);
                await File.WriteAllTextAsync(filePath, jsonContent);

                _logger.LogInformation("Settings exported successfully");
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to export settings");
                throw new SettingsException($"Failed to export settings: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Imports settings from a backup file.
        /// </summary>
        public async Task<ImportResult> ImportSettingsAsync(string filePath, bool overwriteExisting = false)
        {
            if (string.IsNullOrWhiteSpace(filePath))
                throw new ArgumentException("File path cannot be null or empty", nameof(filePath));

            if (!File.Exists(filePath))
                throw new FileNotFoundException($"Settings file not found: {filePath}");

            try
            {
                _logger.LogInformation("Importing settings from: {FilePath}", filePath);

                var result = new ImportResult
                {
                    IsSuccess = false,
                    ImportedCount = 0,
                    SkippedCount = 0,
                    ErrorCount = 0,
                    Messages = new List<string>()
                };

                var jsonContent = await File.ReadAllTextAsync(filePath);
                var importData = JsonSerializer.Deserialize<dynamic>(jsonContent, _jsonOptions);

                // Import user preferences
                if (importData.TryGetProperty("UserPreferences", out var userPrefsElement))
                {
                    try
                    {
                        var userPrefs = JsonSerializer.Deserialize<UserPreferences>(userPrefsElement.GetRawText(), _jsonOptions);
                        if (overwriteExisting || _userPreferences == null)
                        {
                            await SaveUserPreferencesAsync(userPrefs);
                            result.ImportedCount++;
                            result.Messages.Add("User preferences imported successfully");
                        }
                        else
                        {
                            result.SkippedCount++;
                            result.Messages.Add("User preferences skipped (already exists)");
                        }
                    }
                    catch (Exception ex)
                    {
                        result.ErrorCount++;
                        result.Messages.Add($"Failed to import user preferences: {ex.Message}");
                    }
                }

                // Import application config
                if (importData.TryGetProperty("ApplicationConfig", out var appConfigElement))
                {
                    try
                    {
                        var appConfig = JsonSerializer.Deserialize<ApplicationConfig>(appConfigElement.GetRawText(), _jsonOptions);
                        if (overwriteExisting || _applicationConfig == null)
                        {
                            await UpdateApplicationConfigAsync(appConfig);
                            result.ImportedCount++;
                            result.Messages.Add("Application configuration imported successfully");
                        }
                        else
                        {
                            result.SkippedCount++;
                            result.Messages.Add("Application configuration skipped (already exists)");
                        }
                    }
                    catch (Exception ex)
                    {
                        result.ErrorCount++;
                        result.Messages.Add($"Failed to import application configuration: {ex.Message}");
                    }
                }

                result.IsSuccess = result.ErrorCount == 0;
                _logger.LogInformation("Settings import completed: {Imported} imported, {Skipped} skipped, {Errors} errors", 
                    result.ImportedCount, result.SkippedCount, result.ErrorCount);

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to import settings");
                throw new SettingsException($"Failed to import settings: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Validates settings configuration and reports any issues.
        /// </summary>
        public async Task<SettingsValidationResult> ValidateSettingsAsync()
        {
            try
            {
                _logger.LogDebug("Validating settings configuration");

                var result = new SettingsValidationResult
                {
                    IsValid = true,
                    Issues = new List<ValidationIssue>(),
                    ValidatedAt = DateTime.UtcNow
                };

                // Validate user preferences
                var userPrefs = await LoadUserPreferencesAsync();
                ValidateUserPreferences(userPrefs, result);

                // Validate application config
                var appConfig = await GetApplicationConfigAsync();
                ValidateApplicationConfig(appConfig, result);

                result.IsValid = !result.Issues.Any(i => i.Severity == ValidationSeverity.Error);

                _logger.LogDebug("Settings validation completed: {IsValid}, {IssueCount} issues found", 
                    result.IsValid, result.Issues.Count);

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to validate settings");
                throw new SettingsException($"Failed to validate settings: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets the application theme settings.
        /// </summary>
        public async Task<ThemeSettings> GetThemeSettingsAsync()
        {
            try
            {
                var preferences = await LoadUserPreferencesAsync();
                return preferences.ThemeSettings ?? CreateDefaultThemeSettings();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get theme settings");
                return CreateDefaultThemeSettings();
            }
        }

        /// <summary>
        /// Sets the application theme settings.
        /// </summary>
        public async Task SetThemeSettingsAsync(ThemeSettings themeSettings)
        {
            if (themeSettings == null)
                throw new ArgumentNullException(nameof(themeSettings));

            try
            {
                var preferences = await LoadUserPreferencesAsync();
                preferences.ThemeSettings = themeSettings;
                await SaveUserPreferencesAsync(preferences);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to set theme settings");
                throw new SettingsException($"Failed to set theme settings: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets performance optimization settings.
        /// </summary>
        public async Task<PerformanceSettings> GetPerformanceSettingsAsync()
        {
            try
            {
                var config = await GetApplicationConfigAsync();
                return config.PerformanceSettings ?? CreateDefaultPerformanceSettings();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get performance settings");
                return CreateDefaultPerformanceSettings();
            }
        }

        /// <summary>
        /// Updates performance optimization settings.
        /// </summary>
        public async Task SetPerformanceSettingsAsync(PerformanceSettings settings)
        {
            if (settings == null)
                throw new ArgumentNullException(nameof(settings));

            try
            {
                var config = await GetApplicationConfigAsync();
                config.PerformanceSettings = settings;
                await UpdateApplicationConfigAsync(config);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to set performance settings");
                throw new SettingsException($"Failed to set performance settings: {ex.Message}", ex);
            }
        }

        #endregion

        #region Private Methods

        private string GetSettingsFilePath(string key)
        {
            // Organize settings into different files based on key prefix
            var prefix = key.Split(':')[0].ToLowerInvariant();
            return prefix switch
            {
                "user" => Path.Combine(_settingsDirectory, "user-settings.json"),
                "app" => Path.Combine(_settingsDirectory, "app-settings.json"),
                "ui" => Path.Combine(_settingsDirectory, "ui-settings.json"),
                "cloud" => Path.Combine(_settingsDirectory, "cloud-settings.json"),
                _ => Path.Combine(_settingsDirectory, "general-settings.json")
            };
        }

        private T ConvertValue<T>(object value)
        {
            if (value == null)
                return default(T);

            if (value is T directValue)
                return directValue;

            try
            {
                // Handle JSON element conversion
                if (value is JsonElement jsonElement)
                {
                    return JsonSerializer.Deserialize<T>(jsonElement.GetRawText(), _jsonOptions);
                }

                // Use built-in conversion
                return (T)Convert.ChangeType(value, typeof(T));
            }
            catch
            {
                return default(T);
            }
        }

        private UserPreferences CreateDefaultUserPreferences()
        {
            return new UserPreferences
            {
                Id = Guid.NewGuid().ToString(),
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow,
                Language = "en-US",
                ThemeSettings = CreateDefaultThemeSettings(),
                RegionalSettings = CreateDefaultRegionalSettings(),
                AutoSaveEnabled = true,
                AutoSaveIntervalMinutes = 5,
                EnableNotifications = true,
                EnableSounds = true,
                ShowWelcomeScreen = true,
                CheckForUpdates = true
            };
        }

        private ApplicationConfig CreateDefaultApplicationConfig()
        {
            return new ApplicationConfig
            {
                Id = Guid.NewGuid().ToString(),
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow,
                CloudServiceSettings = CreateDefaultCloudServiceSettings(),
                PerformanceSettings = CreateDefaultPerformanceSettings(),
                LoggingLevel = "Information",
                TelemetryEnabled = true,
                CacheEnabled = true,
                MaxCacheSizeMB = 500,
                SessionTimeoutMinutes = 60
            };
        }

        private ThemeSettings CreateDefaultThemeSettings()
        {
            return new ThemeSettings
            {
                ThemeName = "Apple Light",
                AccentColor = "#007AFF",
                FontFamily = "SF Pro Display",
                FontSize = 14,
                EnableAnimations = true,
                HighContrast = false
            };
        }

        private RegionalSettings CreateDefaultRegionalSettings()
        {
            return new RegionalSettings
            {
                Country = "US",
                Region = "North America",
                Locale = "en-US",
                MeasurementSystem = "Imperial",
                Currency = "USD",
                DateFormat = "MM/dd/yyyy",
                TimeFormat = "h:mm tt",
                NumberFormat = "en-US",
                BuildingCodes = new[] { "IBC", "IRC" }
            };
        }

        private CloudServiceSettings CreateDefaultCloudServiceSettings()
        {
            return new CloudServiceSettings
            {
                BaseUrl = "https://api.archbuilder.ai",
                TimeoutSeconds = 30,
                RetryAttempts = 3,
                EnableCaching = true,
                CacheExpirationMinutes = 15,
                ConnectionPoolSize = 10
            };
        }

        private PerformanceSettings CreateDefaultPerformanceSettings()
        {
            return new PerformanceSettings
            {
                MaxConcurrentOperations = 4,
                BackgroundProcessingEnabled = true,
                MemoryOptimizationEnabled = true,
                MaxMemoryUsageMB = 2048,
                GCCollectionMode = "Optimized"
            };
        }

        private void ValidateUserPreferences(UserPreferences preferences, SettingsValidationResult result)
        {
            if (preferences == null)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "UserPreferences",
                    Severity = ValidationSeverity.Error,
                    Message = "User preferences are null",
                    Recommendation = "Reset user preferences to default values"
                });
                return;
            }

            if (string.IsNullOrWhiteSpace(preferences.Language))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "UserPreferences",
                    Severity = ValidationSeverity.Warning,
                    Message = "Language setting is not configured",
                    Recommendation = "Set a valid language code"
                });
            }

            if (preferences.AutoSaveIntervalMinutes <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "UserPreferences",
                    Severity = ValidationSeverity.Warning,
                    Message = "Auto-save interval is invalid",
                    Recommendation = "Set auto-save interval to a positive value"
                });
            }
        }

        private void ValidateApplicationConfig(ApplicationConfig config, SettingsValidationResult result)
        {
            if (config == null)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "ApplicationConfig",
                    Severity = ValidationSeverity.Error,
                    Message = "Application configuration is null",
                    Recommendation = "Reset application configuration to default values"
                });
                return;
            }

            if (config.CloudServiceSettings?.BaseUrl != null && !Uri.IsWellFormedUriString(config.CloudServiceSettings.BaseUrl, UriKind.Absolute))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "ApplicationConfig",
                    Severity = ValidationSeverity.Error,
                    Message = "Cloud service base URL is invalid",
                    Recommendation = "Set a valid URL for cloud service"
                });
            }

            if (config.MaxCacheSizeMB <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "ApplicationConfig",
                    Severity = ValidationSeverity.Warning,
                    Message = "Cache size is invalid",
                    Recommendation = "Set cache size to a positive value"
                });
            }
        }

        private void OnSettingsChanged(SettingsChangedEventArgs args)
        {
            try
            {
                SettingsChanged?.Invoke(this, args);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error invoking SettingsChanged event");
            }
        }

        #endregion
    }
}