---
applyTo: "src/desktop-app/**/*.cs,src/revit-plugin/**/*.cs,src/revit-plugin/**/*Dialog*.cs,src/revit-plugin/**/*Panel*.cs,**/*.xaml,**/*.css"
description: UX/UI Design Standards — ArchBuilder.AI Apple-vari desktop interface design, AI-human collaboration, progress indicators, and review workflows.
---
As UX/UI Designer:
- Design intuitive interfaces for AI-human collaboration workflows
- Create clear progress indicators for realistic AI operation timings (10-30s)
- Build user-friendly review interfaces for AI outputs
- Implement responsive design patterns for different screen sizes
- Ensure accessibility compliance and professional architect workflow integration
- Design error states and recovery pathways that maintain user confidence

## AI-Human Collaboration UX Patterns

### Main AI Layout Generation Interface
```csharp
public class AILayoutGenerationDialog : Form
{
    // Professional architect-focused design
    public AILayoutGenerationDialog()
    {
        Size = new Size(800, 600);
        Text = "AI Layout Generation - RevitAutoPlan";
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(600, 400);
        
        InitializeTabLayout();
        SetupProgressUI();
        ApplyProfessionalStyling();
    }
    
    private void InitializeTabLayout()
    {
        var tabControl = new TabControl { Dock = DockStyle.Fill };
        
        // Tab 1: Basic Requirements
        var basicTab = new TabPage("Project Requirements");
        var basicPanel = CreateBasicRequirementsPanel();
        basicTab.Controls.Add(basicPanel);
        
        // Tab 2: Advanced Settings
        var advancedTab = new TabPage("Advanced Settings");
        var advancedPanel = CreateAdvancedSettingsPanel();
        advancedTab.Controls.Add(advancedPanel);
        
        // Tab 3: Style Preferences
        var styleTab = new TabPage("Style & Constraints");
        var stylePanel = CreateStylePreferencesPanel();
        styleTab.Controls.Add(stylePanel);
        
        tabControl.TabPages.AddRange(new[] { basicTab, advancedTab, styleTab });
        Controls.Add(tabControl);
        
        // Bottom action panel
        var actionPanel = CreateActionPanel();
        Controls.Add(actionPanel);
    }
    
    private Panel CreateBasicRequirementsPanel()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 6,
            Padding = new Padding(20)
        };
        
        // Building type selection with icons
        panel.Controls.Add(new Label { Text = "Building Type:", TextAlign = ContentAlignment.MiddleRight }, 0, 0);
        var buildingTypeCombo = new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDownList,
            Items = { "Residential", "Office", "Retail", "Mixed Use" },
            SelectedIndex = 0
        };
        panel.Controls.Add(buildingTypeCombo, 1, 0);
        
        // Total area with validation
        panel.Controls.Add(new Label { Text = "Total Area (m²):", TextAlign = ContentAlignment.MiddleRight }, 0, 1);
        var areaTextBox = new TextBox { PlaceholderText = "e.g., 150" };
        areaTextBox.TextChanged += ValidateNumericInput;
        panel.Controls.Add(areaTextBox, 1, 1);
        
        // Room requirements with dynamic list
        panel.Controls.Add(new Label { Text = "Room Requirements:", TextAlign = ContentAlignment.MiddleRight }, 0, 2);
        var roomsPanel = CreateRoomRequirementsPanel();
        panel.Controls.Add(roomsPanel, 1, 2);
        
        // User prompt with examples
        panel.Controls.Add(new Label { Text = "Additional Requirements:", TextAlign = ContentAlignment.MiddleRight }, 0, 3);
        var promptTextBox = new RichTextBox
        {
            Height = 100,
            PlaceholderText = "Describe any specific requirements, e.g., 'Large kitchen open to living room', 'Accessibility required', 'Natural light in all rooms'"
        };
        panel.Controls.Add(promptTextBox, 1, 3);
        
        // AI Tips and Examples
        var tipsLabel = new LinkLabel
        {
            Text = "💡 View AI prompting tips and examples",
            LinkColor = Color.Blue
        };
        tipsLabel.LinkClicked += ShowAITips;
        panel.Controls.Add(tipsLabel, 1, 4);
        
        return panel;
    }
    
    private void ShowAITips(object sender, LinkLabelLinkClickedEventArgs e)
    {
        var tipsDialog = new AIPromptsHelpDialog();
        tipsDialog.ShowDialog();
    }
}

public class AIPromptsHelpDialog : Form
{
    public AIPromptsHelpDialog()
    {
        Size = new Size(600, 500);
        Text = "AI Prompting Tips - RevitAutoPlan";
        StartPosition = FormStartPosition.CenterParent;
        
        var webBrowser = new WebBrowser { Dock = DockStyle.Fill };
        webBrowser.DocumentText = GenerateHelpHTML();
        Controls.Add(webBrowser);
    }
    
    private string GenerateHelpHTML()
    {
        return @"
        <html>
        <head>
            <style>
                body { font-family: Segoe UI, Arial, sans-serif; margin: 20px; }
                .tip { background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #0078d4; }
                .example { background-color: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 4px; }
                h3 { color: #0078d4; }
            </style>
        </head>
        <body>
            <h2>🤖 How to Get Better Results from AI</h2>
            
            <h3>✅ Good Prompts</h3>
            <div class='tip'>
                <strong>Be Specific:</strong> ""Create a 2-bedroom apartment with kitchen open to living room, separate bathroom, and storage closet.""
            </div>
            <div class='tip'>
                <strong>Include Dimensions:</strong> ""Master bedroom should be at least 12m², kitchen needs space for island.""
            </div>
            <div class='tip'>
                <strong>Mention Relationships:</strong> ""Bedrooms should be private, away from living areas. Kitchen should connect to dining area.""
            </div>
            
            <h3>❌ Prompts to Avoid</h3>
            <div class='example'>
                ""Make it nice"" - Too vague<br>
                ""Something modern"" - Not specific enough<br>
                ""Like my friend's house"" - AI doesn't have context
            </div>
            
            <h3>🏗️ AI Capabilities</h3>
            <ul>
                <li>✅ Rectangular and L-shaped buildings work best</li>
                <li>✅ Standard room types (bedroom, kitchen, bathroom, living room)</li>
                <li>✅ Building code compliance checking</li>
                <li>⚠️ Complex curved geometry may need manual adjustment</li>
                <li>⚠️ Very specific furniture placement needs review</li>
            </ul>
            
            <h3>🔍 Review Process</h3>
            <p>Remember: All AI outputs require your professional review and approval. You're in control!</p>
        </body>
        </html>";
    }
}
```

