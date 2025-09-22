using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;

namespace ArchBuilder.Models
{
    /// <summary>
    /// Core project information model following ArchBuilder.AI data structure standards.
    /// Represents a design project with multi-format CAD file support and global compliance.
    /// </summary>
    public class ProjectInfo : INotifyPropertyChanged
    {
        private string _name = string.Empty;
        private ProjectStatus _status = ProjectStatus.Draft;
        private string _description = string.Empty;
        private double _totalAreaM2;
        private DateTime _lastModified = DateTime.Now;

        /// <summary>
        /// Unique project identifier following data structure correlation ID standards
        /// </summary>
        public string CorrelationId { get; set; } = Guid.NewGuid().ToString();

        /// <summary>
        /// Project name with validation
        /// </summary>
        [Required]
        [StringLength(200, MinimumLength = 1)]
        public string Name
        {
            get => _name;
            set
            {
                if (_name != value)
                {
                    _name = value;
                    OnPropertyChanged(nameof(Name));
                }
            }
        }

        /// <summary>
        /// Project description with length constraints
        /// </summary>
        [StringLength(2000)]
        public string Description
        {
            get => _description;
            set
            {
                if (_description != value)
                {
                    _description = value;
                    OnPropertyChanged(nameof(Description));
                }
            }
        }

        /// <summary>
        /// Current project status for workflow tracking
        /// </summary>
        public ProjectStatus Status
        {
            get => _status;
            set
            {
                if (_status != value)
                {
                    _status = value;
                    OnPropertyChanged(nameof(Status));
                    OnPropertyChanged(nameof(StatusDisplayName));
                }
            }
        }

        /// <summary>
        /// Project type classification for AI processing
        /// </summary>
        [Required]
        public ProjectType Type { get; set; } = ProjectType.Residential;

        /// <summary>
        /// Total project area with validation constraints
        /// </summary>
        [Range(5.0, 10000.0, ErrorMessage = "Total area must be between 5 and 10,000 square meters")]
        public double TotalAreaM2
        {
            get => _totalAreaM2;
            set
            {
                if (Math.Abs(_totalAreaM2 - value) > 0.01)
                {
                    _totalAreaM2 = value;
                    OnPropertyChanged(nameof(TotalAreaM2));
                    OnPropertyChanged(nameof(TotalAreaDisplayText));
                }
            }
        }

        /// <summary>
        /// Project creation timestamp
        /// </summary>
        public DateTime CreatedAt { get; set; } = DateTime.Now;

        /// <summary>
        /// Last modification timestamp for tracking changes
        /// </summary>
        public DateTime LastModified
        {
            get => _lastModified;
            set
            {
                if (_lastModified != value)
                {
                    _lastModified = value;
                    OnPropertyChanged(nameof(LastModified));
                    OnPropertyChanged(nameof(LastModifiedDisplayText));
                }
            }
        }

        /// <summary>
        /// Regional and cultural context for global compliance
        /// </summary>
        public GlobalBuildingInfo BuildingInfo { get; set; } = new();

        /// <summary>
        /// Collection of project files (DWG/DXF/IFC/PDF)
        /// </summary>
        public List<ProjectFile> Files { get; set; } = new();

        /// <summary>
        /// Project-specific settings and preferences
        /// </summary>
        public ProjectSettings Settings { get; set; } = new();

        /// <summary>
        /// AI processing metadata and history
        /// </summary>
        public AIProjectMetadata AIMetadata { get; set; } = new();

        /// <summary>
        /// Project validation results
        /// </summary>
        public ValidationResult? ValidationResult { get; set; }

        // Display properties for UI binding
        public string StatusDisplayName => Status switch
        {
            ProjectStatus.Draft => "Draft",
            ProjectStatus.InProgress => "In Progress",
            ProjectStatus.UnderReview => "Under Review",
            ProjectStatus.Approved => "Approved",
            ProjectStatus.OnHold => "On Hold",
            ProjectStatus.Completed => "Completed",
            ProjectStatus.Archived => "Archived",
            _ => "Unknown"
        };

        public string TotalAreaDisplayText => $"{TotalAreaM2:F1} m²";

        public string LastModifiedDisplayText => LastModified.ToString("MMM dd, yyyy HH:mm");

        public string TypeDisplayName => Type switch
        {
            ProjectType.Residential => "Residential",
            ProjectType.Commercial => "Commercial",
            ProjectType.Office => "Office",
            ProjectType.Industrial => "Industrial",
            ProjectType.Educational => "Educational",
            ProjectType.Healthcare => "Healthcare",
            ProjectType.Hospitality => "Hospitality",
            ProjectType.Retail => "Retail",
            ProjectType.Mixed => "Mixed Use",
            _ => "Other"
        };

        public event PropertyChangedEventHandler? PropertyChanged;

        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        /// <summary>
        /// Updates the last modified timestamp
        /// </summary>
        public void MarkAsModified()
        {
            LastModified = DateTime.Now;
        }

