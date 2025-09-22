using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ArchBuilder.Desktop.Models;

namespace ArchBuilder.Desktop.Services
{
    /// <summary>
    /// Interface for project data persistence and management services.
    /// Handles project creation, loading, saving, and metadata management.
    /// </summary>
    public interface IProjectDataService
    {
        /// <summary>
        /// Creates a new project with the specified information.
        /// </summary>
        /// <param name="projectInfo">Project information including name, description, and basic settings</param>
        /// <returns>The created project with assigned ID and metadata</returns>
        /// <exception cref="ArgumentNullException">Thrown when projectInfo is null</exception>
        /// <exception cref="InvalidOperationException">Thrown when project creation fails</exception>
        Task<ProjectInfo> CreateProjectAsync(ProjectInfo projectInfo);

        /// <summary>
        /// Loads an existing project by ID with all associated data.
        /// </summary>
        /// <param name="projectId">Unique identifier of the project to load</param>
        /// <returns>Complete project information including files and metadata</returns>
        /// <exception cref="ArgumentException">Thrown when projectId is invalid</exception>
        /// <exception cref="ProjectNotFoundException">Thrown when project is not found</exception>
        Task<ProjectInfo> LoadProjectAsync(string projectId);

        /// <summary>
        /// Saves project changes to persistent storage.
        /// </summary>
        /// <param name="project">Project information to save</param>
        /// <returns>Task representing the save operation</returns>
        /// <exception cref="ArgumentNullException">Thrown when project is null</exception>
        /// <exception cref="UnauthorizedAccessException">Thrown when write access is denied</exception>
        Task SaveProjectAsync(ProjectInfo project);

        /// <summary>
        /// Retrieves a list of all available projects for the current user.
        /// </summary>
        /// <returns>List of project summaries with basic information</returns>
        Task<List<ProjectSummary>> GetProjectListAsync();

        /// <summary>
        /// Deletes a project and all associated data permanently.
        /// </summary>
        /// <param name="projectId">ID of the project to delete</param>
        /// <returns>True if deletion was successful, false otherwise</returns>
        /// <exception cref="ArgumentException">Thrown when projectId is invalid</exception>
        /// <exception cref="ProjectNotFoundException">Thrown when project is not found</exception>
        Task<bool> DeleteProjectAsync(string projectId);

        /// <summary>
        /// Updates project metadata without modifying content data.
        /// </summary>
        /// <param name="projectId">ID of the project to update</param>
        /// <param name="metadata">New metadata to apply</param>
        /// <returns>Task representing the update operation</returns>
        Task UpdateProjectMetadataAsync(string projectId, ProjectMetadata metadata);

        /// <summary>
        /// Imports project files and validates their format and content.
        /// </summary>
        /// <param name="projectId">Target project ID</param>
        /// <param name="files">List of files to import</param>
        /// <returns>Import result with validation details</returns>
        Task<ImportResult> ImportProjectFilesAsync(string projectId, List<ProjectFile> files);

        /// <summary>
        /// Exports project data to specified format and location.
        /// </summary>
        /// <param name="projectId">ID of the project to export</param>
        /// <param name="exportOptions">Export configuration and options</param>
        /// <returns>Export result with file paths and status</returns>
        Task<ExportResult> ExportProjectAsync(string projectId, ExportOptions exportOptions);

        /// <summary>
        /// Gets recent projects for quick access.
        /// </summary>
        /// <param name="count">Maximum number of recent projects to return</param>
        /// <returns>List of recently accessed projects</returns>
        Task<List<ProjectSummary>> GetRecentProjectsAsync(int count = 10);

        /// <summary>
        /// Validates project data integrity and consistency.
        /// </summary>
        /// <param name="projectId">ID of the project to validate</param>
        /// <returns>Validation result with any issues found</returns>
        Task<ProjectValidationResult> ValidateProjectAsync(string projectId);

        /// <summary>
        /// Creates a backup of the specified project.
        /// </summary>
        /// <param name="projectId">ID of the project to backup</param>
        /// <param name="backupLocation">Optional backup location (uses default if null)</param>
        /// <returns>Backup result with backup file path</returns>
        Task<BackupResult> CreateProjectBackupAsync(string projectId, string backupLocation = null);

        /// <summary>
        /// Restores a project from backup file.
        /// </summary>
        /// <param name="backupFilePath">Path to the backup file</param>
        /// <param name="newProjectName">Optional new name for restored project</param>
        /// <returns>Restored project information</returns>
        Task<ProjectInfo> RestoreProjectFromBackupAsync(string backupFilePath, string newProjectName = null);
    }
}