### Realistic Progress Indicators
```csharp
public class AIProgressIndicator : UserControl
{
    private readonly ProgressBar _overallProgress;
    private readonly Label _currentStageLabel;
    private readonly Label _timeRemainingLabel;
    private readonly Panel _stagesPanel;
    private readonly List<ProgressStage> _stages;
    private readonly Timer _updateTimer;
    
    public AIProgressIndicator()
    {
        _stages = new List<ProgressStage>();
        InitializeLayout();
        SetupRealisticTimings();
    }
    
    private void SetupRealisticTimings()
    {
        // Based on actual AI processing times
        _stages.AddRange(new[]
        {
            new ProgressStage("Analyzing your requirements", TimeSpan.FromSeconds(3), "🔍"),
            new ProgressStage("Generating layout options", TimeSpan.FromSeconds(15), "🤖"),
            new ProgressStage("Checking building codes", TimeSpan.FromSeconds(8), "📋"),
            new ProgressStage("Validating geometry", TimeSpan.FromSeconds(5), "📐"),
            new ProgressStage("Preparing for your review", TimeSpan.FromSeconds(2), "👀")
        });
        
        // Total: ~33 seconds (realistic for AI operations)
    }
    
    public async Task RunProgressAsync(CancellationToken cancellationToken = default)
    {
        _updateTimer.Start();
        
        for (int i = 0; i < _stages.Count; i++)
        {
            var stage = _stages[i];
            stage.Status = StageStatus.InProgress;
            stage.StartTime = DateTime.Now;
            
            UpdateUI(i, stage);
            
            // Realistic processing time with some variability
            var actualDuration = stage.EstimatedDuration.Add(TimeSpan.FromSeconds(Random.Shared.Next(-2, 3)));
            await Task.Delay(actualDuration, cancellationToken);
            
            stage.Status = StageStatus.Completed;
            stage.ActualDuration = DateTime.Now - stage.StartTime.Value;
            
            UpdateStageVisual(i, stage);
        }
        
        _updateTimer.Stop();
        ShowCompletionMessage();
    }
    
    private void UpdateUI(int currentStageIndex, ProgressStage currentStage)
    {
        _currentStageLabel.Text = $"{currentStage.Icon} {currentStage.Name}...";
        _overallProgress.Value = (int)((double)currentStageIndex / _stages.Count * 100);
        
        // Calculate remaining time based on remaining stages
        var remainingStages = _stages.Skip(currentStageIndex + 1);
        var estimatedRemaining = remainingStages.Sum(s => s.EstimatedDuration.TotalSeconds);
        
        if (estimatedRemaining > 0)
        {
            _timeRemainingLabel.Text = $"~{estimatedRemaining:F0} seconds remaining";
        }
        else
        {
            _timeRemainingLabel.Text = "Almost done...";
        }
    }
    
    private void ShowCompletionMessage()
    {
        _currentStageLabel.Text = "✅ AI layout generated successfully!";
        _timeRemainingLabel.Text = "Ready for your review";
        _overallProgress.Value = 100;
        
        // Show next steps
        var nextStepsLabel = new Label
        {
            Text = "Next: Review the AI-generated layout and make any adjustments",
            ForeColor = Color.Green,
            Font = new Font(Font, FontStyle.Bold)
        };
        Controls.Add(nextStepsLabel);
    }
}

public class ProgressStage
{
    public string Name { get; set; }
    public string Icon { get; set; }
    public TimeSpan EstimatedDuration { get; set; }
    public StageStatus Status { get; set; } = StageStatus.Pending;
    public DateTime? StartTime { get; set; }
    public TimeSpan? ActualDuration { get; set; }
    
    public ProgressStage(string name, TimeSpan estimatedDuration, string icon)
    {
        Name = name;
        EstimatedDuration = estimatedDuration;
        Icon = icon;
    }
}
```

