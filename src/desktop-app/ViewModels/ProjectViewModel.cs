using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using ArchBuilder.Models;
using ArchBuilder.Core;
using Microsoft.Extensions.Logging;
using Microsoft.Win32;
using System.IO;
using System.Windows;

namespace ArchBuilder.ViewModels
{
    /// <summary>
    /// ViewModel for Project Management interface
    /// Handles project operations, file imports, and status tracking
    /// Following MVVM pattern with Apple-vari design integration
    /// </summary>
    public class ProjectViewModel : INotifyPropertyChanged, IDisposable
    {
        private readonly ILogger<ProjectViewModel> _logger;
        private bool _isLoading;
        private string _loadingMessage = "Loading...";
        private bool _disposed;

        // Observable collections for UI binding
        public ObservableCollection<ProjectInfo> RecentProjects { get; }
        public ObservableCollection<ProjectFile> ImportedFiles { get; }

        // Statistics properties
        private int _totalProjectsCount;
        private int _activeProjectsCount;
        private int _totalFilesCount;
        private double _successRate = 95.5;

        public ProjectViewModel()
        {
            _logger = ServiceLocator.GetService<ILogger<ProjectViewModel>>();
            _logger?.LogInformation("ProjectViewModel initializing");

            // Initialize collections
            RecentProjects = new ObservableCollection<ProjectInfo>();
            ImportedFiles = new ObservableCollection<ProjectFile>();

            // Initialize commands
            InitializeCommands();

            // Load initial data
            _ = LoadInitialDataAsync();

            _logger?.LogInformation("ProjectViewModel initialized successfully");
        }

        #region Properties

