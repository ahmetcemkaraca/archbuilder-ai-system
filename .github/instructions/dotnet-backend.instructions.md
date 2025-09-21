---
applyTo: "src/revit-plugin/**/*.cs,src/desktop-app/**/*.cs,src/revit-plugin/**/*Controller.cs,src/revit-plugin/**/*Api*.cs,src/revit-plugin/**/*Program.cs,src/revit-plugin/**/*.csproj,src/desktop-app/**/*.csproj"
description: .NET Development — ArchBuilder.AI desktop app, Revit plugin integration, cloud API communication, Apple-vari UI implementation.
---
As .NET Revit Developer:
- Enforce strict transaction management for all Revit model modifications
- Implement secure HTTPS cloud API communication with authentication
- Use efficient FilteredElementCollector patterns for performance
- Apply proper memory management and IDisposable patterns
- Validate all inputs and handle Revit API exceptions gracefully
- Use structured logging with correlation IDs
- Implement subscription management and usage tracking
- **NO AI PROCESSING**: C# plugin only executes validated commands from cloud server

Cloud API Communication Architecture:
```csharp
// HTTPS Cloud API client with authentication and subscription management
public class CloudApiClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<CloudApiClient> _logger;
    private readonly IAuthenticationService _authService;
    private readonly string _baseUrl;
    private string _accessToken;
    private string _apiKey;
    
    public CloudApiClient(
        HttpClient httpClient,
        IConfiguration config,
        ILogger<CloudApiClient> logger,
        IAuthenticationService authService)
    {
        _httpClient = httpClient;
        _logger = logger;
        _authService = authService;
        _baseUrl = config.GetValue<string>("CloudApi:BaseUrl");
        
        _httpClient.Timeout = TimeSpan.FromSeconds(60); // Extended for cloud calls
        _httpClient.DefaultRequestHeaders.Add("User-Agent", "RevitAutoPlan-Plugin/1.0");
    }
    
    public async Task<bool> AuthenticateAsync(string username, string password)
    {
        try
        {
            var loginRequest = new LoginRequest
            {
                Username = username,
                Password = password
            };
            
            var json = JsonSerializer.Serialize(loginRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            
            var response = await _httpClient.PostAsync($"{_baseUrl}/v1/auth/login", content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseJson = await response.Content.ReadAsStringAsync();
                var tokenResponse = JsonSerializer.Deserialize<TokenResponse>(responseJson);
                
                _accessToken = tokenResponse.AccessToken;
                _apiKey = tokenResponse.ApiKey;
                
                // Set authentication headers for future requests
                _httpClient.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", _accessToken);
                _httpClient.DefaultRequestHeaders.Add("X-API-Key", _apiKey);
                
                // Store credentials securely
                await _authService.StoreCredentialsAsync(_accessToken, _apiKey);
                
                _logger.LogInformation("Authentication successful",
                    subscription_tier: tokenResponse.SubscriptionTier);
                
                return true;
            }
            else if (response.StatusCode == HttpStatusCode.PaymentRequired)
            {
                _logger.LogWarning("Subscription required for access");
                return false;
            }
            else
            {
                var errorContent = await response.Content.ReadAsStringAsync();
                _logger.LogError("Authentication failed: {StatusCode} - {Error}",
                    response.StatusCode, errorContent);
                return false;
            }
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Network error during authentication");
            return false;
        }
    }
    
    public async Task<LayoutResult> RequestLayoutAsync(
        LayoutRequest request,
        string correlationId,
        IProgress<ProgressInfo> progress = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            // Check authentication
            if (string.IsNullOrEmpty(_accessToken) || string.IsNullOrEmpty(_apiKey))
            {
                throw new UnauthorizedAccessException("Not authenticated. Please login first.");
            }
            
            var json = JsonSerializer.Serialize(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            content.Headers.Add("X-Correlation-ID", correlationId);
            
            _logger.LogInformation("Sending layout request to cloud",
                correlation_id: correlationId,
                building_type: request.BuildingType);
            
            progress?.Report(new ProgressInfo("Sending request to cloud...", 10));
            
            var response = await _httpClient.PostAsync(
                $"{_baseUrl}/v1/ai/layouts/generate",
                content,
                cancellationToken);
            
            if (response.StatusCode == HttpStatusCode.PaymentRequired)
            {
                var errorContent = await response.Content.ReadAsStringAsync(cancellationToken);
                var errorResponse = JsonSerializer.Deserialize<ErrorResponse>(errorContent);
                throw new SubscriptionLimitException(errorResponse.Message);
            }
            
            response.EnsureSuccessStatusCode();
            
            progress?.Report(new ProgressInfo("Processing AI response...", 50));
            
            var responseJson = await response.Content.ReadAsStringAsync(cancellationToken);
            var result = JsonSerializer.Deserialize<LayoutResult>(responseJson);
            
            // If processing is async, poll for completion
            if (result.Status == "processing")
            {
                result = await PollForCompletionAsync(correlationId, progress, cancellationToken);
            }
            
            progress?.Report(new ProgressInfo("Layout received successfully", 100));
            
            _logger.LogInformation("Layout received from cloud successfully",
                correlation_id: correlationId,
                wall_count: result.Walls?.Count ?? 0,
                door_count: result.Doors?.Count ?? 0,
                requires_review: result.RequiresHumanReview);
            
            return result;
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "Cloud API communication failed", correlation_id: correlationId);
            throw new CloudApiException("Failed to communicate with cloud AI service", ex);
        }
        catch (TaskCanceledException ex)
        {
            _logger.LogError(ex, "Cloud API request timed out", correlation_id: correlationId);
            throw new TimeoutException("Cloud AI request timed out", ex);
        }
    }
    
    private async Task<LayoutResult> PollForCompletionAsync(
        string correlationId,
        IProgress<ProgressInfo> progress,
        CancellationToken cancellationToken)
    {
        var maxAttempts = 60; // 5 minutes with 5-second intervals
        var attempt = 0;
        
        while (attempt < maxAttempts && !cancellationToken.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(5000, cancellationToken); // Wait 5 seconds
                
                var response = await _httpClient.GetAsync(
                    $"{_baseUrl}/v1/ai/commands/{correlationId}",
                    cancellationToken);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync(cancellationToken);
                    var result = JsonSerializer.Deserialize<LayoutResult>(responseJson);
                    
                    if (result.Status == "completed")
                    {
                        return result;
                    }
                    else if (result.Status == "failed")
                    {
                        throw new CloudApiException($"Cloud processing failed: {result.ErrorMessage}");
                    }
                    
                    // Update progress
                    var progressPercent = 50 + (attempt * 50 / maxAttempts);
                    progress?.Report(new ProgressInfo(
                        $"AI processing in progress... ({result.Status})",
                        progressPercent));
                }
                
                attempt++;
            }
            catch (Exception ex) when (!(ex is CloudApiException))
            {
                _logger.LogWarning("Error polling for completion, retrying...", ex);
                attempt++;
            }
        }
        
        throw new TimeoutException("Cloud processing timed out");
    }
    
    public async Task<SubscriptionInfo> GetSubscriptionInfoAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync($"{_baseUrl}/v1/subscriptions/current");
            response.EnsureSuccessStatusCode();
            
            var responseJson = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<SubscriptionInfo>(responseJson);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get subscription info");
            throw;
        }
    }
    
    public async Task<UpgradeResult> UpgradeSubscriptionAsync(
        SubscriptionTier newTier,
        string paymentMethodId)
    {
        try
        {
            var upgradeRequest = new SubscriptionUpgradeRequest
            {
                NewTier = newTier,
                PaymentMethodId = paymentMethodId
            };
            
            var json = JsonSerializer.Serialize(upgradeRequest);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            
            var response = await _httpClient.PostAsync(
                $"{_baseUrl}/v1/subscriptions/upgrade",
                content);
            
            response.EnsureSuccessStatusCode();
            
            var responseJson = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<UpgradeResult>(responseJson);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to upgrade subscription");
            throw;
        }
    }
    
    public void Dispose()
    {
        _httpClient?.Dispose();
    }
}

// Subscription-aware Revit command execution
public class RevitAICommand : IExternalCommand
{
    private readonly ICloudApiClient _cloudApi;
    private readonly ILogger<RevitAICommand> _logger;
    private readonly IProgressIndicator _progressIndicator;
    
    public RevitAICommand(
        ICloudApiClient cloudApi,
        ILogger<RevitAICommand> logger,
        IProgressIndicator progressIndicator)
    {
        _cloudApi = cloudApi;
        _logger = logger;
        _progressIndicator = progressIndicator;
    }
    
    public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
    {
        var doc = commandData.Application.ActiveUIDocument.Document;
        var correlationId = $"AI_{DateTime.UtcNow:yyyyMMddHHmmss}_{Guid.NewGuid():N}";
        
        try
        {
            return ExecuteAsync(doc, correlationId).GetAwaiter().GetResult();
        }
        catch (SubscriptionLimitException ex)
        {
            message = ex.Message;
            ShowSubscriptionUpgradeDialog();
            return Result.Cancelled;
        }
        catch (CloudApiException ex)
        {
            message = $"Cloud service error: {ex.Message}";
            _logger.LogError(ex, "Cloud API error", correlation_id: correlationId);
            return Result.Failed;
        }
        catch (Exception ex)
        {
            message = $"Unexpected error: {ex.Message}";
            _logger.LogError(ex, "Unexpected error in AI command", correlation_id: correlationId);
            return Result.Failed;
        }
    }
    
    private async Task<Result> ExecuteAsync(Document doc, string correlationId)
    {
        // Show progress dialog
        using var progress = _progressIndicator.Show("AI Layout Generation", "Initializing...");
        
        // Get user input
        var layoutRequest = await GetLayoutRequestFromUser();
        if (layoutRequest == null)
            return Result.Cancelled;
        
        // Request layout from cloud
        progress.Update("Requesting AI layout from cloud...", 10);
        var layoutResult = await _cloudApi.RequestLayoutAsync(
            layoutRequest,
            correlationId,
            progress,
            CancellationToken.None);
        
        // Show human review dialog if required
        if (layoutResult.RequiresHumanReview)
        {
            progress.Update("Waiting for human review...", 80);
            var reviewResult = await ShowHumanReviewDialog(layoutResult);
            if (!reviewResult.Approved)
            {
                return Result.Cancelled;
            }
        }
        
        // Execute layout in Revit
        progress.Update("Executing layout in Revit...", 90);
        var executionResult = await ExecuteLayoutInRevit(doc, layoutResult, correlationId);
        
        progress.Update("Layout completed successfully!", 100);
        await Task.Delay(1000); // Show completion message
        
        return executionResult;
    }
    
    private async Task<Result> ExecuteLayoutInRevit(
        Document doc,
        LayoutResult layoutResult,
        string correlationId)
    {
        using (var resourceManager = new RevitResourceManager(doc, _logger))
        {
            try
            {
                using (var transaction = new Transaction(doc, "Execute AI Layout"))
                {
                    transaction.Start();
                    
                    // Create walls
                    foreach (var wallData in layoutResult.Walls)
                    {
                        var wall = CreateWallFromData(doc, wallData);
                        resourceManager.TrackElement(wall.Id);
                    }
                    
                    // Create doors and windows
                    foreach (var doorData in layoutResult.Doors)
                    {
                        var door = CreateDoorFromData(doc, doorData);
                        resourceManager.TrackElement(door.Id);
                    }
                    
                    foreach (var windowData in layoutResult.Windows)
                    {
                        var window = CreateWindowFromData(doc, windowData);
                        resourceManager.TrackElement(window.Id);
                    }
                    
                    transaction.Commit();
                    
                    _logger.LogInformation("AI layout executed successfully",
                        correlation_id: correlationId,
                        elements_created: layoutResult.Walls.Count + layoutResult.Doors.Count + layoutResult.Windows.Count);
                    
                    return Result.Succeeded;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to execute AI layout", correlation_id: correlationId);
                resourceManager.CleanupOnError();
                return Result.Failed;
            }
        }
    }
    
    private void ShowSubscriptionUpgradeDialog()
    {
        var upgradeDialog = new SubscriptionUpgradeDialog(_cloudApi);
        upgradeDialog.ShowDialog();
    }
}

// Authentication service for secure credential storage
public class AuthenticationService : IAuthenticationService
{
    private readonly ILogger<AuthenticationService> _logger;
    private readonly string _credentialStorePath;
    
    public AuthenticationService(ILogger<AuthenticationService> logger)
    {
        _logger = logger;
        _credentialStorePath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "RevitAutoPlan",
            "credentials.json");
    }
    
    public async Task StoreCredentialsAsync(string accessToken, string apiKey)
    {
        try
        {
            var credentials = new
            {
                AccessToken = ProtectedData.Protect(
                    Encoding.UTF8.GetBytes(accessToken),
                    null,
                    DataProtectionScope.CurrentUser),
                ApiKey = ProtectedData.Protect(
                    Encoding.UTF8.GetBytes(apiKey),
                    null,
                    DataProtectionScope.CurrentUser),
                StoredAt = DateTime.UtcNow
            };
            
            Directory.CreateDirectory(Path.GetDirectoryName(_credentialStorePath));
            
            var json = JsonSerializer.Serialize(credentials);
            await File.WriteAllTextAsync(_credentialStorePath, json);
            
            _logger.LogInformation("Credentials stored securely");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to store credentials");
            throw;
        }
    }
    
    public async Task<(string accessToken, string apiKey)> LoadCredentialsAsync()
    {
        try
        {
            if (!File.Exists(_credentialStorePath))
                return (null, null);
            
            var json = await File.ReadAllTextAsync(_credentialStorePath);
            var credentials = JsonSerializer.Deserialize<dynamic>(json);
            
            var accessToken = Encoding.UTF8.GetString(
                ProtectedData.Unprotect(
                    credentials.AccessToken,
                    null,
                    DataProtectionScope.CurrentUser));
            
            var apiKey = Encoding.UTF8.GetString(
                ProtectedData.Unprotect(
                    credentials.ApiKey,
                    null,
                    DataProtectionScope.CurrentUser));
            
            return (accessToken, apiKey);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load credentials");
            return (null, null);
        }
    }
    
    public async Task ClearCredentialsAsync()
    {
        try
        {
            if (File.Exists(_credentialStorePath))
            {
                File.Delete(_credentialStorePath);
                _logger.LogInformation("Credentials cleared");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to clear credentials");
        }
    }
}
```

