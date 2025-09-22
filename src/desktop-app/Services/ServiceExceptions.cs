using System;

namespace ArchBuilder.Desktop.Services
{
    /// <summary>
    /// Exception thrown when project operations fail.
    /// </summary>
    public class ProjectException : Exception
    {
        /// <summary>
        /// Gets the error code associated with the project error.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Gets the project identifier associated with the error.
        /// </summary>
        public string ProjectId { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ProjectException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public ProjectException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        public ProjectException(string message, string errorCode) : base(message)
        {
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="projectId">The project identifier.</param>
        public ProjectException(string message, string errorCode, string projectId) : base(message)
        {
            ErrorCode = errorCode;
            ProjectId = projectId;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="projectId">The project identifier.</param>
        /// <param name="innerException">The inner exception.</param>
        public ProjectException(string message, string errorCode, string projectId, Exception innerException) 
            : base(message, innerException)
        {
            ErrorCode = errorCode;
            ProjectId = projectId;
        }
    }

    /// <summary>
    /// Exception thrown when project creation fails.
    /// </summary>
    public class ProjectCreationException : ProjectException
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectCreationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ProjectCreationException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectCreationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public ProjectCreationException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectCreationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="projectId">The project identifier.</param>
        public ProjectCreationException(string message, string projectId) : base(message, "PROJECT_CREATION_FAILED", projectId)
        {
        }
    }

    /// <summary>
    /// Exception thrown when project loading fails.
    /// </summary>
    public class ProjectLoadException : ProjectException
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectLoadException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ProjectLoadException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectLoadException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public ProjectLoadException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectLoadException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="projectId">The project identifier.</param>
        public ProjectLoadException(string message, string projectId) : base(message, "PROJECT_LOAD_FAILED", projectId)
        {
        }
    }

