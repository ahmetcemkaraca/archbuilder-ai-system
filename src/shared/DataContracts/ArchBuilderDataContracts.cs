using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace ArchBuilder.Shared.DataContracts
{
    /// <summary>
    /// Data contracts for ArchBuilder.AI cloud API communication
    /// Following standardized JSON schema patterns for multi-system compatibility
    /// </summary>

    #region Core Value Types

    public record Point3D
    {
        [JsonPropertyName("x")]
        public double X { get; init; }

        [JsonPropertyName("y")] 
        public double Y { get; init; }

        [JsonPropertyName("z")]
        public double Z { get; init; } = 0.0;

        public Point3D() { }

        public Point3D(double x, double y, double z = 0.0)
        {
            X = x;
            Y = y;
            Z = z;
        }

        public double DistanceTo(Point3D other)
        {
            return Math.Sqrt(Math.Pow(X - other.X, 2) + Math.Pow(Y - other.Y, 2) + Math.Pow(Z - other.Z, 2));
        }
    }

    public record AreaMeasurement
    {
        [JsonPropertyName("value")]
        [Range(0.1, double.MaxValue, ErrorMessage = "Area value must be positive")]
        public double Value { get; init; }

        [JsonPropertyName("unit")]
        public string Unit { get; init; } = "m2";

        [JsonPropertyName("converted_value")]
        public double? ConvertedValue { get; init; }
    }

    public record ElementParameter
    {
        [JsonPropertyName("name")]
        [Required]
        public string Name { get; init; } = string.Empty;

        [JsonPropertyName("value")]
        public object Value { get; init; } = string.Empty;

        [JsonPropertyName("parameter_type")]
        public string ParameterType { get; init; } = "string";

        [JsonPropertyName("is_formula")]
        public bool IsFormula { get; init; } = false;
    }

    #endregion

    #region Enumerations

    public enum MeasurementSystem
    {
        [JsonPropertyName("metric")]
        Metric,
        
        [JsonPropertyName("imperial")]
        Imperial,
        
        [JsonPropertyName("mixed")]
        Mixed
    }

    public enum BuildingType
    {
        [JsonPropertyName("residential")]
        Residential,
        
        [JsonPropertyName("office")]
        Office,
        
        [JsonPropertyName("retail")]
        Retail,
        
        [JsonPropertyName("industrial")]
        Industrial,
        
        [JsonPropertyName("educational")]
        Educational,
        
        [JsonPropertyName("healthcare")]
        Healthcare
    }

    public enum AIModel
    {
        [JsonPropertyName("gpt-4o")]
        GPT4,
        
        [JsonPropertyName("claude-3-5-sonnet")]
        Claude35Sonnet,
        
        [JsonPropertyName("gemini-2.5-flash-lite")]
        GeminiPro
    }

    public enum ValidationStatus
    {
        [JsonPropertyName("valid")]
        Valid,
        
        [JsonPropertyName("invalid_but_correctable")]
        InvalidButCorrectable,
        
        [JsonPropertyName("requires_manual_review")]
        RequiresManualReview,
        
        [JsonPropertyName("rejected")]
        Rejected
    }

    public enum ValidationSeverity
    {
        [JsonPropertyName("info")]
        Info,
        
        [JsonPropertyName("warning")]
        Warning,
        
        [JsonPropertyName("error")]
        Error,
        
        [JsonPropertyName("critical")]
        Critical
    }

    #endregion

    #region Validation Models

    public record ValidationError
    {
        [JsonPropertyName("code")]
        [Required]
        [RegularExpression(@"^[A-Z]{3,4}_\d{3}$", ErrorMessage = "Code must match pattern XXXX_000")]
        public string Code { get; init; } = string.Empty;

        [JsonPropertyName("message")]
        [Required]
        public string Message { get; init; } = string.Empty;

        [JsonPropertyName("property")]
        public string? Property { get; init; }

        [JsonPropertyName("attempted_value")]
        public object? AttemptedValue { get; init; }

        [JsonPropertyName("severity")]
        public ValidationSeverity Severity { get; init; } = ValidationSeverity.Error;

        [JsonPropertyName("suggested_fixes")]
        public List<string> SuggestedFixes { get; init; } = new();
    }

    public record ValidationResult
    {
        [JsonPropertyName("correlation_id")]
        [Required]
        public string CorrelationId { get; init; } = string.Empty;

        [JsonPropertyName("status")]
        public ValidationStatus Status { get; init; }

        [JsonPropertyName("errors")]
        public List<ValidationError> Errors { get; init; } = new();

        [JsonPropertyName("warnings")]
        public List<ValidationError> Warnings { get; init; } = new();

        [JsonPropertyName("confidence_score")]
        [Range(0.0, 1.0)]
        public double ConfidenceScore { get; init; }

        [JsonPropertyName("requires_human_review")]
        public bool RequiresHumanReview { get; init; }

        [JsonPropertyName("validated_at")]
        public DateTime ValidatedAt { get; init; } = DateTime.UtcNow;
    }

    #endregion

    #region AI Processing Models

    public record AIOptions
    {
        [JsonPropertyName("model")]
        public AIModel Model { get; init; } = AIModel.GeminiPro;

        [JsonPropertyName("temperature")]
        [Range(0.0, 2.0)]
        public double Temperature { get; init; } = 0.1;

        [JsonPropertyName("max_tokens")]
        [Range(100, 32768)]
        public int MaxTokens { get; init; } = 8192;

        [JsonPropertyName("confidence_threshold")]
        [Range(0.0, 1.0)]
        public double ConfidenceThreshold { get; init; } = 0.7;
    }

    public record AIMetadata
    {
        [JsonPropertyName("model_used")]
        public AIModel ModelUsed { get; init; }

        [JsonPropertyName("confidence_score")]
        [Range(0.0, 1.0)]
        public double ConfidenceScore { get; init; }

        [JsonPropertyName("processing_time_ms")]
        public int ProcessingTimeMs { get; init; }

        [JsonPropertyName("token_count")]
        public int TokenCount { get; init; }

        [JsonPropertyName("provider")]
        public string Provider { get; init; } = string.Empty;

        [JsonPropertyName("prompt_version")]
        public string PromptVersion { get; init; } = "1.0";
    }

    public record AICommandRequest
    {
        [JsonPropertyName("correlation_id")]
        public string CorrelationId { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("timestamp")]
        public DateTime Timestamp { get; init; } = DateTime.UtcNow;

        [JsonPropertyName("user_prompt")]
        [Required]
        [StringLength(5000, MinimumLength = 1)]
        public string UserPrompt { get; init; } = string.Empty;

        [JsonPropertyName("options")]
        public AIOptions? Options { get; init; }

        [JsonPropertyName("context")]
        public Dictionary<string, object>? Context { get; init; }
    }

    public record AICommandResponse
    {
        [JsonPropertyName("correlation_id")]
        public string CorrelationId { get; init; } = string.Empty;

        [JsonPropertyName("timestamp")]
        public DateTime Timestamp { get; init; } = DateTime.UtcNow;

        [JsonPropertyName("status")]
        public string Status { get; init; } = string.Empty; // success, error, requires_review

        [JsonPropertyName("data")]
        public object? Data { get; init; }

        [JsonPropertyName("errors")]
        public List<ValidationError>? Errors { get; init; }

        [JsonPropertyName("confidence")]
        [Range(0.0, 1.0)]
        public double? Confidence { get; init; }

        [JsonPropertyName("requires_human_review")]
        public bool RequiresHumanReview { get; init; }

        [JsonPropertyName("ai_metadata")]
        public AIMetadata? AIMetadata { get; init; }
    }

    #endregion

    #region Architectural Element Definitions

    public record WallDefinition
    {
        [JsonPropertyName("id")]
        public string Id { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("start_point")]
        [Required]
        public Point3D StartPoint { get; init; } = new();

        [JsonPropertyName("end_point")]
        [Required]
        public Point3D EndPoint { get; init; } = new();

        [JsonPropertyName("height_mm")]
        [Range(1000, 6000, ErrorMessage = "Wall height must be between 1000mm and 6000mm")]
        public double HeightMm { get; init; }

        [JsonPropertyName("wall_type_name")]
        public string WallTypeName { get; init; } = "Generic - 200mm";

        [JsonPropertyName("level_name")]
        public string LevelName { get; init; } = "Level 1";

        [JsonPropertyName("parameters")]
        public List<ElementParameter> Parameters { get; init; } = new();
    }

    public record DoorDefinition
    {
        [JsonPropertyName("id")]
        public string Id { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("host_wall_id")]
        [Required]
        public string HostWallId { get; init; } = string.Empty;

        [JsonPropertyName("position_ratio")]
        [Range(0.1, 0.9, ErrorMessage = "Position ratio must be between 0.1 and 0.9")]
        public double PositionRatio { get; init; }

        [JsonPropertyName("family_name")]
        public string FamilyName { get; init; } = "Single-Flush";

        [JsonPropertyName("type_name")]
        public string TypeName { get; init; } = "0915 x 2134mm";

        [JsonPropertyName("width_mm")]
        [Range(600, 2000, ErrorMessage = "Door width must be between 600mm and 2000mm")]
        public double WidthMm { get; init; }

        [JsonPropertyName("height_mm")]
        [Range(1800, 2500, ErrorMessage = "Door height must be between 1800mm and 2500mm")]
        public double HeightMm { get; init; }

        [JsonPropertyName("parameters")]
        public List<ElementParameter> Parameters { get; init; } = new();
    }

    public record WindowDefinition
    {
        [JsonPropertyName("id")]
        public string Id { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("host_wall_id")]
        [Required]
        public string HostWallId { get; init; } = string.Empty;

        [JsonPropertyName("position_ratio")]
        [Range(0.1, 0.9)]
        public double PositionRatio { get; init; }

        [JsonPropertyName("family_name")]
        public string FamilyName { get; init; } = "Fixed";

        [JsonPropertyName("type_name")]
        public string TypeName { get; init; } = "1220 x 1220mm";

        [JsonPropertyName("width_mm")]
        [Range(400, 3000)]
        public double WidthMm { get; init; }

        [JsonPropertyName("height_mm")]
        [Range(400, 2500)]
        public double HeightMm { get; init; }

        [JsonPropertyName("sill_height_mm")]
        [Range(200, 1500)]
        public double SillHeightMm { get; init; } = 900;

        [JsonPropertyName("parameters")]
        public List<ElementParameter> Parameters { get; init; } = new();
    }

    public record RoomDefinition
    {
        [JsonPropertyName("id")]
        public string Id { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("name")]
        [Required]
        public string Name { get; init; } = string.Empty;

        [JsonPropertyName("localized_names")]
        public Dictionary<string, string> LocalizedNames { get; init; } = new();

        [JsonPropertyName("area_m2")]
        [Required]
        public AreaMeasurement AreaM2 { get; init; } = new() { Value = 0, Unit = "m2" };

        [JsonPropertyName("boundary_walls")]
        public List<string> BoundaryWalls { get; init; } = new();

        [JsonPropertyName("room_type")]
        public string RoomType { get; init; } = "Generic";

        [JsonPropertyName("level_name")]
        public string LevelName { get; init; } = "Level 1";

        [JsonPropertyName("parameters")]
        public List<ElementParameter> Parameters { get; init; } = new();
    }

    public record FloorDefinition
    {
        [JsonPropertyName("id")]
        public string Id { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("boundary_points")]
        [MinLength(3, ErrorMessage = "Floor must have at least 3 boundary points")]
        public List<Point3D> BoundaryPoints { get; init; } = new();

        [JsonPropertyName("floor_type_name")]
        public string FloorTypeName { get; init; } = "Generic - 150mm";

        [JsonPropertyName("level_name")]
        public string LevelName { get; init; } = "Level 1";

        [JsonPropertyName("structural")]
        public bool Structural { get; init; } = true;

        [JsonPropertyName("parameters")]
        public List<ElementParameter> Parameters { get; init; } = new();
    }

    #endregion

    #region Project Models

    public record RoomRequirement
    {
        [JsonPropertyName("name")]
        [Required]
        public string Name { get; init; } = string.Empty;

        [JsonPropertyName("area_m2")]
        [Required]
        public AreaMeasurement AreaM2 { get; init; } = new() { Value = 0, Unit = "m2" };

        [JsonPropertyName("preferred_width")]
        public double? PreferredWidth { get; init; }

        [JsonPropertyName("preferred_height")]
        public double? PreferredHeight { get; init; }

        [JsonPropertyName("adjacent_to_rooms")]
        public List<string> AdjacentToRooms { get; init; } = new();

        [JsonPropertyName("required_features")]
        public List<string> RequiredFeatures { get; init; } = new();

        [JsonPropertyName("natural_light_requirement")]
        public string NaturalLightRequirement { get; init; } = "medium"; // high, medium, low, none
    }

    public record RoomProgram
    {
        [JsonPropertyName("correlation_id")]
        public string CorrelationId { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("rooms")]
        [Required]
        [MinLength(1, ErrorMessage = "At least one room is required")]
        public List<RoomRequirement> Rooms { get; init; } = new();

        [JsonPropertyName("total_area_m2")]
        [Required]
        public AreaMeasurement TotalAreaM2 { get; init; } = new() { Value = 0, Unit = "m2" };

        [JsonPropertyName("building_type")]
        public BuildingType BuildingType { get; init; } = BuildingType.Residential;

        [JsonPropertyName("measurement_system")]
        public MeasurementSystem MeasurementSystem { get; init; } = MeasurementSystem.Metric;
    }

    public record LayoutResult
    {
        [JsonPropertyName("correlation_id")]
        public string CorrelationId { get; init; } = string.Empty;

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; init; } = DateTime.UtcNow;

        [JsonPropertyName("walls")]
        [Required]
        [MinLength(1, ErrorMessage = "Layout must have at least one wall")]
        public List<WallDefinition> Walls { get; init; } = new();

        [JsonPropertyName("doors")]
        public List<DoorDefinition> Doors { get; init; } = new();

        [JsonPropertyName("windows")]
        public List<WindowDefinition> Windows { get; init; } = new();

        [JsonPropertyName("rooms")]
        public List<RoomDefinition> Rooms { get; init; } = new();

        [JsonPropertyName("floors")]
        public List<FloorDefinition> Floors { get; init; } = new();

        [JsonPropertyName("ai_metadata")]
        public AIMetadata? AIMetadata { get; init; }

        [JsonPropertyName("validation")]
        public ValidationResult? Validation { get; init; }

        [JsonPropertyName("status")]
        public string Status { get; init; } = "completed"; // pending, processing, completed, failed
    }

    #endregion

    #region Global Building Information

    public record GlobalBuildingInfo
    {
        [JsonPropertyName("id")]
        public string Id { get; init; } = Guid.NewGuid().ToString();

        [JsonPropertyName("region")]
        public string Region { get; init; } = string.Empty;

        [JsonPropertyName("country")]
        [Required]
        public string Country { get; init; } = string.Empty;

        [JsonPropertyName("locale")]
        [Required]
        [RegularExpression(@"^[a-z]{2}-[A-Z]{2}$", ErrorMessage = "Locale must be in format 'en-US'")]
        public string Locale { get; init; } = "en-US";

        [JsonPropertyName("building_type")]
        public BuildingType BuildingType { get; init; }

        [JsonPropertyName("measurement_system")]
        public MeasurementSystem MeasurementSystem { get; init; } = MeasurementSystem.Metric;

        [JsonPropertyName("total_area")]
        [Required]
        public AreaMeasurement TotalArea { get; init; } = new() { Value = 0, Unit = "m2" };

        [JsonPropertyName("applicable_codes")]
        public List<string> ApplicableCodes { get; init; } = new();

        [JsonPropertyName("zone_name")]
        public string ZoneName { get; init; } = string.Empty;

        [JsonPropertyName("occupancy_class")]
        public string OccupancyClass { get; init; } = string.Empty;
    }

    #endregion

    #region API Response Models

    public record ApiResponse<T>
    {
        [JsonPropertyName("success")]
        public bool Success { get; init; }

        [JsonPropertyName("data")]
        public T? Data { get; init; }

        [JsonPropertyName("errors")]
        public List<string> Errors { get; init; } = new();

        [JsonPropertyName("correlation_id")]
        public string CorrelationId { get; init; } = string.Empty;

        [JsonPropertyName("timestamp")]
        public DateTime Timestamp { get; init; } = DateTime.UtcNow;
    }

    public record ErrorResponse
    {
        [JsonPropertyName("error")]
        public string Error { get; init; } = string.Empty;

        [JsonPropertyName("message")]
        public string Message { get; init; } = string.Empty;

        [JsonPropertyName("correlation_id")]
        public string CorrelationId { get; init; } = string.Empty;

        [JsonPropertyName("timestamp")]
        public DateTime Timestamp { get; init; } = DateTime.UtcNow;
    }

    #endregion

    #region Constants

    public static class DataConstants
    {
        // Size constraints (in millimeters)
        public const double MIN_WALL_LENGTH_MM = 100;
        public const double MAX_WALL_LENGTH_MM = 50000;
        public const double MIN_WALL_HEIGHT_MM = 1000;
        public const double MAX_WALL_HEIGHT_MM = 6000;
        
        public const double MIN_DOOR_WIDTH_MM = 600;
        public const double MAX_DOOR_WIDTH_MM = 2000;
        public const double MIN_DOOR_HEIGHT_MM = 1800;
        public const double MAX_DOOR_HEIGHT_MM = 2500;
        
        public const double MIN_ROOM_AREA_M2 = 3.0;
        public const double MAX_ROOM_AREA_M2 = 1000.0;
        
        // AI model constraints
        public const double MIN_CONFIDENCE_THRESHOLD = 0.7;
        public const double HIGH_CONFIDENCE_THRESHOLD = 0.9;
        
        // Default values
        public const string DEFAULT_WALL_TYPE = "Generic - 200mm";
        public const string DEFAULT_DOOR_TYPE = "Single-Flush";
        public const string DEFAULT_WINDOW_TYPE = "Fixed";
    }

    #endregion
}