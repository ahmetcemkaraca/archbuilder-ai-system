using System;
using System.Net.Http;
using System.Threading.Tasks;

namespace ArchBuilder.Core
{
    public static class HttpResponseExtensions
    {
        public static async Task<string> GetResponseContentAsync(this HttpRequestException ex)
        {
            if (ex.Data.Contains("responseContent"))
            {
                return ex.Data["responseContent"] as string;
            }
            
            if (ex.Response != null)
            {
                string content = await ex.Response.Content.ReadAsStringAsync();
                ex.Data["responseContent"] = content; // Cache for future use
                return content;
            }
            return "No response content.";
        }
    }
}

