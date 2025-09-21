using System;
using System.IO;
using System.Reflection;
using Serilog;
using Serilog.Events;

namespace ArchBuilder.Services
{
    public class LoggerService
    {
        private static LoggerService _instance;
        public static LoggerService Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = new LoggerService();
                }
                return _instance;
            }
        }

        private LoggerService()
        {
            // Serilog yapılandırması
            string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "logs", "desktop-app-.log");
            Log.Logger = new LoggerConfiguration()
                .MinimumLevel.Debug() // En düşük log seviyesi
                .MinimumLevel.Override("Microsoft", LogEventLevel.Information)
                .Enrich.FromLogContext()
                .WriteTo.Console() // Konsola yaz
                .WriteTo.File(logFilePath, rollingInterval: RollingInterval.Day) // Günlük dosyalarına yaz
                .CreateLogger();

            Log.Information("LoggerService başlatıldı.");
        }

        public void LogInfo(string message, params object[] properties)
        {
            Log.Information(message, properties);
        }

        public void LogWarning(string message, params object[] properties)
        {
            Log.Warning(message, properties);
        }

        public void LogError(string message, Exception ex = null, params object[] properties)
        {
            Log.Error(ex, message, properties);
        }

        public void LogCritical(string message, Exception ex = null, params object[] properties)
        {
            Log.Fatal(ex, message, properties);
        }

        public void LogDebug(string message, params object[] properties)
        {
            Log.Debug(message, properties);
        }
    }
}

