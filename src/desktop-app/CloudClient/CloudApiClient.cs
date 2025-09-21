using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;
using Newtonsoft.Json;
using ArchBuilder.Services;
using ArchBuilder.Core; // HttpRequestExceptionExtensions için eklendi

namespace ArchBuilder.CloudClient
{
    public class CloudApiClient
    {
        private readonly HttpClient _httpClient;
        private readonly LoggerService _loggerService;
        private readonly AuthService _authService; // Kimlik doğrulama hizmetine erişim için

        public CloudApiClient(AuthService authService, LoggerService loggerService)
        {
            _authService = authService;
            _loggerService = loggerService;

            _httpClient = new HttpClient();
            _httpClient.BaseAddress = new Uri("http://localhost:8000/api/"); // AppSettings'ten okunacak
            _httpClient.DefaultRequestHeaders.Accept.Clear();
            _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        }

        // Her istek öncesi Authorization başlığını ayarlama
        private void SetAuthorizationHeader()
        {
            if (_authService.CurrentUserSession != null && _authService.CurrentUserSession.IsAuthenticated)
            {
                _httpClient.DefaultRequestHeaders.Authorization = 
                    new AuthenticationHeaderValue("Bearer", _authService.CurrentUserSession.AccessToken);
            }
            else
            {
                _httpClient.DefaultRequestHeaders.Authorization = null; // Token yoksa başlığı temizle
            }
        }

        public async Task<TResponse> GetAsync<TResponse>(string requestUri)
        {
            SetAuthorizationHeader();
            try
            {
                _loggerService.LogDebug($"GET isteği gönderiliyor: {requestUri}");
                var response = await _httpClient.GetAsync(requestUri);
                response.EnsureSuccessStatusCode();
                var content = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<TResponse>(content);
            }
            catch (HttpRequestException httpEx)
            {
                string errorResponse = await httpEx.GetResponseContentAsync();
                _loggerService.LogError($"GET isteği hatası ({requestUri}): {httpEx.StatusCode} - {errorResponse}");
                throw new CloudClientException($"API hatası: {httpEx.StatusCode} - {GetErrorMessageFromJson(errorResponse)}", httpEx);
            }
            catch (Exception ex)
            {
                _loggerService.LogCritical($"GET isteği sırasında beklenmedik hata ({requestUri}): {ex.Message}", ex);
                throw new CloudClientException($"Beklenmedik bir hata oluştu: {ex.Message}", ex);
            }
        }

        public async Task<TResponse> PostAsync<TRequest, TResponse>(string requestUri, TRequest data)
        {
            SetAuthorizationHeader();
            try
            {
                _loggerService.LogDebug($"POST isteği gönderiliyor: {requestUri}");
                var json = JsonConvert.SerializeObject(data);
                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync(requestUri, content);
                response.EnsureSuccessStatusCode();

                var responseContent = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<TResponse>(responseContent);
            }
            catch (HttpRequestException httpEx)
            {
                string errorResponse = await httpEx.GetResponseContentAsync();
                _loggerService.LogError($"POST isteği hatası ({requestUri}): {httpEx.StatusCode} - {errorResponse}");
                throw new CloudClientException($"API hatası: {httpEx.StatusCode} - {GetErrorMessageFromJson(errorResponse)}", httpEx);
            }
            catch (Exception ex)
            {
                _loggerService.LogCritical($"POST isteği sırasında beklenmedik hata ({requestUri}): {ex.Message}", ex);
                throw new CloudClientException($"Beklenmedik bir hata oluştu: {ex.Message}", ex);
            }
        }

        // Diğer HTTP metodları (Put, Delete vb.) buraya eklenebilir.

        private string GetErrorMessageFromJson(string jsonErrorResponse)
        {
            try
            {
                dynamic errorObj = JsonConvert.DeserializeObject(jsonErrorResponse);
                if (errorObj?.detail != null)
                {
                    return errorObj.detail;
                }
                return "Bilinmeyen bir hata oluştu.";
            }
            catch
            {
                return "Yanıt formatı okunamadı.";
            }
        }
    }

    // Özel istisna sınıfı
    public class CloudClientException : Exception
    {
        public CloudClientException(string message) : base(message) { }
        public CloudClientException(string message, Exception innerException) : base(message, innerException) { }
    }
}