### Human Review Interface Design
```csharp
public class AILayoutReviewInterface : Form
{
    private readonly LayoutResult _aiOutput;
    private readonly ValidationResult _validation;
    private readonly SplitContainer _mainSplit;
    private readonly LayoutViewer _layoutViewer;
    private readonly ReviewControlPanel _reviewPanel;
    
    public AILayoutReviewInterface(LayoutResult aiOutput, ValidationResult validation)
    {
        _aiOutput = aiOutput;
        _validation = validation;
        
        InitializeProfessionalInterface();
        LoadAIOutput();
        SetupReviewWorkflow();
    }
    
    private void InitializeProfessionalInterface()
    {
        // Professional architect-focused design
        Size = new Size(1400, 900);
        Text = "AI Layout Review - RevitAutoPlan";
        StartPosition = FormStartPosition.CenterScreen;
        WindowState = FormWindowState.Maximized;
        
        // Main split: 75% viewer, 25% controls
        _mainSplit = new SplitContainer
        {
            Dock = DockStyle.Fill,
            Orientation = Orientation.Vertical,
            SplitterDistance = (int)(Width * 0.75),
            FixedPanel = FixedPanel.Panel2
        };
        
        // Left: Layout viewer with zoom and navigation
        _layoutViewer = new ProfessionalLayoutViewer
        {
            Dock = DockStyle.Fill,
            ShowGrid = true,
            ShowDimensions = true,
            AllowZoom = true,
            AllowPan = true
        };
        _mainSplit.Panel1.Controls.Add(_layoutViewer);
        
        // Right: Review and approval controls
        _reviewPanel = new ReviewControlPanel(_validation)
        {
            Dock = DockStyle.Fill
        };
        _mainSplit.Panel2.Controls.Add(_reviewPanel);
        
        Controls.Add(_mainSplit);
    }
    
    private void SetupReviewWorkflow()
    {
        // Step-by-step review process
        var workflowSteps = new[]
        {
            new ReviewStep("1. Examine the overall layout", "Check room placement and circulation"),
            new ReviewStep("2. Verify room sizes", "Ensure all rooms meet your requirements"),
            new ReviewStep("3. Check door and window placement", "Confirm accessibility and natural light"),
            new ReviewStep("4. Review building code compliance", "Validate against regulations"),
            new ReviewStep("5. Make any necessary adjustments", "Use the modification tools if needed"),
            new ReviewStep("6. Approve or request changes", "Make your final decision")
        };
        
        _reviewPanel.SetWorkflowSteps(workflowSteps);
    }
}

public class ReviewControlPanel : UserControl
{
    private readonly ValidationResult _validation;
    private readonly TabControl _reviewTabs;
    
    public ReviewControlPanel(ValidationResult validation)
    {
        _validation = validation;
        InitializeReviewTabs();
    }
    
    private void InitializeReviewTabs()
    {
        _reviewTabs = new TabControl { Dock = DockStyle.Fill };
        
        // Tab 1: AI Confidence & Metadata
        var metadataTab = new TabPage("AI Analysis");
        metadataTab.Controls.Add(CreateMetadataPanel());
        
        // Tab 2: Validation Results
        var validationTab = new TabPage("Validation Results");
        validationTab.Controls.Add(CreateValidationPanel());
        
        // Tab 3: Modification Tools
        var modificationsTab = new TabPage("Modifications");
        modificationsTab.Controls.Add(CreateModificationPanel());
        
        // Tab 4: Approval Workflow
        var approvalTab = new TabPage("Approval");
        approvalTab.Controls.Add(CreateApprovalPanel());
        
        _reviewTabs.TabPages.AddRange(new[] { metadataTab, validationTab, modificationsTab, approvalTab });
        Controls.Add(_reviewTabs);
    }
    
    private Panel CreateApprovalPanel()
    {
        var panel = new Panel { Dock = DockStyle.Fill };
        
        // Approval decision buttons with clear actions
        var approveButton = new Button
        {
            Text = "✅ Approve & Create in Revit",
            Size = new Size(200, 50),
            BackColor = Color.FromArgb(0, 120, 212),
            ForeColor = Color.White,
            Font = new Font(Font.FontFamily, 12, FontStyle.Bold),
            Location = new Point(20, 20)
        };
        approveButton.Click += OnApprove;
        
        var requestChangesButton = new Button
        {
            Text = "🔄 Request AI Changes",
            Size = new Size(200, 50),
            BackColor = Color.FromArgb(255, 140, 0),
            ForeColor = Color.White,
            Font = new Font(Font.FontFamily, 12, FontStyle.Bold),
            Location = new Point(20, 80)
        };
        requestChangesButton.Click += OnRequestChanges;
        
        var rejectButton = new Button
        {
            Text = "❌ Reject & Start Over",
            Size = new Size(200, 50),
            BackColor = Color.FromArgb(196, 43, 28),
            ForeColor = Color.White,
            Font = new Font(Font.FontFamily, 12, FontStyle.Bold),
            Location = new Point(20, 140)
        };
        rejectButton.Click += OnReject;
        
        // Feedback section
        var feedbackLabel = new Label
        {
            Text = "Optional feedback for AI improvement:",
            Location = new Point(20, 220),
            AutoSize = true
        };
        
        var feedbackTextBox = new RichTextBox
        {
            Size = new Size(200, 100),
            Location = new Point(20, 250),
            PlaceholderText = "What could be improved? What did you like?"
        };
        
        panel.Controls.AddRange(new Control[] 
        { 
            approveButton, requestChangesButton, rejectButton, 
            feedbackLabel, feedbackTextBox 
        });
        
        return panel;
    }
    
    private void OnApprove(object sender, EventArgs e)
    {
        // Track approval metrics for AI learning
        var approvalFeedback = new ApprovalFeedback
        {
            Decision = ApprovalDecision.Approved,
            TimeSpentReviewing = GetReviewTimeSpan(),
            ConfidenceInAI = GetUserConfidenceRating(),
            MostImportantFactors = GetSelectedFactors(),
            UserComments = GetUserFeedback()
        };
        
        // Log for AI improvement
        LogUserDecision(approvalFeedback);
        
        // Close dialog with approval
        DialogResult = DialogResult.OK;
        Close();
    }
    
    private void OnRequestChanges(object sender, EventArgs e)
    {
        // Show specific change request dialog
        var changeDialog = new SpecificChangeRequestDialog(_aiOutput);
        if (changeDialog.ShowDialog() == DialogResult.OK)
        {
            var changeRequest = changeDialog.GetChangeRequest();
            
            // Submit change request back to AI
            SubmitChangeRequest(changeRequest);
        }
    }
}
```

