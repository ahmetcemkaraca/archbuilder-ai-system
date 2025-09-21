---
applyTo: "src/revit-plugin/**/*.cs,src/revit-plugin/**/*Command*.cs,src/revit-plugin/**/*Handler*.cs,src/revit-plugin/**/*.addin,src/shared/ProjectAnalysis/**/*.cs"
description: Revit Workflow role — ribbon UI, command patterns, transaction management, user experience, project versioning, and existing project analysis for ArchBuilder.AI.
---
As Revit Workflow Developer:
- Design intuitive ribbon UI for AI-powered commands with clear progress indicators
- Implement command patterns with proper transaction management
- Create user feedback systems for AI processing states
- Build progress indicators for long-running AI operations (10-30s realistic)
- Ensure graceful error handling with user-friendly messages
- Implement project versioning framework for AI command tracking
- Design UX/UI mockups for human-AI collaboration workflows
- **EXISTING PROJECT ANALYSIS**: Implement comprehensive .rvt file analysis and enhancement capabilities
- **REVERSE ENGINEERING**: Build systems to analyze existing Revit projects and generate improvement recommendations

## Existing Project Analysis Framework

Implement comprehensive analysis for existing Revit projects:

```csharp
public class ExistingProjectAnalyzer
{
    private readonly Document _document;
    private readonly ILogger<ExistingProjectAnalyzer> _logger;
    
    public ExistingProjectAnalyzer(Document document, ILogger<ExistingProjectAnalyzer> logger)
    {
        _document = document;
        _logger = logger;
    }
    
    public ProjectAnalysisReport AnalyzeProject()
    {
        var report = new ProjectAnalysisReport();
        
        // BIM Element Analysis
        report.ElementAnalysis = AnalyzeBIMElements();
        
        // Performance Analysis  
        report.PerformanceIssues = DetectPerformanceIssues();
        
        // Clash Detection
        report.ClashDetection = DetectElementClashes();
        
        // Building Code Compliance
        report.ComplianceIssues = CheckBuildingCodeCompliance();
        
        // Space and Area Analysis
        report.SpaceAnalysis = AnalyzeSpacesAndAreas();
        
        // MEP System Analysis
        report.MEPAnalysis = AnalyzeMEPSystems();
        
        return report;
    }
    
    private BIMElementAnalysis AnalyzeBIMElements()
    {
        var walls = new FilteredElementCollector(_document)
            .OfClass(typeof(Wall))
            .Cast<Wall>()
            .ToList();
            
        var doors = new FilteredElementCollector(_document)
            .OfClass(typeof(FamilyInstance))
            .OfCategory(BuiltInCategory.OST_Doors)
            .Cast<FamilyInstance>()
            .ToList();
            
        var windows = new FilteredElementCollector(_document)
            .OfClass(typeof(FamilyInstance))
            .OfCategory(BuiltInCategory.OST_Windows)
            .Cast<FamilyInstance>()
            .ToList();
            
        return new BIMElementAnalysis
        {
            WallCount = walls.Count,
            DoorCount = doors.Count,
            WindowCount = windows.Count,
            WallTypes = walls.Select(w => w.WallType.Name).Distinct().ToList(),
            UnusedElements = FindUnusedElements(),
            DuplicateElements = FindDuplicateElements()
        };
    }
    
    private List<PerformanceIssue> DetectPerformanceIssues()
    {
        var issues = new List<PerformanceIssue>();
        
        // Check for overly complex families
        var complexFamilies = new FilteredElementCollector(_document)
            .OfClass(typeof(FamilyInstance))
            .Cast<FamilyInstance>()
            .Where(fi => GetFamilyComplexity(fi) > 1000)
            .ToList();
            
        foreach (var family in complexFamilies)
        {
            issues.Add(new PerformanceIssue
            {
                Type = "Complex Family",
                ElementId = family.Id,
                Description = $"Family {family.Symbol.Family.Name} has high polygon count",
                Severity = IssueSeverity.Medium,
                Recommendation = "Consider simplifying family geometry or using lower detail levels"
            });
        }
        
        // Check for excessive number of elements
        var totalElements = new FilteredElementCollector(_document).GetElementCount();
        if (totalElements > 50000)
        {
            issues.Add(new PerformanceIssue
            {
                Type = "High Element Count",
                Description = $"Project has {totalElements} elements which may cause performance issues",
                Severity = IssueSeverity.High,
                Recommendation = "Consider using design options or worksets to manage model complexity"
            });
        }
        
        return issues;
    }
    
    private List<ClashIssue> DetectElementClashes()
    {
        var clashes = new List<ClashIssue>();
        
        // Check for overlapping walls
        var walls = new FilteredElementCollector(_document)
            .OfClass(typeof(Wall))
            .Cast<Wall>()
            .ToList();
            
        for (int i = 0; i < walls.Count; i++)
        {
            for (int j = i + 1; j < walls.Count; j++)
            {
                if (CheckWallOverlap(walls[i], walls[j]))
                {
                    clashes.Add(new ClashIssue
                    {
                        Element1Id = walls[i].Id,
                        Element2Id = walls[j].Id,
                        ClashType = "Wall Overlap",
                        Location = GetClashLocation(walls[i], walls[j]),
                        Severity = IssueSeverity.High
                    });
                }
            }
        }
        
        return clashes;
    }
    
    private List<ComplianceIssue> CheckBuildingCodeCompliance()
    {
        var issues = new List<ComplianceIssue>();
        
        // Check door width requirements
        var doors = new FilteredElementCollector(_document)
            .OfClass(typeof(FamilyInstance))
            .OfCategory(BuiltInCategory.OST_Doors)
            .Cast<FamilyInstance>()
            .ToList();
            
        foreach (var door in doors)
        {
            var width = door.Symbol.get_Parameter(BuiltInParameter.CASEWORK_WIDTH)?.AsDouble() ?? 0;
            if (width < UnitUtils.ConvertToInternalUnits(80, DisplayUnitType.DUT_CENTIMETERS))
            {
                issues.Add(new ComplianceIssue
                {
                    ElementId = door.Id,
                    Code = "Turkish Building Code - Accessibility",
                    Description = "Door width less than minimum 80cm requirement",
                    Severity = IssueSeverity.High,
                    Recommendation = "Increase door width to meet accessibility standards"
                });
            }
        }
        
        return issues;
    }
}

public class ProjectAnalysisReport
{
    public BIMElementAnalysis ElementAnalysis { get; set; }
    public List<PerformanceIssue> PerformanceIssues { get; set; }
    public List<ClashIssue> ClashDetection { get; set; }
    public List<ComplianceIssue> ComplianceIssues { get; set; }
    public SpaceAnalysis SpaceAnalysis { get; set; }
    public MEPAnalysis MEPAnalysis { get; set; }
    public List<AIRecommendation> AIRecommendations { get; set; }
}

public class AIRecommendation
{
    public string Category { get; set; }
    public string Title { get; set; }
    public string Description { get; set; }
    public string Implementation { get; set; }
    public int Priority { get; set; }
    public string EstimatedTimeToImplement { get; set; }
}
```

