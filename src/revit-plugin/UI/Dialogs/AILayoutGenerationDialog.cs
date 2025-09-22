using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.UI.Dialogs
{
    /// <summary>
    /// AI Layout Generation dialog implementing Apple-vari design principles.
    /// Provides intuitive interface for AI-powered architectural layout generation.
    /// </summary>
    public partial class AILayoutGenerationDialog : Form
    {
        private static readonly ILogger Logger = LoggerFactory.Create(builder => builder.AddConsole()).CreateLogger<AILayoutGenerationDialog>();
        
        // UI Controls
        private TabControl _tabControl;
        private Panel _actionPanel;
        private Button _generateButton;
        private Button _cancelButton;
        private Button _previewButton;
        
        // Input Controls
        private ComboBox _buildingTypeCombo;
        private TextBox _totalAreaTextBox;
        private RichTextBox _requirementsTextBox;
        private Panel _roomRequirementsPanel;
        private ComboBox _stylePreferenceCombo;
        private CheckBox _accessibilityCheckBox;
        private ComboBox _buildingCodeCombo;

        // Configuration
        private LayoutGenerationRequest _generationRequest;
        private readonly string _correlationId;

        public AILayoutGenerationDialog()
        {
            _correlationId = Guid.NewGuid().ToString();
            Logger.LogDebug("Initializing AI Layout Generation dialog", _correlationId);
            
            InitializeComponent();
            SetupAppleVariDesign();
            ConfigureValidation();
            LoadDefaultValues();
        }

        /// <summary>
        /// Gets the configured layout generation request.
        /// </summary>
        /// <returns>The layout generation request.</returns>
        public LayoutGenerationRequest GetGenerationRequest()
        {
            return _generationRequest;
        }

        private void InitializeComponent()
        {
            try
            {
                // Main form setup
                Size = new Size(800, 600);
                Text = "AI Layout Generation - ArchBuilder.AI";
                StartPosition = FormStartPosition.CenterParent;
                MinimumSize = new Size(600, 400);
                MaximizeBox = false;
                FormBorderStyle = FormBorderStyle.FixedDialog;

                // Create main tab control
                _tabControl = new TabControl
                {
                    Dock = DockStyle.Fill,
                    Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom
                };

                // Create tabs
                CreateBasicRequirementsTab();
                CreateAdvancedSettingsTab();
                CreateStylePreferencesTab();

                // Create action panel
                CreateActionPanel();

                // Add controls to form
                Controls.Add(_tabControl);
                Controls.Add(_actionPanel);

                Logger.LogDebug("UI components initialized successfully", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to initialize UI components", _correlationId);
                throw;
            }
        }

        private void SetupAppleVariDesign()
        {
            try
            {
                // Apple-vari color scheme
                BackColor = Color.FromArgb(248, 248, 248); // Light gray background
                ForeColor = Color.FromArgb(51, 51, 51);    // Dark text

                // Clean, minimal font
                Font = new Font("Segoe UI", 9F, FontStyle.Regular);

                // Tab control styling
                _tabControl.Appearance = TabAppearance.Normal;
                _tabControl.Font = new Font("Segoe UI", 9F, FontStyle.Regular);

                Logger.LogDebug("Apple-vari design applied", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to apply design styling", _correlationId);
            }
        }

        private void CreateBasicRequirementsTab()
        {
            var basicTab = new TabPage("Project Requirements")
            {
                BackColor = BackColor,
                Padding = new Padding(20)
            };

            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 2,
                RowCount = 6,
                CellBorderStyle = TableLayoutPanelCellBorderStyle.None
            };

            // Set column widths: 30% labels, 70% controls
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30F));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 70F));

            // Building type selection
            var buildingTypeLabel = CreateLabel("Building Type:");
            _buildingTypeCombo = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Font = Font,
                Anchor = AnchorStyles.Left | AnchorStyles.Right
            };
            _buildingTypeCombo.Items.AddRange(new[] { "Residential", "Office", "Retail", "Mixed Use", "Healthcare", "Educational" });
            _buildingTypeCombo.SelectedIndex = 0;

            mainPanel.Controls.Add(buildingTypeLabel, 0, 0);
            mainPanel.Controls.Add(_buildingTypeCombo, 1, 0);

            // Total area input
            var areaLabel = CreateLabel("Total Area (m²):");
            _totalAreaTextBox = new TextBox
            {
                Font = Font,
                Anchor = AnchorStyles.Left | AnchorStyles.Right
            };
            _totalAreaTextBox.TextChanged += ValidateNumericInput;

            mainPanel.Controls.Add(areaLabel, 0, 1);
            mainPanel.Controls.Add(_totalAreaTextBox, 1, 1);

            // Room requirements
            var roomsLabel = CreateLabel("Room Requirements:");
            _roomRequirementsPanel = CreateRoomRequirementsPanel();

            mainPanel.Controls.Add(roomsLabel, 0, 2);
            mainPanel.Controls.Add(_roomRequirementsPanel, 1, 2);

            // Additional requirements
            var requirementsLabel = CreateLabel("Additional Requirements:");
            _requirementsTextBox = new RichTextBox
            {
                Height = 100,
                Font = Font,
                Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top | AnchorStyles.Bottom
            };

            mainPanel.Controls.Add(requirementsLabel, 0, 3);
            mainPanel.Controls.Add(_requirementsTextBox, 1, 3);

            // AI Tips link
            var tipsLink = new LinkLabel
            {
                Text = "💡 View AI prompting tips and examples",
                Font = Font,
                LinkColor = Color.FromArgb(0, 122, 255), // Apple blue
                Anchor = AnchorStyles.Left
            };
            tipsLink.LinkClicked += ShowAITips;

            mainPanel.Controls.Add(new Label(), 0, 4); // Empty cell
            mainPanel.Controls.Add(tipsLink, 1, 4);

            // Set row heights
            for (int i = 0; i < 6; i++)
            {
                mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            }

            basicTab.Controls.Add(mainPanel);
            _tabControl.TabPages.Add(basicTab);
        }

        private void CreateAdvancedSettingsTab()
        {
            var advancedTab = new TabPage("Advanced Settings")
            {
                BackColor = BackColor,
                Padding = new Padding(20)
            };

            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 2,
                RowCount = 5
            };

            // Set column widths
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30F));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 70F));

            // Building code selection
            var codeLabel = CreateLabel("Building Code:");
            _buildingCodeCombo = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Font = Font,
                Anchor = AnchorStyles.Left | AnchorStyles.Right
            };
            _buildingCodeCombo.Items.AddRange(new[] { "Turkish Building Code", "International Building Code (IBC)", "Eurocode", "British Standards", "Custom" });
            _buildingCodeCombo.SelectedIndex = 0;

            mainPanel.Controls.Add(codeLabel, 0, 0);
            mainPanel.Controls.Add(_buildingCodeCombo, 1, 0);

            // Accessibility requirements
            var accessibilityLabel = CreateLabel("Accessibility:");
            _accessibilityCheckBox = new CheckBox
            {
                Text = "Include accessibility features (ramps, wide doors, etc.)",
                Font = Font,
                Checked = true,
                Anchor = AnchorStyles.Left
            };

            mainPanel.Controls.Add(accessibilityLabel, 0, 1);
            mainPanel.Controls.Add(_accessibilityCheckBox, 1, 1);

            // Set row heights
            for (int i = 0; i < 5; i++)
            {
                mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            }

            advancedTab.Controls.Add(mainPanel);
            _tabControl.TabPages.Add(advancedTab);
        }

        private void CreateStylePreferencesTab()
        {
            var styleTab = new TabPage("Style & Constraints")
            {
                BackColor = BackColor,
                Padding = new Padding(20)
            };

            var mainPanel = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 2,
                RowCount = 4
            };

            // Set column widths
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30F));
            mainPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 70F));

            // Architectural style preference
            var styleLabel = CreateLabel("Architectural Style:");
            _stylePreferenceCombo = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Font = Font,
                Anchor = AnchorStyles.Left | AnchorStyles.Right
            };
            _stylePreferenceCombo.Items.AddRange(new[] { "Modern", "Contemporary", "Traditional", "Minimalist", "Industrial", "Custom" });
            _stylePreferenceCombo.SelectedIndex = 0;

            mainPanel.Controls.Add(styleLabel, 0, 0);
            mainPanel.Controls.Add(_stylePreferenceCombo, 1, 0);

            // Set row heights
            for (int i = 0; i < 4; i++)
            {
                mainPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            }

            styleTab.Controls.Add(mainPanel);
            _tabControl.TabPages.Add(styleTab);
        }

        private void CreateActionPanel()
        {
            _actionPanel = new Panel
            {
                Height = 60,
                Dock = DockStyle.Bottom,
                BackColor = Color.FromArgb(245, 245, 245) // Slightly darker gray
            };

            // Generate button (primary action)
            _generateButton = new Button
            {
                Text = "Generate Layout with AI",
                Size = new Size(180, 35),
                Location = new Point(20, 12),
                BackColor = Color.FromArgb(0, 122, 255), // Apple blue
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(Font.FontFamily, 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            _generateButton.FlatAppearance.BorderSize = 0;
            _generateButton.Click += OnGenerateClicked;

            // Preview button (secondary action)
            _previewButton = new Button
            {
                Text = "Preview Settings",
                Size = new Size(120, 35),
                Location = new Point(210, 12),
                BackColor = Color.Transparent,
                ForeColor = Color.FromArgb(0, 122, 255),
                FlatStyle = FlatStyle.Flat,
                Font = Font,
                Cursor = Cursors.Hand
            };
            _previewButton.FlatAppearance.BorderColor = Color.FromArgb(0, 122, 255);
            _previewButton.Click += OnPreviewClicked;

            // Cancel button
            _cancelButton = new Button
            {
                Text = "Cancel",
                Size = new Size(80, 35),
                Location = new Point(Width - 110, 12),
                BackColor = Color.Transparent,
                ForeColor = Color.FromArgb(51, 51, 51),
                FlatStyle = FlatStyle.Flat,
                Font = Font,
                Cursor = Cursors.Hand,
                Anchor = AnchorStyles.Top | AnchorStyles.Right
            };
            _cancelButton.FlatAppearance.BorderColor = Color.FromArgb(200, 200, 200);
            _cancelButton.Click += OnCancelClicked;

            _actionPanel.Controls.AddRange(new Control[] { _generateButton, _previewButton, _cancelButton });
        }

        private Label CreateLabel(string text)
        {
            return new Label
            {
                Text = text,
                Font = Font,
                TextAlign = ContentAlignment.MiddleRight,
                Anchor = AnchorStyles.Left | AnchorStyles.Right,
                AutoSize = false,
                Height = 23
            };
        }

        private Panel CreateRoomRequirementsPanel()
        {
            var panel = new Panel
            {
                Height = 120,
                Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top,
                BorderStyle = BorderStyle.FixedSingle
            };

            var roomsList = new CheckedListBox
            {
                Dock = DockStyle.Fill,
                Font = Font,
                CheckOnClick = true,
                BorderStyle = BorderStyle.None
            };

            roomsList.Items.AddRange(new object[]
            {
                "Living Room",
                "Kitchen",
                "Master Bedroom",
                "Bedroom 2",
                "Bedroom 3",
                "Bathroom",
                "Guest Bathroom",
                "Dining Room",
                "Study/Office",
                "Storage/Utility"
            });

            // Select common rooms by default
            roomsList.SetItemChecked(0, true); // Living Room
            roomsList.SetItemChecked(1, true); // Kitchen
            roomsList.SetItemChecked(2, true); // Master Bedroom
            roomsList.SetItemChecked(5, true); // Bathroom

            panel.Controls.Add(roomsList);
            return panel;
        }

        private void ConfigureValidation()
        {
            // Add validation for numeric inputs
            _totalAreaTextBox.KeyPress += (sender, e) =>
            {
                if (!char.IsControl(e.KeyChar) && !char.IsDigit(e.KeyChar) && e.KeyChar != '.')
                {
                    e.Handled = true;
                }
            };
        }

        private void LoadDefaultValues()
        {
            try
            {
                // Set reasonable defaults
                _totalAreaTextBox.Text = "150";
                _requirementsTextBox.Text = "Please create an efficient layout with good natural light and circulation.";

                Logger.LogDebug("Default values loaded", _correlationId);
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to load default values", _correlationId);
            }
        }

        private void ValidateNumericInput(object sender, EventArgs e)
        {
            var textBox = sender as TextBox;
            if (textBox == null) return;

            // Validate that input is numeric
            if (double.TryParse(textBox.Text, out var value))
            {
                textBox.BackColor = Color.White;
                UpdateGenerateButtonState();
            }
            else if (!string.IsNullOrEmpty(textBox.Text))
            {
                textBox.BackColor = Color.FromArgb(255, 240, 240); // Light red
            }
        }

        private void UpdateGenerateButtonState()
        {
            try
            {
                // Enable generate button only if required fields are valid
                var hasValidArea = double.TryParse(_totalAreaTextBox.Text, out var area) && area > 0;
                var hasSelectedRooms = GetSelectedRooms().Any();

                _generateButton.Enabled = hasValidArea && hasSelectedRooms;
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to update generate button state", _correlationId);
                _generateButton.Enabled = false;
            }
        }

        private string[] GetSelectedRooms()
        {
            try
            {
                var roomsList = _roomRequirementsPanel.Controls.OfType<CheckedListBox>().FirstOrDefault();
                if (roomsList == null) return new string[0];

                return roomsList.CheckedItems.Cast<string>().ToArray();
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to get selected rooms", _correlationId);
                return new string[0];
            }
        }

        private void ShowAITips(object sender, LinkLabelLinkClickedEventArgs e)
        {
            try
            {
                var tipsDialog = new AIPromptsHelpDialog();
                tipsDialog.ShowDialog(this);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to show AI tips dialog", _correlationId);
                MessageBox.Show("Unable to load AI tips. Please try again.", "Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void OnPreviewClicked(object sender, EventArgs e)
        {
            try
            {
                var request = BuildGenerationRequest();
                var previewDialog = new LayoutPreviewDialog(request);
                previewDialog.ShowDialog(this);
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to show preview", _correlationId);
                MessageBox.Show("Unable to generate preview. Please check your inputs.", "Preview Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void OnGenerateClicked(object sender, EventArgs e)
        {
            try
            {
                if (!ValidateAllInputs())
                    return;

                _generationRequest = BuildGenerationRequest();
                DialogResult = DialogResult.OK;
                Close();
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to process generation request", _correlationId);
                MessageBox.Show("Failed to process your request. Please check your inputs and try again.", 
                    "Generation Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void OnCancelClicked(object sender, EventArgs e)
        {
            DialogResult = DialogResult.Cancel;
            Close();
        }

        private bool ValidateAllInputs()
        {
            try
            {
                // Validate total area
                if (!double.TryParse(_totalAreaTextBox.Text, out var area) || area <= 0)
                {
                    MessageBox.Show("Please enter a valid total area greater than 0.", "Validation Error", 
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    _tabControl.SelectedIndex = 0;
                    _totalAreaTextBox.Focus();
                    return false;
                }

                // Validate room selection
                var selectedRooms = GetSelectedRooms();
                if (!selectedRooms.Any())
                {
                    MessageBox.Show("Please select at least one room type.", "Validation Error", 
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    _tabControl.SelectedIndex = 0;
                    return false;
                }

                return true;
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Error during input validation", _correlationId);
                return false;
            }
        }

        private LayoutGenerationRequest BuildGenerationRequest()
        {
            var selectedRooms = GetSelectedRooms();
            
            return new LayoutGenerationRequest
            {
                CorrelationId = _correlationId,
                BuildingType = _buildingTypeCombo.SelectedItem?.ToString() ?? "Residential",
                TotalArea = double.Parse(_totalAreaTextBox.Text),
                RequiredRooms = selectedRooms.ToList(),
                AdditionalRequirements = _requirementsTextBox.Text?.Trim(),
                BuildingCode = _buildingCodeCombo.SelectedItem?.ToString() ?? "Turkish Building Code",
                RequiresAccessibility = _accessibilityCheckBox.Checked,
                ArchitecturalStyle = _stylePreferenceCombo.SelectedItem?.ToString() ?? "Modern",
                RequestedAt = DateTime.UtcNow,
                RequestedBy = Environment.UserName
            };
        }
    }

    /// <summary>
    /// Data contract for layout generation requests.
    /// </summary>
    public class LayoutGenerationRequest
    {
        public string CorrelationId { get; set; }
        public string BuildingType { get; set; }
        public double TotalArea { get; set; }
        public System.Collections.Generic.List<string> RequiredRooms { get; set; }
        public string AdditionalRequirements { get; set; }
        public string BuildingCode { get; set; }
        public bool RequiresAccessibility { get; set; }
        public string ArchitecturalStyle { get; set; }
        public DateTime RequestedAt { get; set; }
        public string RequestedBy { get; set; }
    }
}