Always implement secure authentication, subscription management, comprehensive error handling, and cloud-aware patterns.

---

Revit-specific patterns:
```csharp
// Required transaction pattern
using (var transaction = new Transaction(doc, "Operation Name"))
{
    try
    {
        transaction.Start();
        // Revit API operations
        transaction.Commit();
        return Result.Succeeded;
    }
    catch (Exception ex)
    {
        transaction.RollBack();
        return Result.Failed;
    }
}

// Safe element creation
public Wall CreateWallSafely(Curve centerLine, WallType wallType, Level level)
{
    ValidateInputs(centerLine, wallType, level);
    var wall = Wall.Create(doc, centerLine, wallType.Id, level.Id, false);
    return wall ?? throw new ElementCreationException();
}

// Efficient filtering
var walls = new FilteredElementCollector(doc)
    .OfClass(typeof(Wall))
    .OfCategory(BuiltInCategory.OST_Walls)
    .OfType<Wall>()
    .Where(w => w.WallType.Id == targetTypeId)
    .ToList();
```

AI Output Execution (No Processing):
```csharp
// Execute validated AI commands - NEVER process AI directly in C#
public async Task<Result> ExecuteAILayoutAsync(string correlationId)
{
    try
    {
        // Request pre-validated layout from Python MCP Server
        var validatedLayout = await mcpServerClient.GetValidatedLayoutAsync(correlationId);
        
        if (!validatedLayout.IsApproved)
        {
            _logger.LogWarning("Layout not approved for execution", correlation_id: correlationId);
            return Result.Cancelled;
        }
        
        // Execute using Revit API
        using (var transaction = new Transaction(doc, "Execute AI Layout"))
        {
            transaction.Start();
            
            // Create walls
            foreach (var wallData in validatedLayout.Walls)
            {
                CreateWallFromData(wallData);
            }
            
            // Create doors and windows
            foreach (var doorData in validatedLayout.Doors)
            {
                CreateDoorFromData(doorData);
            }
            
            transaction.Commit();
            
            _logger.LogInformation("AI layout executed successfully",
                correlation_id: correlationId,
                element_count: validatedLayout.Walls.Count + validatedLayout.Doors.Count);
            
            return Result.Succeeded;
        }
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Failed to execute AI layout", correlation_id: correlationId);
        return Result.Failed;
    }
}
```