Project Versioning Framework:
```csharp
public class ProjectVersionManager
{
    private readonly IArchBuilderRepository _repository;
    private readonly ILogger<ProjectVersionManager> _logger;
    
    public ProjectVersionManager(IRevitAutoPlanRepository repository, ILogger<ProjectVersionManager> logger)
    {
        _repository = repository;
        _logger = logger;
    }
    
    public async Task<ProjectVersion> CreateVersionAsync(Document doc, string correlationId, VersionType type)
    {
        var version = new ProjectVersion
        {
            Id = Guid.NewGuid(),
            ProjectId = GetProjectId(doc),
            VersionNumber = await GetNextVersionNumber(doc),
            CorrelationId = correlationId,
            Type = type,
            CreatedAt = DateTime.UtcNow,
            CreatedBy = Environment.UserName,
            ElementSnapshot = await CaptureElementSnapshot(doc),
            ChangeDescription = GetChangeDescription(type, correlationId)
        };
        
        await _repository.SaveProjectVersionAsync(version);
        
        _logger.LogInformation("Project version created",
            version_id: version.Id,
            version_number: version.VersionNumber,
            type: type.ToString(),
            correlation_id: correlationId);
        
        return version;
    }
    
    public async Task<bool> RollbackToVersionAsync(Document doc, Guid versionId)
    {
        var version = await _repository.GetProjectVersionAsync(versionId);
        if (version == null) return false;
        
        using (var transaction = new Transaction(doc, $"Rollback to Version {version.VersionNumber}"))
        {
            transaction.Start();
            
            try
            {
                // Delete elements created after this version
                await DeleteElementsAfterVersion(doc, version);
                
                // Restore elements from snapshot
                await RestoreElementsFromSnapshot(doc, version.ElementSnapshot);
                
                transaction.Commit();
                
                _logger.LogInformation("Rolled back to project version",
                    version_id: versionId,
                    version_number: version.VersionNumber);
                
                return true;
            }
            catch (Exception ex)
            {
                transaction.RollBack();
                _logger.LogError(ex, "Failed to rollback to version", version_id: versionId);
                return false;
            }
        }
    }
    
    private async Task<ElementSnapshot> CaptureElementSnapshot(Document doc)
    {
        var allElements = new FilteredElementCollector(doc)
            .WhereElementIsNotElementType()
            .ToElementIds()
            .Select(id => new ElementInfo
            {
                Id = id,
                Category = doc.GetElement(id)?.Category?.Name,
                Type = doc.GetElement(id)?.GetType().Name,
                Parameters = CaptureElementParameters(doc.GetElement(id))
            })
            .ToList();
        
        return new ElementSnapshot
        {
            Elements = allElements,
            CapturedAt = DateTime.UtcNow,
            TotalElementCount = allElements.Count
        };
    }
}

public enum VersionType
{
    BeforeAICommand,
    AfterAICommand,
    AfterHumanReview,
    Manual,
    Rollback
}
```

