using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using System.Windows.Input;
using ArchBuilder.Core;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.ViewModels
{
    /// <summary>
    /// Ana pencere için ViewModel - Apple-vari navigation pattern ile
    /// </summary>
    public class MainViewModel : INotifyPropertyChanged
    {
        private readonly ILogger<MainViewModel> _logger;
        private readonly IProjectService _projectService;
        private readonly INavigationService _navigationService;
        
        private object _currentViewModel;
        private string _currentPageTitle = "ArchBuilder.AI";
        private bool _isLoading;
        private NavigationItem _selectedNavigationItem;

        public MainViewModel()
        {
            // Dependency injection container'dan servisleri al
            _logger = ServiceLocator.GetService<ILogger<MainViewModel>>();
            _projectService = ServiceLocator.GetService<IProjectService>();
            _navigationService = ServiceLocator.GetService<INavigationService>();

            InitializeCommands();
            InitializeNavigation();
            
            // Ana sayfa ile başla
            NavigateToHome();
            
            _logger?.LogInformation("MainViewModel initialized successfully");
        }

        #region Properties

        /// <summary>
        /// Şu anki görüntülenen ViewModel
        /// </summary>
        public object CurrentViewModel
        {
            get => _currentViewModel;
            set => SetProperty(ref _currentViewModel, value);
        }

        /// <summary>
        /// Sayfa başlığı
        /// </summary>
        public string CurrentPageTitle
        {
            get => _currentPageTitle;
            set => SetProperty(ref _currentPageTitle, value);
        }

        /// <summary>
        /// Yükleme durumu
        /// </summary>
        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        /// <summary>
        /// Seçili navigation item
        /// </summary>
        public NavigationItem SelectedNavigationItem
        {
            get => _selectedNavigationItem;
            set 
            { 
                SetProperty(ref _selectedNavigationItem, value);
                if (value != null)
                {
                    ExecuteNavigation(value);
                }
            }
        }

        /// <summary>
        /// Navigation menü öğeleri
        /// </summary>
        public ObservableCollection<NavigationItem> NavigationItems { get; } = new ObservableCollection<NavigationItem>();

        #endregion

        #region Commands

        public ICommand NavigateToHomeCommand { get; private set; }
        public ICommand NavigateToProjectsCommand { get; private set; }
        public ICommand NavigateToAIDesignCommand { get; private set; }
        public ICommand NavigateToAnalysisCommand { get; private set; }
        public ICommand NavigateToSettingsCommand { get; private set; }
        public ICommand RefreshCommand { get; private set; }

        #endregion

        #region Private Methods

        private void InitializeCommands()
        {
            NavigateToHomeCommand = new RelayCommand(() => NavigateToHome());
            NavigateToProjectsCommand = new RelayCommand(() => NavigateToProjects());
            NavigateToAIDesignCommand = new RelayCommand(() => NavigateToAIDesign());
            NavigateToAnalysisCommand = new RelayCommand(() => NavigateToAnalysis());
            NavigateToSettingsCommand = new RelayCommand(() => NavigateToSettings());
            RefreshCommand = new RelayCommand(() => RefreshCurrentView());
        }

        private void InitializeNavigation()
        {
            NavigationItems.Clear();
            
            NavigationItems.Add(new NavigationItem
            {
                Icon = "🏠",
                Title = "Ana Sayfa",
                Description = "Genel bakış ve hızlı erişim",
                NavigationType = NavigationType.Home,
                Command = NavigateToHomeCommand
            });

            NavigationItems.Add(new NavigationItem
            {
                Icon = "📁",
                Title = "Projeler",
                Description = "Proje yönetimi ve dosya işlemleri",
                NavigationType = NavigationType.Projects,
                Command = NavigateToProjectsCommand
            });

            NavigationItems.Add(new NavigationItem
            {
                Icon = "🤖",
                Title = "AI Tasarım",
                Description = "Yapay zeka destekli tasarım oluşturma",
                NavigationType = NavigationType.AIDesign,
                Command = NavigateToAIDesignCommand
            });

            NavigationItems.Add(new NavigationItem
            {
                Icon = "📊",
                Title = "Proje Analizi",
                Description = "Mevcut projelerin analizi ve iyileştirme",
                NavigationType = NavigationType.Analysis,
                Command = NavigateToAnalysisCommand
            });

            NavigationItems.Add(new NavigationItem
            {
                Icon = "⚙️",
                Title = "Ayarlar",
                Description = "Uygulama ve AI ayarları",
                NavigationType = NavigationType.Settings,
                Command = NavigateToSettingsCommand
            });
        }

        private async void ExecuteNavigation(NavigationItem item)
        {
            try
            {
                IsLoading = true;
                CurrentPageTitle = item.Title;

                switch (item.NavigationType)
                {
                    case NavigationType.Home:
                        await NavigateToHomeAsync();
                        break;
                    case NavigationType.Projects:
                        await NavigateToProjectsAsync();
                        break;
                    case NavigationType.AIDesign:
                        await NavigateToAIDesignAsync();
                        break;
                    case NavigationType.Analysis:
                        await NavigateToAnalysisAsync();
                        break;
                    case NavigationType.Settings:
                        await NavigateToSettingsAsync();
                        break;
                }

                _logger?.LogInformation("Navigated to {NavigationType}", item.NavigationType);
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Navigation failed for {NavigationType}", item.NavigationType);
                // Hata durumunda ana sayfaya dön
                await NavigateToHomeAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void NavigateToHome()
        {
            var homeItem = NavigationItems[0];
            SelectedNavigationItem = homeItem;
        }

        private void NavigateToProjects()
        {
            var projectsItem = NavigationItems[1];
            SelectedNavigationItem = projectsItem;
        }

        private void NavigateToAIDesign()
        {
            var aiDesignItem = NavigationItems[2];
            SelectedNavigationItem = aiDesignItem;
        }

        private void NavigateToAnalysis()
        {
            var analysisItem = NavigationItems[3];
            SelectedNavigationItem = analysisItem;
        }

        private void NavigateToSettings()
        {
            var settingsItem = NavigationItems[4];
            SelectedNavigationItem = settingsItem;
        }

        private async Task NavigateToHomeAsync()
        {
            // HomeViewModel oluştur ve ayarla
            var homeViewModel = ServiceLocator.GetService<HomeViewModel>();
            await homeViewModel.InitializeAsync();
            CurrentViewModel = homeViewModel;
        }

        private async Task NavigateToProjectsAsync()
        {
            // ProjectViewModel oluştur ve ayarla (ProjectView için güncellenmiş ViewModel)
            var projectViewModel = ServiceLocator.GetService<ProjectViewModel>();
            if (projectViewModel == null)
            {
                // Fallback olarak yeni instance oluştur
                projectViewModel = new ProjectViewModel();
            }
            
            // Veri yüklenmesi beklenmez çünkü ProjectViewModel kendi başlatma işlemini yapar
            await Task.Delay(100); // UI responsiveness için küçük gecikme
            CurrentViewModel = projectViewModel;
            
            _logger?.LogInformation("Navigated to Projects view with ProjectViewModel");
        }

        private async Task NavigateToAIDesignAsync()
        {
            // AIDesignViewModel oluştur ve ayarla
            var aiDesignViewModel = ServiceLocator.GetService<AIDesignViewModel>();
            await aiDesignViewModel.InitializeAsync();
            CurrentViewModel = aiDesignViewModel;
        }

        private async Task NavigateToAnalysisAsync()
        {
            // AnalysisViewModel oluştur ve ayarla
            var analysisViewModel = ServiceLocator.GetService<AnalysisViewModel>();
            await analysisViewModel.LoadAnalysisDataAsync();
            CurrentViewModel = analysisViewModel;
        }

        private async Task NavigateToSettingsAsync()
        {
            // SettingsViewModel oluştur ve ayarla
            var settingsViewModel = ServiceLocator.GetService<SettingsViewModel>();
            await settingsViewModel.LoadSettingsAsync();
            CurrentViewModel = settingsViewModel;
        }

        private async void RefreshCurrentView()
        {
            try
            {
                IsLoading = true;
                
                if (SelectedNavigationItem != null)
                {
                    await ExecuteNavigationAsync(SelectedNavigationItem);
                }
                
                _logger?.LogInformation("Current view refreshed");
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Failed to refresh current view");
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task ExecuteNavigationAsync(NavigationItem item)
        {
            switch (item.NavigationType)
            {
                case NavigationType.Home:
                    await NavigateToHomeAsync();
                    break;
                case NavigationType.Projects:
                    await NavigateToProjectsAsync();
                    break;
                case NavigationType.AIDesign:
                    await NavigateToAIDesignAsync();
                    break;
                case NavigationType.Analysis:
                    await NavigateToAnalysisAsync();
                    break;
                case NavigationType.Settings:
                    await NavigateToSettingsAsync();
                    break;
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
    /// Navigation menü öğesi
    /// </summary>
    public class NavigationItem
    {
        public string Icon { get; set; }
        public string Title { get; set; }
        public string Description { get; set; }
        public NavigationType NavigationType { get; set; }
        public ICommand Command { get; set; }
    }

    /// <summary>
    /// Navigation türleri
    /// </summary>
    public enum NavigationType
    {
        Home,
        Projects,
        AIDesign,
        Analysis,
        Settings
    }
}