    /// <summary>
    /// Exception thrown when project validation fails.
    /// </summary>
    public class ProjectValidationException : ProjectException
    {
        /// <summary>
        /// Gets the validation errors.
        /// </summary>
        public string[] ValidationErrors { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="validationErrors">The validation errors.</param>
        public ProjectValidationException(string message, string[] validationErrors) 
            : base(message, "PROJECT_VALIDATION_FAILED")
        {
            ValidationErrors = validationErrors ?? new string[0];
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ProjectValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="projectId">The project identifier.</param>
        /// <param name="validationErrors">The validation errors.</param>
        public ProjectValidationException(string message, string projectId, string[] validationErrors) 
            : base(message, "PROJECT_VALIDATION_FAILED", projectId)
        {
            ValidationErrors = validationErrors ?? new string[0];
        }
    }

    /// <summary>
    /// Exception thrown when settings operations fail.
    /// </summary>
    public class SettingsException : Exception
    {
        /// <summary>
        /// Gets the error code associated with the settings error.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Gets the setting key associated with the error.
        /// </summary>
        public string SettingKey { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public SettingsException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public SettingsException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        public SettingsException(string message, string errorCode) : base(message)
        {
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="settingKey">The setting key.</param>
        public SettingsException(string message, string errorCode, string settingKey) : base(message)
        {
            ErrorCode = errorCode;
            SettingKey = settingKey;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="settingKey">The setting key.</param>
        /// <param name="innerException">The inner exception.</param>
        public SettingsException(string message, string errorCode, string settingKey, Exception innerException) 
            : base(message, innerException)
        {
            ErrorCode = errorCode;
            SettingKey = settingKey;
        }
    }

    /// <summary>
    /// Exception thrown when settings loading fails.
    /// </summary>
    public class SettingsLoadException : SettingsException
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsLoadException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public SettingsLoadException(string message) : base(message, "SETTINGS_LOAD_FAILED")
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsLoadException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public SettingsLoadException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsLoadException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="settingKey">The setting key.</param>
        public SettingsLoadException(string message, string settingKey) 
            : base(message, "SETTINGS_LOAD_FAILED", settingKey)
        {
        }
    }

    /// <summary>
    /// Exception thrown when settings saving fails.
    /// </summary>
    public class SettingsSaveException : SettingsException
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsSaveException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public SettingsSaveException(string message) : base(message, "SETTINGS_SAVE_FAILED")
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsSaveException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public SettingsSaveException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="SettingsSaveException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="settingKey">The setting key.</param>
        public SettingsSaveException(string message, string settingKey) 
            : base(message, "SETTINGS_SAVE_FAILED", settingKey)
        {
        }
    }

    /// <summary>
    /// Exception thrown when configuration operations fail.
    /// </summary>
    public class ConfigurationException : Exception
    {
        /// <summary>
        /// Gets the error code associated with the configuration error.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Gets the configuration section associated with the error.
        /// </summary>
        public string Section { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ConfigurationException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public ConfigurationException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        public ConfigurationException(string message, string errorCode) : base(message)
        {
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="section">The configuration section.</param>
        public ConfigurationException(string message, string errorCode, string section) : base(message)
        {
            ErrorCode = errorCode;
            Section = section;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="section">The configuration section.</param>
        /// <param name="innerException">The inner exception.</param>
        public ConfigurationException(string message, string errorCode, string section, Exception innerException) 
            : base(message, innerException)
        {
            ErrorCode = errorCode;
            Section = section;
        }
    }

    /// <summary>
    /// Exception thrown when configuration initialization fails.
    /// </summary>
    public class ConfigurationInitializationException : ConfigurationException
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationInitializationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ConfigurationInitializationException(string message) : base(message, "CONFIGURATION_INIT_FAILED")
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationInitializationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public ConfigurationInitializationException(string message, Exception innerException) 
            : base(message, "CONFIGURATION_INIT_FAILED", null, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationInitializationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="section">The configuration section.</param>
        public ConfigurationInitializationException(string message, string section) 
            : base(message, "CONFIGURATION_INIT_FAILED", section)
        {
        }
    }

    /// <summary>
    /// Exception thrown when configuration validation fails.
    /// </summary>
    public class ConfigurationValidationException : ConfigurationException
    {
        /// <summary>
        /// Gets the validation errors.
        /// </summary>
        public string[] ValidationErrors { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="validationErrors">The validation errors.</param>
        public ConfigurationValidationException(string message, string[] validationErrors) 
            : base(message, "CONFIGURATION_VALIDATION_FAILED")
        {
            ValidationErrors = validationErrors ?? new string[0];
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ConfigurationValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="section">The configuration section.</param>
        /// <param name="validationErrors">The validation errors.</param>
        public ConfigurationValidationException(string message, string section, string[] validationErrors) 
            : base(message, "CONFIGURATION_VALIDATION_FAILED", section)
        {
            ValidationErrors = validationErrors ?? new string[0];
        }
    }

    /// <summary>
    /// Exception thrown when service operations fail.
    /// </summary>
    public class ServiceException : Exception
    {
        /// <summary>
        /// Gets the error code associated with the service error.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Gets the service name associated with the error.
        /// </summary>
        public string ServiceName { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="ServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ServiceException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public ServiceException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="serviceName">The service name.</param>
        public ServiceException(string message, string errorCode, string serviceName) : base(message)
        {
            ErrorCode = errorCode;
            ServiceName = serviceName;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="serviceName">The service name.</param>
        /// <param name="innerException">The inner exception.</param>
        public ServiceException(string message, string errorCode, string serviceName, Exception innerException) 
            : base(message, innerException)
        {
            ErrorCode = errorCode;
            ServiceName = serviceName;
        }
    }

    /// <summary>
    /// Exception thrown when validation operations fail.
    /// </summary>
    public class ValidationException : Exception
    {
        /// <summary>
        /// Gets the validation errors.
        /// </summary>
        public string[] ValidationErrors { get; }

        /// <summary>
        /// Gets the field name associated with the validation error.
        /// </summary>
        public string FieldName { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="ValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public ValidationException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="fieldName">The field name.</param>
        public ValidationException(string message, string fieldName) : base(message)
        {
            FieldName = fieldName;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="validationErrors">The validation errors.</param>
        public ValidationException(string message, string[] validationErrors) : base(message)
        {
            ValidationErrors = validationErrors ?? new string[0];
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ValidationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="fieldName">The field name.</param>
        /// <param name="validationErrors">The validation errors.</param>
        public ValidationException(string message, string fieldName, string[] validationErrors) : base(message)
        {
            FieldName = fieldName;
            ValidationErrors = validationErrors ?? new string[0];
        }
    }

    /// <summary>
    /// Exception thrown when cloud service operations fail.
    /// </summary>
    public class CloudServiceException : Exception
    {
        /// <summary>
        /// Gets the HTTP status code associated with the error.
        /// </summary>
        public int? StatusCode { get; }

        /// <summary>
        /// Gets the error code from the cloud service.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="CloudServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        public CloudServiceException(string message) : base(message)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="CloudServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="innerException">The inner exception.</param>
        public CloudServiceException(string message, Exception innerException) : base(message, innerException)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="CloudServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="statusCode">The HTTP status code.</param>
        /// <param name="errorCode">The error code.</param>
        public CloudServiceException(string message, int statusCode, string errorCode) : base(message)
        {
            StatusCode = statusCode;
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="CloudServiceException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="statusCode">The HTTP status code.</param>
        /// <param name="errorCode">The error code.</param>
        /// <param name="innerException">The inner exception.</param>
        public CloudServiceException(string message, int statusCode, string errorCode, Exception innerException) 
            : base(message, innerException)
        {
            StatusCode = statusCode;
            ErrorCode = errorCode;
        }
    }

    /// <summary>
    /// Exception thrown when file operations fail.
    /// </summary>
    public class FileOperationException : Exception
    {
        /// <summary>
        /// Gets the file path associated with the error.
        /// </summary>
        public string FilePath { get; }

        /// <summary>
        /// Gets the operation that failed.
        /// </summary>
        public string Operation { get; }

        /// <summary>
        /// Initializes a new instance of the <see cref="FileOperationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="filePath">The file path.</param>
        /// <param name="operation">The operation that failed.</param>
        public FileOperationException(string message, string filePath, string operation) : base(message)
        {
            FilePath = filePath;
            Operation = operation;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="FileOperationException"/> class.
        /// </summary>
        /// <param name="message">The error message.</param>
        /// <param name="filePath">The file path.</param>
        /// <param name="operation">The operation that failed.</param>
        /// <param name="innerException">The inner exception.</param>
        public FileOperationException(string message, string filePath, string operation, Exception innerException) 
            : base(message, innerException)
        {
            FilePath = filePath;
            Operation = operation;
        }
    }
}