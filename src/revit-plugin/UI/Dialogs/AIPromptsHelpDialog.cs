using System;
using System.Drawing;
using System.Windows.Forms;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Revit.UI.Dialogs
{
    /// <summary>
    /// AI Prompts Help dialog providing guidance for better AI results.
    /// Implements Apple-vari design with educational content for architects.
    /// </summary>
    public partial class AIPromptsHelpDialog : Form
    {
        private static readonly ILogger Logger = LoggerFactory.Create(builder => builder.AddConsole()).CreateLogger<AIPromptsHelpDialog>();
        
        private WebBrowser _webBrowser;
        private Button _closeButton;

        public AIPromptsHelpDialog()
        {
            InitializeComponent();
            SetupAppleVariDesign();
            LoadHelpContent();
        }

        private void InitializeComponent()
        {
            try
            {
                // Main form setup
                Size = new Size(700, 600);
                Text = "AI Prompting Tips - ArchBuilder.AI";
                StartPosition = FormStartPosition.CenterParent;
                MinimumSize = new Size(600, 500);
                MaximizeBox = false;
                FormBorderStyle = FormBorderStyle.Sizable;

                // Web browser for rich content
                _webBrowser = new WebBrowser
                {
                    Dock = DockStyle.Fill,
                    AllowWebBrowserDrop = false,
                    IsWebBrowserContextMenuEnabled = false,
                    WebBrowserShortcutsEnabled = false,
                    ScrollBarsEnabled = true
                };

                // Close button panel
                var buttonPanel = new Panel
                {
                    Height = 50,
                    Dock = DockStyle.Bottom,
                    BackColor = Color.FromArgb(245, 245, 245)
                };

                _closeButton = new Button
                {
                    Text = "Close",
                    Size = new Size(80, 30),
                    Location = new Point(Width - 100, 10),
                    BackColor = Color.FromArgb(0, 122, 255),
                    ForeColor = Color.White,
                    FlatStyle = FlatStyle.Flat,
                    Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                    Cursor = Cursors.Hand,
                    Anchor = AnchorStyles.Top | AnchorStyles.Right
                };
                _closeButton.FlatAppearance.BorderSize = 0;
                _closeButton.Click += (s, e) => Close();

                buttonPanel.Controls.Add(_closeButton);

                // Add controls to form
                Controls.Add(_webBrowser);
                Controls.Add(buttonPanel);

                Logger.LogDebug("AI Prompts Help dialog initialized");
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to initialize AI Prompts Help dialog");
                throw;
            }
        }

        private void SetupAppleVariDesign()
        {
            try
            {
                // Apple-vari styling
                BackColor = Color.FromArgb(248, 248, 248);
                Font = new Font("Segoe UI", 9F, FontStyle.Regular);
            }
            catch (Exception ex)
            {
                Logger.LogWarning(ex, "Failed to apply design styling");
            }
        }

        private void LoadHelpContent()
        {
            try
            {
                var htmlContent = GenerateHelpHTML();
                _webBrowser.DocumentText = htmlContent;
                
                Logger.LogDebug("Help content loaded successfully");
            }
            catch (Exception ex)
            {
                Logger.LogError(ex, "Failed to load help content");
                
                // Fallback to simple text
                _webBrowser.DocumentText = @"
                <html><body style='font-family: Segoe UI, Arial, sans-serif; margin: 20px;'>
                <h2>AI Prompting Tips</h2>
                <p>Unable to load detailed help content. Please contact support.</p>
                </body></html>";
            }
        }

        private string GenerateHelpHTML()
        {
            return @"
<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>AI Prompting Tips</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
            color: #333;
            background-color: #fafafa;
        }
        
        h1 {
            color: #007AFF;
            border-bottom: 2px solid #007AFF;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        
        h2 {
            color: #007AFF;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        
        h3 {
            color: #555;
            margin-top: 25px;
            margin-bottom: 10px;
        }
        
        .tip {
            background: linear-gradient(135deg, #E3F2FD 0%, #F0F8FF 100%);
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #007AFF;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .example {
            background-color: #F5F5F5;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border: 1px solid #DDD;
            font-family: 'Consolas', 'Monaco', monospace;
        }
        
        .good {
            border-left: 4px solid #4CAF50;
            background: linear-gradient(135deg, #E8F5E8 0%, #F1F8E9 100%);
        }
        
        .bad {
            border-left: 4px solid #F44336;
            background: linear-gradient(135deg, #FFEBEE 0%, #FFF3F3 100%);
        }
        
        .capability {
            display: inline-block;
            padding: 5px 10px;
            margin: 5px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        
        .supported {
            background-color: #E8F5E8;
            color: #2E7D32;
            border: 1px solid #4CAF50;
        }
        
        .limited {
            background-color: #FFF3E0;
            color: #E65100;
            border: 1px solid #FF9800;
        }
        
        .icon {
            font-size: 1.2em;
            margin-right: 8px;
        }
        
        ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        li {
            margin: 5px 0;
        }
        
        .highlight {
            background-color: #FFEB3B;
            padding: 2px 4px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h1>🤖 How to Get Better Results from AI</h1>
    
    <div class='tip'>
        <strong>💡 Key Principle:</strong> The more specific and detailed your requirements, the better the AI can understand and create what you need.
    </div>
    
    <h2>✅ Effective Prompting Strategies</h2>
    
    <h3>Be Specific with Measurements</h3>
    <div class='tip good'>
        <strong>✅ Good:</strong> ""Create a 2-bedroom apartment, total 85m². Master bedroom 15m², second bedroom 12m², living room 25m², kitchen 15m², bathroom 8m², hallway and storage 10m².""
    </div>
    <div class='tip bad'>
        <strong>❌ Avoid:</strong> ""Make a nice apartment with some bedrooms.""
    </div>
    
    <h3>Describe Relationships and Adjacencies</h3>
    <div class='tip good'>
        <strong>✅ Good:</strong> ""Kitchen should be open to living room but separated from bedrooms. Bathroom should be accessible from hallway but private from living areas. Master bedroom needs en-suite bathroom.""
    </div>
    <div class='tip bad'>
        <strong>❌ Avoid:</strong> ""Put rooms somewhere that makes sense.""
    </div>
    
    <h3>Include Functional Requirements</h3>
    <div class='tip good'>
        <strong>✅ Good:</strong> ""Kitchen needs space for island (2m x 1m), dining table for 6 people, and pantry storage. Living room should accommodate sectional sofa and TV wall. Need natural light in all bedrooms.""
    </div>
    <div class='tip bad'>
        <strong>❌ Avoid:</strong> ""Make it functional.""
    </div>
    
    <h3>Specify Constraints and Preferences</h3>
    <div class='tip good'>
        <strong>✅ Good:</strong> ""No stairs (single level), wide doorways for accessibility (min 90cm), entry should not directly face living room, windows on south and east sides for morning light.""
    </div>
    
    <h2>🏗️ AI Capabilities & Limitations</h2>
    
    <h3>What AI Does Best</h3>
    <div class='capability supported'><span class='icon'>✅</span> Rectangular and L-shaped buildings</div>
    <div class='capability supported'><span class='icon'>✅</span> Standard room types and layouts</div>
    <div class='capability supported'><span class='icon'>✅</span> Building code compliance checking</div>
    <div class='capability supported'><span class='icon'>✅</span> Accessibility features integration</div>
    <div class='capability supported'><span class='icon'>✅</span> Natural light optimization</div>
    <div class='capability supported'><span class='icon'>✅</span> Efficient circulation patterns</div>
    
    <h3>What Requires Extra Attention</h3>
    <div class='capability limited'><span class='icon'>⚠️</span> Complex curved or angled geometry</div>
    <div class='capability limited'><span class='icon'>⚠️</span> Very specific furniture placement</div>
    <div class='capability limited'><span class='icon'>⚠️</span> Unusual room shapes or sizes</div>
    <div class='capability limited'><span class='icon'>⚠️</span> Multi-story coordination</div>
    <div class='capability limited'><span class='icon'>⚠️</span> Highly custom architectural features</div>
    
    <h2>📋 Example Prompts That Work Well</h2>
    
    <div class='example'>
        <strong>Residential Example:</strong><br>
        ""Create a 3-bedroom single-family home, 120m² total. Open concept living/dining/kitchen (40m²) with kitchen island. Master bedroom (18m²) with en-suite bathroom (6m²). Two additional bedrooms (12m² each) sharing hallway bathroom (5m²). Laundry room (4m²) near kitchen. Entry foyer (5m²) with coat closet. Large windows in living room and bedrooms for natural light. Accessible design with 36"" doorways.""
    </div>
    
    <div class='example'>
        <strong>Office Example:</strong><br>
        ""Design a small office suite, 200m². Reception area (20m²) with waiting seating. 4 private offices (15m² each) along exterior wall for windows. Conference room (25m²) for 8 people with presentation wall. Open work area (60m²) for 12 workstations. Break room (15m²) with kitchenette. Storage closet (8m²). Two restrooms (6m² each). Wide corridors for accessibility.""
    </div>
    
    <h2>🔍 Review and Refinement Process</h2>
    
    <div class='tip'>
        <span class='icon'>👨‍💼</span> <strong>Remember:</strong> All AI outputs require your professional review and approval. You maintain complete control over the final design.
    </div>
    
    <h3>What to Check During Review</h3>
    <ul>
        <li><strong>Room Sizes:</strong> Verify all rooms meet your specified requirements</li>
        <li><strong>Circulation:</strong> Check that hallways and pathways are logical and efficient</li>
        <li><strong>Natural Light:</strong> Ensure windows are well-placed for daylight</li>
        <li><strong>Privacy:</strong> Confirm bedrooms and bathrooms have appropriate privacy</li>
        <li><strong>Building Codes:</strong> Review compliance with local regulations</li>
        <li><strong>Accessibility:</strong> Verify accessible routes and features if required</li>
    </ul>
    
    <h2>🚀 Advanced Tips</h2>
    
    <h3>Iterative Refinement</h3>
    <p>Don't expect perfection on the first try. Use the ""Request Changes"" feature to refine specific aspects:</p>
    <ul>
        <li>""Move the kitchen island to be parallel with the sink wall""</li>
        <li>""Increase master bedroom size by 2m² and reduce living room accordingly""</li>
        <li>""Add a window to the second bedroom on the east wall""</li>
    </ul>
    
    <h3>Cultural and Regional Considerations</h3>
    <p>Mention specific cultural or regional requirements:</p>
    <ul>
        <li>""Turkish-style entry with shoe removal area""</li>
        <li>""Separate guest and family living areas""</li>
        <li>""Orientation for prayer direction (Qibla)""</li>
        <li>""Balcony access from living room""</li>
    </ul>
    
    <div class='tip'>
        <span class='icon'>💬</span> <strong>Need Help?</strong> If you're not getting the results you want, try breaking down your request into smaller, more specific parts, or use the ""Request Changes"" feature to guide the AI toward your vision.
    </div>
    
</body>
</html>";
        }
    }
}