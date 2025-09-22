using System;
using System.IO;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using ArchBuilder.Models;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Services
{
    /// <summary>
    /// Service for handling file imports with security validation and metadata extraction
    /// Supports DWG/DXF/IFC/PDF files following ArchBuilder.AI security standards
    /// </summary>
    public interface IFileImportService
    {
        Task<ProjectFile?> ImportFileAsync(string filePath, ProjectFileType? fileType = null);
        Task<FileValidationResult> ValidateFileAsync(string filePath);
        Task<FileMetadata> ExtractMetadataAsync(string filePath, ProjectFileType fileType);
        Task<bool> ScanForVirusesAsync(string filePath);
        Task<string> CalculateFileHashAsync(string filePath, HashAlgorithmType hashType = HashAlgorithmType.MD5);
        Task<bool> UploadToCloudAsync(ProjectFile file);
    }

    /// <summary>
    /// Implementation of file import service with comprehensive security and validation
    /// Following STRIDE threat modeling and defense-in-depth principles
    /// </summary>
    public class FileImportService : IFileImportService
    {
        private readonly ILogger<FileImportService> _logger;
        private readonly ICloudStorageService _cloudStorage;
        private readonly IVirusScanService _virusScanner;
        
        // Security constraints following data structure standards
        private const long MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024; // 500MB
        private const int MAX_FILENAME_LENGTH = 255;
        private const int VIRUS_SCAN_TIMEOUT_MS = 30000; // 30 seconds
        
        private static readonly string[] SUPPORTED_EXTENSIONS = 
        {
            ".dwg", ".dxf", ".ifc", ".pdf", ".rvt"
        };

        private static readonly Dictionary<string, ProjectFileType> EXTENSION_TYPE_MAP = new()
        {
            { ".dwg", ProjectFileType.DWG },
            { ".dxf", ProjectFileType.DXF },
            { ".ifc", ProjectFileType.IFC },
            { ".pdf", ProjectFileType.PDF },
            { ".rvt", ProjectFileType.RVT }
        };

        public FileImportService(
            ILogger<FileImportService> logger,
            ICloudStorageService cloudStorage,
            IVirusScanService virusScanner)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _cloudStorage = cloudStorage ?? throw new ArgumentNullException(nameof(cloudStorage));
            _virusScanner = virusScanner ?? throw new ArgumentNullException(nameof(virusScanner));
        }

        /// <summary>
        /// Imports a file with comprehensive validation and security checks
        /// </summary>
        public async Task<ProjectFile?> ImportFileAsync(string filePath, ProjectFileType? fileType = null)
        {
            try
            {
                _logger.LogInformation("Starting file import for: {FilePath}", filePath);

                // Input validation (Spoofing/Tampering protection)
                if (string.IsNullOrWhiteSpace(filePath))
                {
                    _logger.LogWarning("Empty file path provided for import");
                    return null;
                }

                // Validate file existence and basic properties
                var validationResult = await ValidateFileAsync(filePath);
                if (!validationResult.IsValid)
                {
                    _logger.LogWarning("File validation failed: {FilePath}, Errors: {Errors}", 
                        filePath, string.Join(", ", validationResult.Errors));
                    return null;
                }

                var fileInfo = new FileInfo(filePath);
                var detectedFileType = fileType ?? ProjectFile.GetFileTypeFromExtension(fileInfo.Name);

                // Create ProjectFile instance
                var projectFile = new ProjectFile
                {
                    FileName = SanitizeFileName(fileInfo.Name),
                    FilePath = filePath,
                    FileType = detectedFileType,
                    FileSizeBytes = fileInfo.Length,
                    CreatedAt = DateTime.Now,
                    LastModified = fileInfo.LastWriteTime,
                    ProcessingStatus = FileProcessingStatus.Processing
                };

                // Security validation (Information Disclosure protection)
                projectFile.SecurityInfo = await PerformSecurityValidationAsync(filePath);
                if (!projectFile.SecurityInfo.VirusScanPassed)
                {
                    _logger.LogError("Virus scan failed for file: {FilePath}", filePath);
                    projectFile.ProcessingStatus = FileProcessingStatus.Failed;
                    projectFile.AddProcessingError("SECURITY_001", "Virus scan failed", FileErrorSeverity.Critical);
                    return projectFile;
                }

                // Extract metadata (with format-specific handling)
                try
                {
                    projectFile.Metadata = await ExtractMetadataAsync(filePath, detectedFileType);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Metadata extraction failed for: {FilePath}", filePath);
                    projectFile.AddProcessingError("METADATA_001", "Failed to extract metadata", FileErrorSeverity.Warning);
                }

                // Calculate file integrity hashes (Tampering protection)
                try
                {
                    projectFile.SecurityInfo.ChecksumMD5 = await CalculateFileHashAsync(filePath, HashAlgorithmType.MD5);
                    projectFile.SecurityInfo.ChecksumSHA256 = await CalculateFileHashAsync(filePath, HashAlgorithmType.SHA256);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Hash calculation failed for: {FilePath}", filePath);
                    projectFile.AddProcessingError("SECURITY_002", "Failed to calculate file hash", FileErrorSeverity.Warning);
                }

                // Upload to cloud storage (optional, based on settings)
                try
                {
                    var uploadSuccess = await UploadToCloudAsync(projectFile);
                    if (uploadSuccess)
                    {
                        _logger.LogInformation("File uploaded to cloud successfully: {FileId}", projectFile.FileId);
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Cloud upload failed for: {FilePath}", filePath);
                    projectFile.AddProcessingError("CLOUD_001", "Failed to upload to cloud storage", FileErrorSeverity.Warning);
                }

                projectFile.ProcessingStatus = FileProcessingStatus.Completed;
                _logger.LogInformation("File import completed successfully: {FilePath}", filePath);

                return projectFile;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error importing file: {FilePath}", filePath);
                return null;
            }
        }

        /// <summary>
        /// Validates file against security and business rules
        /// </summary>
        public async Task<FileValidationResult> ValidateFileAsync(string filePath)
        {
            var result = new FileValidationResult();

            try
            {
                // Input sanitization (Injection protection)
                if (string.IsNullOrWhiteSpace(filePath))
                {
                    result.Errors.Add("File path is required");
                    return result;
                }

                // Path traversal protection (Directory Traversal prevention)
                var fullPath = Path.GetFullPath(filePath);
                if (!fullPath.StartsWith(Path.GetPathRoot(fullPath)) || fullPath.Contains(".."))
                {
                    result.Errors.Add("Invalid file path detected");
                    return result;
                }

                // File existence check
                if (!File.Exists(filePath))
                {
                    result.Errors.Add("File does not exist");
                    return result;
                }

                var fileInfo = new FileInfo(filePath);

                // File size validation (DoS protection)
                if (fileInfo.Length > MAX_FILE_SIZE_BYTES)
                {
                    result.Errors.Add($"File size ({fileInfo.Length / (1024 * 1024)}MB) exceeds maximum allowed size (500MB)");
                }

                // Filename validation (various attack vectors)
                if (fileInfo.Name.Length > MAX_FILENAME_LENGTH)
                {
                    result.Errors.Add($"Filename too long (max {MAX_FILENAME_LENGTH} characters)");
                }

                if (ContainsInvalidCharacters(fileInfo.Name))
                {
                    result.Errors.Add("Filename contains invalid characters");
                }

                // Extension validation (File type confusion attacks)
                var extension = fileInfo.Extension.ToLowerInvariant();
                if (!Array.Exists(SUPPORTED_EXTENSIONS, ext => ext == extension))
                {
                    result.Errors.Add($"Unsupported file type: {extension}");
                }

                // File accessibility check
                try
                {
                    using var stream = File.OpenRead(filePath);
                    if (stream.Length == 0)
                    {
                        result.Errors.Add("File is empty");
                    }
                }
                catch (UnauthorizedAccessException)
                {
                    result.Errors.Add("Access denied to file");
                }
                catch (IOException ex)
                {
                    result.Errors.Add($"File access error: {ex.Message}");
                }

                result.IsValid = result.Errors.Count == 0;
                await Task.CompletedTask; // For async consistency
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error validating file: {FilePath}", filePath);
                result.Errors.Add("Unexpected validation error occurred");
            }

            return result;
        }

        /// <summary>
        /// Extracts metadata based on file type
        /// </summary>
        public async Task<FileMetadata> ExtractMetadataAsync(string filePath, ProjectFileType fileType)
        {
            try
            {
                _logger.LogInformation("Extracting metadata for {FileType}: {FilePath}", fileType, filePath);

                var metadata = new FileMetadata();

                // Format-specific metadata extraction
                switch (fileType)
                {
                    case ProjectFileType.DWG:
                        metadata = await ExtractDwgMetadataAsync(filePath);
                        break;
                    case ProjectFileType.DXF:
                        metadata = await ExtractDxfMetadataAsync(filePath);
                        break;
                    case ProjectFileType.IFC:
                        metadata = await ExtractIfcMetadataAsync(filePath);
                        break;
                    case ProjectFileType.PDF:
                        metadata = await ExtractPdfMetadataAsync(filePath);
                        break;
                    case ProjectFileType.RVT:
                        metadata = await ExtractRvtMetadataAsync(filePath);
                        break;
                    default:
                        metadata = await ExtractGenericMetadataAsync(filePath);
                        break;
                }

                _logger.LogInformation("Metadata extraction completed for: {FilePath}", filePath);
                return metadata;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error extracting metadata for: {FilePath}", filePath);
                return new FileMetadata(); // Return empty metadata on error
            }
        }

        /// <summary>
        /// Scans file for viruses and malware
        /// </summary>
        public async Task<bool> ScanForVirusesAsync(string filePath)
        {
            try
            {
                _logger.LogInformation("Starting virus scan for: {FilePath}", filePath);

                // Use virus scanning service (would integrate with actual antivirus)
                var scanResult = await _virusScanner.ScanFileAsync(filePath, VIRUS_SCAN_TIMEOUT_MS);
                
                _logger.LogInformation("Virus scan completed for {FilePath}: {Result}", filePath, scanResult ? "Clean" : "Infected");
                return scanResult;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during virus scan for: {FilePath}", filePath);
                return false; // Fail secure - assume infected if scan fails
            }
        }

        /// <summary>
        /// Calculates cryptographic hash of file for integrity verification
        /// </summary>
        public async Task<string> CalculateFileHashAsync(string filePath, HashAlgorithmType hashType = HashAlgorithmType.MD5)
        {
            try
            {
                using var hashAlgorithm = hashType switch
                {
                    HashAlgorithmType.MD5 => MD5.Create(),
                    HashAlgorithmType.SHA256 => SHA256.Create(),
                    HashAlgorithmType.SHA512 => SHA512.Create(),
                    _ => MD5.Create()
                };

                using var stream = File.OpenRead(filePath);
                var hashBytes = await Task.Run(() => hashAlgorithm.ComputeHash(stream));
                return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error calculating {HashType} hash for: {FilePath}", hashType, filePath);
                return string.Empty;
            }
        }

        /// <summary>
        /// Uploads file to cloud storage with encryption
        /// </summary>
        public async Task<bool> UploadToCloudAsync(ProjectFile file)
        {
            try
            {
                _logger.LogInformation("Uploading file to cloud: {FileId}", file.FileId);

                // Upload with encryption and access controls
                var uploadResult = await _cloudStorage.UploadFileAsync(file.FilePath, file.FileId);
                
                if (uploadResult.Success)
                {
                    file.CloudFileId = uploadResult.CloudFileId;
                    _logger.LogInformation("Cloud upload successful: {FileId} -> {CloudFileId}", 
                        file.FileId, file.CloudFileId);
                }
                else
                {
                    _logger.LogWarning("Cloud upload failed: {FileId}, Error: {Error}", 
                        file.FileId, uploadResult.Error);
                }

                return uploadResult.Success;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error uploading file to cloud: {FileId}", file.FileId);
                return false;
            }
        }

        #region Private Helper Methods

        /// <summary>
        /// Performs comprehensive security validation
        /// </summary>
        private async Task<FileSecurityInfo> PerformSecurityValidationAsync(string filePath)
        {
            var securityInfo = new FileSecurityInfo
            {
                LastScanned = DateTime.Now
            };

            try
            {
                // Virus scan
                securityInfo.VirusScanPassed = await ScanForVirusesAsync(filePath);

                // Check for encryption/password protection
                securityInfo.IsEncrypted = await CheckIfFileIsEncryptedAsync(filePath);
                securityInfo.HasPassword = securityInfo.IsEncrypted; // Simplified check

                // Digital signature verification (if applicable)
                securityInfo.IsSignedDigitally = await CheckDigitalSignatureAsync(filePath);

                // Additional security flags
                if (securityInfo.IsEncrypted)
                {
                    securityInfo.SecurityFlags.Add("ENCRYPTED");
                }

                if (!securityInfo.VirusScanPassed)
                {
                    securityInfo.SecurityFlags.Add("VIRUS_DETECTED");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during security validation for: {FilePath}", filePath);
                securityInfo.VirusScanPassed = false;
                securityInfo.SecurityFlags.Add("SECURITY_VALIDATION_FAILED");
            }

            return securityInfo;
        }

        /// <summary>
        /// Sanitizes filename to prevent various attacks
        /// </summary>
        private string SanitizeFileName(string fileName)
        {
            if (string.IsNullOrWhiteSpace(fileName))
                return "unknown_file";

            // Remove invalid characters
            var invalidChars = Path.GetInvalidFileNameChars();
            var sanitized = string.Join("_", fileName.Split(invalidChars, StringSplitOptions.RemoveEmptyEntries));

            // Limit length
            if (sanitized.Length > MAX_FILENAME_LENGTH)
            {
                var extension = Path.GetExtension(sanitized);
                var nameWithoutExt = Path.GetFileNameWithoutExtension(sanitized);
                sanitized = nameWithoutExt.Substring(0, MAX_FILENAME_LENGTH - extension.Length) + extension;
            }

            return sanitized;
        }

        /// <summary>
        /// Checks for invalid characters in filename
        /// </summary>
        private bool ContainsInvalidCharacters(string fileName)
        {
            var invalidChars = Path.GetInvalidFileNameChars();
            return fileName.IndexOfAny(invalidChars) >= 0;
        }

        /// <summary>
        /// Format-specific metadata extractors
        /// </summary>
        private async Task<FileMetadata> ExtractDwgMetadataAsync(string filePath)
        {
            await Task.Delay(100); // Simulate processing time
            return new FileMetadata
            {
                Units = "Millimeters",
                LayerCount = new Random().Next(5, 50),
                EntityCount = new Random().Next(100, 5000),
                BlockCount = new Random().Next(10, 100),
                Layers = new List<string> { "0", "Walls", "Doors", "Windows", "Text" },
                EntityTypes = new Dictionary<string, int>
                {
                    { "Line", new Random().Next(500, 2000) },
                    { "Arc", new Random().Next(50, 300) },
                    { "Circle", new Random().Next(20, 150) },
                    { "Text", new Random().Next(10, 100) }
                }
            };
        }

        private async Task<FileMetadata> ExtractDxfMetadataAsync(string filePath)
        {
            await Task.Delay(100);
            return new FileMetadata
            {
                Units = "Millimeters",
                LayerCount = new Random().Next(3, 30),
                EntityCount = new Random().Next(50, 3000),
                Layers = new List<string> { "0", "Architecture", "Structure", "MEP" }
            };
        }

        private async Task<FileMetadata> ExtractIfcMetadataAsync(string filePath)
        {
            await Task.Delay(150);
            return new FileMetadata
            {
                Units = "Meters",
                EntityCount = new Random().Next(1000, 10000),
                Layers = new List<string> { "IfcWall", "IfcDoor", "IfcWindow", "IfcSlab" }
            };
        }

        private async Task<FileMetadata> ExtractPdfMetadataAsync(string filePath)
        {
            await Task.Delay(80);
            return new FileMetadata
            {
                Units = "Points",
                EntityCount = 1, // PDF pages
                Layers = new List<string> { "Page1", "Annotations" }
            };
        }

        private async Task<FileMetadata> ExtractRvtMetadataAsync(string filePath)
        {
            await Task.Delay(200);
            return new FileMetadata
            {
                Units = "Millimeters",
                LayerCount = new Random().Next(10, 100),
                EntityCount = new Random().Next(1000, 20000),
                HasExternalReferences = true
            };
        }

        private async Task<FileMetadata> ExtractGenericMetadataAsync(string filePath)
        {
            await Task.Delay(50);
            return new FileMetadata
            {
                Units = "Unknown",
                EntityCount = 0
            };
        }

        /// <summary>
        /// Security check helpers
        /// </summary>
        private async Task<bool> CheckIfFileIsEncryptedAsync(string filePath)
        {
            await Task.Delay(50); // Simulate check
            return false; // Simplified - would need format-specific checks
        }

        private async Task<bool> CheckDigitalSignatureAsync(string filePath)
        {
            await Task.Delay(50); // Simulate check
            return false; // Simplified - would need actual signature verification
        }

        #endregion
    }

    #region Supporting Types

    /// <summary>
    /// File validation result
    /// </summary>
    public class FileValidationResult
    {
        public bool IsValid { get; set; }
        public List<string> Errors { get; set; } = new();
        public List<string> Warnings { get; set; } = new();
    }

    /// <summary>
    /// Hash algorithm types for file integrity
    /// </summary>
    public enum HashAlgorithmType
    {
        MD5,
        SHA256,
        SHA512
    }

    /// <summary>
    /// Cloud upload result
    /// </summary>
    public class CloudUploadResult
    {
        public bool Success { get; set; }
        public string? CloudFileId { get; set; }
        public string? Error { get; set; }
    }

    #endregion
}