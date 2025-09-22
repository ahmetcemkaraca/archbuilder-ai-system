using System;
using System.Collections.Generic;
using System.Drawing;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.UI.Dialogs
{
    /// <summary>
    /// AI Progress dialog showing realistic progress indicators for AI operations.
    /// Implements Apple-vari design with professional feedback for architects.
    /// </summary>
    public partial class AIProgressDialog : Form
    {
        private static readonly ILogger Logger = LoggerFactory.Create(builder => builder.AddConsole()).CreateLogger<AIProgressDialog>();
        
        // UI Controls
        private ProgressBar _overallProgressBar;
        private Label _currentStageLabel;
        private Label _timeRemainingLabel;
        private Label _titleLabel;
        private Panel _stagesPanel;
        private Button _cancelButton;
        private PictureBox _aiIconPictureBox;
        
        // Progress Management
        private readonly List<ProgressStage> _stages;
        private readonly Timer _updateTimer;
        private readonly CancellationTokenSource _cancellationTokenSource;
        private int _currentStageIndex;
        private DateTime _operationStartTime;
        
        // Configuration
        private readonly string _operationTitle;
        private readonly string _correlationId;

        public AIProgressDialog(string operationTitle = "AI Processing")
        {
            _operationTitle = operationTitle;
            _correlationId = Guid.NewGuid().ToString();
            _stages = new List<ProgressStage>();
            _cancellationTokenSource = new CancellationTokenSource();
            _currentStageIndex = -1;
            
            Logger.LogDebug("Initializing AI Progress dialog for operation: {Operation}", operationTitle, _correlationId);
            
            InitializeComponent();
            SetupAppleVariDesign();
            SetupRealisticProgressStages();
            SetupUpdateTimer();
        }

        /// <summary>
        /// Gets the cancellation token for the operation.
        /// </summary>
        public CancellationToken CancellationToken => _cancellationTokenSource.Token;

        /// <summary>
        /// Executes an operation with progress tracking.
        /// </summary>
        /// <typeparam name="T">The return type.</typeparam>
        /// <param name="operation">The operation to execute.</param>
        /// <returns>The operation result.</returns>
        public async Task<T> ExecuteWithProgressAsync<T>(Func<IProgress<string>, CancellationToken, Task<T>> operation)
        {
            try
            {
                _operationStartTime = DateTime.Now;
                var progress = new Progress<string>(UpdateCustomStatus);
                
                Logger.LogInformation("Starting AI operation with progress tracking", _correlationId);
                
                // Start progress stages
                var progressTask = RunProgressStagesAsync();
                
                // Show dialog
                Show();
                BringToFront();
                
                // Execute the operation
                var result = await operation(progress, _cancellationTokenSource.Token);
                
                // Complete progress
                await CompleteProgressAsync();
                
                Logger.LogInformation("AI operation completed successfully", _correlationId);
                
                // Small delay to show completion
                await Task.Delay(1000, CancellationToken.None);
                
                Hide();
                return result;
            }
            catch (OperationCanceledException)
            {
                Logger.LogInformation("AI operation cancelled by user", _correlationId);
                Hide();
                throw;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "AI operation failed", _correlationId);
                Hide();
                ShowErrorState(ex);
                throw;
            }
        }

        private void InitializeComponent()
        {
            try
            {
                // Main form setup
                Size = new Size(500, 350);
                Text = $"{_operationTitle} - ArchBuilder.AI";
                StartPosition = FormStartPosition.CenterParent;
                FormBorderStyle = FormBorderStyle.FixedDialog;
                MaximizeBox = false;
                MinimizeBox = false;
                ControlBox = false;
                ShowInTaskbar = false;

                // Title label
                _titleLabel = new Label
                {
                    Text = _operationTitle,
                    Font = new Font("Segoe UI", 14F, FontStyle.Bold),
                    Location = new Point(60, 20),
                    Size = new Size(400, 30),
                    TextAlign = ContentAlignment.MiddleLeft
                };

                // AI icon
                _aiIconPictureBox = new PictureBox
                {
                    Size = new Size(40, 40),
                    Location = new Point(15, 15),
                    SizeMode = PictureBoxSizeMode.Zoom,
                    Image = CreateAIIcon()
                };

                // Current stage label
                _currentStageLabel = new Label
                {
                    Text = "Preparing AI processing...",
                    Font = new Font("Segoe UI", 10F, FontStyle.Regular),
                    Location = new Point(20, 70),
                    Size = new Size(450, 25),
                    TextAlign = ContentAlignment.MiddleLeft
                };

                // Overall progress bar
                _overallProgressBar = new ProgressBar
                {
                    Location = new Point(20, 100),
                    Size = new Size(450, 25),
                    Style = ProgressBarStyle.Continuous,
                    Minimum = 0,
                    Maximum = 100,
                    Value = 0
                };

                // Time remaining label
                _timeRemainingLabel = new Label
                {
                    Text = "Estimating time...",
                    Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                    ForeColor = Color.FromArgb(102, 102, 102),
                    Location = new Point(20, 130),
                    Size = new Size(300, 20),
                    TextAlign = ContentAlignment.MiddleLeft
                };

                // Stages panel
                _stagesPanel = new Panel
                {
                    Location = new Point(20, 160),
                    Size = new Size(450, 130),
                    AutoScroll = true,
                    BorderStyle = BorderStyle.FixedSingle,
                    BackColor = Color.FromArgb(250, 250, 250)
                };

                // Cancel button
                _cancelButton = new Button
                {
                    Text = "Cancel",
                    Size = new Size(80, 30),
                    Location = new Point(390, 300),
                    BackColor = Color.FromArgb(200, 200, 200),
                    ForeColor = Color.FromArgb(51, 51, 51),
                    FlatStyle = FlatStyle.Flat,
                    Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                    Cursor = Cursors.Hand
                };
                _cancelButton.FlatAppearance.BorderSize = 0;
                _cancelButton.Click += OnCancelClicked;

                // Add controls to form
                Controls.AddRange(new Control[] 
                {
                    _titleLabel, _aiIconPictureBox, _currentStageLabel, 
                    _overallProgressBar, _timeRemainingLabel, _stagesPanel, _cancelButton
                });

                Logger.LogDebug("AI Progress dialog UI components initialized", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to initialize AI Progress dialog UI", _correlationId);
                throw;
            }
        }

        private void SetupAppleVariDesign()
        {
            try
            {
                // Apple-vari color scheme
                BackColor = Color.FromArgb(248, 248, 248);
                ForeColor = Color.FromArgb(51, 51, 51);
                
                // Progress bar styling
                _overallProgressBar.ForeColor = Color.FromArgb(0, 122, 255);
                
                Logger.LogDebug("Apple-vari design applied to progress dialog", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to apply design styling to progress dialog", _correlationId);
            }
        }

        private void SetupRealisticProgressStages()
        {
            try
            {
                // Based on actual AI processing times for architectural layouts
                _stages.AddRange(new[]
                {
                    new ProgressStage("🔍 Analyzing your requirements", TimeSpan.FromSeconds(3), "Parsing project specifications and constraints"),
                    new ProgressStage("🧠 Generating layout with AI", TimeSpan.FromSeconds(15), "Creating optimized room arrangements and spatial relationships"),
                    new ProgressStage("📋 Checking building codes", TimeSpan.FromSeconds(8), "Validating compliance with regional building regulations"),
                    new ProgressStage("📐 Validating geometry", TimeSpan.FromSeconds(5), "Ensuring structural feasibility and dimensional accuracy"),
                    new ProgressStage("🎯 Optimizing placement", TimeSpan.FromSeconds(4), "Fine-tuning door, window, and fixture positions"),
                    new ProgressStage("👀 Preparing for your review", TimeSpan.FromSeconds(2), "Finalizing output and generating review materials")
                });

                // Total estimated time: ~37 seconds (realistic for AI operations)
                var totalTime = TimeSpan.Zero;
                foreach (var stage in _stages)
                {
                    totalTime = totalTime.Add(stage.EstimatedDuration);
                }

                Logger.LogDebug("Progress stages configured - Total estimated time: {TotalTime}s", 
                    totalTime.TotalSeconds, _correlationId);

                // Create visual stages in panel
                CreateStageVisuals();
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to setup progress stages", _correlationId);
                throw;
            }
        }

        private void CreateStageVisuals()
        {
            try
            {
                _stagesPanel.Controls.Clear();

                for (int i = 0; i < _stages.Count; i++)
                {
                    var stage = _stages[i];
                    var stagePanel = new Panel
                    {
                        Size = new Size(420, 18),
                        Location = new Point(5, i * 20),
                        Tag = i
                    };

                    var stageLabel = new Label
                    {
                        Text = stage.Name,
                        Font = new Font("Segoe UI", 8F, FontStyle.Regular),
                        ForeColor = Color.FromArgb(102, 102, 102),
                        Size = new Size(350, 16),
                        Location = new Point(0, 1),
                        TextAlign = ContentAlignment.MiddleLeft
                    };

                    var statusIcon = new Label
                    {
                        Text = "⭕", // Pending
                        Font = new Font("Segoe UI", 8F),
                        Size = new Size(16, 16),
                        Location = new Point(360, 1),
                        TextAlign = ContentAlignment.MiddleCenter
                    };

                    stagePanel.Controls.Add(stageLabel);
                    stagePanel.Controls.Add(statusIcon);
                    _stagesPanel.Controls.Add(stagePanel);

                    // Store references for easy access
                    stage.VisualPanel = stagePanel;
                    stage.StatusIcon = statusIcon;
                }

                Logger.LogDebug("Stage visuals created for {StageCount} stages", _stages.Count, _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to create stage visuals", _correlationId);
            }
        }

        private void SetupUpdateTimer()
        {
            try
            {
                _updateTimer = new Timer
                {
                    Interval = 500, // Update every 500ms
                    Enabled = false
                };
                _updateTimer.Tick += UpdateProgressDisplay;

                Logger.LogDebug("Update timer configured", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to setup update timer", _correlationId);
                throw;
            }
        }

        private async Task RunProgressStagesAsync()
        {
            try
            {
                _updateTimer.Start();

                for (int i = 0; i < _stages.Count; i++)
                {
                    if (_cancellationTokenSource.Token.IsCancellationRequested)
                        break;

                    _currentStageIndex = i;
                    var stage = _stages[i];
                    
                    // Update stage status
                    stage.Status = StageStatus.InProgress;
                    stage.StartTime = DateTime.Now;
                    
                    // Update UI
                    UpdateStageVisual(i, stage);
                    _currentStageLabel.Text = $"{stage.Name}...";
                    
                    Logger.LogDebug("Started stage {StageIndex}: {StageName}", i, stage.Name, _correlationId);

                    // Simulate realistic processing time with some variability
                    var actualDuration = stage.EstimatedDuration.Add(TimeSpan.FromSeconds(Random.Shared.Next(-1, 2)));
                    await Task.Delay(actualDuration, _cancellationTokenSource.Token);

                    // Complete stage
                    stage.Status = StageStatus.Completed;
                    stage.ActualDuration = DateTime.Now - stage.StartTime.Value;
                    
                    UpdateStageVisual(i, stage);
                    
                    Logger.LogDebug("Completed stage {StageIndex}: {StageName} in {Duration}s", 
                        i, stage.Name, stage.ActualDuration.Value.TotalSeconds, _correlationId);
                }

                _updateTimer.Stop();
            }
            catch (OperationCanceledException)
            {
                Logger.LogDebug("Progress stages cancelled", _correlationId);
                _updateTimer.Stop();
                throw;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error running progress stages", _correlationId);
                _updateTimer.Stop();
                throw;
            }
        }

        private async Task CompleteProgressAsync()
        {
            try
            {
                // Ensure all stages are marked as completed
                for (int i = 0; i < _stages.Count; i++)
                {
                    if (_stages[i].Status != StageStatus.Completed)
                    {
                        _stages[i].Status = StageStatus.Completed;
                        UpdateStageVisual(i, _stages[i]);
                    }
                }

                // Update UI to show completion
                _currentStageLabel.Text = "✅ AI layout generated successfully!";
                _timeRemainingLabel.Text = "Ready for your review";
                _overallProgressBar.Value = 100;
                _cancelButton.Text = "Close";

                Logger.LogDebug("Progress completed successfully", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error completing progress", _correlationId);
            }
        }

        private void UpdateProgressDisplay(object sender, EventArgs e)
        {
            try
            {
                if (_currentStageIndex < 0 || _currentStageIndex >= _stages.Count)
                    return;

                // Update overall progress
                var completedStages = _currentStageIndex;
                var totalStages = _stages.Count;
                var progressPercentage = (int)((double)completedStages / totalStages * 100);
                _overallProgressBar.Value = Math.Min(progressPercentage, 100);

                // Update time remaining
                var currentStage = _stages[_currentStageIndex];
                if (currentStage.Status == StageStatus.InProgress && currentStage.StartTime.HasValue)
                {
                    var elapsed = DateTime.Now - currentStage.StartTime.Value;
                    var remaining = currentStage.EstimatedDuration - elapsed;

                    if (remaining > TimeSpan.Zero)
                    {
                        // Add remaining time for future stages
                        for (int i = _currentStageIndex + 1; i < _stages.Count; i++)
                        {
                            remaining = remaining.Add(_stages[i].EstimatedDuration);
                        }

                        _timeRemainingLabel.Text = $"~{remaining.TotalSeconds:F0} seconds remaining";
                    }
                    else
                    {
                        _timeRemainingLabel.Text = "Finishing current step...";
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error updating progress display", _correlationId);
            }
        }

        private void UpdateStageVisual(int stageIndex, ProgressStage stage)
        {
            try
            {
                if (stage.StatusIcon == null) return;

                // Update status icon based on stage status
                switch (stage.Status)
                {
                    case StageStatus.Pending:
                        stage.StatusIcon.Text = "⭕";
                        stage.StatusIcon.ForeColor = Color.FromArgb(200, 200, 200);
                        break;
                    case StageStatus.InProgress:
                        stage.StatusIcon.Text = "🔄";
                        stage.StatusIcon.ForeColor = Color.FromArgb(0, 122, 255);
                        break;
                    case StageStatus.Completed:
                        stage.StatusIcon.Text = "✅";
                        stage.StatusIcon.ForeColor = Color.FromArgb(76, 175, 80);
                        break;
                    case StageStatus.Failed:
                        stage.StatusIcon.Text = "❌";
                        stage.StatusIcon.ForeColor = Color.FromArgb(244, 67, 54);
                        break;
                }

                // Update visual panel background for current stage
                if (stage.VisualPanel != null)
                {
                    stage.VisualPanel.BackColor = stage.Status == StageStatus.InProgress 
                        ? Color.FromArgb(240, 248, 255) 
                        : Color.Transparent;
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error updating stage visual for stage {StageIndex}", stageIndex, _correlationId);
            }
        }

        private void UpdateCustomStatus(string customMessage)
        {
            try
            {
                if (InvokeRequired)
                {
                    Invoke(new Action<string>(UpdateCustomStatus), customMessage);
                    return;
                }

                if (!string.IsNullOrEmpty(customMessage))
                {
                    _currentStageLabel.Text = customMessage;
                    Logger.LogDebug("Custom status updated: {Message}", customMessage, _correlationId);
                }
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Error updating custom status", _correlationId);
            }
        }

        private void ShowErrorState(Exception error)
        {
            try
            {
                _currentStageLabel.Text = "❌ AI processing encountered an error";
                _timeRemainingLabel.Text = "Operation failed";
                _overallProgressBar.Value = 0;
                _cancelButton.Text = "Close";

                // Mark current stage as failed
                if (_currentStageIndex >= 0 && _currentStageIndex < _stages.Count)
                {
                    _stages[_currentStageIndex].Status = StageStatus.Failed;
                    UpdateStageVisual(_currentStageIndex, _stages[_currentStageIndex]);
                }

                Logger.LogError("Error state displayed for exception: {Error}", error.Message, _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error showing error state", _correlationId);
            }
        }

        private Bitmap CreateAIIcon()
        {
            try
            {
                // Create a simple AI icon
                var bitmap = new Bitmap(40, 40);
                using (var g = Graphics.FromImage(bitmap))
                {
                    g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                    g.Clear(Color.Transparent);
                    
                    // Draw AI brain icon
                    using (var brush = new SolidBrush(Color.FromArgb(0, 122, 255)))
                    {
                        g.FillEllipse(brush, 5, 5, 30, 30);
                    }
                    
                    // Draw neural network pattern
                    using (var pen = new Pen(Color.White, 2))
                    {
                        g.DrawLines(pen, new Point[] { new Point(15, 15), new Point(20, 20), new Point(25, 15) });
                        g.DrawLines(pen, new Point[] { new Point(15, 25), new Point(20, 20), new Point(25, 25) });
                    }
                }
                return bitmap;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to create AI icon, using default", _correlationId);
                return new Bitmap(40, 40); // Return empty bitmap
            }
        }

        private void OnCancelClicked(object sender, EventArgs e)
        {
            try
            {
                if (_cancelButton.Text == "Close")
                {
                    Close();
                    return;
                }

                var result = MessageBox.Show(
                    "Are you sure you want to cancel the AI processing?",
                    "Cancel AI Operation",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);

                if (result == DialogResult.Yes)
                {
                    _cancellationTokenSource.Cancel();
                    _currentStageLabel.Text = "Cancelling AI operation...";
                    _cancelButton.Enabled = false;
                    
                    Logger.LogInformation("AI operation cancelled by user", _correlationId);
                }
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error handling cancel click", _correlationId);
            }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            try
            {
                _updateTimer?.Stop();
                _updateTimer?.Dispose();
                base.OnFormClosing(e);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error closing progress dialog", _correlationId);
            }
        }
    }

    /// <summary>
    /// Represents a stage in the AI processing pipeline.
    /// </summary>
    public class ProgressStage
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public TimeSpan EstimatedDuration { get; set; }
        public StageStatus Status { get; set; } = StageStatus.Pending;
        public DateTime? StartTime { get; set; }
        public TimeSpan? ActualDuration { get; set; }
        
        // UI References
        public Panel VisualPanel { get; set; }
        public Label StatusIcon { get; set; }

        public ProgressStage(string name, TimeSpan estimatedDuration, string description = "")
        {
            Name = name;
            EstimatedDuration = estimatedDuration;
            Description = description;
        }
    }

    /// <summary>
    /// Status of a progress stage.
    /// </summary>
    public enum StageStatus
    {
        Pending,
        InProgress,
        Completed,
        Failed
    }
}