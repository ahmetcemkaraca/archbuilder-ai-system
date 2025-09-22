using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.IO;

namespace ArchBuilder.Models
{
    /// <summary>
    /// Represents a project file (DWG/DXF/IFC/PDF) with multi-format support
    /// Following ArchBuilder.AI data structure standards for CAD processing
    /// </summary>
    public class ProjectFile : INotifyPropertyChanged
    {
        private string _displayName = string.Empty;
        private FileProcessingStatus _processingStatus = FileProcessingStatus.Pending;
        private long _fileSizeBytes;
        private DateTime _lastModified = DateTime.Now;

        /// <summary>
        /// Unique file identifier for tracking and correlation
        /// </summary>
        public string FileId { get; set; } = Guid.NewGuid().ToString();

        /// <summary>
        /// Original file name with extension
        /// </summary>
        [Required]
        public string FileName { get; set; } = string.Empty;

        /// <summary>
        /// User-friendly display name for the file
        /// </summary>
        [StringLength(200)]
        public string DisplayName
        {
            get => string.IsNullOrWhiteSpace(_displayName) ? Path.GetFileNameWithoutExtension(FileName) : _displayName;
            set
            {
                if (_displayName != value)
                {
                    _displayName = value;
                    OnPropertyChanged(nameof(DisplayName));
                }
            }
        }

        /// <summary>
        /// Full file path on local system
        /// </summary>
        public string FilePath { get; set; } = string.Empty;

        /// <summary>
        /// File type classification for processing
        /// </summary>
        public ProjectFileType FileType { get; set; }

        /// <summary>
        /// File format specific metadata
        /// </summary>
        public FileFormatInfo FormatInfo { get; set; } = new();

        /// <summary>
        /// File size in bytes
        /// </summary>
        public long FileSizeBytes
        {
            get => _fileSizeBytes;
            set
            {
                if (_fileSizeBytes != value)
                {
                    _fileSizeBytes = value;
                    OnPropertyChanged(nameof(FileSizeBytes));
                    OnPropertyChanged(nameof(FileSizeDisplayText));
                }
            }
        }

        /// <summary>
        /// File creation timestamp
        /// </summary>
        public DateTime CreatedAt { get; set; } = DateTime.Now;

        /// <summary>
        /// Last modification timestamp
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
        /// File processing status for workflow tracking
        /// </summary>
        public FileProcessingStatus ProcessingStatus
        {
            get => _processingStatus;
            set
            {
                if (_processingStatus != value)
                {
                    _processingStatus = value;
                    OnPropertyChanged(nameof(ProcessingStatus));
                    OnPropertyChanged(nameof(ProcessingStatusDisplayName));
                    OnPropertyChanged(nameof(IsProcessing));
                    OnPropertyChanged(nameof(CanProcess));
                }
            }
        }

        /// <summary>
        /// Processing progress (0-100)
        /// </summary>
        public double ProcessingProgress { get; set; }

        /// <summary>
        /// Cloud storage reference (if uploaded)
        /// </summary>
        public string? CloudFileId { get; set; }

        /// <summary>
        /// File hash for integrity verification
        /// </summary>
        public string? FileHash { get; set; }

        /// <summary>
        /// File metadata extracted during processing
        /// </summary>
        public FileMetadata Metadata { get; set; } = new();

        /// <summary>
        /// Processing errors and warnings
        /// </summary>
        public List<FileProcessingError> ProcessingErrors { get; set; } = new();

        /// <summary>
        /// Security and validation information
        /// </summary>
        public FileSecurityInfo SecurityInfo { get; set; } = new();

        // Display properties for UI binding
        public string FileTypeDisplayName => FileType switch
        {
            ProjectFileType.DWG => "AutoCAD Drawing (DWG)",
            ProjectFileType.DXF => "AutoCAD Exchange (DXF)",
            ProjectFileType.IFC => "Industry Foundation Classes (IFC)",
            ProjectFileType.PDF => "Portable Document Format (PDF)",
            ProjectFileType.RVT => "Revit Project (RVT)",
            ProjectFileType.Image => "Image File",
            ProjectFileType.Document => "Document",
            ProjectFileType.Archive => "Archive",
            ProjectFileType.Other => "Other",
            _ => "Unknown"
        };

