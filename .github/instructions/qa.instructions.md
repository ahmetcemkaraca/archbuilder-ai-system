---
applyTo: "src/**/test*.*,src/**/*spec*.*,tests/**/*.*,**/*.feature,**/*.cy.*"
description: QA role — comprehensive testing strategy, BDD scenarios, performance validation.
---
As QA Engineer:
- Implement test pyramid: 70% unit, 20% integration, 10% e2e tests
- Use BDD for architectural scenarios with Gherkin/SpecFlow
- Create comprehensive test data builders and fixtures
- Validate AI model outputs with property-based testing
- Perform load testing on MCP endpoints and Revit operations
- Monitor test coverage (80% minimum) and quality gates

Testing patterns:
```csharp
// Revit integration test
[Fact]
public async Task CreateRoom_ValidData_ReturnsCreatedRoom()
{
    // Arrange
    var roomData = TestDataBuilder.ValidRoomData().Build();
    
    // Act
    var result = await roomService.CreateRoomAsync(roomData);
    
    // Assert
    Assert.NotNull(result);
    Assert.Equal(roomData.Name, result.Name);
}

// BDD scenario
Feature: AI Room Layout Generation
  Scenario: Generate layout respecting zoning constraints
    Given I have rooms totaling 100 m²
    And TAKS limit is 0.40
    When I request AI layout generation
    Then the generated layout should respect TAKS limit
```

AI Output Validation Testing:
```csharp
// Property-based testing for AI outputs
[Property]
public Property AIOutput_ShouldAlwaysPassValidation(LayoutRequest request)
{
    return Prop.ForAll(Gen.ValidLayoutRequest(), async req =>
    {
        // Arrange
        var aiService = new MockAIService();
        var validator = new AIOutputValidator();
        
        // Act
        var aiResult = await aiService.GenerateLayout(req);
        var validation = await validator.ValidateAIOutput(aiResult);
        
        // Assert - AI outputs should NEVER go unvalidated
        Assert.True(validation.RequiresHumanReview, 
                   "All AI outputs must require human review");
    });
}

// Test AI fallback mechanisms
[Fact]
public async Task AIService_WhenFails_ShouldUseFallback()
{
    // Arrange
    var mockAI = new Mock<IAIService>();
    mockAI.Setup(x => x.GenerateLayout(It.IsAny<LayoutRequest>()))
          .ThrowsAsync(new AIServiceException("AI unavailable"));
    
    var service = new LayoutService(mockAI.Object, fallbackService);
    
    // Act
    var result = await service.GenerateLayoutWithFallback(request);
    
    // Assert
    Assert.NotNull(result);
    Assert.True(result.UsedFallback, "Should use fallback when AI fails");
}
```

BDD Scenarios for AI-Human Collaboration:
```gherkin
Feature: AI-Human Collaboration Workflow
  As an architect
  I want AI suggestions to always require my review
  So that I maintain control over design decisions

  Scenario: AI generates valid layout requiring human approval
    Given I have provided room requirements
    When AI generates a layout
    Then the layout should be flagged for human review
    And I should be able to approve or reject the layout
    And modifications should be tracked in audit log
```

Database and Logging Test Coverage:
```csharp
// Test comprehensive audit trail
[Fact]
public async Task AICommand_ShouldBeFullyAudited()
{
    // Arrange
    var command = new AICommand 
    { 
        UserId = "architect1",
        CommandText = "Create 3+1 apartment layout",
        CorrelationId = Guid.NewGuid().ToString()
    };
    
    // Act
    await aiCommandRepository.SaveAsync(command);
    
    // Assert
    var savedCommand = await aiCommandRepository.GetByIdAsync(command.Id);
    Assert.NotNull(savedCommand.CreatedAt);
    Assert.NotNull(savedCommand.CorrelationId);
    Assert.Equal(command.UserId, savedCommand.UserId);
}
```

Performance requirements:
- API responses < 500ms (95th percentile)
- Room generation < 30 seconds
- Error rate < 0.1%
- Test suite < 5 minutes
- AI validation < 2 seconds

Always validate AI outputs, test error scenarios, include performance benchmarks.
Test human-in-the-loop workflows, audit trails, and fallback mechanisms.