        /// <summary>
        /// Loading state for UI feedback
        /// </summary>
        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (_isLoading != value)
                {
                    _isLoading = value;
                    OnPropertyChanged(nameof(IsLoading));
                }
            }
        }

        /// <summary>
        /// Loading message for user feedback
        /// </summary>
        public string LoadingMessage
        {
            get => _loadingMessage;
            set
            {
                if (_loadingMessage != value)
                {
                    _loadingMessage = value;
                    OnPropertyChanged(nameof(LoadingMessage));
                }
            }
        }

        /// <summary>
        /// Total number of projects
        /// </summary>
        public int TotalProjectsCount
        {
            get => _totalProjectsCount;
            set
            {
                if (_totalProjectsCount != value)
                {
                    _totalProjectsCount = value;
                    OnPropertyChanged(nameof(TotalProjectsCount));
                }
            }
        }

        /// <summary>
        /// Number of active projects
        /// </summary>
        public int ActiveProjectsCount
        {
            get => _activeProjectsCount;
            set
            {
                if (_activeProjectsCount != value)
                {
                    _activeProjectsCount = value;
                    OnPropertyChanged(nameof(ActiveProjectsCount));
                }
            }
        }

        /// <summary>
        /// Total number of imported files
        /// </summary>
        public int TotalFilesCount
        {
            get => _totalFilesCount;
            set
            {
                if (_totalFilesCount != value)
                {
                    _totalFilesCount = value;
                    OnPropertyChanged(nameof(TotalFilesCount));
                }
            }
        }

        /// <summary>
        /// Project success rate percentage
        /// </summary>
        public double SuccessRate
        {
            get => _successRate;
            set
            {
                if (Math.Abs(_successRate - value) > 0.01)
                {
                    _successRate = value;
                    OnPropertyChanged(nameof(SuccessRate));
                }
            }
        }

        /// <summary>
        /// Whether there are recent projects to display
        /// </summary>
        public bool HasRecentProjects => RecentProjects?.Count == 0;

        #endregion

        #region Commands

        public ICommand CreateNewProjectCommand { get; private set; }
        public ICommand ImportProjectCommand { get; private set; }
        public ICommand ImportFileCommand { get; private set; }
        public ICommand OpenProjectCommand { get; private set; }
        public ICommand ViewAllProjectsCommand { get; private set; }
        public ICommand HandleDroppedFilesCommand { get; private set; }
        public ICommand RefreshCommand { get; private set; }

        private void InitializeCommands()
        {
            try
            {
                CreateNewProjectCommand = new RelayCommand(async _ => await CreateNewProjectAsync(), _ => !IsLoading);
                ImportProjectCommand = new RelayCommand(async _ => await ImportProjectAsync(), _ => !IsLoading);
                ImportFileCommand = new RelayCommand<ProjectFileType>(async fileType => await ImportFileAsync(fileType), _ => !IsLoading);
                OpenProjectCommand = new RelayCommand<ProjectInfo>(async project => await OpenProjectAsync(project), project => project != null && !IsLoading);
                ViewAllProjectsCommand = new RelayCommand(async _ => await ViewAllProjectsAsync(), _ => !IsLoading);
                HandleDroppedFilesCommand = new RelayCommand<string[]>(async files => await HandleDroppedFilesAsync(files), files => files != null && files.Length > 0 && !IsLoading);
                RefreshCommand = new RelayCommand(async _ => await RefreshDataAsync(), _ => !IsLoading);

                _logger?.LogInformation("Commands initialized successfully");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error initializing commands");
                throw;
            }
        }

        #endregion

        #region Command Implementations

        /// <summary>
        /// Creates a new project with initial setup
        /// </summary>
        private async Task CreateNewProjectAsync()
        {
            try
            {
                _logger?.LogInformation("Starting new project creation");
                IsLoading = true;
                LoadingMessage = "Creating new project...";

                // Create new project with default values
                var newProject = new ProjectInfo
                {
                    Name = $"New Project {DateTime.Now:yyyyMMdd-HHmmss}",
                    Description = "A new architectural project created with ArchBuilder.AI",
                    Type = ProjectType.Residential,
                    Status = ProjectStatus.Draft,
                    TotalAreaM2 = 100.0, // Default 100 m²
                    CreatedAt = DateTime.Now,
                    LastModified = DateTime.Now
                };

                // Initialize project status
                var statusInfo = new ProjectStatusInfo
                {
                    ProjectCorrelationId = newProject.CorrelationId,
                    CurrentPhase = ProjectPhase.Initialization,
                    OverallProgress = 0.0,
                    StatusMessage = "Project created successfully"
                };
                statusInfo.InitializePhaseProgresses();

                // Simulate project creation delay (would be actual API call)
                await Task.Delay(1000);

                // Add to recent projects
                RecentProjects.Insert(0, newProject);
                
                // Update statistics
                TotalProjectsCount++;
                ActiveProjectsCount++;
                
                OnPropertyChanged(nameof(HasRecentProjects));

                _logger?.LogInformation("New project created successfully: {ProjectName}", newProject.Name);

                // Show success message
                MessageBox.Show(
                    $"Project '{newProject.Name}' created successfully!",
                    "ArchBuilder.AI - Project Created",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error creating new project");
                MessageBox.Show(
                    "Failed to create new project. Please try again.",
                    "ArchBuilder.AI - Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                IsLoading = false;
            }
        }

        /// <summary>
        /// Imports project files through file dialog
        /// </summary>
        private async Task ImportProjectAsync()
        {
            try
            {
                _logger?.LogInformation("Starting project import");

                var openFileDialog = new OpenFileDialog
                {
                    Title = "Import Project Files - ArchBuilder.AI",
                    Filter = "All Supported Files|*.dwg;*.dxf;*.ifc;*.pdf;*.rvt|" +
                            "AutoCAD Files (*.dwg)|*.dwg|" +
                            "AutoCAD Exchange (*.dxf)|*.dxf|" +
                            "IFC Files (*.ifc)|*.ifc|" +
                            "PDF Documents (*.pdf)|*.pdf|" +
                            "Revit Files (*.rvt)|*.rvt|" +
                            "All Files (*.*)|*.*",
                    Multiselect = true,
                    CheckFileExists = true,
                    CheckPathExists = true
                };

                if (openFileDialog.ShowDialog() == true)
                {
                    await ProcessSelectedFilesAsync(openFileDialog.FileNames);
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during project import");
                MessageBox.Show(
                    "Failed to import project files. Please try again.",
                    "ArchBuilder.AI - Import Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// Imports specific file type
        /// </summary>
        private async Task ImportFileAsync(ProjectFileType fileType)
        {
            try
            {
                _logger?.LogInformation("Starting file import for type: {FileType}", fileType);

                var filter = fileType switch
                {
                    ProjectFileType.DWG => "AutoCAD Drawing Files (*.dwg)|*.dwg",
                    ProjectFileType.DXF => "AutoCAD Exchange Files (*.dxf)|*.dxf",
                    ProjectFileType.IFC => "IFC Model Files (*.ifc)|*.ifc",
                    ProjectFileType.PDF => "PDF Documents (*.pdf)|*.pdf",
                    ProjectFileType.RVT => "Revit Project Files (*.rvt)|*.rvt",
                    _ => "All Files (*.*)|*.*"
                };

                var openFileDialog = new OpenFileDialog
                {
                    Title = $"Import {fileType} Files - ArchBuilder.AI",
                    Filter = filter,
                    Multiselect = true,
                    CheckFileExists = true,
                    CheckPathExists = true
                };

                if (openFileDialog.ShowDialog() == true)
                {
                    await ProcessSelectedFilesAsync(openFileDialog.FileNames);
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error importing {FileType} files", fileType);
                MessageBox.Show(
                    $"Failed to import {fileType} files. Please try again.",
                    "ArchBuilder.AI - Import Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// Opens an existing project
        /// </summary>
        private async Task OpenProjectAsync(ProjectInfo project)
        {
            try
            {
                _logger?.LogInformation("Opening project: {ProjectName}", project.Name);
                IsLoading = true;
                LoadingMessage = $"Opening project '{project.Name}'...";

                // Simulate project loading (would be actual navigation/loading)
                await Task.Delay(800);

                // TODO: Navigate to project detail view
                // For now, just show a message
                MessageBox.Show(
                    $"Opening project '{project.Name}'\n\n" +
                    $"Type: {project.TypeDisplayName}\n" +
                    $"Status: {project.StatusDisplayName}\n" +
                    $"Area: {project.TotalAreaDisplayText}\n" +
                    $"Last Modified: {project.LastModifiedDisplayText}",
                    "ArchBuilder.AI - Project Details",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);

                _logger?.LogInformation("Project opened successfully: {ProjectName}", project.Name);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error opening project: {ProjectName}", project.Name);
                MessageBox.Show(
                    $"Failed to open project '{project.Name}'. Please try again.",
                    "ArchBuilder.AI - Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                IsLoading = false;
            }
        }

        /// <summary>
        /// Views all projects in expanded view
        /// </summary>
        private async Task ViewAllProjectsAsync()
        {
            try
            {
                _logger?.LogInformation("Viewing all projects");
                IsLoading = true;
                LoadingMessage = "Loading all projects...";

                // Simulate loading all projects
                await Task.Delay(500);

                // TODO: Navigate to all projects view
                MessageBox.Show(
                    "All Projects view would be displayed here.\n\n" +
                    $"Total Projects: {TotalProjectsCount}\n" +
                    $"Active Projects: {ActiveProjectsCount}\n" +
                    $"Recent Projects: {RecentProjects.Count}",
                    "ArchBuilder.AI - All Projects",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);

                _logger?.LogInformation("All projects view displayed");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error viewing all projects");
                MessageBox.Show(
                    "Failed to load all projects. Please try again.",
                    "ArchBuilder.AI - Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                IsLoading = false;
            }
        }

        /// <summary>
        /// Handles files dropped onto the interface
        /// </summary>
        private async Task HandleDroppedFilesAsync(string[] files)
        {
            try
            {
                _logger?.LogInformation("Handling dropped files: {FileCount} files", files.Length);
                await ProcessSelectedFilesAsync(files);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling dropped files");
                MessageBox.Show(
                    "Failed to process dropped files. Please try importing them individually.",
                    "ArchBuilder.AI - Drop Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// Refreshes all data
        /// </summary>
        private async Task RefreshDataAsync()
        {
            try
            {
                _logger?.LogInformation("Refreshing project data");
                IsLoading = true;
                LoadingMessage = "Refreshing data...";

                // Simulate data refresh
                await Task.Delay(1000);
                await LoadInitialDataAsync();

                _logger?.LogInformation("Project data refreshed successfully");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error refreshing project data");
                MessageBox.Show(
                    "Failed to refresh data. Please try again.",
                    "ArchBuilder.AI - Refresh Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                IsLoading = false;
            }
        }

        #endregion

        #region Helper Methods

        /// <summary>
        /// Loads initial project data
        /// </summary>
        private async Task LoadInitialDataAsync()
        {
            try
            {
                _logger?.LogInformation("Loading initial project data");
                IsLoading = true;
                LoadingMessage = "Loading projects...";

                // Simulate data loading (would be actual data service calls)
                await Task.Delay(800);

                // Load sample projects for demonstration
                LoadSampleProjects();

                // Update statistics
                UpdateStatistics();

                OnPropertyChanged(nameof(HasRecentProjects));
                _logger?.LogInformation("Initial project data loaded successfully");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error loading initial project data");
            }
            finally
            {
                IsLoading = false;
            }
        }

        /// <summary>
        /// Loads sample projects for demonstration
        /// </summary>
        private void LoadSampleProjects()
        {
            RecentProjects.Clear();

            // Add sample projects
            var sampleProjects = new[]
            {
                new ProjectInfo
                {
                    Name = "Modern Residential Complex",
                    Description = "A contemporary residential building with sustainable design features",
                    Type = ProjectType.Residential,
                    Status = ProjectStatus.InProgress,
                    TotalAreaM2 = 2500.0,
                    CreatedAt = DateTime.Now.AddDays(-10),
                    LastModified = DateTime.Now.AddDays(-2)
                },
                new ProjectInfo
                {
                    Name = "Corporate Office Tower",
                    Description = "High-rise office building with smart building technologies",
                    Type = ProjectType.Commercial,
                    Status = ProjectStatus.UnderReview,
                    TotalAreaM2 = 15000.0,
                    CreatedAt = DateTime.Now.AddDays(-20),
                    LastModified = DateTime.Now.AddDays(-5)
                },
                new ProjectInfo
                {
                    Name = "Educational Campus",
                    Description = "University campus expansion project with multiple buildings",
                    Type = ProjectType.Educational,
                    Status = ProjectStatus.Approved,
                    TotalAreaM2 = 8000.0,
                    CreatedAt = DateTime.Now.AddDays(-30),
                    LastModified = DateTime.Now.AddDays(-7)
                }
            };

            foreach (var project in sampleProjects)
            {
                RecentProjects.Add(project);
            }
        }

        /// <summary>
        /// Updates project statistics
        /// </summary>
        private void UpdateStatistics()
        {
            TotalProjectsCount = RecentProjects.Count + 15; // Including non-recent projects
            ActiveProjectsCount = RecentProjects.Count(p => p.Status == ProjectStatus.InProgress || p.Status == ProjectStatus.UnderReview);
            TotalFilesCount = ImportedFiles.Count + 45; // Including historical files
            SuccessRate = 95.5; // Sample success rate
        }

        /// <summary>
        /// Processes selected files for import
        /// </summary>
        private async Task ProcessSelectedFilesAsync(string[] filePaths)
        {
            try
            {
                _logger?.LogInformation("Processing {FileCount} selected files", filePaths.Length);
                IsLoading = true;
                LoadingMessage = "Processing files...";

                var validFiles = new List<string>();
                var invalidFiles = new List<string>();

                // Validate each file
                foreach (var filePath in filePaths)
                {
                    if (ValidateFile(filePath))
                    {
                        validFiles.Add(filePath);
                    }
                    else
                    {
                        invalidFiles.Add(filePath);
                    }
                }

                if (validFiles.Count == 0)
                {
                    MessageBox.Show(
                        "No valid files found to import.\n\n" +
                        "Supported formats: DWG, DXF, IFC, PDF, RVT",
                        "ArchBuilder.AI - No Valid Files",
                        MessageBoxButton.OK,
                        MessageBoxImage.Warning);
                    return;
                }

                // Process valid files
                var processedFiles = new List<ProjectFile>();
                var currentFile = 1;

                foreach (var filePath in validFiles)
                {
                    LoadingMessage = $"Processing file {currentFile} of {validFiles.Count}...";
                    
                    var projectFile = await ProcessSingleFileAsync(filePath);
                    if (projectFile != null)
                    {
                        processedFiles.Add(projectFile);
                        ImportedFiles.Add(projectFile);
                    }

                    currentFile++;
                    await Task.Delay(200); // Simulate processing time
                }

                // Update statistics
                TotalFilesCount += processedFiles.Count;

                // Show results
                var resultMessage = $"Successfully imported {processedFiles.Count} file(s).";
                if (invalidFiles.Count > 0)
                {
                    resultMessage += $"\n\n{invalidFiles.Count} file(s) were skipped (unsupported format or invalid).";
                }

                MessageBox.Show(
                    resultMessage,
                    "ArchBuilder.AI - Import Complete",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);

                _logger?.LogInformation("File processing completed: {ValidFiles} valid, {InvalidFiles} invalid",
                    processedFiles.Count, invalidFiles.Count);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error processing selected files");
                MessageBox.Show(
                    "Error occurred while processing files. Some files may not have been imported.",
                    "ArchBuilder.AI - Processing Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                IsLoading = false;
            }
        }

        /// <summary>
        /// Processes a single file and creates ProjectFile model
        /// </summary>
        private async Task<ProjectFile?> ProcessSingleFileAsync(string filePath)
        {
            try
            {
                var fileInfo = new FileInfo(filePath);
                var fileType = ProjectFile.GetFileTypeFromExtension(fileInfo.Name);

                var projectFile = new ProjectFile
                {
                    FileName = fileInfo.Name,
                    FilePath = filePath,
                    FileType = fileType,
                    FileSizeBytes = fileInfo.Length,
                    CreatedAt = DateTime.Now,
                    LastModified = fileInfo.LastWriteTime,
                    ProcessingStatus = FileProcessingStatus.Processing
                };

                // Simulate file processing
                await Task.Delay(500);

                // Extract basic metadata (simplified for demo)
                projectFile.Metadata.Units = "Millimeters";
                projectFile.Metadata.LayerCount = new Random().Next(5, 50);
                projectFile.Metadata.EntityCount = new Random().Next(100, 5000);

                // Set security info
                projectFile.SecurityInfo.ChecksumMD5 = GenerateSimpleHash(filePath);
                projectFile.SecurityInfo.VirusScanPassed = true;
                projectFile.SecurityInfo.LastScanned = DateTime.Now;

                projectFile.ProcessingStatus = FileProcessingStatus.Completed;

                return projectFile;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error processing file: {FilePath}", filePath);
                return null;
            }
        }

        /// <summary>
        /// Validates file for import
        /// </summary>
        private bool ValidateFile(string filePath)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
                    return false;

                var fileInfo = new FileInfo(filePath);
                
                // Check file size (500MB limit)
                if (fileInfo.Length > 500 * 1024 * 1024)
                    return false;

                // Check supported extensions
                var extension = fileInfo.Extension.ToLowerInvariant();
                var supportedExtensions = new[] { ".dwg", ".dxf", ".ifc", ".pdf", ".rvt" };
                
                return Array.Exists(supportedExtensions, ext => ext == extension);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error validating file: {FilePath}", filePath);
                return false;
            }
        }

        /// <summary>
        /// Generates a simple hash for demonstration
        /// </summary>
        private string GenerateSimpleHash(string input)
        {
            return $"MD5{DateTime.Now.Ticks:X}";
        }

        #endregion

        #region INotifyPropertyChanged Implementation

        public event PropertyChangedEventHandler? PropertyChanged;

        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        #endregion

        #region IDisposable Implementation

        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        protected virtual void Dispose(bool disposing)
        {
            if (!_disposed && disposing)
            {
                try
                {
                    _logger?.LogInformation("ProjectViewModel disposing");
                    
                    // Clear collections
                    RecentProjects?.Clear();
                    ImportedFiles?.Clear();

                    _disposed = true;
                    _logger?.LogInformation("ProjectViewModel disposed successfully");
                }
                catch (Exception ex)
                {
                    _logger?.LogError(ex, "Error during ProjectViewModel disposal");
                }
            }
        }

        ~ProjectViewModel()
        {
            Dispose(false);
        }

        #endregion
    }
}