        public string ProcessingStatusDisplayName => ProcessingStatus switch
        {
            FileProcessingStatus.Pending => "Pending",
            FileProcessingStatus.Uploading => "Uploading",
            FileProcessingStatus.Processing => "Processing",
            FileProcessingStatus.Completed => "Completed",
            FileProcessingStatus.Failed => "Failed",
            FileProcessingStatus.Cancelled => "Cancelled",
            _ => "Unknown"
        };

        public string FileSizeDisplayText => FormatFileSize(FileSizeBytes);

        public string LastModifiedDisplayText => LastModified.ToString("MMM dd, yyyy HH:mm");

        public bool IsProcessing => ProcessingStatus == FileProcessingStatus.Processing || 
                                   ProcessingStatus == FileProcessingStatus.Uploading;

        public bool CanProcess => ProcessingStatus == FileProcessingStatus.Pending || 
                                 ProcessingStatus == FileProcessingStatus.Failed;

        public bool HasErrors => ProcessingErrors.Any(e => e.Severity == FileErrorSeverity.Error);

        public bool HasWarnings => ProcessingErrors.Any(e => e.Severity == FileErrorSeverity.Warning);

        public event PropertyChangedEventHandler? PropertyChanged;

        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        /// <summary>
        /// Determines file type from file extension
        /// </summary>
        public static ProjectFileType GetFileTypeFromExtension(string fileName)
        {
            var extension = Path.GetExtension(fileName).ToLowerInvariant();
            return extension switch
            {
                ".dwg" => ProjectFileType.DWG,
                ".dxf" => ProjectFileType.DXF,
                ".ifc" => ProjectFileType.IFC,
                ".pdf" => ProjectFileType.PDF,
                ".rvt" => ProjectFileType.RVT,
                ".jpg" or ".jpeg" or ".png" or ".bmp" or ".tiff" => ProjectFileType.Image,
                ".doc" or ".docx" or ".txt" or ".rtf" => ProjectFileType.Document,
                ".zip" or ".rar" or ".7z" => ProjectFileType.Archive,
                _ => ProjectFileType.Other
            };
        }

        /// <summary>
        /// Formats file size for display
        /// </summary>
        private static string FormatFileSize(long bytes)
        {
            if (bytes < 1024) return $"{bytes} B";
            if (bytes < 1024 * 1024) return $"{bytes / 1024.0:F1} KB";
            if (bytes < 1024 * 1024 * 1024) return $"{bytes / (1024.0 * 1024.0):F1} MB";
            return $"{bytes / (1024.0 * 1024.0 * 1024.0):F1} GB";
        }

        /// <summary>
        /// Updates processing status and marks file as modified
        /// </summary>
        public void UpdateProcessingStatus(FileProcessingStatus status, double progress = 0)
        {
            ProcessingStatus = status;
            ProcessingProgress = progress;
            LastModified = DateTime.Now;
        }

        /// <summary>
        /// Adds a processing error or warning
        /// </summary>
        public void AddProcessingError(string code, string message, FileErrorSeverity severity, string? property = null)
        {
            ProcessingErrors.Add(new FileProcessingError
            {
                Code = code,
                Message = message,
                Severity = severity,
                Property = property,
                Timestamp = DateTime.Now
            });
            OnPropertyChanged(nameof(HasErrors));
            OnPropertyChanged(nameof(HasWarnings));
        }

        /// <summary>
        /// Validates the file information
        /// </summary>
        public List<ValidationError> Validate()
        {
            var errors = new List<ValidationError>();

            if (string.IsNullOrWhiteSpace(FileName))
            {
                errors.Add(new ValidationError
                {
                    Code = "FILE_001",
                    Message = "File name is required",
                    Property = nameof(FileName),
                    Severity = ValidationSeverity.Error
                });
            }

            if (!File.Exists(FilePath) && string.IsNullOrWhiteSpace(CloudFileId))
            {
                errors.Add(new ValidationError
                {
                    Code = "FILE_002", 
                    Message = "File does not exist on local system or cloud storage",
                    Property = nameof(FilePath),
                    Severity = ValidationSeverity.Error
                });
            }

            if (FileSizeBytes > 500 * 1024 * 1024) // 500MB limit
            {
                errors.Add(new ValidationError
                {
                    Code = "FILE_003",
                    Message = "File size exceeds maximum allowed size of 500MB",
                    Property = nameof(FileSizeBytes),
                    Severity = ValidationSeverity.Error,
                    AttemptedValue = FileSizeBytes
                });
            }

            return errors;
        }
    }

