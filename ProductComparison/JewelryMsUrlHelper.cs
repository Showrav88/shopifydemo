namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>
/// Buy/checkout links must point at the React storefront, not the .NET API host.
/// </summary>
public static class JewelryMsUrlHelper
{
    private const string DefaultProductionFrontend = "https://jewelryms-frontend.onrender.com";

    /// <summary>
    /// Customer-facing base URL (no trailing slash). Override via JEWELRYMS_PUBLIC_FRONTEND_URL env var.
    /// </summary>
    public static string ResolveCustomerBaseUrl(string? siteUrl, string? apiUrl)
    {
        var configured = Environment.GetEnvironmentVariable("JEWELRYMS_PUBLIC_FRONTEND_URL")?.Trim()
            ?? Environment.GetEnvironmentVariable("App__FrontendBaseUrl")?.Trim();
        var fallback   = string.IsNullOrWhiteSpace(configured) ? DefaultProductionFrontend : configured.TrimEnd('/');

        if (string.IsNullOrWhiteSpace(siteUrl) || LooksLikeApiBase(siteUrl, apiUrl))
            return fallback;

        return siteUrl.Trim().TrimEnd('/');
    }

    public static string? BuildProductUrl(string? siteUrl, string? apiUrl, string externalId)
    {
        if (string.IsNullOrWhiteSpace(apiUrl) || !Guid.TryParse(externalId, out _))
            return null;

        var slug = ExtractSlug(apiUrl);
        if (string.IsNullOrWhiteSpace(slug)) return null;

        var baseUrl = ResolveCustomerBaseUrl(siteUrl, apiUrl);
        return $"{baseUrl}/imitation-store/{slug}/product/{externalId}";
    }

    /// <summary>/imitation-store/{slug}/checkout?productId=… — matches the live imitation store checkout route.</summary>
    public static string? BuildCheckoutUrl(string? siteUrl, string? apiUrl, string externalId)
    {
        var slug = ExtractSlug(apiUrl);
        if (string.IsNullOrWhiteSpace(slug) || !Guid.TryParse(externalId, out _))
            return null;

        var baseUrl = ResolveCustomerBaseUrl(siteUrl, apiUrl);
        return $"{baseUrl}/imitation-store/{slug}/checkout?productId={externalId}";
    }

    /// <summary>Rewrite cached links that mistakenly use the API host.</summary>
    public static string? NormalizeStoreUrl(string? url, string? siteUrl, string? apiUrl)
    {
        if (string.IsNullOrWhiteSpace(url)) return url;

        var marker = "/imitation-store/";
        var idx    = url.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
        if (idx < 0) return url;

        if (!LooksLikeApiBase(url[..idx], apiUrl) && !url.Contains("jewelrymsv1.onrender.com", StringComparison.OrdinalIgnoreCase)
            && !url.Contains("localhost:5284", StringComparison.OrdinalIgnoreCase))
            return url;

        var baseUrl = ResolveCustomerBaseUrl(siteUrl, apiUrl);
        return baseUrl + url[idx..];
    }

    public static string? ExtractSlug(string? apiUrl)
    {
        if (string.IsNullOrEmpty(apiUrl)) return null;
        const string marker = "/imitation-store/";
        var idx = apiUrl.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
        if (idx < 0) return null;
        var rest  = apiUrl[(idx + marker.Length)..];
        var slash = rest.IndexOf('/');
        return slash > 0 ? rest[..slash] : rest.Split('?')[0];
    }

    private static bool LooksLikeApiBase(string url, string? apiUrl)
    {
        if (string.IsNullOrWhiteSpace(url)) return true;
        if (url.Contains("/api", StringComparison.OrdinalIgnoreCase)) return true;
        if (url.Contains("jewelrymsv1.onrender.com", StringComparison.OrdinalIgnoreCase)) return true;
        if (url.Contains("localhost:5284", StringComparison.OrdinalIgnoreCase)) return true;

        if (!Uri.TryCreate(url.TrimEnd('/'), UriKind.Absolute, out var siteUri)) return false;

        if (siteUri.Port == 5284) return true;

        if (!string.IsNullOrEmpty(apiUrl) && Uri.TryCreate(apiUrl, UriKind.Absolute, out var apiUri)
            && siteUri.Host.Equals(apiUri.Host, StringComparison.OrdinalIgnoreCase))
            return true;

        return false;
    }
}
