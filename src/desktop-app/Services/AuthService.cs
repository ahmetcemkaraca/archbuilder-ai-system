using System;
using System.Net.Http;
using System.Security;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using ArchBuilder.Models;
using ArchBuilder.Core;

namespace ArchBuilder.Services
{
    public class AuthService
    {
        private readonly HttpClient _httpClient;
        private readonly LoggerService _loggerService;

        public UserSession CurrentUserSession { get; private set; }

        public AuthService()
        {
            _httpClient = new HttpClient();
            _httpClient.BaseAddress = new Uri("http://localhost:8000/api/"); // Cloud Server API adresi
            _loggerService = LoggerService.Instance;
        }

        public async Task<LoginResult> LoginAsync(string email, SecureString password)
        {
            try
            {
                string plainPassword = SecureStringToString(password);
                var loginRequest = new { username = email, password = plainPassword };
                var content = new StringContent(JsonConvert.SerializeObject(loginRequest), Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync("auth/login", content);
                response.EnsureSuccessStatusCode();

                var responseContent = await response.Content.ReadAsStringAsync();
                var tokenResponse = JsonConvert.DeserializeObject<TokenResponse>(responseContent);

                CurrentUserSession = new UserSession(
                    tokenResponse.UserId,
                    email,
                    tokenResponse.FirstName,
                    tokenResponse.LastName,
                    tokenResponse.AccessToken,
                    tokenResponse.ApiKey,
                    tokenResponse.SubscriptionTier,
                    tokenResponse.UsageRemaining
                );

                _loggerService.LogInfo($"Kullanıcı girişi başarılı: {email}");
                return LoginResult.SuccessResult();
            }
            catch (HttpRequestException httpEx)
            {
                string errorResponse = await httpEx.GetResponseContentAsync();
                _loggerService.LogError($"Giriş hatası (HTTP): {httpEx.StatusCode} - {errorResponse}");
                return LoginResult.FailResult($"Giriş başarısız: {GetErrorMessageFromJson(errorResponse)}");
            }
            catch (Exception ex)
            {
                _loggerService.LogCritical($"Giriş sırasında beklenmedik hata: {ex.Message}");
                return LoginResult.FailResult($"Beklenmedik bir hata oluştu: {ex.Message}");
            }
        }

        public async Task<LoginResult> RegisterAsync(string firstName, string lastName, string email, SecureString password)
        {
            try
            {
                string plainPassword = SecureStringToString(password);
                var registerRequest = new
                {
                    first_name = firstName,
                    last_name = lastName,
                    email = email,
                    password = plainPassword
                };
                var content = new StringContent(JsonConvert.SerializeObject(registerRequest), Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync("auth/register", content);
                response.EnsureSuccessStatusCode();

                var responseContent = await response.Content.ReadAsStringAsync();
                var userResponse = JsonConvert.DeserializeObject<UserResponse>(responseContent);

                _loggerService.LogInfo($"Kullanıcı kaydı başarılı: {email}");
                return LoginResult.SuccessResult();
            }
            catch (HttpRequestException httpEx)
            {
                string errorResponse = await httpEx.GetResponseContentAsync();
                _loggerService.LogError($"Kayıt hatası (HTTP): {httpEx.StatusCode} - {errorResponse}");
                return LoginResult.FailResult($"Kayıt başarısız: {GetErrorMessageFromJson(errorResponse)}");
            }
            catch (Exception ex)
            {
                _loggerService.LogCritical($"Kayıt sırasında beklenmedik hata: {ex.Message}");
                return LoginResult.FailResult($"Beklenmedik bir hata oluştu: {ex.Message}");
            }
        }

        private string SecureStringToString(SecureString secureString)
        {
            if (secureString == null)
                return string.Empty;

            IntPtr unmanagedString = IntPtr.Zero;
            try
            {
                unmanagedString = System.Runtime.InteropServices.Marshal.SecureStringToGlobalAllocUnicode(secureString);
                return System.Runtime.InteropServices.Marshal.PtrToStringUni(unmanagedString);
            }
            finally
            {
                System.Runtime.InteropServices.Marshal.ZeroFreeGlobalAllocUnicode(unmanagedString);
            }
        }

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

        // Helper classes for API responses
        public class TokenResponse
        {
            [JsonProperty("access_token")]
            public string AccessToken { get; set; }

            [JsonProperty("token_type")]
            public string TokenType { get; set; }

            [JsonProperty("api_key")]
            public string ApiKey { get; set; }

            [JsonProperty("subscription_tier")]
            public string SubscriptionTier { get; set; }

            [JsonProperty("usage_remaining")]
            public int UsageRemaining { get; set; }

            [JsonProperty("user_id")]
            public Guid UserId { get; set; }

            [JsonProperty("first_name")]
            public string FirstName { get; set; }

            [JsonProperty("last_name")]
            public string LastName { get; set; }
        }

        public class UserResponse
        {
            public Guid Id { get; set; }
            public string Email { get; set; }
            
            [JsonProperty("first_name")]
            public string FirstName { get; set; }
            
            [JsonProperty("last_name")]
            public string LastName { get; set; }

            [JsonProperty("is_active")]
            public bool IsActive { get; set; }
            
            [JsonProperty("is_verified")]
            public bool IsVerified { get; set; }
            
            public string Role { get; set; }

            [JsonProperty("tenant_id")]
            public Guid TenantId { get; set; }
            
            [JsonProperty("created_at")]
            public DateTime CreatedAt { get; set; }

            [JsonProperty("last_login")]
            public DateTime? LastLogin { get; set; }
        }

        public class LoginResult
        {
            public bool Success { get; set; }
            public string Message { get; set; }

            public static LoginResult SuccessResult() => new LoginResult { Success = true };
            public static LoginResult FailResult(string message) => new LoginResult { Success = false, Message = message };
        }
    }
}