    /// <summary>
    /// Project file type enumeration for multi-format support
    /// </summary>
    public enum ProjectFileType
    {
        DWG,        // AutoCAD Drawing
        DXF,        // AutoCAD Exchange Format
        IFC,        // Industry Foundation Classes
        PDF,        // Portable Document Format (regulations, plans)
        RVT,        // Revit Project File
        Image,      // Various image formats
        Document,   // Text documents
        Archive,    // Compressed archives
        Other       // Other file types
    }

    /// <summary>
    /// File processing status for workflow management
    /// </summary>
    public enum FileProcessingStatus
    {
        Pending,
        Uploading,
        Processing,
        Completed,
        Failed,
        Cancelled
    }

    /// <summary>
    /// File format specific information
    /// </summary>
    public class FileFormatInfo
    {
        public string FormatVersion { get; set; } = string.Empty;
        public string ApplicationName { get; set; } = string.Empty;
        public string ApplicationVersion { get; set; } = string.Empty;
        public DateTime? CreatedDate { get; set; }
        public string Author { get; set; } = string.Empty;
        public Dictionary<string, object> CustomProperties { get; set; } = new();
    }

    /// <summary>
    /// File metadata extracted during processing
    /// </summary>
    public class FileMetadata
    {
        public int LayerCount { get; set; }
        public int EntityCount { get; set; }
        public int BlockCount { get; set; }
        public string Units { get; set; } = string.Empty;
        public BoundingBox? BoundingBox { get; set; }
        public List<string> Layers { get; set; } = new();
        public List<string> FontsUsed { get; set; } = new();
        public Dictionary<string, int> EntityTypes { get; set; } = new();
        public bool HasExternalReferences { get; set; }
        public List<string> ExternalReferences { get; set; } = new();
    }

    /// <summary>
    /// File security and validation information
    /// </summary>
    public class FileSecurityInfo
    {
        public bool IsEncrypted { get; set; }
        public bool HasPassword { get; set; }
        public bool IsSignedDigitally { get; set; }
        public string ChecksumMD5 { get; set; } = string.Empty;
        public string ChecksumSHA256 { get; set; } = string.Empty;
        public bool VirusScanPassed { get; set; } = true;
        public DateTime? LastScanned { get; set; }
        public List<string> SecurityFlags { get; set; } = new();
    }

    /// <summary>
    /// 3D bounding box for spatial metadata
    /// </summary>
    public class BoundingBox
    {
        public Point3D MinPoint { get; set; } = new();
        public Point3D MaxPoint { get; set; } = new();

        public double Width => MaxPoint.X - MinPoint.X;
        public double Height => MaxPoint.Y - MinPoint.Y;
        public double Depth => MaxPoint.Z - MinPoint.Z;
        public double Volume => Width * Height * Depth;
    }

    /// <summary>
    /// 3D point structure
    /// </summary>
    public class Point3D
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }

        public Point3D() { }
        public Point3D(double x, double y, double z = 0)
        {
            X = x;
            Y = y;
            Z = z;
        }

        public double DistanceTo(Point3D other)
        {
            return Math.Sqrt(Math.Pow(X - other.X, 2) + Math.Pow(Y - other.Y, 2) + Math.Pow(Z - other.Z, 2));
        }
    }

    /// <summary>
    /// File processing error information
    /// </summary>
    public class FileProcessingError
    {
        public string Code { get; set; } = string.Empty;
        public string Message { get; set; } = string.Empty;
        public FileErrorSeverity Severity { get; set; } = FileErrorSeverity.Error;
        public string? Property { get; set; }
        public DateTime Timestamp { get; set; } = DateTime.Now;
        public string? StackTrace { get; set; }
        public Dictionary<string, object> Context { get; set; } = new();
    }

    /// <summary>
    /// File error severity levels
    /// </summary>
    public enum FileErrorSeverity
    {
        Info,
        Warning,
        Error,
        Critical
    }
}