Proper Memory Management for Revit:
```csharp
// Correct async/memory patterns for Revit API
public class RevitResourceManager : IDisposable
{
    private readonly Document _document;
    private readonly ILogger<RevitResourceManager> _logger;
    private readonly ConcurrentBag<ElementId> _createdElements;
    private bool _disposed = false;
    
    public RevitResourceManager(Document document, ILogger<RevitResourceManager> logger)
    {
        _document = document ?? throw new ArgumentNullException(nameof(document));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        _createdElements = new ConcurrentBag<ElementId>();
    }
    
    public void TrackElement(ElementId elementId)
    {
        if (elementId != null && elementId != ElementId.InvalidElementId)
        {
            _createdElements.Add(elementId);
        }
    }
    
    public void CleanupOnError()
    {
        if (_disposed) return;
        
        try
        {
            if (_createdElements.Any())
            {
                using (var transaction = new Transaction(_document, "Cleanup Failed Operation"))
                {
                    transaction.Start();
                    
                    var elementsToDelete = _createdElements.Where(id => 
                        _document.GetElement(id) != null).ToList();
                    
                    if (elementsToDelete.Any())
                    {
                        _document.Delete(elementsToDelete);
                        _logger.LogInformation("Cleaned up {Count} elements after error", 
                            elementsToDelete.Count);
                    }
                    
                    transaction.Commit();
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to cleanup elements after error");
        }
    }
    
    public void Dispose()
    {
        if (_disposed) return;
        
        // No need for GC manipulation - let .NET handle it
        _disposed = true;
        
        _logger.LogDebug("RevitResourceManager disposed, tracked {Count} elements", 
            _createdElements.Count);
    }
}
```

Dynamo Integration as Script Engine:
```csharp
// Execute Dynamo scripts for complex geometry
public async Task<GeometryResult> ExecuteGeometricOperation(GeometryParameters parameters)
{
    var scriptPath = GenerateDynamoScript(parameters);
    
    using (var transaction = new Transaction(doc, "Dynamo Geometry"))
    {
        transaction.Start();
        var dynamoResults = await dynamoRunner.ExecuteScript(scriptPath);
        var revitElements = ConvertDynamoToRevitElements(dynamoResults);
        transaction.Commit();
        return new GeometryResult { Elements = revitElements };
    }
}
```

Database Integration:
```csharp
// Full audit trail with SQLite + Entity Framework
public class AutoPlanContext : DbContext
{
    public DbSet<Project> Projects { get; set; }
    public DbSet<AICommand> AICommands { get; set; }
    public DbSet<UserAction> UserActions { get; set; }
    public DbSet<ValidationResult> ValidationResults { get; set; }
}
```

Always wrap model changes in transactions, validate before creation, log operations.