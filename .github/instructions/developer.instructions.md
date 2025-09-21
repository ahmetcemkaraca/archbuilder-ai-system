---
applyTo: "src/revit-plugin/**/*.cs,src/mcp-server/**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: Developer role — Revit vertical slices, test-first development, trio workflow.
---
As Developer:
- Follow trio workflow: update `requirements.md`, `design.md`, `tasks.md` before coding
- Implement vertical slices with 80%+ test coverage
- Use test-first development with Arrange-Act-Assert pattern
- Apply clean code principles and SOLID design patterns
- Enforce security defaults: input validation, output encoding, no secrets in code
- Keep CI pipeline green; provide rollback instructions
- **NO C# AI PROCESSING**: All AI logic must be in Python MCP Server only

Code quality standards:
- **C# Revit Plugin**: PascalCase classes, camelCase variables, XML documentation
- **Python MCP Server**: snake_case, type hints, FastAPI security patterns  
- **Transaction Management**: Every Revit model change in proper Transaction
- **Error Handling**: Specific exceptions, structured logging, graceful degradation

Essential patterns:
```csharp
// Revit API pattern
using (var transaction = new Transaction(doc, "AI Operation"))
{
    transaction.Start();
    // Model changes here - NO AI processing
    transaction.Commit();
}
```

```python
# HTTP REST API pattern (not MCP protocol)
@limiter.limit("5/minute")
async def generate_layout(request: Request, data: LayoutRequest):
    # ALL AI processing happens here
    return await ai_service.process_with_fallback(data)
```

AI Command Execution Pattern (C# executes only):
```csharp
// C# executes pre-validated AI commands - NO AI processing
public async Task<Result> ExecuteValidatedAICommand(string correlationId)
{
    try
    {
        // Get pre-validated, human-approved layout from Python server
        var validatedLayout = await httpClient.GetAsync($"/api/layouts/{correlationId}/approved");
        
        if (validatedLayout == null || !validatedLayout.IsApproved)
        {
            logger.LogWarning("No approved layout found for execution", correlationId);
            return Result.Cancelled;
        }
        
        // Execute using Revit API only
        using (var transaction = new Transaction(doc, "Execute AI Layout"))
        {
            transaction.Start();
            
            var executor = new LayoutExecutor(doc, logger);
            await executor.CreateElementsFromLayout(validatedLayout);
            
            transaction.Commit();
            
            logger.LogInformation("AI layout executed successfully", correlationId);
            return Result.Succeeded;
        }
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Failed to execute AI layout", correlationId);
        return Result.Failed;
    }
}
```

Realistic Development Workflow:
```python
# Python MCP Server - ALL AI processing
class AILayoutService:
    async def generate_layout_with_realistic_timing(
        self, 
        request: LayoutRequest,
        correlation_id: str
    ) -> LayoutResult:
        """Generate layout with realistic timing (10-30s)"""
        
        progress = ProgressTracker(correlation_id)
        
        try:
            # Stage 1: Process requirements (2s)
            await progress.update_stage("Processing requirements", 0.1)
            requirements = await self.process_requirements(request)
            await asyncio.sleep(2)  # Realistic processing time
            
            # Stage 2: Generate with AI model (15s)
            await progress.update_stage("Generating with AI", 0.3)
            ai_result = await self.call_ai_model(requirements)
            await asyncio.sleep(15)  # AI models take time
            
            # Stage 3: Validate output (5s)
            await progress.update_stage("Validating output", 0.7)
            validation = await self.validate_output(ai_result)
            await asyncio.sleep(5)
            
            # Stage 4: Prepare for review (3s)
            await progress.update_stage("Preparing for review", 0.9)
            layout_result = await self.prepare_for_human_review(ai_result, validation)
            await asyncio.sleep(3)
            
            await progress.complete()
            return layout_result
            
        except Exception as ex:
            await progress.fail(str(ex))
            # Use rule-based fallback
            return await self.generate_fallback_layout(request)
```
    logger.Information("AI command processed: {Command} -> {Result}", 
                      command, result);
    return result;
}
```

Dynamo Integration:
```csharp
// Use Dynamo as script engine, not replacement
public void ExecuteGeometricOperation(GeometryParams parameters)
{
    var dynamoScript = scriptGenerator.CreateDynamoScript(parameters);
    using (var transaction = new Transaction(doc, "Dynamo Geometry"))
    {
        transaction.Start();
        var results = dynamoRunner.Execute(dynamoScript);
        ApplyResultsToRevit(results);
        transaction.Commit();
    }
}
```

Database & Logging Setup:
```csharp
// Comprehensive logging from day one
services.AddSerilog(config => config
    .WriteTo.File("logs/revit-autoplan-.log", 
                  rollingInterval: RollingInterval.Day)
    .WriteTo.Console()
    .Enrich.WithCorrelationId());

// Database with full audit trail
services.AddDbContext<AutoPlanContext>(options => 
    options.UseSqlite(connectionString)
           .EnableSensitiveDataLogging(isDevelopment));
```

Never ship without tests, never hardcode secrets, always validate inputs.
Update `tasks.md` progress and `CHANGELOG.md` entries.To: "**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.py,**/*.cs,**/*.kt,**/*.swift,**/*.rb,**/*.go"