Enhanced UX/UI Design with Mockups:
```csharp
public class AILayoutReviewDialog : Form
{
    // Layout viewer with 3D/2D toggle
    private readonly LayoutViewer3D _layoutViewer3D;
    private readonly LayoutViewer2D _layoutViewer2D;
    private readonly TabControl _viewerTabs;
    
    // Approval workflow panel
    private readonly Panel _approvalPanel;
    private readonly Button _approveButton;
    private readonly Button _rejectButton;
    private readonly Button _requestChangesButton;
    
    // Progress indicators for realistic timing
    private readonly ProgressIndicator _progressIndicator;
    
    public AILayoutReviewDialog(LayoutResult aiOutput, ValidationResult validation)
    {
        InitializeDesign();
        SetupProgressIndicators();
        DisplayAIOutput(aiOutput, validation);
    }
    
    private void InitializeDesign()
    {
        // Main window design - professional architect workflow
        Size = new Size(1200, 800);
        StartPosition = FormStartPosition.CenterScreen;
        Text = "AI Layout Review - RevitAutoPlan";
        
        // Split layout: 70% viewer, 30% controls
        var mainSplit = new SplitContainer
        {
            Dock = DockStyle.Fill,
            SplitterDistance = (int)(Width * 0.7),
            Orientation = Orientation.Vertical
        };
        
        // Left panel: Layout viewer with tabs
        _viewerTabs = new TabControl { Dock = DockStyle.Fill };
        
        var tab3D = new TabPage("3D View");
        _layoutViewer3D = new LayoutViewer3D { Dock = DockStyle.Fill };
        tab3D.Controls.Add(_layoutViewer3D);
        
        var tab2D = new TabPage("Plan View");
        _layoutViewer2D = new LayoutViewer2D { Dock = DockStyle.Fill };
        tab2D.Controls.Add(_layoutViewer2D);
        
        _viewerTabs.TabPages.AddRange(new[] { tab2D, tab3D });
        mainSplit.Panel1.Controls.Add(_viewerTabs);
        
        // Right panel: Review controls
        var rightPanel = new Panel { Dock = DockStyle.Fill };
        SetupReviewControls(rightPanel);
        mainSplit.Panel2.Controls.Add(rightPanel);
        
        Controls.Add(mainSplit);
    }
    
    private void SetupProgressIndicators()
    {
        // Realistic progress indicators for AI operations
        _progressIndicator = new ProgressIndicator();
        
        // Define expected durations for different operations
        _progressIndicator.AddStage("Analyzing Requirements", TimeSpan.FromSeconds(2));
        _progressIndicator.AddStage("Generating Layout", TimeSpan.FromSeconds(15));
        _progressIndicator.AddStage("Validating Geometry", TimeSpan.FromSeconds(3));
        _progressIndicator.AddStage("Checking Regulations", TimeSpan.FromSeconds(8));
        _progressIndicator.AddStage("Preparing Review", TimeSpan.FromSeconds(2));
        
        // Total expected time: ~30 seconds
    }
    
    private void SetupReviewControls(Panel parent)
    {
        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 5
        };
        
        // 1. AI Confidence and metadata
        var metadataPanel = CreateMetadataPanel();
        layout.Controls.Add(metadataPanel, 0, 0);
        
        // 2. Validation issues (if any)
        var validationPanel = CreateValidationPanel();
        layout.Controls.Add(validationPanel, 0, 1);
        
        // 3. Revision tools
        var revisionPanel = CreateRevisionPanel();
        layout.Controls.Add(revisionPanel, 0, 2);
        
        // 4. Approval workflow
        var approvalPanel = CreateApprovalPanel();
        layout.Controls.Add(approvalPanel, 0, 3);
        
        // 5. Comments and feedback
        var feedbackPanel = CreateFeedbackPanel();
        layout.Controls.Add(feedbackPanel, 0, 4);
        
        parent.Controls.Add(layout);
    }
    
    private Panel CreateApprovalPanel()
    {
        var panel = new Panel { Height = 80, Dock = DockStyle.Top };
        
        _approveButton = new Button
        {
            Text = "✓ Approve Layout",
            Size = new Size(120, 35),
            BackColor = Color.Green,
            ForeColor = Color.White,
            Location = new Point(10, 20)
        };
        _approveButton.Click += OnApprove;
        
        _requestChangesButton = new Button
        {
            Text = "⚠ Request Changes",
            Size = new Size(120, 35),
            BackColor = Color.Orange,
            ForeColor = Color.White,
            Location = new Point(140, 20)
        };
        _requestChangesButton.Click += OnRequestChanges;
        
        _rejectButton = new Button
        {
            Text = "✗ Reject",
            Size = new Size(80, 35),
            BackColor = Color.Red,
            ForeColor = Color.White,
            Location = new Point(270, 20)
        };
        _rejectButton.Click += OnReject;
        
        panel.Controls.AddRange(new Control[] { _approveButton, _requestChangesButton, _rejectButton });
        return panel;
    }
    
    private void OnApprove(object sender, EventArgs e)
    {
        // Track human approval for learning
        var feedback = new HumanFeedback
        {
            Decision = ApprovalDecision.Approved,
            ConfidenceInAI = GetUserConfidenceRating(),
            Comments = GetUserComments(),
            TimeSpentReviewing = GetReviewTime()
        };
        
        LogHumanReview(feedback);
        DialogResult = DialogResult.OK;
        Close();
    }
    
    private void OnRequestChanges(object sender, EventArgs e)
    {
        // Show detailed feedback form
        var changeRequestDialog = new ChangeRequestDialog();
        if (changeRequestDialog.ShowDialog() == DialogResult.OK)
        {
            var changeRequest = changeRequestDialog.GetChangeRequest();
            
            // Send back to AI with specific feedback
            RequestAIChanges(changeRequest);
        }
    }
}

// Progress indicator for realistic AI operation timing
public class ProgressIndicator : UserControl
{
    private readonly List<ProgressStage> _stages;
    private readonly ProgressBar _progressBar;
    private readonly Label _currentStageLabel;
    private readonly Label _timeRemainingLabel;
    private readonly Timer _updateTimer;
    
    public ProgressIndicator()
    {
        _stages = new List<ProgressStage>();
        InitializeControls();
        _updateTimer = new Timer { Interval = 500 };
        _updateTimer.Tick += UpdateProgress;
    }
    
    public void AddStage(string name, TimeSpan expectedDuration)
    {
        _stages.Add(new ProgressStage
        {
            Name = name,
            ExpectedDuration = expectedDuration,
            Status = StageStatus.Pending
        });
    }
    
    public async Task ExecuteStagesAsync(CancellationToken cancellationToken = default)
    {
        _updateTimer.Start();
        var totalStages = _stages.Count;
        
        for (int i = 0; i < totalStages; i++)
        {
            var stage = _stages[i];
            stage.Status = StageStatus.InProgress;
            stage.StartTime = DateTime.Now;
            
            _currentStageLabel.Text = $"Step {i + 1}/{totalStages}: {stage.Name}";
            _progressBar.Value = (int)((double)i / totalStages * 100);
            
            // Simulate work with realistic timing
            await Task.Delay(stage.ExpectedDuration, cancellationToken);
            
            stage.Status = StageStatus.Completed;
            stage.EndTime = DateTime.Now;
        }
        
        _progressBar.Value = 100;
        _currentStageLabel.Text = "Complete";
        _timeRemainingLabel.Text = "";
        _updateTimer.Stop();
    }
    
    private void UpdateProgress(object sender, EventArgs e)
    {
        var currentStage = _stages.FirstOrDefault(s => s.Status == StageStatus.InProgress);
        if (currentStage != null)
        {
            var elapsed = DateTime.Now - currentStage.StartTime;
            var remaining = currentStage.ExpectedDuration - elapsed;
            
            if (remaining > TimeSpan.Zero)
            {
                _timeRemainingLabel.Text = $"~{remaining.TotalSeconds:F0}s remaining";
            }
            else
            {
                _timeRemainingLabel.Text = "Finishing up...";
            }
        }
    }
}

public class ProgressStage
{
    public string Name { get; set; }
    public TimeSpan ExpectedDuration { get; set; }
    public StageStatus Status { get; set; }
    public DateTime? StartTime { get; set; }
    public DateTime? EndTime { get; set; }
}

public enum StageStatus
{
    Pending,
    InProgress,
    Completed,
    Failed
}
```