        /// <summary>
        /// Validates the project information
        /// </summary>
        public List<ValidationError> Validate()
        {
            var errors = new List<ValidationError>();

            if (string.IsNullOrWhiteSpace(Name))
            {
                errors.Add(new ValidationError
                {
                    Code = "PROJ_001",
                    Message = "Project name is required",
                    Property = nameof(Name),
                    Severity = ValidationSeverity.Error
                });
            }

            if (TotalAreaM2 < 5.0 || TotalAreaM2 > 10000.0)
            {
                errors.Add(new ValidationError
                {
                    Code = "PROJ_002",
                    Message = "Total area must be between 5 and 10,000 square meters",
                    Property = nameof(TotalAreaM2),
                    Severity = ValidationSeverity.Error,
                    AttemptedValue = TotalAreaM2
                });
            }

            return errors;
        }
    }

    /// <summary>
    /// Project status enumeration for workflow management
    /// </summary>
    public enum ProjectStatus
    {
        Draft,
        InProgress,
        UnderReview,
        Approved,
        OnHold,
        Completed,
        Archived
    }

    /// <summary>
    /// Project type classification for AI processing and compliance
    /// </summary>
    public enum ProjectType
    {
        Residential,
        Commercial,
        Office,
        Industrial,
        Educational,
        Healthcare,
        Hospitality,
        Retail,
        Mixed,
        Other
    }

    /// <summary>
    /// Global building information for multi-regional compliance
    /// Following data structure standards for international support
    /// </summary>
    public class GlobalBuildingInfo
    {
        public string Region { get; set; } = "north_america";
        public string Country { get; set; } = "USA";
        public string Locale { get; set; } = "en-US";
        public string MeasurementSystem { get; set; } = "metric";
        public List<string> ApplicableCodes { get; set; } = new() { "IBC", "IRC" };
        public string ZoneName { get; set; } = string.Empty;
        public string OccupancyClass { get; set; } = string.Empty;
        public CulturalContext CulturalContext { get; set; } = new();
        public EnvironmentalFactors EnvironmentalFactors { get; set; } = new();
        public string ClimateZone { get; set; } = "temperate";
    }

    /// <summary>
    /// Cultural context for regional adaptations
    /// </summary>
    public class CulturalContext
    {
        public string FamilyStructure { get; set; } = "nuclear";
        public string PrivacyRequirements { get; set; } = "medium";
        public string EntertainmentStyle { get; set; } = "casual";
        public string OutdoorConnection { get; set; } = "medium";
        public List<string> ReligiousConsiderations { get; set; } = new();
    }

    /// <summary>
    /// Environmental factors for compliance and safety
    /// </summary>
    public class EnvironmentalFactors
    {
        public int? SeismicZone { get; set; }
        public bool FloodZone { get; set; }
        public bool WindLoadRequirements { get; set; }
        public string EnergyEfficiencyStandard { get; set; } = string.Empty;
    }

    /// <summary>
    /// Project-specific settings and preferences
    /// </summary>
    public class ProjectSettings
    {
        public bool AutoSaveEnabled { get; set; } = true;
        public int AutoSaveIntervalMinutes { get; set; } = 10;
        public bool CloudSyncEnabled { get; set; } = true;
        public string PreferredUnits { get; set; } = "metric";
        public List<string> EnabledFeatures { get; set; } = new();
        public Dictionary<string, object> CustomSettings { get; set; } = new();
    }

    /// <summary>
    /// AI processing metadata and history
    /// </summary>
    public class AIProjectMetadata
    {
        public List<string> AICommandHistory { get; set; } = new();
        public DateTime? LastAIProcessing { get; set; }
        public string? LastUsedAIModel { get; set; }
        public double? LastConfidenceScore { get; set; }
        public bool RequiresHumanReview { get; set; }
        public List<string> AIGeneratedElements { get; set; } = new();
        public Dictionary<string, object> AISettings { get; set; } = new();
    }

    /// <summary>
    /// Validation error structure following data contract standards
    /// </summary>
    public class ValidationError
    {
        public string Code { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
        public string Property { get; set; } = string.Empty;
        public object? AttemptedValue { get; set; }
        public ValidationSeverity Severity { get; set; } = ValidationSeverity.Error;
        public List<string> SuggestedFixes { get; set; } = new();
    }

    /// <summary>
    /// Validation result structure
    /// </summary>
    public class ValidationResult
    {
        public string CorrelationId { get; set; } = string.Empty;
        public ValidationStatus Status { get; set; } = ValidationStatus.Valid;
        public List<ValidationError> Errors { get; set; } = new();
        public List<ValidationError> Warnings { get; set; } = new();
        public double ConfidenceScore { get; set; } = 1.0;
        public bool RequiresHumanReview { get; set; }
        public DateTime ValidatedAt { get; set; } = DateTime.Now;
    }

    /// <summary>
    /// Validation status enumeration
    /// </summary>
    public enum ValidationStatus
    {
        Valid,
        InvalidButCorrectable,
        RequiresManualReview,
        Rejected
    }

    /// <summary>
    /// Validation severity levels
    /// </summary>
    public enum ValidationSeverity
    {
        Info,
        Warning,
        Error,
        Critical
    }
}