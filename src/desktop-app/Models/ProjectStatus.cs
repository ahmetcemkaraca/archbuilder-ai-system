using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;

namespace ArchBuilder.Models
{
    /// <summary>
    /// Comprehensive project status tracking model
    /// Following ArchBuilder.AI workflow standards for AI-human collaboration
    /// </summary>
    public class ProjectStatusInfo : INotifyPropertyChanged
    {
        private ProjectPhase _currentPhase = ProjectPhase.Initialization;
        private double _overallProgress = 0.0;
        private DateTime _lastUpdate = DateTime.Now;

        /// <summary>
        /// Unique status tracking identifier
        /// </summary>
        public string StatusId { get; set; } = Guid.NewGuid().ToString();

        /// <summary>
        /// Associated project correlation ID
        /// </summary>
        public string ProjectCorrelationId { get; set; } = string.Empty;

        /// <summary>
        /// Current project phase
        /// </summary>
        public ProjectPhase CurrentPhase
        {
            get => _currentPhase;
            set
            {
                if (_currentPhase != value)
                {
                    _currentPhase = value;
                    OnPropertyChanged(nameof(CurrentPhase));
                    OnPropertyChanged(nameof(CurrentPhaseDisplayName));
                    UpdateLastUpdate();
                }
            }
        }

        /// <summary>
        /// Overall project progress (0-100)
        /// </summary>
        public double OverallProgress
        {
            get => _overallProgress;
            set
            {
                var clampedValue = Math.Max(0, Math.Min(100, value));
                if (Math.Abs(_overallProgress - clampedValue) > 0.01)
                {
                    _overallProgress = clampedValue;
                    OnPropertyChanged(nameof(OverallProgress));
                    OnPropertyChanged(nameof(OverallProgressDisplayText));
                    UpdateLastUpdate();
                }
            }
        }

        /// <summary>
        /// Detailed phase progress tracking
        /// </summary>
        public List<PhaseProgress> PhaseProgresses { get; set; } = new();

        /// <summary>
        /// Active tasks and milestones
        /// </summary>
        public List<ProjectTask> ActiveTasks { get; set; } = new();

        /// <summary>
        /// Completed tasks history
        /// </summary>
        public List<ProjectTask> CompletedTasks { get; set; } = new();

        /// <summary>
        /// Current status message
        /// </summary>
        public string StatusMessage { get; set; } = "Project initialized";

        /// <summary>
        /// Last status update timestamp
        /// </summary>
        public DateTime LastUpdate
        {
            get => _lastUpdate;
            private set
            {
                if (_lastUpdate != value)
                {
                    _lastUpdate = value;
                    OnPropertyChanged(nameof(LastUpdate));
                    OnPropertyChanged(nameof(LastUpdateDisplayText));
                }
            }
        }

        /// <summary>
        /// Project timeline estimates
        /// </summary>
        public ProjectTimeline Timeline { get; set; } = new();

        /// <summary>
        /// Quality assurance and validation tracking
        /// </summary>
        public QualityAssurance QA { get; set; } = new();

        /// <summary>
        /// AI processing status and history
        /// </summary>
        public AIProcessingStatus AIStatus { get; set; } = new();

        /// <summary>
        /// Resource utilization tracking
        /// </summary>
        public ResourceUtilization Resources { get; set; } = new();

        /// <summary>
        /// Risk assessment and mitigation
        /// </summary>
        public List<ProjectRisk> Risks { get; set; } = new();

        // Display properties for UI binding
        public string CurrentPhaseDisplayName => CurrentPhase switch
        {
            ProjectPhase.Initialization => "Initialization",
            ProjectPhase.RequirementsGathering => "Requirements Gathering",
            ProjectPhase.ConceptualDesign => "Conceptual Design",
            ProjectPhase.SchematicDesign => "Schematic Design", 
            ProjectPhase.DesignDevelopment => "Design Development",
            ProjectPhase.ConstructionDocuments => "Construction Documents",
            ProjectPhase.Review => "Review & Approval",
            ProjectPhase.Revision => "Revision",
            ProjectPhase.Finalization => "Finalization",
            ProjectPhase.Delivery => "Delivery",
            ProjectPhase.PostDelivery => "Post-Delivery",
            _ => "Unknown"
        };