Revit Command Structure:
```csharp
[Transaction(TransactionMode.Manual)]
public class AILayoutCommand : IExternalCommand
{
    private static readonly ILogger Logger = Log.ForContext<AILayoutCommand>();
    
    public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
    {
        var correlationId = Guid.NewGuid().ToString();
        Logger.Information("AI Layout command started", correlationId);
        
        try
        {
            var uiApp = commandData.Application;
            var doc = uiApp.ActiveUIDocument.Document;
            
            // Show progress dialog for AI processing
            using (var progressDialog = new ProgressDialog("AI Layout Generation"))
            {
                progressDialog.Show();
                progressDialog.SetProgressText("Analyzing requirements...");
                
                // Get user requirements through dialog
                var requirementsDialog = new RoomRequirementsDialog();
                if (requirementsDialog.ShowDialog() != DialogResult.OK)
                {
                    return Result.Cancelled;
                }
                
                var requirements = requirementsDialog.GetRequirements();
                Logger.Information("User requirements collected", correlationId, requirements);
                
                // Call AI service with progress updates
                progressDialog.SetProgressText("Generating layout with AI...");
                var aiService = ServiceLocator.GetService<IAILayoutService>();
                var layoutResult = await aiService.GenerateLayoutAsync(requirements, correlationId);
                
                // Validate AI output
                progressDialog.SetProgressText("Validating AI output...");
                var validator = ServiceLocator.GetService<ILayoutValidator>();
                var validation = await validator.ValidateLayoutAsync(layoutResult);
                
                if (validation.Status == ValidationStatus.REJECTED)
                {
                    Logger.Warning("AI layout rejected by validation", correlationId, validation.Errors);
                    MessageBox.Show($"AI generated layout has issues:\n{string.Join("\n", validation.Errors)}", 
                                  "Validation Failed", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return Result.Failed;
                }
                
                // Show human review dialog if required
                if (validation.RequiresHumanReview)
                {
                    progressDialog.SetProgressText("Awaiting human review...");
                    var reviewDialog = new AIReviewDialog(layoutResult, validation);
                    if (reviewDialog.ShowDialog() != DialogResult.OK)
                    {
                        Logger.Information("User cancelled AI layout review", correlationId);
                        return Result.Cancelled;
                    }
                    
                    // Process any human corrections
                    layoutResult = reviewDialog.GetFinalLayout();
                }
                
                // Execute in Revit transaction
                progressDialog.SetProgressText("Creating elements in Revit...");
                using (var transaction = new Transaction(doc, "AI Layout Generation"))
                {
                    transaction.Start();
                    
                    try
                    {
                        var executor = new LayoutExecutor(doc);
                        executor.CreateLayout(layoutResult);
                        
                        transaction.Commit();
                        Logger.Information("AI layout successfully created in Revit", correlationId);
                    }
                    catch (Exception ex)
                    {
                        transaction.RollBack();
                        Logger.Error(ex, "Failed to create layout in Revit", correlationId);
                        throw;
                    }
                }
            }
            
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "AI Layout command failed", correlationId);
            message = $"AI Layout generation failed: {ex.Message}";
            return Result.Failed;
        }
    }
}
```

