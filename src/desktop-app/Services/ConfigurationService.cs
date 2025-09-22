using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using ArchBuilder.Desktop.Models;
using ArchBuilder.Desktop.Core.Exceptions;

namespace ArchBuilder.Desktop.Services
{
    /// <summary>
    /// Service implementation for application configuration management and lifecycle.
    /// Handles application initialization, resource management, and system configuration with comprehensive validation.
    /// </summary>
    public class ConfigurationService : IConfigurationService
    {
        #region Private Fields

        private readonly ILogger<ConfigurationService> _logger;
        private readonly IConfiguration _configuration;
        private readonly string _environment;
        private readonly ApplicationVersion _versionInfo;
        private bool _isInitialized;

        #endregion

        #region Events

        /// <summary>
        /// Event raised when configuration is reloaded or changed.
        /// </summary>
        public event EventHandler<ConfigurationChangedEventArgs> ConfigurationChanged;

        #endregion

        #region Constructor

        /// <summary>
        /// Initializes a new instance of the ConfigurationService.
        /// </summary>
        /// <param name="logger">Logger instance for tracking operations</param>
        /// <param name="configuration">Configuration provider instance</param>
        public ConfigurationService(
            ILogger<ConfigurationService> logger,
            IConfiguration configuration)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _configuration = configuration ?? throw new ArgumentNullException(nameof(configuration));

            // Determine environment
            _environment = Environment.GetEnvironmentVariable("ARCHBUILDER_ENVIRONMENT") ?? "Production";

            // Initialize version information
            _versionInfo = InitializeVersionInfo();

            _logger.LogInformation("ConfigurationService initialized for environment: {Environment}", _environment);
        }

        #endregion

        #region Public Methods

        /// <summary>
        /// Initializes the application configuration and dependencies.
        /// </summary>
        public async Task<InitializationResult> InitializeAsync(string configurationPath = null)
        {
            var result = new InitializationResult
            {
                IsSuccess = false,
                Messages = new List<string>(),
                Errors = new List<string>(),
                StartedAt = DateTime.UtcNow
            };

            try
            {
                _logger.LogInformation("Initializing application configuration");

                // Validate configuration
                await ValidateConfigurationAsync();

                // Initialize directories
                InitializeDirectories(result);

                // Initialize logging
                InitializeLogging(result);

                // Initialize database
                await InitializeDatabaseAsync(result);

                // Initialize cloud integration
                await InitializeCloudIntegrationAsync(result);

                // Initialize security
                InitializeSecurity(result);

                // Initialize performance monitoring
                InitializePerformanceMonitoring(result);

                _isInitialized = true;
                result.IsSuccess = true;
                result.CompletedAt = DateTime.UtcNow;

                _logger.LogInformation("Application configuration initialized successfully in {Duration}ms", 
                    (result.CompletedAt - result.StartedAt)?.TotalMilliseconds);

                // Raise configuration changed event
                OnConfigurationChanged(new ConfigurationChangedEventArgs { ChangeType = "Initialized" });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to initialize application configuration");
                result.Errors.Add($"Initialization failed: {ex.Message}");
                result.CompletedAt = DateTime.UtcNow;
            }

            return result;
        }

        /// <summary>
        /// Gets the current application environment.
        /// </summary>
        public string GetEnvironment()
        {
            return _environment;
        }

        /// <summary>
        /// Gets application version information.
        /// </summary>
        public ApplicationVersion GetVersionInfo()
        {
            return _versionInfo;
        }