        public string OverallProgressDisplayText => $"{OverallProgress:F1}%";

        public string LastUpdateDisplayText => LastUpdate.ToString("MMM dd, yyyy HH:mm");

        public int ActiveTasksCount => ActiveTasks?.Count ?? 0;

        public int CompletedTasksCount => CompletedTasks?.Count ?? 0;

        public int TotalTasksCount => ActiveTasksCount + CompletedTasksCount;

        public bool HasActiveTasks => ActiveTasksCount > 0;

        public bool HasRisks => Risks?.Any(r => r.Severity >= RiskSeverity.Medium) ?? false;

        public string NextMilestone => GetNextMilestone();

        public TimeSpan EstimatedTimeRemaining => Timeline?.EstimatedCompletion?.Subtract(DateTime.Now) ?? TimeSpan.Zero;

        public event PropertyChangedEventHandler? PropertyChanged;

        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        private void UpdateLastUpdate()
        {
            LastUpdate = DateTime.Now;
        }

        /// <summary>
        /// Initializes default phase progresses
        /// </summary>
        public void InitializePhaseProgresses()
        {
            if (PhaseProgresses.Count == 0)
            {
                foreach (ProjectPhase phase in Enum.GetValues<ProjectPhase>())
                {
                    PhaseProgresses.Add(new PhaseProgress
                    {
                        Phase = phase,
                        Progress = phase == ProjectPhase.Initialization ? 100.0 : 0.0,
                        Status = phase == ProjectPhase.Initialization ? PhaseStatus.Completed : PhaseStatus.NotStarted
                    });
                }
            }
        }

        /// <summary>
        /// Advances to the next project phase
        /// </summary>
        public void AdvanceToNextPhase()
        {
            var currentPhaseProgress = PhaseProgresses.FirstOrDefault(p => p.Phase == CurrentPhase);
            if (currentPhaseProgress != null)
            {
                currentPhaseProgress.Status = PhaseStatus.Completed;
                currentPhaseProgress.Progress = 100.0;
                currentPhaseProgress.CompletedAt = DateTime.Now;
            }

            var nextPhase = (ProjectPhase)((int)CurrentPhase + 1);
            if (Enum.IsDefined(typeof(ProjectPhase), nextPhase))
            {
                CurrentPhase = nextPhase;
                var nextPhaseProgress = PhaseProgresses.FirstOrDefault(p => p.Phase == nextPhase);
                if (nextPhaseProgress != null)
                {
                    nextPhaseProgress.Status = PhaseStatus.InProgress;
                    nextPhaseProgress.StartedAt = DateTime.Now;
                }
            }

            RecalculateOverallProgress();
        }

        /// <summary>
        /// Recalculates overall progress based on phase progress
        /// </summary>
        public void RecalculateOverallProgress()
        {
            if (PhaseProgresses.Count == 0) return;

            var totalProgress = PhaseProgresses.Sum(p => p.Progress);
            OverallProgress = totalProgress / PhaseProgresses.Count;
        }

        /// <summary>
        /// Adds a new task to the project
        /// </summary>
        public void AddTask(string name, string description, TaskPriority priority = TaskPriority.Medium, DateTime? dueDate = null)
        {
            ActiveTasks.Add(new ProjectTask
            {
                Name = name,
                Description = description,
                Priority = priority,
                DueDate = dueDate,
                CreatedAt = DateTime.Now,
                Status = TaskStatus.Todo
            });
            OnPropertyChanged(nameof(ActiveTasksCount));
            OnPropertyChanged(nameof(HasActiveTasks));
        }