Ribbon UI Design Patterns:
```csharp
public class AutoPlanRibbonPanel
{
    public static void CreateRibbonPanel(UIControlledApplication application)
    {
        var ribbonPanel = application.CreateRibbonPanel("AutoPlan AI");
        
        // Split button for AI commands
        var splitButtonData = new SplitButtonData("aiCommands", "AI Commands");
        var splitButton = ribbonPanel.AddItem(splitButtonData) as SplitButton;
        
        // Main AI layout command
        var layoutButtonData = new PushButtonData(
            "aiLayout", 
            "Generate\nLayout", 
            Assembly.GetExecutingAssembly().Location, 
            typeof(AILayoutCommand).FullName)
        {
            LargeImage = GetEmbeddedImage("Icons.ai_layout_32.png"),
            ToolTip = "Generate room layout using AI",
            LongDescription = "Uses AI to automatically generate optimized room layouts based on your requirements. All AI outputs are validated and require human review."
        };
        splitButton.AddPushButton(layoutButtonData);
        
        // Quick AI commands
        var quickCommandsData = new PushButtonData(
            "aiQuick",
            "Quick\nCommands",
            Assembly.GetExecutingAssembly().Location,
            typeof(AIQuickCommandsDialog).FullName)
        {
            LargeImage = GetEmbeddedImage("Icons.ai_quick_32.png"),
            ToolTip = "Quick AI commands for repetitive tasks"
        };
        splitButton.AddPushButton(quickCommandsData);
        
        // Separator
        ribbonPanel.AddSeparator();
        
        // AI Review queue
        var reviewButtonData = new PushButtonData(
            "aiReview",
            "Review\nQueue",
            Assembly.GetExecutingAssembly().Location,
            typeof(AIReviewQueueCommand).FullName)
        {
            Image = GetEmbeddedImage("Icons.review_16.png"),
            ToolTip = "View pending AI outputs requiring review"
        };
        ribbonPanel.AddItem(reviewButtonData);
        
        // AI Settings
        var settingsButtonData = new PushButtonData(
            "aiSettings",
            "Settings",
            Assembly.GetExecutingAssembly().Location,
            typeof(AISettingsCommand).FullName)
        {
            Image = GetEmbeddedImage("Icons.settings_16.png"),
            ToolTip = "Configure AI integration settings"
        };
        ribbonPanel.AddItem(settingsButtonData);
    }
}
```

