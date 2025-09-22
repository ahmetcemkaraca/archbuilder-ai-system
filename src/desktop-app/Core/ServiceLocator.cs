using System;
using System.Collections.Concurrent;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace ArchBuilder.Core
{
    /// <summary>
    /// Basit Service Locator pattern implementasyonu - Dependency Injection için
    /// </summary>
    public static class ServiceLocator
    {
        private static IServiceProvider _serviceProvider;
        private static readonly ConcurrentDictionary<Type, object> _singletonCache = new ConcurrentDictionary<Type, object>();

        /// <summary>
        /// Service provider'ı initialize eder
        /// </summary>
        public static void Initialize()
        {
            var services = new ServiceCollection();
            ConfigureServices(services);
            _serviceProvider = services.BuildServiceProvider();
        }

        /// <summary>
        /// Servisleri yapılandırır
        /// </summary>
        private static void ConfigureServices(IServiceCollection services)
        {
            // Logging
            services.AddLogging(builder =>
            {
                builder.AddConsole();
                builder.AddDebug();
                builder.SetMinimumLevel(LogLevel.Information);
            });

            // ViewModels
            services.AddTransient<ArchBuilder.ViewModels.HomeViewModel>();
            services.AddTransient<ArchBuilder.ViewModels.ProjectsViewModel>();
            services.AddTransient<ArchBuilder.ViewModels.AIDesignViewModel>();
            services.AddTransient<ArchBuilder.ViewModels.AnalysisViewModel>();
            services.AddTransient<ArchBuilder.ViewModels.SettingsViewModel>();

            // Services
            services.AddSingleton<IProjectService, ProjectService>();
            services.AddSingleton<INavigationService, NavigationService>();
            services.AddSingleton<IFileProcessingService, FileProcessingService>();
            services.AddSingleton<ICloudApiService, CloudApiService>();
        }

        /// <summary>
        /// Service instance'ını alır
        /// </summary>
        public static T GetService<T>()
        {
            if (_serviceProvider == null)
            {
                Initialize();
            }

            try
            {
                return _serviceProvider.GetService<T>();
            }
            catch (Exception)
            {
                // Fallback to null for optional services
                return default(T);
            }
        }

        /// <summary>
        /// Required service instance'ını alır - null dönerse exception atar
        /// </summary>
        public static T GetRequiredService<T>()
        {
            if (_serviceProvider == null)
            {
                Initialize();
            }

            return _serviceProvider.GetRequiredService<T>();
        }

        /// <summary>
        /// Singleton instance'ı cache'den alır veya oluşturur
        /// </summary>
        public static T GetSingleton<T>() where T : class, new()
        {
            return (T)_singletonCache.GetOrAdd(typeof(T), _ => new T());
        }
    }

    #region Service Interfaces

    /// <summary>
    /// Proje yönetimi servisi
    /// </summary>
    public interface IProjectService
    {
        Task<List<Project>> GetProjectsAsync();
        Task<Project> CreateProjectAsync(string name, string description);
        Task<bool> DeleteProjectAsync(Guid projectId);
        Task<Project> GetProjectAsync(Guid projectId);
    }

    /// <summary>
    /// Navigation servisi
    /// </summary>
    public interface INavigationService
    {
        void NavigateTo(string viewName);
        void NavigateBack();
        bool CanNavigateBack { get; }
    }

    /// <summary>
    /// Dosya işleme servisi
    /// </summary>
    public interface IFileProcessingService
    {
        Task<bool> ProcessFileAsync(string filePath, string fileType);
        Task<List<string>> GetSupportedFormatsAsync();
    }

    /// <summary>
    /// Cloud API servisi
    /// </summary>
    public interface ICloudApiService
    {
        Task<bool> IsConnectedAsync();
        Task<string> GetApiStatusAsync();
    }

    #endregion

    #region Service Implementations (Placeholder)

    public class ProjectService : IProjectService
    {
        private readonly ILogger<ProjectService> _logger;

        public ProjectService(ILogger<ProjectService> logger)
        {
            _logger = logger;
        }

        public async Task<List<Project>> GetProjectsAsync()
        {
            // TODO: Implement actual project loading
            await Task.Delay(100);
            return new List<Project>();
        }

        public async Task<Project> CreateProjectAsync(string name, string description)
        {
            // TODO: Implement project creation
            await Task.Delay(100);
            return new Project { Id = Guid.NewGuid(), Name = name, Description = description };
        }

        public async Task<bool> DeleteProjectAsync(Guid projectId)
        {
            // TODO: Implement project deletion
            await Task.Delay(100);
            return true;
        }

        public async Task<Project> GetProjectAsync(Guid projectId)
        {
            // TODO: Implement project loading
            await Task.Delay(100);
            return new Project { Id = projectId, Name = "Sample Project" };
        }
    }

    public class NavigationService : INavigationService
    {
        public bool CanNavigateBack => false; // TODO: Implement navigation history

        public void NavigateBack()
        {
            // TODO: Implement navigation back
        }

        public void NavigateTo(string viewName)
        {
            // TODO: Implement navigation
        }
    }

    public class FileProcessingService : IFileProcessingService
    {
        public async Task<List<string>> GetSupportedFormatsAsync()
        {
            await Task.Delay(50);
            return new List<string> { "DWG", "DXF", "IFC", "PDF" };
        }

        public async Task<bool> ProcessFileAsync(string filePath, string fileType)
        {
            // TODO: Implement file processing
            await Task.Delay(1000);
            return true;
        }
    }

    public class CloudApiService : ICloudApiService
    {
        public async Task<string> GetApiStatusAsync()
        {
            await Task.Delay(100);
            return "Connected";
        }

        public async Task<bool> IsConnectedAsync()
        {
            await Task.Delay(100);
            return true;
        }
    }

    #endregion

    #region Data Models

    public class Project
    {
        public Guid Id { get; set; }
        public string Name { get; set; }
        public string Description { get; set; }
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
        public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    }

    #endregion
}