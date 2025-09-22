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
    /// Service implementation for project data persistence and management.
    /// Handles project creation, loading, saving, and metadata management with comprehensive validation.
    /// </summary>
    public class ProjectDataService : IProjectDataService
    {
        #region Private Fields

        private readonly ILogger<ProjectDataService> _logger;
        private readonly ISettingsService _settingsService;
        private readonly IConfigurationService _configurationService;
        private readonly string _projectsDirectory;
        private readonly JsonSerializerOptions _jsonOptions;

        #endregion

        #region Constructor

        /// <summary>
        /// Initializes a new instance of the ProjectDataService.
        /// </summary>
        /// <param name="logger">Logger instance for tracking operations</param>
        /// <param name="settingsService">Settings service for user preferences</param>
        /// <param name="configurationService">Configuration service for application settings</param>
        public ProjectDataService(
            ILogger<ProjectDataService> logger,
            ISettingsService settingsService,
            IConfigurationService configurationService)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _settingsService = settingsService ?? throw new ArgumentNullException(nameof(settingsService));
            _configurationService = configurationService ?? throw new ArgumentNullException(nameof(configurationService));

            // Get projects directory from configuration
            _projectsDirectory = _configurationService.GetConfigValue<string>("Storage:ProjectsDirectory", 
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ArchBuilder", "Projects"));

            // Ensure projects directory exists
            Directory.CreateDirectory(_projectsDirectory);

            // Configure JSON serialization options
            _jsonOptions = new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                PropertyNameCaseInsensitive = true
            };

            _logger.LogInformation("ProjectDataService initialized with projects directory: {ProjectsDirectory}", _projectsDirectory);
        }

        #endregion

        #region Public Methods

        /// <summary>
        /// Creates a new project with the specified information.
        /// </summary>
        public async Task<ProjectInfo> CreateProjectAsync(ProjectInfo projectInfo)
        {
            if (projectInfo == null)
                throw new ArgumentNullException(nameof(projectInfo));

            var correlationId = Guid.NewGuid().ToString();
            using var scope = _logger.BeginScope("CreateProject {CorrelationId}", correlationId);

            try
            {
                _logger.LogInformation("Creating new project: {ProjectName}", projectInfo.Name);

                // Validate project information
                await ValidateProjectInfoAsync(projectInfo);

                // Generate unique project ID
                projectInfo.Id = $"PROJ_{DateTime.UtcNow:yyyyMMddHHmmss}_{Guid.NewGuid():N}";
                projectInfo.CreatedAt = DateTime.UtcNow;
                projectInfo.UpdatedAt = DateTime.UtcNow;
                projectInfo.Status = ProjectStatus.Active;

                // Create project directory
                var projectPath = Path.Combine(_projectsDirectory, projectInfo.Id);
                Directory.CreateDirectory(projectPath);

                // Create subdirectories
                Directory.CreateDirectory(Path.Combine(projectPath, "Files"));
                Directory.CreateDirectory(Path.Combine(projectPath, "Exports"));
                Directory.CreateDirectory(Path.Combine(projectPath, "Backups"));
                Directory.CreateDirectory(Path.Combine(projectPath, "Documentation"));

                // Save project metadata
                await SaveProjectMetadataAsync(projectInfo);

                // Create initial backup
                await CreateProjectBackupAsync(projectInfo.Id);

                _logger.LogInformation("Project created successfully: {ProjectId}", projectInfo.Id);
                return projectInfo;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to create project: {ProjectName}", projectInfo.Name);
                throw new ProjectCreationException($"Failed to create project: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Loads an existing project by ID with all associated data.
        /// </summary>
        public async Task<ProjectInfo> LoadProjectAsync(string projectId)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            using var scope = _logger.BeginScope("LoadProject {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Loading project: {ProjectId}", projectId);

                var projectPath = Path.Combine(_projectsDirectory, projectId);
                if (!Directory.Exists(projectPath))
                {
                    throw new ProjectNotFoundException($"Project not found: {projectId}");
                }

                var metadataPath = Path.Combine(projectPath, "project.json");
                if (!File.Exists(metadataPath))
                {
                    throw new ProjectCorruptedException($"Project metadata file not found: {projectId}");
                }

                var jsonContent = await File.ReadAllTextAsync(metadataPath);
                var projectInfo = JsonSerializer.Deserialize<ProjectInfo>(jsonContent, _jsonOptions);

                // Load project files
                await LoadProjectFilesAsync(projectInfo);

                // Update last accessed time
                projectInfo.LastAccessedAt = DateTime.UtcNow;
                await SaveProjectMetadataAsync(projectInfo);

                _logger.LogInformation("Project loaded successfully: {ProjectId}", projectId);
                return projectInfo;
            }
            catch (ProjectNotFoundException)
            {
                throw;
            }
            catch (ProjectCorruptedException)
            {
                throw;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load project: {ProjectId}", projectId);
                throw new ProjectLoadException($"Failed to load project: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Saves project changes to persistent storage.
        /// </summary>
        public async Task SaveProjectAsync(ProjectInfo project)
        {
            if (project == null)
                throw new ArgumentNullException(nameof(project));

            using var scope = _logger.BeginScope("SaveProject {ProjectId}", project.Id);

            try
            {
                _logger.LogInformation("Saving project: {ProjectId}", project.Id);

                // Update metadata
                project.UpdatedAt = DateTime.UtcNow;

                // Save metadata
                await SaveProjectMetadataAsync(project);

                // Save project files metadata
                await SaveProjectFilesMetadataAsync(project);

                _logger.LogInformation("Project saved successfully: {ProjectId}", project.Id);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to save project: {ProjectId}", project.Id);
                throw new ProjectSaveException($"Failed to save project: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Retrieves a list of all available projects for the current user.
        /// </summary>
        public async Task<List<ProjectSummary>> GetProjectListAsync()
        {
            try
            {
                _logger.LogInformation("Getting project list");

                var projects = new List<ProjectSummary>();
                var projectDirectories = Directory.GetDirectories(_projectsDirectory);

                foreach (var projectDir in projectDirectories)
                {
                    try
                    {
                        var projectId = Path.GetFileName(projectDir);
                        var metadataPath = Path.Combine(projectDir, "project.json");

                        if (File.Exists(metadataPath))
                        {
                            var jsonContent = await File.ReadAllTextAsync(metadataPath);
                            var projectInfo = JsonSerializer.Deserialize<ProjectInfo>(jsonContent, _jsonOptions);

                            projects.Add(new ProjectSummary
                            {
                                Id = projectInfo.Id,
                                Name = projectInfo.Name,
                                Description = projectInfo.Description,
                                CreatedAt = projectInfo.CreatedAt,
                                UpdatedAt = projectInfo.UpdatedAt,
                                LastAccessedAt = projectInfo.LastAccessedAt,
                                Status = projectInfo.Status,
                                FileCount = projectInfo.Files?.Count ?? 0,
                                TotalSizeBytes = await CalculateProjectSizeAsync(projectDir)
                            });
                        }
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, "Failed to load project summary from directory: {ProjectDir}", projectDir);
                    }
                }

                // Sort by last accessed date (most recent first)
                projects.Sort((x, y) => (y.LastAccessedAt ?? y.UpdatedAt).CompareTo(x.LastAccessedAt ?? x.UpdatedAt));

                _logger.LogInformation("Retrieved {ProjectCount} projects", projects.Count);
                return projects;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get project list");
                throw new ProjectServiceException($"Failed to get project list: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Deletes a project and all associated data permanently.
        /// </summary>
        public async Task<bool> DeleteProjectAsync(string projectId)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            using var scope = _logger.BeginScope("DeleteProject {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Deleting project: {ProjectId}", projectId);

                var projectPath = Path.Combine(_projectsDirectory, projectId);
                if (!Directory.Exists(projectPath))
                {
                    _logger.LogWarning("Project directory not found for deletion: {ProjectId}", projectId);
                    return false;
                }

                // Create final backup before deletion
                await CreateProjectBackupAsync(projectId, Path.Combine(_projectsDirectory, "DeletedProjects"));

                // Delete project directory
                Directory.Delete(projectPath, recursive: true);

                _logger.LogInformation("Project deleted successfully: {ProjectId}", projectId);
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to delete project: {ProjectId}", projectId);
                throw new ProjectDeletionException($"Failed to delete project: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Updates project metadata without modifying content data.
        /// </summary>
        public async Task UpdateProjectMetadataAsync(string projectId, ProjectMetadata metadata)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            if (metadata == null)
                throw new ArgumentNullException(nameof(metadata));

            using var scope = _logger.BeginScope("UpdateProjectMetadata {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Updating project metadata: {ProjectId}", projectId);

                var project = await LoadProjectAsync(projectId);
                
                // Update metadata fields
                project.Name = metadata.Name ?? project.Name;
                project.Description = metadata.Description ?? project.Description;
                project.Tags = metadata.Tags ?? project.Tags;
                project.Category = metadata.Category ?? project.Category;
                project.UpdatedAt = DateTime.UtcNow;

                await SaveProjectMetadataAsync(project);

                _logger.LogInformation("Project metadata updated successfully: {ProjectId}", projectId);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to update project metadata: {ProjectId}", projectId);
                throw new ProjectUpdateException($"Failed to update project metadata: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Imports project files and validates their format and content.
        /// </summary>
        public async Task<ImportResult> ImportProjectFilesAsync(string projectId, List<ProjectFile> files)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            if (files == null || files.Count == 0)
                throw new ArgumentException("Files list cannot be null or empty", nameof(files));

            using var scope = _logger.BeginScope("ImportProjectFiles {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Importing {FileCount} files to project: {ProjectId}", files.Count, projectId);

                var result = new ImportResult
                {
                    ProjectId = projectId,
                    TotalFiles = files.Count,
                    SuccessfulImports = 0,
                    FailedImports = 0,
                    ImportedFiles = new List<ProjectFile>(),
                    FailedFiles = new List<ImportError>(),
                    StartedAt = DateTime.UtcNow
                };

                var project = await LoadProjectAsync(projectId);
                var projectFilesPath = Path.Combine(_projectsDirectory, projectId, "Files");

                foreach (var file in files)
                {
                    try
                    {
                        // Validate file
                        var validationResult = await ValidateProjectFileAsync(file);
                        if (!validationResult.IsValid)
                        {
                            result.FailedFiles.Add(new ImportError
                            {
                                FileName = file.Name,
                                ErrorMessage = string.Join(", ", validationResult.Errors),
                                ErrorType = "Validation"
                            });
                            result.FailedImports++;
                            continue;
                        }

                        // Copy file to project directory
                        var targetPath = Path.Combine(projectFilesPath, file.Name);
                        await File.WriteAllBytesAsync(targetPath, file.Content);

                        // Update file metadata
                        file.Id = Guid.NewGuid().ToString();
                        file.ImportedAt = DateTime.UtcNow;
                        file.FilePath = targetPath;
                        file.SizeBytes = file.Content.Length;

                        project.Files ??= new List<ProjectFile>();
                        project.Files.Add(file);

                        result.ImportedFiles.Add(file);
                        result.SuccessfulImports++;

                        _logger.LogDebug("File imported successfully: {FileName}", file.Name);
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, "Failed to import file: {FileName}", file.Name);
                        result.FailedFiles.Add(new ImportError
                        {
                            FileName = file.Name,
                            ErrorMessage = ex.Message,
                            ErrorType = "Processing"
                        });
                        result.FailedImports++;
                    }
                }

                // Save updated project
                await SaveProjectAsync(project);

                result.CompletedAt = DateTime.UtcNow;
                result.IsSuccess = result.FailedImports == 0;

                _logger.LogInformation("File import completed: {SuccessCount} successful, {FailCount} failed", 
                    result.SuccessfulImports, result.FailedImports);

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to import project files: {ProjectId}", projectId);
                throw new ProjectImportException($"Failed to import project files: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Exports project data to specified format and location.
        /// </summary>
        public async Task<ExportResult> ExportProjectAsync(string projectId, ExportOptions exportOptions)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            if (exportOptions == null)
                throw new ArgumentNullException(nameof(exportOptions));

            using var scope = _logger.BeginScope("ExportProject {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Exporting project: {ProjectId} to format: {Format}", projectId, exportOptions.Format);

                var project = await LoadProjectAsync(projectId);
                var result = new ExportResult
                {
                    ProjectId = projectId,
                    Format = exportOptions.Format,
                    StartedAt = DateTime.UtcNow
                };

                switch (exportOptions.Format.ToLowerInvariant())
                {
                    case "zip":
                        result.FilePath = await ExportAsZipAsync(project, exportOptions);
                        break;
                    case "json":
                        result.FilePath = await ExportAsJsonAsync(project, exportOptions);
                        break;
                    case "pdf":
                        result.FilePath = await ExportAsPdfAsync(project, exportOptions);
                        break;
                    default:
                        throw new ArgumentException($"Unsupported export format: {exportOptions.Format}");
                }

                result.CompletedAt = DateTime.UtcNow;
                result.IsSuccess = true;
                result.SizeBytes = new FileInfo(result.FilePath).Length;

                _logger.LogInformation("Project exported successfully: {ExportPath}", result.FilePath);
                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to export project: {ProjectId}", projectId);
                throw new ProjectExportException($"Failed to export project: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Gets recent projects for quick access.
        /// </summary>
        public async Task<List<ProjectSummary>> GetRecentProjectsAsync(int count = 10)
        {
            try
            {
                var allProjects = await GetProjectListAsync();
                return allProjects.Take(Math.Min(count, allProjects.Count)).ToList();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to get recent projects");
                throw;
            }
        }

        /// <summary>
        /// Validates project data integrity and consistency.
        /// </summary>
        public async Task<ProjectValidationResult> ValidateProjectAsync(string projectId)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            using var scope = _logger.BeginScope("ValidateProject {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Validating project: {ProjectId}", projectId);

                var result = new ProjectValidationResult
                {
                    ProjectId = projectId,
                    IsValid = true,
                    Issues = new List<ValidationIssue>(),
                    ValidatedAt = DateTime.UtcNow
                };

                var project = await LoadProjectAsync(projectId);

                // Validate project structure
                await ValidateProjectStructureAsync(project, result);

                // Validate project files
                await ValidateProjectFilesAsync(project, result);

                // Validate project metadata
                await ValidateProjectMetadataAsync(project, result);

                result.IsValid = !result.Issues.Any(i => i.Severity == ValidationSeverity.Error);

                _logger.LogInformation("Project validation completed: {IsValid}, {IssueCount} issues found", 
                    result.IsValid, result.Issues.Count);

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to validate project: {ProjectId}", projectId);
                throw new ProjectValidationException($"Failed to validate project: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Creates a backup of the specified project.
        /// </summary>
        public async Task<BackupResult> CreateProjectBackupAsync(string projectId, string backupLocation = null)
        {
            if (string.IsNullOrWhiteSpace(projectId))
                throw new ArgumentException("Project ID cannot be null or empty", nameof(projectId));

            using var scope = _logger.BeginScope("CreateProjectBackup {ProjectId}", projectId);

            try
            {
                _logger.LogInformation("Creating backup for project: {ProjectId}", projectId);

                var project = await LoadProjectAsync(projectId);
                
                backupLocation ??= Path.Combine(_projectsDirectory, projectId, "Backups");
                Directory.CreateDirectory(backupLocation);

                var backupFileName = $"backup_{project.Name}_{DateTime.UtcNow:yyyyMMddHHmmss}.zip";
                var backupPath = Path.Combine(backupLocation, backupFileName);

                // Create backup using export functionality
                var exportOptions = new ExportOptions
                {
                    Format = "zip",
                    OutputPath = backupPath,
                    IncludeFiles = true,
                    IncludeMetadata = true
                };

                await ExportAsZipAsync(project, exportOptions);

                var result = new BackupResult
                {
                    ProjectId = projectId,
                    BackupPath = backupPath,
                    CreatedAt = DateTime.UtcNow,
                    SizeBytes = new FileInfo(backupPath).Length,
                    IsSuccess = true
                };

                _logger.LogInformation("Project backup created successfully: {BackupPath}", backupPath);
                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to create project backup: {ProjectId}", projectId);
                throw new ProjectBackupException($"Failed to create project backup: {ex.Message}", ex);
            }
        }

        /// <summary>
        /// Restores a project from backup file.
        /// </summary>
        public async Task<ProjectInfo> RestoreProjectFromBackupAsync(string backupFilePath, string newProjectName = null)
        {
            if (string.IsNullOrWhiteSpace(backupFilePath))
                throw new ArgumentException("Backup file path cannot be null or empty", nameof(backupFilePath));

            if (!File.Exists(backupFilePath))
                throw new FileNotFoundException($"Backup file not found: {backupFilePath}");

            using var scope = _logger.BeginScope("RestoreProjectFromBackup {BackupFile}", backupFilePath);

            try
            {
                _logger.LogInformation("Restoring project from backup: {BackupFile}", backupFilePath);

                // Extract backup to temporary location
                var tempDir = Path.Combine(Path.GetTempPath(), $"ArchBuilder_Restore_{Guid.NewGuid():N}");
                Directory.CreateDirectory(tempDir);

                try
                {
                    // Extract backup zip file
                    System.IO.Compression.ZipFile.ExtractToDirectory(backupFilePath, tempDir);

                    // Load project metadata from backup
                    var metadataPath = Path.Combine(tempDir, "project.json");
                    if (!File.Exists(metadataPath))
                    {
                        throw new ProjectCorruptedException("Invalid backup file: project metadata not found");
                    }

                    var jsonContent = await File.ReadAllTextAsync(metadataPath);
                    var restoredProject = JsonSerializer.Deserialize<ProjectInfo>(jsonContent, _jsonOptions);

                    // Update project information
                    restoredProject.Id = $"PROJ_{DateTime.UtcNow:yyyyMMddHHmmss}_{Guid.NewGuid():N}";
                    restoredProject.Name = newProjectName ?? $"{restoredProject.Name}_Restored";
                    restoredProject.CreatedAt = DateTime.UtcNow;
                    restoredProject.UpdatedAt = DateTime.UtcNow;
                    restoredProject.LastAccessedAt = DateTime.UtcNow;

                    // Create new project directory
                    var newProjectPath = Path.Combine(_projectsDirectory, restoredProject.Id);
                    Directory.CreateDirectory(newProjectPath);

                    // Copy all files from temp directory to new project directory
                    await CopyDirectoryAsync(tempDir, newProjectPath);

                    // Save updated project metadata
                    await SaveProjectMetadataAsync(restoredProject);

                    _logger.LogInformation("Project restored successfully: {ProjectId}", restoredProject.Id);
                    return restoredProject;
                }
                finally
                {
                    // Clean up temporary directory
                    if (Directory.Exists(tempDir))
                    {
                        Directory.Delete(tempDir, recursive: true);
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to restore project from backup: {BackupFile}", backupFilePath);
                throw new ProjectRestoreException($"Failed to restore project from backup: {ex.Message}", ex);
            }
        }

        #endregion

        #region Private Methods

        private async Task ValidateProjectInfoAsync(ProjectInfo projectInfo)
        {
            var errors = new List<string>();

            if (string.IsNullOrWhiteSpace(projectInfo.Name))
                errors.Add("Project name is required");

            if (projectInfo.Name?.Length > 100)
                errors.Add("Project name cannot exceed 100 characters");

            if (projectInfo.Description?.Length > 1000)
                errors.Add("Project description cannot exceed 1000 characters");

            // Check for duplicate project names
            var existingProjects = await GetProjectListAsync();
            if (existingProjects.Any(p => p.Name.Equals(projectInfo.Name, StringComparison.OrdinalIgnoreCase)))
                errors.Add($"A project with the name '{projectInfo.Name}' already exists");

            if (errors.Any())
                throw new ValidationException($"Project validation failed: {string.Join(", ", errors)}");
        }

        private async Task SaveProjectMetadataAsync(ProjectInfo project)
        {
            var projectPath = Path.Combine(_projectsDirectory, project.Id);
            var metadataPath = Path.Combine(projectPath, "project.json");

            var jsonContent = JsonSerializer.Serialize(project, _jsonOptions);
            await File.WriteAllTextAsync(metadataPath, jsonContent);
        }

        private async Task LoadProjectFilesAsync(ProjectInfo project)
        {
            var filesPath = Path.Combine(_projectsDirectory, project.Id, "Files");
            if (!Directory.Exists(filesPath))
                return;

            project.Files ??= new List<ProjectFile>();

            var fileInfos = new DirectoryInfo(filesPath).GetFiles();
            foreach (var fileInfo in fileInfos)
            {
                var existingFile = project.Files.FirstOrDefault(f => f.Name == fileInfo.Name);
                if (existingFile == null)
                {
                    // File exists on disk but not in metadata, add it
                    var projectFile = new ProjectFile
                    {
                        Id = Guid.NewGuid().ToString(),
                        Name = fileInfo.Name,
                        FilePath = fileInfo.FullName,
                        SizeBytes = fileInfo.Length,
                        ImportedAt = fileInfo.CreationTime,
                        Type = GetFileTypeFromExtension(fileInfo.Extension)
                    };
                    project.Files.Add(projectFile);
                }
                else
                {
                    // Update file metadata
                    existingFile.FilePath = fileInfo.FullName;
                    existingFile.SizeBytes = fileInfo.Length;
                }
            }
        }

        private async Task SaveProjectFilesMetadataAsync(ProjectInfo project)
        {
            // Implementation for saving file metadata
            // This could involve creating a separate files.json or updating the main project.json
            await SaveProjectMetadataAsync(project);
        }

        private async Task<long> CalculateProjectSizeAsync(string projectPath)
        {
            try
            {
                var dirInfo = new DirectoryInfo(projectPath);
                return dirInfo.GetFiles("*", SearchOption.AllDirectories).Sum(f => f.Length);
            }
            catch
            {
                return 0;
            }
        }

        private async Task<ValidationResult> ValidateProjectFileAsync(ProjectFile file)
        {
            var result = new ValidationResult { IsValid = true, Errors = new List<string>() };

            // Validate file size
            var maxFileSizeMb = _configurationService.GetConfigValue<int>("FileProcessing:MaxFileSizeMB", 100);
            if (file.Content?.Length > maxFileSizeMb * 1024 * 1024)
            {
                result.Errors.Add($"File size exceeds maximum allowed size of {maxFileSizeMb}MB");
            }

            // Validate file type
            var allowedExtensions = _configurationService.GetConfigValue<string[]>("FileProcessing:AllowedExtensions", 
                new[] { ".dwg", ".dxf", ".ifc", ".pdf", ".png", ".jpg", ".jpeg" });

            var extension = Path.GetExtension(file.Name).ToLowerInvariant();
            if (!allowedExtensions.Contains(extension))
            {
                result.Errors.Add($"File type {extension} is not allowed");
            }

            result.IsValid = !result.Errors.Any();
            return result;
        }

        private async Task<string> ExportAsZipAsync(ProjectInfo project, ExportOptions options)
        {
            var exportPath = options.OutputPath ?? Path.Combine(_projectsDirectory, project.Id, "Exports", $"{project.Name}_{DateTime.UtcNow:yyyyMMddHHmmss}.zip");
            
            var projectPath = Path.Combine(_projectsDirectory, project.Id);
            System.IO.Compression.ZipFile.CreateFromDirectory(projectPath, exportPath);
            
            return exportPath;
        }

        private async Task<string> ExportAsJsonAsync(ProjectInfo project, ExportOptions options)
        {
            var exportPath = options.OutputPath ?? Path.Combine(_projectsDirectory, project.Id, "Exports", $"{project.Name}_{DateTime.UtcNow:yyyyMMddHHmmss}.json");
            
            var jsonContent = JsonSerializer.Serialize(project, _jsonOptions);
            await File.WriteAllTextAsync(exportPath, jsonContent);
            
            return exportPath;
        }

        private async Task<string> ExportAsPdfAsync(ProjectInfo project, ExportOptions options)
        {
            // TODO: Implement PDF export functionality
            // This would involve creating a PDF report with project information and thumbnails
            throw new NotImplementedException("PDF export functionality is not yet implemented");
        }

        private async Task ValidateProjectStructureAsync(ProjectInfo project, ProjectValidationResult result)
        {
            var projectPath = Path.Combine(_projectsDirectory, project.Id);
            
            var requiredDirs = new[] { "Files", "Exports", "Backups", "Documentation" };
            foreach (var dir in requiredDirs)
            {
                var dirPath = Path.Combine(projectPath, dir);
                if (!Directory.Exists(dirPath))
                {
                    result.Issues.Add(new ValidationIssue
                    {
                        Type = "Structure",
                        Severity = ValidationSeverity.Warning,
                        Message = $"Missing directory: {dir}",
                        Recommendation = $"Create the {dir} directory"
                    });
                }
            }
        }

        private async Task ValidateProjectFilesAsync(ProjectInfo project, ProjectValidationResult result)
        {
            if (project.Files == null || !project.Files.Any())
                return;

            foreach (var file in project.Files)
            {
                if (!File.Exists(file.FilePath))
                {
                    result.Issues.Add(new ValidationIssue
                    {
                        Type = "File",
                        Severity = ValidationSeverity.Error,
                        Message = $"File not found: {file.Name}",
                        Recommendation = "Remove file reference or restore missing file"
                    });
                }
            }
        }

        private async Task ValidateProjectMetadataAsync(ProjectInfo project, ProjectValidationResult result)
        {
            if (string.IsNullOrWhiteSpace(project.Name))
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Metadata",
                    Severity = ValidationSeverity.Error,
                    Message = "Project name is missing",
                    Recommendation = "Set a valid project name"
                });
            }

            if (project.CreatedAt == default)
            {
                result.Issues.Add(new ValidationIssue
                {
                    Type = "Metadata",
                    Severity = ValidationSeverity.Warning,
                    Message = "Project creation date is not set",
                    Recommendation = "Update creation date metadata"
                });
            }
        }

        private string GetFileTypeFromExtension(string extension)
        {
            return extension.ToLowerInvariant() switch
            {
                ".dwg" => "CAD Drawing",
                ".dxf" => "CAD Exchange",
                ".ifc" => "Building Information Model",
                ".pdf" => "Document",
                ".png" or ".jpg" or ".jpeg" => "Image",
                _ => "Unknown"
            };
        }

        private async Task CopyDirectoryAsync(string sourceDir, string destDir)
        {
            Directory.CreateDirectory(destDir);

            foreach (var file in Directory.GetFiles(sourceDir))
            {
                var destFile = Path.Combine(destDir, Path.GetFileName(file));
                File.Copy(file, destFile, overwrite: true);
            }

            foreach (var dir in Directory.GetDirectories(sourceDir))
            {
                var destSubDir = Path.Combine(destDir, Path.GetFileName(dir));
                await CopyDirectoryAsync(dir, destSubDir);
            }
        }

        #endregion
    }
}