Progress Dialog for Long-Running AI Operations:
```csharp
public class AIProgressDialog : Form
{
    private ProgressBar progressBar;
    private Label statusLabel;
    private Button cancelButton;
    private CancellationTokenSource cancellationTokenSource;
    
    public AIProgressDialog(string title)
    {
        InitializeDialog(title);
        cancellationTokenSource = new CancellationTokenSource();
    }
    
    public async Task<T> ExecuteWithProgressAsync<T>(
        Func<IProgress<string>, CancellationToken, Task<T>> operation)
    {
        var progress = new Progress<string>(UpdateStatus);
        
        try
        {
            Show();
            var result = await operation(progress, cancellationTokenSource.Token);
            Close();
            return result;
        }
        catch (OperationCanceledException)
        {
            Close();
            throw;
        }
        catch (Exception ex)
        {
            Close();
            MessageBox.Show($"Operation failed: {ex.Message}", "Error", 
                          MessageBoxButtons.OK, MessageBoxIcon.Error);
            throw;
        }
    }
    
    private void UpdateStatus(string status)
    {
        if (InvokeRequired)
        {
            Invoke(new Action<string>(UpdateStatus), status);
            return;
        }
        
        statusLabel.Text = status;
        progressBar.PerformStep();
    }
    
    private void CancelButton_Click(object sender, EventArgs e)
    {
        cancellationTokenSource.Cancel();
        cancelButton.Enabled = false;
        statusLabel.Text = "Cancelling...";
    }
}
```