        /// <summary>
        /// Completes a task
        /// </summary>
        public void CompleteTask(string taskId)
        {
            var task = ActiveTasks.FirstOrDefault(t => t.TaskId == taskId);
            if (task != null)
            {
                task.Status = TaskStatus.Completed;
                task.CompletedAt = DateTime.Now;
                ActiveTasks.Remove(task);
                CompletedTasks.Add(task);
                
                OnPropertyChanged(nameof(ActiveTasksCount));
                OnPropertyChanged(nameof(CompletedTasksCount));
                OnPropertyChanged(nameof(HasActiveTasks));
                UpdateLastUpdate();
            }
        }

        /// <summary>
        /// Gets the next milestone description
        /// </summary>
        private string GetNextMilestone()
        {
            var nextPhase = PhaseProgresses
                .Where(p => p.Status == PhaseStatus.NotStarted)
                .OrderBy(p => (int)p.Phase)
                .FirstOrDefault();

            return nextPhase?.Phase switch
            {
                ProjectPhase.RequirementsGathering => "Complete Requirements Analysis",
                ProjectPhase.ConceptualDesign => "Finalize Concept Design",
                ProjectPhase.SchematicDesign => "Complete Schematic Design",
                ProjectPhase.DesignDevelopment => "Develop Detailed Design",
                ProjectPhase.ConstructionDocuments => "Prepare Construction Documents",
                ProjectPhase.Review => "Submit for Review",
                ProjectPhase.Finalization => "Finalize Documentation",
                ProjectPhase.Delivery => "Deliver Project",
                _ => "No upcoming milestones"
            };
        }
    }

    /// <summary>
    /// Project phase enumeration for workflow tracking
    /// </summary>
    public enum ProjectPhase
    {
        Initialization = 0,
        RequirementsGathering = 1,
        ConceptualDesign = 2,
        SchematicDesign = 3,
        DesignDevelopment = 4,
        ConstructionDocuments = 5,
        Review = 6,
        Revision = 7,
        Finalization = 8,
        Delivery = 9,
        PostDelivery = 10
    }

    /// <summary>
    /// Individual phase progress tracking
    /// </summary>
    public class PhaseProgress
    {
        public ProjectPhase Phase { get; set; }
        public double Progress { get; set; } = 0.0;
        public PhaseStatus Status { get; set; } = PhaseStatus.NotStarted;
        public DateTime? StartedAt { get; set; }
        public DateTime? CompletedAt { get; set; }
        public List<string> Deliverables { get; set; } = new();
        public List<string> Issues { get; set; } = new();
    }

    /// <summary>
    /// Phase status enumeration
    /// </summary>
    public enum PhaseStatus
    {
        NotStarted,
        InProgress,
        OnHold,
        Completed,
        Skipped
    }

    /// <summary>
    /// Project task model for detailed tracking
    /// </summary>
    public class ProjectTask
    {
        public string TaskId { get; set; } = Guid.NewGuid().ToString();
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public TaskStatus Status { get; set; } = TaskStatus.Todo;
        public TaskPriority Priority { get; set; } = TaskPriority.Medium;
        public DateTime CreatedAt { get; set; } = DateTime.Now;
        public DateTime? DueDate { get; set; }
        public DateTime? StartedAt { get; set; }
        public DateTime? CompletedAt { get; set; }
        public string? AssignedTo { get; set; }
        public double EstimatedHours { get; set; }
        public double ActualHours { get; set; }
        public List<string> Dependencies { get; set; } = new();
        public List<string> Tags { get; set; } = new();
    }

    /// <summary>
    /// Task status enumeration
    /// </summary>
    public enum TaskStatus
    {
        Todo,
        InProgress,
        UnderReview,
        Blocked,
        Completed,
        Cancelled
    }

    /// <summary>
    /// Task priority levels
    /// </summary>
    public enum TaskPriority
    {
        Low,
        Medium,
        High,
        Critical
    }

