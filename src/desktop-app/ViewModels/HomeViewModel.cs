using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using System.Windows.Input;
using ArchBuilder.Core;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.ViewModels
{
    /// <summary>
    /// Ana sayfa ViewModel'i - Dashboard ve genel bakış
    /// </summary>
    public class HomeViewModel : INotifyPropertyChanged
    {
        private readonly ILogger<HomeViewModel> _logger;
        private readonly IProjectService _projectService;
        private readonly ICloudApiService _cloudApiService;
        
        private bool _isLoading;
        private string _welcomeMessage;
        private string _apiStatus;
        private int _recentProjectsCount;
        private DateTime _lastSyncTime;

        public HomeViewModel()
        {
            _logger = ServiceLocator.GetService<ILogger<HomeViewModel>>();
            _projectService = ServiceLocator.GetService<IProjectService>();
            _cloudApiService = ServiceLocator.GetService<ICloudApiService>();

            // Initialize commands
            InitializeCommands();
            
            // Set initial values
            WelcomeMessage = "ArchBuilder.AI'ye Hoş Geldiniz";
            ApiStatus = "Bağlanıyor...";
            LastSyncTime = DateTime.Now;

            RecentProjects = new ObservableCollection<Project>();
            QuickActions = new ObservableCollection<QuickAction>();
            
            // Initialize quick actions
            InitializeQuickActions();
        }

        #region Properties

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public string WelcomeMessage
        {
            get => _welcomeMessage;
            set => SetProperty(ref _welcomeMessage, value);
        }

        public string ApiStatus
        {
            get => _apiStatus;
            set => SetProperty(ref _apiStatus, value);
        }

        public int RecentProjectsCount
        {
            get => _recentProjectsCount;
            set => SetProperty(ref _recentProjectsCount, value);
        }

        public DateTime LastSyncTime
        {
            get => _lastSyncTime;
            set => SetProperty(ref _lastSyncTime, value);
        }

        public ObservableCollection<Project> RecentProjects { get; }
        public ObservableCollection<QuickAction> QuickActions { get; }

        #endregion

        #region Commands

        public ICommand CreateNewProjectCommand { get; private set; }
        public ICommand OpenProjectCommand { get; private set; }
        public ICommand StartAIDesignCommand { get; private set; }
        public ICommand AnalyzeProjectCommand { get; private set; }
        public ICommand RefreshDashboardCommand { get; private set; }

        #endregion

        #region Initialization

        private void InitializeCommands()
        {
            CreateNewProjectCommand = new RelayCommand(async () => await CreateNewProject());
            OpenProjectCommand = new RelayCommand<Project>(async (project) => await OpenProject(project));
            StartAIDesignCommand = new RelayCommand(async () => await StartAIDesign());
            AnalyzeProjectCommand = new RelayCommand(async () => await AnalyzeProject());
            RefreshDashboardCommand = new RelayCommand(async () => await RefreshDashboard());
        }

        private void InitializeQuickActions()
        {
            QuickActions.Clear();
            
            QuickActions.Add(new QuickAction
            {
                Icon = "📁",
                Title = "Yeni Proje",
                Description = "Boş proje oluştur",
                Command = CreateNewProjectCommand
            });

            QuickActions.Add(new QuickAction
            {
                Icon = "🤖",
                Title = "AI Tasarım",
                Description = "AI ile tasarım oluştur",
                Command = StartAIDesignCommand
            });

            QuickActions.Add(new QuickAction
            {
                Icon = "📊",
                Title = "Proje Analizi",
                Description = "Mevcut projeyi analiz et",
                Command = AnalyzeProjectCommand
            });

            QuickActions.Add(new QuickAction
            {
                Icon = "📄",
                Title = "Dosya İçe Aktar",
                Description = "DWG/DXF/IFC dosyası aç",
                Command = new RelayCommand(async () => await ImportFile())
            });
        }

        public async Task InitializeAsync()
        {
            try
            {
                IsLoading = true;
                
                // Load dashboard data in parallel
                var tasks = new[]
                {
                    LoadRecentProjectsAsync(),
                    CheckApiStatusAsync(),
                    LoadUserStatsAsync()
                };

                await Task.WhenAll(tasks);
                
                _logger?.LogInformation("HomeViewModel initialized successfully");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to initialize HomeViewModel");
            }
            finally
            {
                IsLoading = false;
            }
        }

        #endregion

        #region Private Methods

        private async Task LoadRecentProjectsAsync()
        {
            try
            {
                var projects = await _projectService.GetProjectsAsync();
                RecentProjects.Clear();
                
                // Add recent projects (limit to 5)
                var recentProjects = projects.Take(5);
                foreach (var project in recentProjects)
                {
                    RecentProjects.Add(project);
                }
                
                RecentProjectsCount = projects.Count;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to load recent projects");
            }
        }

        private async Task CheckApiStatusAsync()
        {
            try
            {
                var isConnected = await _cloudApiService.IsConnectedAsync();
                ApiStatus = isConnected ? "Bağlı ✅" : "Bağlantı Yok ❌";
                LastSyncTime = DateTime.Now;
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to check API status");
                ApiStatus = "Hata ⚠️";
            }
        }

        private async Task LoadUserStatsAsync()
        {
            try
            {
                // TODO: Load user statistics from database/API
                await Task.Delay(200);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to load user stats");
            }
        }

        private async Task CreateNewProject()
        {
            try
            {
                // TODO: Show new project dialog
                var project = await _projectService.CreateProjectAsync("Yeni Proje", "Açıklama");
                RecentProjects.Insert(0, project);
                RecentProjectsCount++;
                
                _logger?.LogInformation("New project created: {ProjectId}", project.Id);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to create new project");
            }
        }

        private async Task OpenProject(Project project)
        {
            try
            {
                if (project == null) return;
                
                // TODO: Navigate to project view
                _logger?.LogInformation("Opening project: {ProjectId}", project.Id);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to open project {ProjectId}", project?.Id);
            }
        }

        private async Task StartAIDesign()
        {
            try
            {
                // TODO: Navigate to AI design view
                _logger?.LogInformation("Starting AI design workflow");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to start AI design");
            }
        }

        private async Task AnalyzeProject()
        {
            try
            {
                // TODO: Navigate to analysis view
                _logger?.LogInformation("Starting project analysis");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to start project analysis");
            }
        }

        private async Task ImportFile()
        {
            try
            {
                // TODO: Show file import dialog
                _logger?.LogInformation("Starting file import");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to import file");
            }
        }

        private async Task RefreshDashboard()
        {
            try
            {
                await InitializeAsync();
                _logger?.LogInformation("Dashboard refreshed");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to refresh dashboard");
            }
        }

        #endregion

        #region INotifyPropertyChanged Implementation

        public event PropertyChangedEventHandler PropertyChanged;

        protected virtual void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        protected bool SetProperty<T>(ref T backingStore, T value, [CallerMemberName] string propertyName = "")
        {
            if (EqualityComparer<T>.Default.Equals(backingStore, value))
                return false;

            backingStore = value;
            OnPropertyChanged(propertyName);
            return true;
        }

        #endregion
    }

    /// <summary>
    /// Hızlı eylem öğesi
    /// </summary>
    public class QuickAction
    {
        public string Icon { get; set; }
        public string Title { get; set; }
        public string Description { get; set; }
        public ICommand Command { get; set; }
    }
}