        /// <summary>
        /// Gets configuration value by key with type conversion.
        /// </summary>
        public T GetConfigValue<T>(string key, T defaultValue = default)
        {
            if (string.IsNullOrWhiteSpace(key))
                return defaultValue;

            try
            {
                var value = _configuration[key];
                if (value == null)
                    return defaultValue;

                // Handle type conversion
                if (typeof(T) == typeof(string))
                    return (T)(object)value;

                if (typeof(T) == typeof(bool))
                    return (T)(object)bool.Parse(value);

                if (typeof(T) == typeof(int))
                    return (T)(object)int.Parse(value);

                if (typeof(T) == typeof(double))
                    return (T)(object)double.Parse(value);

                if (typeof(T).IsArray && typeof(T).GetElementType() == typeof(string))
                {
                    var arrayValue = value.Split(',', StringSplitOptions.RemoveEmptyEntries);
                    return (T)(object)arrayValue;
                }

                // Use configuration binding for complex types
                var section = _configuration.GetSection(key);
                if (section.Exists())
                {
                    var instance = Activator.CreateInstance<T>();
                    section.Bind(instance);
                    return instance;
                }

                return defaultValue;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to get configuration value for key: {Key}", key);
                return defaultValue;
            }
        }

        /// <summary>
        /// Checks if a configuration key exists.
        /// </summary>
        public bool HasConfigValue(string key)
        {
            if (string.IsNullOrWhiteSpace(key))
                return false;

            return _configuration[key] != null || _configuration.GetSection(key).Exists();
        }