    /// <summary>
    /// Project timeline and estimates
    /// </summary>
    public class ProjectTimeline
    {
        public DateTime? EstimatedStart { get; set; }
        public DateTime? ActualStart { get; set; }
        public DateTime? EstimatedCompletion { get; set; }
        public DateTime? ActualCompletion { get; set; }
        public List<ProjectMilestone> Milestones { get; set; } = new();
        public double BufferTimePercentage { get; set; } = 20.0; // 20% buffer
    }

    /// <summary>
    /// Project milestone tracking
    /// </summary>
    public class ProjectMilestone
    {
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public DateTime TargetDate { get; set; }
        public DateTime? ActualDate { get; set; }
        public bool IsCompleted { get; set; }
        public List<string> Deliverables { get; set; } = new();
    }

    /// <summary>
    /// Quality assurance tracking
    /// </summary>
    public class QualityAssurance
    {
        public List<QACheckpoint> Checkpoints { get; set; } = new();
        public double QualityScore { get; set; } = 0.0;
        public int TotalChecks { get; set; }
        public int PassedChecks { get; set; }
        public int FailedChecks { get; set; }
        public List<string> QualityIssues { get; set; } = new();
    }

    /// <summary>
    /// Quality assurance checkpoint
    /// </summary>
    public class QACheckpoint
    {
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public QAStatus Status { get; set; } = QAStatus.Pending;
        public DateTime? CheckedAt { get; set; }
        public string? CheckedBy { get; set; }
        public List<string> Issues { get; set; } = new();
    }

    /// <summary>
    /// QA checkpoint status
    /// </summary>
    public enum QAStatus
    {
        Pending,
        Passed,
        Failed,
        Skipped
    }

    /// <summary>
    /// AI processing status and metrics
    /// </summary>
    public class AIProcessingStatus
    {
        public DateTime? LastAIProcessing { get; set; }
        public string? CurrentAITask { get; set; }
        public double AIProgress { get; set; } = 0.0;
        public List<AIProcessingEvent> ProcessingHistory { get; set; } = new();
        public double AverageConfidenceScore { get; set; } = 0.0;
        public int TotalAIRequests { get; set; }
        public int SuccessfulAIRequests { get; set; }
        public int FailedAIRequests { get; set; }
        public bool RequiresHumanReview { get; set; }
    }

    /// <summary>
    /// AI processing event for history tracking
    /// </summary>
    public class AIProcessingEvent
    {
        public DateTime Timestamp { get; set; } = DateTime.Now;
        public string EventType { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public double ConfidenceScore { get; set; }
        public bool Successful { get; set; }
        public string? ErrorMessage { get; set; }
    }

    /// <summary>
    /// Resource utilization tracking
    /// </summary>
    public class ResourceUtilization
    {
        public double CpuUsagePercentage { get; set; }
        public double MemoryUsageMB { get; set; }
        public double DiskUsageGB { get; set; }
        public double NetworkUsageMB { get; set; }
        public int ActiveConnections { get; set; }
        public DateTime LastResourceUpdate { get; set; } = DateTime.Now;
    }

    /// <summary>
    /// Project risk tracking and mitigation
    /// </summary>
    public class ProjectRisk
    {
        public string RiskId { get; set; } = Guid.NewGuid().ToString();
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public RiskSeverity Severity { get; set; } = RiskSeverity.Low;
        public double Probability { get; set; } = 0.0; // 0-1
        public double Impact { get; set; } = 0.0; // 0-1
        public RiskStatus Status { get; set; } = RiskStatus.Identified;
        public string? MitigationPlan { get; set; }
        public DateTime IdentifiedAt { get; set; } = DateTime.Now;
        public DateTime? MitigatedAt { get; set; }
    }

    /// <summary>
    /// Risk severity levels
    /// </summary>
    public enum RiskSeverity
    {
        Low,
        Medium,
        High,
        Critical
    }

    /// <summary>
    /// Risk status tracking
    /// </summary>
    public enum RiskStatus
    {
        Identified,
        Analyzing,
        Mitigating,
        Resolved,
        Accepted
    }
}