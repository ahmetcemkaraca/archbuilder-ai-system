using System;
using System.Windows;
using System.Windows.Input;
using ArchBuilder.ViewModels;
using ArchBuilder.Core;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Views
{
    /// <summary>
    /// MainWindow.xaml için etkileşim mantığı - Apple-vari design pattern
    /// </summary>
    public partial class MainWindow : Window
    {
        private readonly ILogger<MainWindow> _logger;
        private bool _isMaximized = false;
        private WindowState _previousWindowState;
        private Rect _previousBounds;

        public MainWindow()
        {
            InitializeComponent();
            
            // Dependency injection
            _logger = ServiceLocator.GetService<ILogger<MainWindow>>();
            
            // Window setup
            SetupWindow();
            
            // Initialize ViewModel
            DataContext = new MainViewModel();
            
            _logger?.LogInformation("MainWindow initialized successfully");
        }

        #region Window Setup

        private void SetupWindow()
        {
            // Responsive design settings
            MaxHeight = SystemParameters.MaximizedPrimaryScreenHeight;
            MaxWidth = SystemParameters.MaximizedPrimaryScreenWidth;
            
            // Store initial state
            _previousWindowState = WindowState;
            _previousBounds = new Rect(Left, Top, Width, Height);
            
            // Window event handlers
            StateChanged += MainWindow_StateChanged;
            SizeChanged += MainWindow_SizeChanged;
        }

        #endregion

        #region Window Controls

        private void MinimizeWindow_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                WindowState = WindowState.Minimized;
                _logger?.LogDebug("Window minimized");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to minimize window");
            }
        }

        private void MaximizeRestoreWindow_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                if (_isMaximized)
                {
                    RestoreWindow();
                }
                else
                {
                    MaximizeWindow();
                }
                
                _logger?.LogDebug("Window state changed to {WindowState}", WindowState);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to change window state");
            }
        }

        private void CloseWindow_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                // Graceful shutdown
                var viewModel = DataContext as MainViewModel;
                
                // TODO: Check for unsaved changes, cleanup resources etc.
                
                _logger?.LogInformation("Application shutting down");
                Application.Current.Shutdown();
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during application shutdown");
                Application.Current.Shutdown();
            }
        }

        #endregion

        #region Window Drag and Resize

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            try
            {
                if (e.ClickCount == 2)
                {
                    // Double-click to maximize/restore
                    MaximizeRestoreWindow_Click(sender, null);
                }
                else if (e.ButtonState == MouseButtonState.Pressed)
                {
                    // Single-click to drag
                    DragMove();
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during window drag operation");
            }
        }

        protected override void OnMouseLeftButtonDown(MouseButtonEventArgs e)
        {
            try
            {
                base.OnMouseLeftButtonDown(e);
                
                // Only allow drag if clicked on title bar area
                var titleBarHeight = 40;
                if (e.GetPosition(this).Y <= titleBarHeight)
                {
                    DragMove();
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during mouse down event");
            }
        }

        #endregion

        #region Window State Management

        private void MaximizeWindow()
        {
            try
            {
                _previousBounds = new Rect(Left, Top, Width, Height);
                _previousWindowState = WindowState;
                
                // Custom maximize to leave space for taskbar (Apple-like behavior)
                var workingArea = SystemParameters.WorkArea;
                Left = workingArea.Left;
                Top = workingArea.Top;
                Width = workingArea.Width;
                Height = workingArea.Height;
                
                _isMaximized = true;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to maximize window");
            }
        }

        private void RestoreWindow()
        {
            try
            {
                Left = _previousBounds.Left;
                Top = _previousBounds.Top;
                Width = _previousBounds.Width;
                Height = _previousBounds.Height;
                WindowState = _previousWindowState;
                
                _isMaximized = false;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to restore window");
            }
        }

        private void MainWindow_StateChanged(object sender, EventArgs e)
        {
            try
            {
                if (WindowState == WindowState.Maximized)
                {
                    _isMaximized = true;
                }
                else if (WindowState == WindowState.Normal)
                {
                    _isMaximized = false;
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during window state change");
            }
        }

        private void MainWindow_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            try
            {
                // Responsive design adjustments
                AdjustLayoutForSize(e.NewSize);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during window size change");
            }
        }

        #endregion

        #region Responsive Design

        private void AdjustLayoutForSize(Size newSize)
        {
            try
            {
                // Adjust navigation sidebar width based on window size
                var navigationColumn = (Grid.ColumnDefinitions[0] as System.Windows.Controls.ColumnDefinition);
                
                if (newSize.Width < 1200)
                {
                    // Narrow navigation for smaller screens
                    navigationColumn.Width = new GridLength(240);
                }
                else
                {
                    // Full navigation for larger screens
                    navigationColumn.Width = new GridLength(280);
                }

                // Adjust font sizes for very small screens
                if (newSize.Width < 1024)
                {
                    // Apply compact styles
                    Resources["CompactMode"] = true;
                }
                else
                {
                    // Apply normal styles
                    Resources["CompactMode"] = false;
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error adjusting layout for size");
            }
        }

        #endregion

        #region Keyboard Shortcuts

        protected override void OnKeyDown(KeyEventArgs e)
        {
            try
            {
                base.OnKeyDown(e);

                // Handle global keyboard shortcuts
                if (e.Key == Key.F11)
                {
                    // Toggle fullscreen
                    MaximizeRestoreWindow_Click(this, null);
                    e.Handled = true;
                }
                else if (e.KeyboardDevice.Modifiers == ModifierKeys.Control)
                {
                    switch (e.Key)
                    {
                        case Key.R:
                            // Refresh current view
                            if (DataContext is MainViewModel viewModel)
                            {
                                viewModel.RefreshCommand?.Execute(null);
                            }
                            e.Handled = true;
                            break;
                            
                        case Key.N:
                            // New project (navigate to projects)
                            if (DataContext is MainViewModel vm)
                            {
                                vm.NavigateToProjectsCommand?.Execute(null);
                            }
                            e.Handled = true;
                            break;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error handling keyboard shortcut");
            }
        }

        #endregion

        #region Window Lifecycle

        protected override void OnSourceInitialized(EventArgs e)
        {
            base.OnSourceInitialized(e);
            
            try
            {
                // Additional window setup after source is initialized
                _logger?.LogDebug("Window source initialized");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during window source initialization");
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            try
            {
                // Cleanup
                base.OnClosed(e);
                _logger?.LogInformation("MainWindow closed");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Error during window close");
            }
        }

        #endregion
    }
}