Human Review Dialog System:
```csharp
public class AIReviewDialog : Form
{
    private readonly LayoutResult aiOutput;
    private readonly ValidationResult validation;
    private readonly List<Correction> userCorrections;
    
    public AIReviewDialog(LayoutResult aiOutput, ValidationResult validation)
    {
        this.aiOutput = aiOutput;
        this.validation = validation;
        this.userCorrections = new List<Correction>();
        
        InitializeReviewInterface();
        PopulateAIOutput();
        HighlightValidationIssues();
    }
    
    private void InitializeReviewInterface()
    {
        // Main layout display
        var layoutViewer = new LayoutViewer();
        layoutViewer.DisplayLayout(aiOutput);
        
        // Validation issues panel
        var issuesPanel = new ValidationIssuesPanel();
        issuesPanel.DisplayIssues(validation.Errors);
        
        // Correction tools
        var correctionPanel = new CorrectionToolsPanel();
        correctionPanel.CorrectionMade += OnCorrectionMade;
        
        // Approval buttons
        var buttonPanel = new Panel();
        var approveButton = new Button { Text = "Approve", DialogResult = DialogResult.OK };
        var rejectButton = new Button { Text = "Reject", DialogResult = DialogResult.Cancel };
        var requestChangesButton = new Button { Text = "Request AI Changes" };
        
        approveButton.Click += (s, e) => ApproveWithCorrections();
        rejectButton.Click += (s, e) => RejectWithFeedback();
        requestChangesButton.Click += (s, e) => RequestAIChanges();
    }
    
    private void OnCorrectionMade(object sender, CorrectionEventArgs e)
    {
        userCorrections.Add(e.Correction);
        
        // Update layout viewer to show correction
        var layoutViewer = Controls.OfType<LayoutViewer>().First();
        layoutViewer.ApplyCorrection(e.Correction);
        
        // Log correction for learning
        Logger.Information("User correction made",
            correction_type = e.Correction.Type,
            original_value = e.Correction.OriginalValue,
            corrected_value = e.Correction.CorrectedValue);
    }
    
    public LayoutResult GetFinalLayout()
    {
        var finalLayout = aiOutput.Clone();
        
        // Apply all user corrections
        foreach (var correction in userCorrections)
        {
            finalLayout.ApplyCorrection(correction);
        }
        
        // Mark as human-reviewed
        finalLayout.HumanReviewed = true;
        finalLayout.ReviewedBy = Environment.UserName;
        finalLayout.ReviewedAt = DateTime.UtcNow;
        
        return finalLayout;
    }
}
```