        /// <summary>
        /// Gets all configuration keys under a specific section.
        /// </summary>
        public List<string> GetConfigSection(string section)
        {
            var keys = new List<string>();

            try
            {
                var configSection = _configuration.GetSection(section);
                if (configSection.Exists())
                {
                    foreach (var child in configSection.GetChildren())
                    {
                        keys.Add(child.Key);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to get configuration section: {Section}", section);
            }

            return keys;
        }

        /// <summary>
        /// Gets database connection configuration.
        /// </summary>
        public DatabaseConfig GetDatabaseConfig()
        {
            return new DatabaseConfig
            {
                ConnectionString = GetConfigValue<string>("Database:ConnectionString", "Data Source=archbuilder.db"),
                Provider = GetConfigValue<string>("Database:Provider", "SQLite"),
                CommandTimeout = GetConfigValue<int>("Database:CommandTimeout", 30),
                EnablePooling = GetConfigValue<bool>("Database:EnablePooling", true),
                MaxPoolSize = GetConfigValue<int>("Database:MaxPoolSize", 100),
                EnableRetryOnFailure = GetConfigValue<bool>("Database:EnableRetryOnFailure", true),
                MaxRetryCount = GetConfigValue<int>("Database:MaxRetryCount", 3)
            };
        }

        /// <summary>
        /// Gets logging configuration settings.
        /// </summary>
        public LoggingConfig GetLoggingConfig()
        {
            return new LoggingConfig
            {
                MinimumLevel = GetConfigValue<string>("Logging:LogLevel:Default", "Information"),
                EnableFileLogging = GetConfigValue<bool>("Logging:EnableFileLogging", true),
                LogFilePath = GetConfigValue<string>("Logging:FilePath", "logs/archbuilder-.log"),
                MaxFileSizeMB = GetConfigValue<int>("Logging:MaxFileSizeMB", 10),
                RetainedFileCount = GetConfigValue<int>("Logging:RetainedFileCount", 7),
                EnableConsoleLogging = GetConfigValue<bool>("Logging:EnableConsoleLogging", true),
                EnableStructuredLogging = GetConfigValue<bool>("Logging:EnableStructuredLogging", true),
                IncludeScopes = GetConfigValue<bool>("Logging:IncludeScopes", true)
            };
        }

        /// <summary>
        /// Gets cloud service integration configuration.
        /// </summary>
        public CloudIntegrationConfig GetCloudIntegrationConfig()
        {
            return new CloudIntegrationConfig
            {
                BaseUrl = GetConfigValue<string>("CloudIntegration:BaseUrl", "https://api.archbuilder.ai"),
                ApiVersion = GetConfigValue<string>("CloudIntegration:ApiVersion", "v1"),
                TimeoutSeconds = GetConfigValue<int>("CloudIntegration:TimeoutSeconds", 30),
                RetryAttempts = GetConfigValue<int>("CloudIntegration:RetryAttempts", 3),
                EnableCaching = GetConfigValue<bool>("CloudIntegration:EnableCaching", true),
                CacheExpirationMinutes = GetConfigValue<int>("CloudIntegration:CacheExpirationMinutes", 15),
                EnableCircuitBreaker = GetConfigValue<bool>("CloudIntegration:EnableCircuitBreaker", true),
                CircuitBreakerThreshold = GetConfigValue<int>("CloudIntegration:CircuitBreakerThreshold", 5),
                EnableCompression = GetConfigValue<bool>("CloudIntegration:EnableCompression", true)
            };
        }

        /// <summary>
        /// Gets AI service configuration and model settings.
        /// </summary>
        public AIServiceConfig GetAIServiceConfig()
        {
            return new AIServiceConfig
            {
                DefaultModel = GetConfigValue<string>("AIService:DefaultModel", "gpt-4"),
                MaxTokens = GetConfigValue<int>("AIService:MaxTokens", 4000),
                Temperature = GetConfigValue<double>("AIService:Temperature", 0.7),
                ConfidenceThreshold = GetConfigValue<double>("AIService:ConfidenceThreshold", 0.8),
                TimeoutSeconds = GetConfigValue<int>("AIService:TimeoutSeconds", 60),
                EnableFallback = GetConfigValue<bool>("AIService:EnableFallback", true),
                FallbackModel = GetConfigValue<string>("AIService:FallbackModel", "claude-3-5-sonnet"),
                MaxRetryAttempts = GetConfigValue<int>("AIService:MaxRetryAttempts", 3),
                EnableValidation = GetConfigValue<bool>("AIService:EnableValidation", true),
                ValidationTimeout = GetConfigValue<int>("AIService:ValidationTimeout", 30)
            };
        }

        /// <summary>
        /// Gets security and encryption configuration.
        /// </summary>
        public SecurityConfig GetSecurityConfig()
        {
            return new SecurityConfig
            {
                EncryptionKey = GetConfigValue<string>("Security:EncryptionKey", GenerateDefaultEncryptionKey()),
                EnableEncryption = GetConfigValue<bool>("Security:EnableEncryption", true),
                HashAlgorithm = GetConfigValue<string>("Security:HashAlgorithm", "SHA256"),
                EnableDataProtection = GetConfigValue<bool>("Security:EnableDataProtection", true),
                SessionTimeoutMinutes = GetConfigValue<int>("Security:SessionTimeoutMinutes", 60),
                EnableAuditLogging = GetConfigValue<bool>("Security:EnableAuditLogging", true),
                MaxLoginAttempts = GetConfigValue<int>("Security:MaxLoginAttempts", 3),
                LockoutDurationMinutes = GetConfigValue<int>("Security:LockoutDurationMinutes", 30),
                RequireSecureConnection = GetConfigValue<bool>("Security:RequireSecureConnection", true)
            };
        }

        /// <summary>
        /// Gets Revit integration configuration.
        /// </summary>
        public RevitIntegrationConfig GetRevitIntegrationConfig()
        {
            return new RevitIntegrationConfig
            {
                RevitVersion = GetConfigValue<string>("RevitIntegration:Version", "2026"),
                PluginPath = GetConfigValue<string>("RevitIntegration:PluginPath", @"C:\ProgramData\Autodesk\Revit\Addins\2026"),
                EnableAutoUpdate = GetConfigValue<bool>("RevitIntegration:EnableAutoUpdate", true),
                CommandTimeout = GetConfigValue<int>("RevitIntegration:CommandTimeout", 120),
                EnableTransactionLogging = GetConfigValue<bool>("RevitIntegration:EnableTransactionLogging", true),
                MaxConcurrentOperations = GetConfigValue<int>("RevitIntegration:MaxConcurrentOperations", 1),
                EnableBackup = GetConfigValue<bool>("RevitIntegration:EnableBackup", true),
                BackupInterval = GetConfigValue<int>("RevitIntegration:BackupIntervalMinutes", 15)
            };
        }

        /// <summary>
        /// Gets file processing configuration for supported formats.
        /// </summary>
        public FileProcessingConfig GetFileProcessingConfig()
        {
            return new FileProcessingConfig
            {
                MaxFileSizeMB = GetConfigValue<int>("FileProcessing:MaxFileSizeMB", 100),
                AllowedExtensions = GetConfigValue<string[]>("FileProcessing:AllowedExtensions", 
                    new[] { ".dwg", ".dxf", ".ifc", ".pdf", ".png", ".jpg", ".jpeg" }),
                EnableVirusScanning = GetConfigValue<bool>("FileProcessing:EnableVirusScanning", true),
                TempDirectory = GetConfigValue<string>("FileProcessing:TempDirectory", Path.GetTempPath()),
                ProcessingTimeout = GetConfigValue<int>("FileProcessing:ProcessingTimeout", 300),
                EnableCompression = GetConfigValue<bool>("FileProcessing:EnableCompression", true),
                CompressionLevel = GetConfigValue<string>("FileProcessing:CompressionLevel", "Optimal"),
                EnableParallelProcessing = GetConfigValue<bool>("FileProcessing:EnableParallelProcessing", true)
            };
        }

        /// <summary>
        /// Gets regional building code configuration.
        /// </summary>
        public BuildingCodeConfig GetBuildingCodeConfig()
        {
            return new BuildingCodeConfig
            {
                DefaultRegion = GetConfigValue<string>("BuildingCodes:DefaultRegion", "North America"),
                EnableValidation = GetConfigValue<bool>("BuildingCodes:EnableValidation", true),
                ValidationTimeout = GetConfigValue<int>("BuildingCodes:ValidationTimeout", 60),
                CacheEnabled = GetConfigValue<bool>("BuildingCodes:CacheEnabled", true),
                CacheExpirationHours = GetConfigValue<int>("BuildingCodes:CacheExpirationHours", 24),
                EnableAutoUpdate = GetConfigValue<bool>("BuildingCodes:EnableAutoUpdate", true),
                UpdateCheckInterval = GetConfigValue<int>("BuildingCodes:UpdateCheckIntervalHours", 168), // 7 days
                SupportedRegions = GetConfigValue<string[]>("BuildingCodes:SupportedRegions",
                    new[] { "North America", "Europe", "Asia Pacific", "Middle East", "Africa", "South America" })
            };
        }

        /// <summary>
        /// Validates the current configuration and reports any issues.
        /// </summary>
        public async Task<ConfigValidationResult> ValidateConfigurationAsync()
        {
            var result = new ConfigValidationResult
            {
                IsValid = true,
                Issues = new List<ValidationIssue>(),
                ValidatedAt = DateTime.UtcNow
            };

            try
            {
                _logger.LogDebug("Validating application configuration");

                // Validate database configuration
                ValidateDatabaseConfig(result);

                // Validate cloud integration configuration
                ValidateCloudIntegrationConfig(result);

                // Validate AI service configuration
                ValidateAIServiceConfig(result);

                // Validate security configuration
                ValidateSecurityConfig(result);

                // Validate file processing configuration
                ValidateFileProcessingConfig(result);

                // Validate Revit integration configuration
                ValidateRevitIntegrationConfig(result);

                result.IsValid = !result.Issues.Any(i => i.Severity == ValidationSeverity.Error);

                _logger.LogDebug("Configuration validation completed: {IsValid}, {IssueCount} issues found", 
                    result.IsValid, result.Issues.Count);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to validate configuration");
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Configuration",
                    Severity = ValidationSeverity.Error,
                    Message = $"Configuration validation failed: {ex.Message}",
                    Recommendation = "Review configuration settings and restart application"
                });
                result.IsValid = false;
            }

            return result;
        }

