using System;
using System.Collections.Generic;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using ArchBuilder.Desktop.Services;

namespace ArchBuilder.Desktop.Core
{
    /// <summary>
    /// Service locator for dependency injection and service resolution.
    /// </summary>
    public class ServiceLocator
    {
        private static ServiceLocator _instance;
        private static readonly object _lock = new object();
        private IServiceProvider _serviceProvider;
        private readonly IServiceCollection _services;
        private bool _isBuilt = false;

        /// <summary>
        /// Gets the singleton instance of the service locator.
        /// </summary>
        public static ServiceLocator Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        if (_instance == null)
                        {
                            _instance = new ServiceLocator();
                        }
                    }
                }
                return _instance;
            }
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="ServiceLocator"/> class.
        /// </summary>
        private ServiceLocator()
        {
            _services = new ServiceCollection();
        }

        /// <summary>
        /// Configures and builds the service provider with all required services.
        /// </summary>
        /// <param name="configuration">The application configuration.</param>
        public void BuildServices(IConfiguration configuration = null)
        {
            if (_isBuilt)
            {
                throw new InvalidOperationException("Services have already been built. Call Reset() first if you need to rebuild.");
            }

            try
            {
                // Add configuration if provided
                if (configuration != null)
                {
                    _services.AddSingleton(configuration);
                }

                // Add logging services
                _services.AddLogging(builder =>
                {
                    builder.AddConsole();
                    builder.AddDebug();
                    builder.SetMinimumLevel(LogLevel.Information);
                });

                // Register core services
                RegisterCoreServices();

                // Register application services
                RegisterApplicationServices();

                // Register utility services
                RegisterUtilityServices();

                // Build the service provider
                _serviceProvider = _services.BuildServiceProvider();
                _isBuilt = true;
            }
            catch (Exception ex)
            {
                throw new ServiceException("Failed to build service provider", "SERVICE_BUILD_FAILED", "ServiceLocator", ex);
            }
        }

        /// <summary>
        /// Registers core infrastructure services.
        /// </summary>
        private void RegisterCoreServices()
        {
            // Configuration service
            _services.AddSingleton<IConfigurationService, ConfigurationService>();

            // Settings service
            _services.AddSingleton<ISettingsService, SettingsService>();

            // Project data service
            _services.AddSingleton<IProjectDataService, ProjectDataService>();
        }

        /// <summary>
        /// Registers application-specific services.
        /// </summary>
        private void RegisterApplicationServices()
        {
            // ViewModels
            _services.AddTransient<ArchBuilder.ViewModels.HomeViewModel>();
            _services.AddTransient<ArchBuilder.ViewModels.ProjectsViewModel>();
            _services.AddTransient<ArchBuilder.ViewModels.AIDesignViewModel>();
            _services.AddTransient<ArchBuilder.ViewModels.AnalysisViewModel>();
            _services.AddTransient<ArchBuilder.ViewModels.SettingsViewModel>();

            // Legacy services (maintain backward compatibility)
            _services.AddSingleton<IProjectService, ProjectService>();
            _services.AddSingleton<INavigationService, NavigationService>();
            _services.AddSingleton<IFileProcessingService, FileProcessingService>();
            _services.AddSingleton<ICloudApiService, CloudApiService>();

            // Cloud client service (placeholder for future implementation)
            // _services.AddSingleton<ICloudClientService, CloudClientService>();

            // File handler services (placeholder for future implementation)
            // _services.AddSingleton<IFileHandlerService, FileHandlerService>();

            // AI service client (placeholder for future implementation)
            // _services.AddSingleton<IAIServiceClient, AIServiceClient>();

            // Revit integration service (placeholder for future implementation)
            // _services.AddSingleton<IRevitIntegrationService, RevitIntegrationService>();
        }

        /// <summary>
        /// Registers utility and helper services.
        /// </summary>
        private void RegisterUtilityServices()
        {
            // Validation service (placeholder for future implementation)
            // _services.AddSingleton<IValidationService, ValidationService>();

            // Security service (placeholder for future implementation)
            // _services.AddSingleton<ISecurityService, SecurityService>();

            // Notification service (placeholder for future implementation)
            // _services.AddSingleton<INotificationService, NotificationService>();

            // Performance monitoring (placeholder for future implementation)
            // _services.AddSingleton<IPerformanceMonitor, PerformanceMonitor>();
        }

        /// <summary>
        /// Gets a service of the specified type.
        /// </summary>
        /// <typeparam name="T">The type of service to retrieve.</typeparam>
        /// <returns>The service instance.</returns>
        /// <exception cref="InvalidOperationException">Thrown when services have not been built.</exception>
        /// <exception cref="ServiceException">Thrown when the service cannot be resolved.</exception>
        public T GetService<T>()
        {
            if (!_isBuilt)
            {
                throw new InvalidOperationException("Services have not been built. Call BuildServices() first.");
            }

            try
            {
                return _serviceProvider.GetService<T>();
            }
            catch (Exception ex)
            {
                throw new ServiceException($"Failed to resolve service of type {typeof(T).Name}", 
                    "SERVICE_RESOLUTION_FAILED", typeof(T).Name, ex);
            }
        }

        /// <summary>
        /// Gets a required service of the specified type.
        /// </summary>
        /// <typeparam name="T">The type of service to retrieve.</typeparam>
        /// <returns>The service instance.</returns>
        /// <exception cref="InvalidOperationException">Thrown when services have not been built or service is not registered.</exception>
        /// <exception cref="ServiceException">Thrown when the service cannot be resolved.</exception>
        public T GetRequiredService<T>()
        {
            if (!_isBuilt)
            {
                throw new InvalidOperationException("Services have not been built. Call BuildServices() first.");
            }

            try
            {
                return _serviceProvider.GetRequiredService<T>();
            }
            catch (Exception ex)
            {
                throw new ServiceException($"Failed to resolve required service of type {typeof(T).Name}", 
                    "SERVICE_RESOLUTION_FAILED", typeof(T).Name, ex);
            }
        }

        /// <summary>
        /// Gets all services of the specified type.
        /// </summary>
        /// <typeparam name="T">The type of services to retrieve.</typeparam>
        /// <returns>An enumerable of service instances.</returns>
        /// <exception cref="InvalidOperationException">Thrown when services have not been built.</exception>
        /// <exception cref="ServiceException">Thrown when the services cannot be resolved.</exception>
        public IEnumerable<T> GetServices<T>()
        {
            if (!_isBuilt)
            {
                throw new InvalidOperationException("Services have not been built. Call BuildServices() first.");
            }

            try
            {
                return _serviceProvider.GetServices<T>();
            }
            catch (Exception ex)
            {
                throw new ServiceException($"Failed to resolve services of type {typeof(T).Name}", 
                    "SERVICE_RESOLUTION_FAILED", typeof(T).Name, ex);
            }
        }

        /// <summary>
        /// Gets a service of the specified type.
        /// </summary>
        /// <param name="serviceType">The type of service to retrieve.</param>
        /// <returns>The service instance, or null if not found.</returns>
        /// <exception cref="InvalidOperationException">Thrown when services have not been built.</exception>
        /// <exception cref="ServiceException">Thrown when the service cannot be resolved.</exception>
        public object GetService(Type serviceType)
        {
            if (!_isBuilt)
            {
                throw new InvalidOperationException("Services have not been built. Call BuildServices() first.");
            }

            try
            {
                return _serviceProvider.GetService(serviceType);
            }
            catch (Exception ex)
            {
                throw new ServiceException($"Failed to resolve service of type {serviceType.Name}", 
                    "SERVICE_RESOLUTION_FAILED", serviceType.Name, ex);
            }
        }

        /// <summary>
        /// Gets a required service of the specified type.
        /// </summary>
        /// <param name="serviceType">The type of service to retrieve.</param>
        /// <returns>The service instance.</returns>
        /// <exception cref="InvalidOperationException">Thrown when services have not been built or service is not registered.</exception>
        /// <exception cref="ServiceException">Thrown when the service cannot be resolved.</exception>
        public object GetRequiredService(Type serviceType)
        {
            if (!_isBuilt)
            {
                throw new InvalidOperationException("Services have not been built. Call BuildServices() first.");
            }

            try
            {
                return _serviceProvider.GetRequiredService(serviceType);
            }
            catch (Exception ex)
            {
                throw new ServiceException($"Failed to resolve required service of type {serviceType.Name}", 
                    "SERVICE_RESOLUTION_FAILED", serviceType.Name, ex);
            }
        }

        /// <summary>
        /// Registers a service descriptor.
        /// </summary>
        /// <param name="serviceDescriptor">The service descriptor to register.</param>
        /// <exception cref="InvalidOperationException">Thrown when services have already been built.</exception>
        public void RegisterService(ServiceDescriptor serviceDescriptor)
        {
            if (_isBuilt)
            {
                throw new InvalidOperationException("Cannot register services after the service provider has been built.");
            }

            _services.Add(serviceDescriptor);
        }

        /// <summary>
        /// Registers a singleton service.
        /// </summary>
        /// <typeparam name="TInterface">The service interface type.</typeparam>
        /// <typeparam name="TImplementation">The service implementation type.</typeparam>
        /// <exception cref="InvalidOperationException">Thrown when services have already been built.</exception>
        public void RegisterSingleton<TInterface, TImplementation>()
            where TInterface : class
            where TImplementation : class, TInterface
        {
            if (_isBuilt)
            {
                throw new InvalidOperationException("Cannot register services after the service provider has been built.");
            }

            _services.AddSingleton<TInterface, TImplementation>();
        }

        /// <summary>
        /// Registers a singleton service with an instance.
        /// </summary>
        /// <typeparam name="T">The service type.</typeparam>
        /// <param name="instance">The service instance.</param>
        /// <exception cref="InvalidOperationException">Thrown when services have already been built.</exception>
        public void RegisterSingleton<T>(T instance) where T : class
        {
            if (_isBuilt)
            {
                throw new InvalidOperationException("Cannot register services after the service provider has been built.");
            }

            _services.AddSingleton(instance);
        }

        /// <summary>
        /// Registers a transient service.
        /// </summary>
        /// <typeparam name="TInterface">The service interface type.</typeparam>
        /// <typeparam name="TImplementation">The service implementation type.</typeparam>
        /// <exception cref="InvalidOperationException">Thrown when services have already been built.</exception>
        public void RegisterTransient<TInterface, TImplementation>()
            where TInterface : class
            where TImplementation : class, TInterface
        {
            if (_isBuilt)
            {
                throw new InvalidOperationException("Cannot register services after the service provider has been built.");
            }

            _services.AddTransient<TInterface, TImplementation>();
        }

        /// <summary>
        /// Registers a scoped service.
        /// </summary>
        /// <typeparam name="TInterface">The service interface type.</typeparam>
        /// <typeparam name="TImplementation">The service implementation type.</typeparam>
        /// <exception cref="InvalidOperationException">Thrown when services have already been built.</exception>
        public void RegisterScoped<TInterface, TImplementation>()
            where TInterface : class
            where TImplementation : class, TInterface
        {
            if (_isBuilt)
            {
                throw new InvalidOperationException("Cannot register services after the service provider has been built.");
            }

            _services.AddScoped<TInterface, TImplementation>();
        }

        /// <summary>
        /// Gets whether the service provider has been built.
        /// </summary>
        public bool IsBuilt => _isBuilt;

        /// <summary>
        /// Gets the number of registered services.
        /// </summary>
        public int ServiceCount => _services.Count;

        /// <summary>
        /// Checks if a service of the specified type is registered.
        /// </summary>
        /// <typeparam name="T">The service type to check.</typeparam>
        /// <returns>True if the service is registered; otherwise, false.</returns>
        public bool IsServiceRegistered<T>()
        {
            return IsServiceRegistered(typeof(T));
        }

        /// <summary>
        /// Checks if a service of the specified type is registered.
        /// </summary>
        /// <param name="serviceType">The service type to check.</param>
        /// <returns>True if the service is registered; otherwise, false.</returns>
        public bool IsServiceRegistered(Type serviceType)
        {
            foreach (var service in _services)
            {
                if (service.ServiceType == serviceType)
                {
                    return true;
                }
            }
            return false;
        }

        /// <summary>
        /// Gets the service descriptors for diagnostics.
        /// </summary>
        /// <returns>A read-only list of service descriptors.</returns>
        public IReadOnlyList<ServiceDescriptor> GetServiceDescriptors()
        {
            return new List<ServiceDescriptor>(_services).AsReadOnly();
        }

        /// <summary>
        /// Resets the service locator, allowing for re-configuration.
        /// </summary>
        public void Reset()
        {
            if (_serviceProvider is IDisposable disposable)
            {
                disposable.Dispose();
            }

            _serviceProvider = null;
            _services.Clear();
            _isBuilt = false;
        }

        /// <summary>
        /// Disposes the service provider and cleans up resources.
        /// </summary>
        public void Dispose()
        {
            if (_serviceProvider is IDisposable disposable)
            {
                disposable.Dispose();
            }

            _serviceProvider = null;
            _isBuilt = false;
        }

        /// <summary>
        /// Creates a service scope for scoped service resolution.
        /// </summary>
        /// <returns>A service scope.</returns>
        /// <exception cref="InvalidOperationException">Thrown when services have not been built.</exception>
        public IServiceScope CreateScope()
        {
            if (!_isBuilt)
            {
                throw new InvalidOperationException("Services have not been built. Call BuildServices() first.");
            }

            return _serviceProvider.CreateScope();
        }

        /// <summary>
        /// Validates all registered services can be resolved.
        /// </summary>
        /// <returns>A list of validation errors, or empty list if all services are valid.</returns>
        public List<string> ValidateServices()
        {
            var errors = new List<string>();

            if (!_isBuilt)
            {
                errors.Add("Services have not been built.");
                return errors;
            }

            try
            {
                // Try to resolve all registered singleton services
                foreach (var service in _services)
                {
                    if (service.Lifetime == ServiceLifetime.Singleton)
                    {
                        try
                        {
                            _serviceProvider.GetService(service.ServiceType);
                        }
                        catch (Exception ex)
                        {
                            errors.Add($"Failed to resolve service {service.ServiceType.Name}: {ex.Message}");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                errors.Add($"Service validation failed: {ex.Message}");
            }

            return errors;
        }
    }

    #region Legacy Service Interfaces and Implementations

    /// <summary>
    /// Proje yönetimi servisi (legacy compatibility).
    /// </summary>
    public interface IProjectService
    {
        Task<List<Project>> GetProjectsAsync();
        Task<Project> CreateProjectAsync(string name, string description);
        Task<bool> DeleteProjectAsync(Guid projectId);
        Task<Project> GetProjectAsync(Guid projectId);
    }

    /// <summary>
    /// Navigation servisi.
    /// </summary>
    public interface INavigationService
    {
        void NavigateTo(string viewName);
        void NavigateBack();
        bool CanNavigateBack { get; }
    }

    /// <summary>
    /// Dosya işleme servisi.
    /// </summary>
    public interface IFileProcessingService
    {
        Task<bool> ProcessFileAsync(string filePath, string fileType);
        Task<List<string>> GetSupportedFormatsAsync();
    }

    /// <summary>
    /// Cloud API servisi.
    /// </summary>
    public interface ICloudApiService
    {
        Task<bool> IsConnectedAsync();
        Task<string> GetApiStatusAsync();
    }

    /// <summary>
    /// Legacy project service implementation.
    /// </summary>
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

    /// <summary>
    /// Navigation service implementation.
    /// </summary>
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

    /// <summary>
    /// File processing service implementation.
    /// </summary>
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

    /// <summary>
    /// Cloud API service implementation.
    /// </summary>
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

    /// <summary>
    /// Legacy project data model.
    /// </summary>
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
}