Error Handling and User Communication:
```csharp
public static class UserErrorHandler
{
    public static void HandleAIError(Exception ex, string correlationId)
    {
        Logger.Error(ex, "AI operation failed", correlationId);
        
        string userMessage = ex switch
        {
            AIServiceUnavailableException => 
                "AI service is temporarily unavailable. Please try again later or use manual tools.",
            AIValidationException validationEx => 
                $"AI generated layout has validation issues:\n{string.Join("\n", validationEx.ValidationErrors)}",
            AITimeoutException => 
                "AI processing is taking longer than expected. Would you like to continue waiting or try a simpler request?",
            HttpRequestException => 
                "Network connection issue. Please check your internet connection and try again.",
            _ => 
                $"An unexpected error occurred during AI processing. Error ID: {correlationId}"
        };
        
        // Show user-friendly error dialog
        var errorDialog = new AIErrorDialog(userMessage, ex, correlationId);
        errorDialog.ShowDialog();
    }
    
    public static void ShowAIProcessingTips()
    {
        var tipsDialog = new AITipsDialog();
        tipsDialog.AddTip("Be specific with room requirements (sizes, adjacencies)");
        tipsDialog.AddTip("AI works best with rectangular or simple L-shaped buildings");
        tipsDialog.AddTip("Complex geometric constraints may require manual adjustment");
        tipsDialog.AddTip("All AI outputs require your review and approval");
        tipsDialog.ShowDialog();
    }
}
```

Command Registration and Lifecycle:
```csharp
public class AutoPlanApplication : IExternalApplication
{
    public Result OnStartup(UIControlledApplication application)
    {
        try
        {
            // Initialize logging
            ConfigureLogging();
            
            // Initialize dependency injection
            ServiceLocator.Initialize();
            
            // Create ribbon UI
            AutoPlanRibbonPanel.CreateRibbonPanel(application);
            
            // Initialize AI services
            var aiService = ServiceLocator.GetService<IAILayoutService>();
            aiService.InitializeAsync().Wait();
            
            // Register for document events
            application.ControlledApplication.DocumentOpened += OnDocumentOpened;
            application.ControlledApplication.DocumentClosed += OnDocumentClosed;
            
            Logger.Information("AutoPlan add-in successfully initialized");
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            Logger.Error(ex, "Failed to initialize AutoPlan add-in");
            return Result.Failed;
        }
    }
    
    public Result OnShutdown(UIControlledApplication application)
    {
        try
        {
            // Cleanup AI services
            var aiService = ServiceLocator.GetService<IAILayoutService>();
            aiService?.Dispose();
            
            // Cleanup logging
            Log.CloseAndFlush();
            
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            // Can't log here as logger is disposed
            return Result.Failed;
        }
    }
}
```

Always wrap AI operations in transactions, provide progress feedback, require human review, and handle errors gracefully.