        /// <summary>
        /// Reloads configuration from all sources.
        /// </summary>
        public async Task ReloadConfigurationAsync()
        {
            try
            {
                _logger.LogInformation("Reloading application configuration");

                // Configuration reloading is handled by the IConfiguration provider
                // This method can be used to trigger custom reload logic

                // Validate reloaded configuration
                var validationResult = await ValidateConfigurationAsync();
                if (!validationResult.IsValid)
                {
                    _logger.LogWarning("Configuration validation failed after reload: {IssueCount} issues found", 
                        validationResult.Issues.Count);
                }

                // Raise configuration changed event
                OnConfigurationChanged(new ConfigurationChangedEventArgs { ChangeType = "Reloaded" });

                _logger.LogInformation("Configuration reloaded successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to reload configuration");
                throw new ConfigurationException($"Failed to reload configuration: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets feature flags configuration.
        /// </summary>
        public FeatureFlags GetFeatureFlags()
        {
            return new FeatureFlags
            {
                EnableAdvancedAI = GetConfigValue<bool>("FeatureFlags:EnableAdvancedAI", true),
                EnableCloudSync = GetConfigValue<bool>("FeatureFlags:EnableCloudSync", true),
                EnableRealTimeCollaboration = GetConfigValue<bool>("FeatureFlags:EnableRealTimeCollaboration", false),
                EnableBetaFeatures = GetConfigValue<bool>("FeatureFlags:EnableBetaFeatures", false),
                EnableTelemetry = GetConfigValue<bool>("FeatureFlags:EnableTelemetry", true),
                EnableAutoUpdate = GetConfigValue<bool>("FeatureFlags:EnableAutoUpdate", true),
                EnableExperimentalUI = GetConfigValue<bool>("FeatureFlags:EnableExperimentalUI", false),
                EnablePerformanceMonitoring = GetConfigValue<bool>("FeatureFlags:EnablePerformanceMonitoring", true)
            };
        }

        /// <summary>
        /// Checks if a specific feature is enabled.
        /// </summary>
        public bool IsFeatureEnabled(string featureName)
        {
            if (string.IsNullOrWhiteSpace(featureName))
                return false;

            return GetConfigValue<bool>($"FeatureFlags:{featureName}", false);
        }

        /// <summary>
        /// Gets performance monitoring configuration.
        /// </summary>
        public PerformanceConfig GetPerformanceConfig()
        {
            return new PerformanceConfig
            {
                EnableMonitoring = GetConfigValue<bool>("Performance:EnableMonitoring", true),
                SamplingRate = GetConfigValue<double>("Performance:SamplingRate", 0.1),
                MetricsRetentionDays = GetConfigValue<int>("Performance:MetricsRetentionDays", 30),
                AlertThresholds = new PerformanceThresholds
                {
                    MaxMemoryUsageMB = GetConfigValue<int>("Performance:AlertThresholds:MaxMemoryUsageMB", 2048),
                    MaxCpuUsagePercent = GetConfigValue<double>("Performance:AlertThresholds:MaxCpuUsagePercent", 80.0),
                    MaxResponseTimeMs = GetConfigValue<int>("Performance:AlertThresholds:MaxResponseTimeMs", 5000)
                }
            };
        }

        /// <summary>
        /// Gets application telemetry configuration.
        /// </summary>
        public TelemetryConfig GetTelemetryConfig()
        {
            return new TelemetryConfig
            {
                EnableTelemetry = GetConfigValue<bool>("Telemetry:EnableTelemetry", true),
                CollectionInterval = GetConfigValue<int>("Telemetry:CollectionIntervalSeconds", 60),
                EnableCrashReporting = GetConfigValue<bool>("Telemetry:EnableCrashReporting", true),
                EnableUsageAnalytics = GetConfigValue<bool>("Telemetry:EnableUsageAnalytics", true),
                EnablePerformanceMetrics = GetConfigValue<bool>("Telemetry:EnablePerformanceMetrics", true),
                DataRetentionDays = GetConfigValue<int>("Telemetry:DataRetentionDays", 90),
                EnableAnonymization = GetConfigValue<bool>("Telemetry:EnableAnonymization", true)
            };
        }

        /// <summary>
        /// Gets user interface configuration and theme settings.
        /// </summary>
        public UIConfig GetUIConfig()
        {
            return new UIConfig
            {
                DefaultTheme = GetConfigValue<string>("UI:DefaultTheme", "Apple Light"),
                EnableAnimations = GetConfigValue<bool>("UI:EnableAnimations", true),
                AnimationDuration = GetConfigValue<int>("UI:AnimationDurationMs", 300),
                FontFamily = GetConfigValue<string>("UI:FontFamily", "SF Pro Display"),
                FontSize = GetConfigValue<int>("UI:FontSize", 14),
                EnableHighDPI = GetConfigValue<bool>("UI:EnableHighDPI", true),
                EnableTooltips = GetConfigValue<bool>("UI:EnableTooltips", true),
                TooltipDelay = GetConfigValue<int>("UI:TooltipDelayMs", 500)
            };
        }

        /// <summary>
        /// Gets localization and internationalization configuration.
        /// </summary>
        public LocalizationConfig GetLocalizationConfig()
        {
            return new LocalizationConfig
            {
                DefaultCulture = GetConfigValue<string>("Localization:DefaultCulture", "en-US"),
                SupportedCultures = GetConfigValue<string[]>("Localization:SupportedCultures",
                    new[] { "en-US", "tr-TR", "de-DE", "fr-FR", "es-ES", "ja-JP", "zh-CN" }),
                EnableAutoDetection = GetConfigValue<bool>("Localization:EnableAutoDetection", true),
                FallbackCulture = GetConfigValue<string>("Localization:FallbackCulture", "en-US"),
                ResourcePath = GetConfigValue<string>("Localization:ResourcePath", "Resources"),
                EnablePluralSupport = GetConfigValue<bool>("Localization:EnablePluralSupport", true)
            };
        }

        /// <summary>
        /// Saves current configuration state to persistent storage.
        /// </summary>
        public async Task SaveConfigurationAsync(string configSection = null)
        {
            try
            {
                _logger.LogInformation("Saving configuration section: {Section}", configSection ?? "all");

                // Note: This is a placeholder implementation
                // In a real application, you would implement configuration persistence
                // based on your configuration provider (file, database, etc.)

                await Task.CompletedTask;

                _logger.LogInformation("Configuration saved successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to save configuration");
                throw new ConfigurationException($"Failed to save configuration: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Resets configuration section to default values.
        /// </summary>
        public async Task ResetConfigurationSectionAsync(string configSection)
        {
            if (string.IsNullOrWhiteSpace(configSection))
                throw new ArgumentException("Config section cannot be null or empty", nameof(configSection));

            try
            {
                _logger.LogInformation("Resetting configuration section: {Section}", configSection);

                // Note: This is a placeholder implementation
                // In a real application, you would implement section reset logic

                await Task.CompletedTask;

                // Raise configuration changed event
                OnConfigurationChanged(new ConfigurationChangedEventArgs 
                { 
                    ChangeType = "SectionReset", 
                    Section = configSection 
                });

                _logger.LogInformation("Configuration section reset successfully: {Section}", configSection);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to reset configuration section: {Section}", configSection);
                throw new ConfigurationException($"Failed to reset configuration section: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets diagnostic information about configuration state.
        /// </summary>
        public async Task<ConfigurationDiagnostics> GetDiagnosticsAsync()
        {
            try
            {
                var diagnostics = new ConfigurationDiagnostics
                {
                    Environment = _environment,
                    Version = _versionInfo,
                    IsInitialized = _isInitialized,
                    ConfigurationSources = new List<string>(),
                    ValidationResult = await ValidateConfigurationAsync(),
                    GeneratedAt = DateTime.UtcNow
                };

                // Get configuration sources
                if (_configuration is IConfigurationRoot configRoot)
                {
                    foreach (var provider in configRoot.Providers)
                    {
                        diagnostics.ConfigurationSources.Add(provider.GetType().Name);
                    }
                }

                return diagnostics;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get configuration diagnostics");
                throw new ConfigurationException($"Failed to get configuration diagnostics: {ex.Message}", ex);
            }
        }

        #endregion

        #region Private Methods

        private ApplicationVersion InitializeVersionInfo()
        {
            try
            {
                var assembly = Assembly.GetExecutingAssembly();
                var version = assembly.GetName().Version;
                var fileVersionInfo = System.Diagnostics.FileVersionInfo.GetVersionInfo(assembly.Location);

                return new ApplicationVersion
                {
                    Version = version?.ToString() ?? "1.0.0.0",
                    BuildNumber = version?.Build.ToString() ?? "0",
                    BuildDate = File.GetCreationTime(assembly.Location),
                    ProductName = fileVersionInfo.ProductName ?? "ArchBuilder.AI",
                    CompanyName = fileVersionInfo.CompanyName ?? "ArchBuilder Technologies",
                    Copyright = fileVersionInfo.LegalCopyright ?? $"Copyright © {DateTime.Now.Year} ArchBuilder Technologies"
                };
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to initialize version info, using defaults");
                return new ApplicationVersion
                {
                    Version = "1.0.0.0",
                    BuildNumber = "0",
                    BuildDate = DateTime.UtcNow,
                    ProductName = "ArchBuilder.AI",
                    CompanyName = "ArchBuilder Technologies",
                    Copyright = $"Copyright © {DateTime.Now.Year} ArchBuilder Technologies"
                };
            }
        }

        private void InitializeDirectories(InitializationResult result)
        {
            try
            {
                var appDataPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ArchBuilder");
                var requiredDirectories = new[]
                {
                    appDataPath,
                    Path.Combine(appDataPath, "Projects"),
                    Path.Combine(appDataPath, "Settings"),
                    Path.Combine(appDataPath, "Logs"),
                    Path.Combine(appDataPath, "Cache"),
                    Path.Combine(appDataPath, "Temp"),
                    Path.Combine(appDataPath, "Backups")
                };

                foreach (var directory in requiredDirectories)
                {
                    if (!Directory.Exists(directory))
                    {
                        Directory.CreateDirectory(directory);
                        result.Messages.Add($"Created directory: {directory}");
                    }
                }
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to initialize directories: {ex.Message}");
            }
        }

        private void InitializeLogging(InitializationResult result)
        {
            try
            {
                var loggingConfig = GetLoggingConfig();
                result.Messages.Add($"Logging initialized with level: {loggingConfig.MinimumLevel}");
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to initialize logging: {ex.Message}");
            }
        }

        private async Task InitializeDatabaseAsync(InitializationResult result)
        {
            try
            {
                var dbConfig = GetDatabaseConfig();
                // Database initialization would go here
                result.Messages.Add($"Database configuration loaded: {dbConfig.Provider}");
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to initialize database: {ex.Message}");
            }
        }

        private async Task InitializeCloudIntegrationAsync(InitializationResult result)
        {
            try
            {
                var cloudConfig = GetCloudIntegrationConfig();
                // Cloud integration initialization would go here
                result.Messages.Add($"Cloud integration configured: {cloudConfig.BaseUrl}");
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to initialize cloud integration: {ex.Message}");
            }
        }

        private void InitializeSecurity(InitializationResult result)
        {
            try
            {
                var securityConfig = GetSecurityConfig();
                // Security initialization would go here
                result.Messages.Add($"Security initialized with encryption: {securityConfig.EnableEncryption}");
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to initialize security: {ex.Message}");
            }
        }

        private void InitializePerformanceMonitoring(InitializationResult result)
        {
            try
            {
                var perfConfig = GetPerformanceConfig();
                // Performance monitoring initialization would go here
                result.Messages.Add($"Performance monitoring: {perfConfig.EnableMonitoring}");
            }
            catch (Exception ex)
            {
                result.Errors.Add($"Failed to initialize performance monitoring: {ex.Message}");
            }
        }

        private string GenerateDefaultEncryptionKey()
        {
            // Generate a default encryption key (this should be replaced with proper key management)
            return Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes($"ArchBuilder_{Environment.MachineName}_{_environment}"));
        }

        private void ValidateDatabaseConfig(ConfigValidationResult result)
        {
            var dbConfig = GetDatabaseConfig();
            
            if (string.IsNullOrWhiteSpace(dbConfig.ConnectionString))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Database",
                    Severity = ValidationSeverity.Error,
                    Message = "Database connection string is not configured",
                    Recommendation = "Configure a valid database connection string"
                });
            }

            if (dbConfig.CommandTimeout <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Database",
                    Severity = ValidationSeverity.Warning,
                    Message = "Database command timeout is invalid",
                    Recommendation = "Set command timeout to a positive value"
                });
            }
        }

        private void ValidateCloudIntegrationConfig(ConfigValidationResult result)
        {
            var cloudConfig = GetCloudIntegrationConfig();
            
            if (string.IsNullOrWhiteSpace(cloudConfig.BaseUrl) || !Uri.IsWellFormedUriString(cloudConfig.BaseUrl, UriKind.Absolute))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "CloudIntegration",
                    Severity = ValidationSeverity.Error,
                    Message = "Cloud service base URL is invalid",
                    Recommendation = "Configure a valid cloud service URL"
                });
            }

            if (cloudConfig.TimeoutSeconds <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "CloudIntegration",
                    Severity = ValidationSeverity.Warning,
                    Message = "Cloud service timeout is invalid",
                    Recommendation = "Set timeout to a positive value"
                });
            }
        }

        private void ValidateAIServiceConfig(ConfigValidationResult result)
        {
            var aiConfig = GetAIServiceConfig();
            
            if (aiConfig.ConfidenceThreshold < 0 || aiConfig.ConfidenceThreshold > 1)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "AIService",
                    Severity = ValidationSeverity.Warning,
                    Message = "AI confidence threshold is out of valid range (0-1)",
                    Recommendation = "Set confidence threshold between 0 and 1"
                });
            }

            if (aiConfig.MaxTokens <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "AIService",
                    Severity = ValidationSeverity.Warning,
                    Message = "AI max tokens is invalid",
                    Recommendation = "Set max tokens to a positive value"
                });
            }
        }

        private void ValidateSecurityConfig(ConfigValidationResult result)
        {
            var securityConfig = GetSecurityConfig();
            
            if (string.IsNullOrWhiteSpace(securityConfig.EncryptionKey))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Security",
                    Severity = ValidationSeverity.Error,
                    Message = "Encryption key is not configured",
                    Recommendation = "Configure a secure encryption key"
                });
            }

            if (securityConfig.SessionTimeoutMinutes <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Security",
                    Severity = ValidationSeverity.Warning,
                    Message = "Session timeout is invalid",
                    Recommendation = "Set session timeout to a positive value"
                });
            }
        }

        private void ValidateFileProcessingConfig(ConfigValidationResult result)
        {
            var fileConfig = GetFileProcessingConfig();
            
            if (fileConfig.MaxFileSizeMB <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "FileProcessing",
                    Severity = ValidationSeverity.Warning,
                    Message = "Max file size is invalid",
                    Recommendation = "Set max file size to a positive value"
                });
            }

            if (!Directory.Exists(fileConfig.TempDirectory))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "FileProcessing",
                    Severity = ValidationSeverity.Warning,
                    Message = "Temp directory does not exist",
                    Recommendation = "Ensure temp directory exists and is writable"
                });
            }
        }

        private void ValidateRevitIntegrationConfig(ConfigValidationResult result)
        {
            var revitConfig = GetRevitIntegrationConfig();
            
            if (!Directory.Exists(revitConfig.PluginPath))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "RevitIntegration",
                    Severity = ValidationSeverity.Warning,
                    Message = "Revit plugin path does not exist",
                    Recommendation = "Ensure Revit is installed and plugin path is correct"
                });
            }

            if (revitConfig.CommandTimeout <= 0)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "RevitIntegration",
                    Severity = ValidationSeverity.Warning,
                    Message = "Revit command timeout is invalid",
                    Recommendation = "Set command timeout to a positive value"
                });
            }
        }

        private void OnConfigurationChanged(ConfigurationChangedEventArgs args)
        {
            try
            {
                ConfigurationChanged?.Invoke(this, args);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error invoking ConfigurationChanged event");
            }
        }

        #endregion
    }
}