### Error State and Recovery Design
```csharp
public class AIErrorRecoveryDialog : Form
{
    private readonly Exception _error;
    private readonly string _correlationId;
    
    public AIErrorRecoveryDialog(Exception error, string correlationId)
    {
        _error = error;
        _correlationId = correlationId;
        
        InitializeRecoveryInterface();
    }
    
    private void InitializeRecoveryInterface()
    {
        Size = new Size(600, 400);
        Text = "AI Processing Issue - RevitAutoPlan";
        StartPosition = FormStartPosition.CenterParent;
        
        var mainPanel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 4,
            ColumnCount = 1,
            Padding = new Padding(20)
        };
        
        // Friendly error explanation
        var errorIcon = new PictureBox
        {
            Image = SystemIcons.Warning.ToBitmap(),
            Size = new Size(48, 48),
            SizeMode = PictureBoxSizeMode.Zoom
        };
        
        var errorMessage = GetUserFriendlyErrorMessage(_error);
        var messageLabel = new Label
        {
            Text = errorMessage,
            Font = new Font(Font.FontFamily, 10, FontStyle.Regular),
            AutoSize = false,
            TextAlign = ContentAlignment.MiddleLeft
        };
        
        // Recovery options
        var recoveryOptions = CreateRecoveryOptionsPanel();
        
        // Support information
        var supportPanel = CreateSupportPanel();
        
        mainPanel.Controls.Add(CreateHeaderPanel(errorIcon, messageLabel), 0, 0);
        mainPanel.Controls.Add(recoveryOptions, 0, 1);
        mainPanel.Controls.Add(supportPanel, 0, 2);
        mainPanel.Controls.Add(CreateButtonPanel(), 0, 3);
        
        Controls.Add(mainPanel);
    }
    
    private string GetUserFriendlyErrorMessage(Exception error)
    {
        return error switch
        {
            HttpRequestException => 
                "The AI service is temporarily unavailable. This could be due to network connectivity or server maintenance.",
                
            TimeoutException => 
                "The AI is taking longer than expected to process your request. This sometimes happens with complex layouts.",
                
            AIValidationException validationEx => 
                $"The AI generated a layout, but it has some issues that need to be addressed:\n\n{string.Join("\n• ", validationEx.ValidationErrors)}",
                
            AIServiceUnavailableException => 
                "The AI service is currently offline for maintenance. You can try again later or use manual design tools.",
                
            _ => 
                "An unexpected issue occurred during AI processing. Don't worry - your project is safe and you have several options to continue."
        };
    }
    
    private Panel CreateRecoveryOptionsPanel()
    {
        var panel = new Panel { Height = 150 };
        
        var optionsLabel = new Label
        {
            Text = "What would you like to do?",
            Font = new Font(Font.FontFamily, 10, FontStyle.Bold),
            Location = new Point(0, 0),
            AutoSize = true
        };
        
        var tryAgainButton = new Button
        {
            Text = "🔄 Try Again",
            Size = new Size(120, 35),
            Location = new Point(0, 30)
        };
        tryAgainButton.Click += (s, e) => 
        {
            DialogResult = DialogResult.Retry;
            Close();
        };
        
        var simplifyButton = new Button
        {
            Text = "📝 Simplify Request",
            Size = new Size(120, 35),
            Location = new Point(130, 30)
        };
        simplifyButton.Click += OnSimplifyRequest;
        
        var manualButton = new Button
        {
            Text = "✏️ Design Manually",
            Size = new Size(120, 35),
            Location = new Point(260, 30)
        };
        manualButton.Click += (s, e) =>
        {
            DialogResult = DialogResult.Cancel;
            Close();
        };
        
        var helpButton = new Button
        {
            Text = "❓ Get Help",
            Size = new Size(120, 35),
            Location = new Point(0, 75)
        };
        helpButton.Click += ShowHelp;
        
        panel.Controls.AddRange(new Control[] 
        { 
            optionsLabel, tryAgainButton, simplifyButton, manualButton, helpButton 
        });
        
        return panel;
    }
    
    private void OnSimplifyRequest(object sender, EventArgs e)
    {
        var helpDialog = new SimplificationGuideDialog();
        helpDialog.ShowDialog();
    }
    
    private void ShowHelp(object sender, EventArgs e)
    {
        var helpDialog = new AITroubleshootingDialog(_error, _correlationId);
        helpDialog.ShowDialog();
    }
}
```

