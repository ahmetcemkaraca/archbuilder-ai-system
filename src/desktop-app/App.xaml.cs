using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ArchBuilder.Services;
using ArchBuilder.ViewModels;
using ArchBuilder.Views;

namespace ArchBuilder
{
    /// <summary>
    /// Uygulamanın ana giriş noktası ve başlatma mantığı.
    /// </summary>
    public partial class App : Application
    {
        private IHost _host;

        public App()
        {
            InitializeComponent(); // Bu satırı ekledim
            _host = Host.CreateDefaultBuilder()
                .ConfigureServices((context, services) =>
                {
                    // Servisleri burada kaydedin
                    services.AddSingleton<LoggerService>();
                    services.AddSingleton<AuthService>();
                    services.AddSingleton<NavigationService>();
                    
                    // ViewModels
                    services.AddTransient<MainViewModel>();
                    services.AddTransient<StartupViewModel>();
                    services.AddTransient<HomeViewModel>();

                    // Views
                    services.AddSingleton<MainWindow>();
                    services.AddTransient<StartupView>();
                    // services.AddTransient<HomeView>(); // Henüz oluşturulmadı
                })
                .Build();

            // LoggerService'i erken başlat
            _ = _host.Services.GetRequiredService<LoggerService>();
        }

        protected override async void OnStartup(StartupEventArgs e)
        {
            await _host.StartAsync();

            // MainViewModel'i ve MainWindow'u IoC kapsayıcısından al
            var mainWindow = _host.Services.GetRequiredService<MainWindow>();
            var mainViewModel = _host.Services.GetRequiredService<MainViewModel>();

            // MainWindow'un DataContext'ini MainViewModel olarak ayarla
            mainWindow.DataContext = mainViewModel;
            mainWindow.Show();

            base.OnStartup(e);
        }

        protected override async void OnExit(ExitEventArgs e)
        {
            await _host.StopAsync();
            _host.Dispose();
            base.OnExit(e);
        }
    }
}

