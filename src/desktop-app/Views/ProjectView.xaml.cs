using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using ArchBuilder.ViewModels;
using ArchBuilder.Models;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Views
{
    /// <summary>
    /// Project Management View - Apple-vari design interface for managing architectural projects
    /// Handles file imports (DWG/DXF/IFC/PDF), project creation, and status tracking
    /// Following UX/UI design standards for professional architect workflows
    /// </summary>
    public partial class ProjectView : UserControl
    {
        private readonly ILogger<ProjectView> _logger;
        private ProjectViewModel? _viewModel;

        public ProjectView()
        {
            InitializeComponent();
            _logger = ServiceLocator.GetService<ILogger<ProjectView>>();
            _logger?.LogInformation("ProjectView initialized");
            
            Loaded += ProjectView_Loaded;
        }

        private void ProjectView_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                _viewModel = DataContext as ProjectViewModel;
                if (_viewModel == null)
                {
                    _logger?.LogWarning("ProjectViewModel not found in DataContext");
                }
                else
                {
                    _logger?.LogInformation("ProjectView loaded successfully with ViewModel");
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during ProjectView load");
            }
        }

        /// <summary>
        /// Handles project item click for navigation to project details
        /// </summary>
        private void ProjectItem_Click(object sender, MouseButtonEventArgs e)
        {
            try
            {
                if (sender is Border border && border.Tag is ProjectInfo project)
                {
                    _logger?.LogInformation("Project item clicked: {ProjectName}", project.Name);
                    _viewModel?.OpenProjectCommand?.Execute(project);
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling project item click");
                ShowErrorMessage("Failed to open project. Please try again.");
            }
        }

        /// <summary>
        /// Handles file import click based on file type
        /// </summary>
        private void ImportFile_Click(object sender, MouseButtonEventArgs e)
        {
            try
            {
                if (sender is Border border && border.Tag is string fileType)
                {
                    _logger?.LogInformation("File import clicked for type: {FileType}", fileType);
                    
                    var fileTypeEnum = fileType switch
                    {
                        "DWG" => ProjectFileType.DWG,
                        "DXF" => ProjectFileType.DXF,
                        "IFC" => ProjectFileType.IFC,
                        "PDF" => ProjectFileType.PDF,
                        _ => ProjectFileType.Other
                    };

                    _viewModel?.ImportFileCommand?.Execute(fileTypeEnum);
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling file import click for type: {FileType}", 
                    (sender as Border)?.Tag);
                ShowErrorMessage("Failed to start file import. Please try again.");
            }
        }

        /// <summary>
        /// Handles drag and drop file operations
        /// </summary>
        private void DropArea_Drop(object sender, DragEventArgs e)
        {
            try
            {
                if (e.Data.GetDataPresent(DataFormats.FileDrop))
                {
                    var files = (string[])e.Data.GetData(DataFormats.FileDrop);
                    if (files != null && files.Length > 0)
                    {
                        _logger?.LogInformation("Files dropped: {FileCount} files", files.Length);
                        _viewModel?.HandleDroppedFilesCommand?.Execute(files);
                    }
                }

                // Reset drop area appearance
                if (sender is Border border)
                {
                    border.Background = System.Windows.Media.Brushes.Transparent;
                    border.BorderBrush = (System.Windows.Media.Brush)FindResource("CardBorderBrush");
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling dropped files");
                ShowErrorMessage("Failed to process dropped files. Please try importing them individually.");
            }
        }

        /// <summary>
        /// Handles drag over events for visual feedback
        /// </summary>
        private void DropArea_DragOver(object sender, DragEventArgs e)
        {
            try
            {
                if (e.Data.GetDataPresent(DataFormats.FileDrop))
                {
                    var files = (string[])e.Data.GetData(DataFormats.FileDrop);
                    bool hasValidFiles = false;

                    if (files != null)
                    {
                        foreach (var file in files)
                        {
                            var extension = System.IO.Path.GetExtension(file).ToLowerInvariant();
                            if (extension == ".dwg" || extension == ".dxf" || 
                                extension == ".ifc" || extension == ".pdf")
                            {
                                hasValidFiles = true;
                                break;
                            }
                        }
                    }

                    e.Effects = hasValidFiles ? DragDropEffects.Copy : DragDropEffects.None;

                    // Visual feedback for valid drop area
                    if (sender is Border border && hasValidFiles)
                    {
                        border.Background = (System.Windows.Media.Brush)FindResource("CardHoverBrush");
                        border.BorderBrush = (System.Windows.Media.Brush)FindResource("AccentBrush");
                    }
                }
                else
                {
                    e.Effects = DragDropEffects.None;
                }

                e.Handled = true;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling drag over");
                e.Effects = DragDropEffects.None;
            }
        }

        /// <summary>
        /// Handles drag leave events to reset visual state
        /// </summary>
        private void DropArea_DragLeave(object sender, DragEventArgs e)
        {
            try
            {
                if (sender is Border border)
                {
                    border.Background = System.Windows.Media.Brushes.Transparent;
                    border.BorderBrush = (System.Windows.Media.Brush)FindResource("CardBorderBrush");
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling drag leave");
            }
        }

        /// <summary>
        /// Shows error message to user with Apple-vari styling
        /// </summary>
        private void ShowErrorMessage(string message)
        {
            try
            {
                MessageBox.Show(
                    message,
                    "ArchBuilder.AI - Project Management",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to show error message: {Message}", message);
            }
        }

        /// <summary>
        /// Shows success message to user
        /// </summary>
        private void ShowSuccessMessage(string message)
        {
            try
            {
                MessageBox.Show(
                    message,
                    "ArchBuilder.AI - Project Management",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to show success message: {Message}", message);
            }
        }

        /// <summary>
        /// Validates file before processing
        /// </summary>
        private bool ValidateFile(string filePath)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(filePath))
                {
                    _logger?.LogWarning("Empty file path provided for validation");
                    return false;
                }

                if (!System.IO.File.Exists(filePath))
                {
                    _logger?.LogWarning("File does not exist: {FilePath}", filePath);
                    return false;
                }

                var fileInfo = new System.IO.FileInfo(filePath);
                
                // Check file size (500MB limit)
                if (fileInfo.Length > 500 * 1024 * 1024)
                {
                    _logger?.LogWarning("File too large: {FilePath}, Size: {FileSize}MB", 
                        filePath, fileInfo.Length / (1024 * 1024));
                    ShowErrorMessage($"File is too large. Maximum allowed size is 500MB.\nFile size: {fileInfo.Length / (1024 * 1024)}MB");
                    return false;
                }

                // Check file extension
                var extension = fileInfo.Extension.ToLowerInvariant();
                var supportedExtensions = new[] { ".dwg", ".dxf", ".ifc", ".pdf", ".rvt" };
                
                if (!Array.Exists(supportedExtensions, ext => ext == extension))
                {
                    _logger?.LogWarning("Unsupported file type: {FilePath}, Extension: {Extension}", 
                        filePath, extension);
                    ShowErrorMessage($"Unsupported file type: {extension}\nSupported types: DWG, DXF, IFC, PDF, RVT");
                    return false;
                }

                return true;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error validating file: {FilePath}", filePath);
                return false;
            }
        }

        /// <summary>
        /// Handles keyboard shortcuts for accessibility and power users
        /// </summary>
        protected override void OnKeyDown(KeyEventArgs e)
        {
            try
            {
                // Ctrl+N for new project
                if (e.Key == Key.N && Keyboard.Modifiers == ModifierKeys.Control)
                {
                    _viewModel?.CreateNewProjectCommand?.Execute(null);
                    e.Handled = true;
                    return;
                }

                // Ctrl+I for import files
                if (e.Key == Key.I && Keyboard.Modifiers == ModifierKeys.Control)
                {
                    _viewModel?.ImportProjectCommand?.Execute(null);
                    e.Handled = true;
                    return;
                }

                // F5 for refresh
                if (e.Key == Key.F5)
                {
                    _viewModel?.RefreshCommand?.Execute(null);
                    e.Handled = true;
                    return;
                }

                base.OnKeyDown(e);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling keyboard shortcut");
                base.OnKeyDown(e);
            }
        }

        /// <summary>
        /// Handles focus for accessibility
        /// </summary>
        protected override void OnGotFocus(RoutedEventArgs e)
        {
            try
            {
                base.OnGotFocus(e);
                _logger?.LogDebug("ProjectView gained focus");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling focus gained");
                base.OnGotFocus(e);
            }
        }

        /// <summary>
        /// Cleanup resources when view is unloaded
        /// </summary>
        private void ProjectView_Unloaded(object sender, RoutedEventArgs e)
        {
            try
            {
                _logger?.LogInformation("ProjectView unloading");
                
                // Cleanup any resources if needed
                if (_viewModel is IDisposable disposableViewModel)
                {
                    disposableViewModel.Dispose();
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during ProjectView unload");
            }
        }
    }
}