## Accessibility and Professional Standards

### Keyboard Navigation and Screen Reader Support
```csharp
public class AccessibleAIInterface : Form
{
    protected override void SetBoundsCore(int x, int y, int width, int height, BoundsSpecified specified)
    {
        // Ensure minimum readable size
        if (width < 800) width = 800;
        if (height < 600) height = 600;
        base.SetBoundsCore(x, y, width, height, specified);
    }
    
    protected override bool ProcessTabKey(bool forward)
    {
        // Custom tab order for logical navigation through AI workflow
        return base.ProcessTabKey(forward);
    }
    
    private void SetupAccessibility()
    {
        // Screen reader descriptions
        this.AccessibleName = "AI Layout Generation Dialog";
        this.AccessibleDescription = "Generate architectural layouts using artificial intelligence";
        
        // High contrast support
        if (SystemInformation.HighContrast)
        {
            ApplyHighContrastTheme();
        }
        
        // Keyboard shortcuts
        var shortcuts = new[]
        {
            new KeyboardShortcut(Keys.Control | Keys.G, "Generate Layout", GenerateLayout),
            new KeyboardShortcut(Keys.Control | Keys.R, "Review Layout", ShowReview),
            new KeyboardShortcut(Keys.F1, "Show Help", ShowHelp),
            new KeyboardShortcut(Keys.Escape, "Cancel", Cancel)
        };
        
        RegisterKeyboardShortcuts(shortcuts);
    }
}
```

Always design for professional architects, provide clear feedback, show realistic timings, and maintain user confidence throughout the AI collaboration process.
