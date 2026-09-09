namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>
/// Daraz BD exposes catalog JSON via <c>?ajax=true</c> on category and search pages (not the Open Platform seller API).
/// </summary>
public static class DarazCatalogUrls
{
    public const string DefaultSite = "https://www.daraz.com.bd";

    public static string JewelryDiscoveryProbe(string? siteUrl = null)
    {
        var baseUrl = (siteUrl ?? DefaultSite).TrimEnd('/');
        return $"{baseUrl}/catalog/?ajax=true&isFirstRequest=true&q=jewelry&page=1";
    }

    public static string CategoryFetchUrl(string slug, string? siteUrl = null, int page = 1)
    {
        var baseUrl = (siteUrl ?? DefaultSite).TrimEnd('/');
        var slugPath = slug.Trim('/');
        if (page <= 1)
            return $"{baseUrl}/{slugPath}/?ajax=true&isFirstRequest=true&page=1";
        return $"{baseUrl}/{slugPath}/?ajax=true&page={page}";
    }

    public static string CategoryShopPage(string slug, string? siteUrl = null)
    {
        var baseUrl = (siteUrl ?? DefaultSite).TrimEnd('/');
        return $"{baseUrl}/{slug.Trim('/')}/";
    }

    public static string WithPage(string apiUrl, int page)
    {
        if (page <= 1) return apiUrl;
        if (!Uri.TryCreate(apiUrl, UriKind.Absolute, out var uri))
            return apiUrl;

        var path = uri.GetLeftPart(UriPartial.Path).TrimEnd('/');
        var pairs = uri.Query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries)
            .Select(p => p.Split('=', 2))
            .Where(p => p.Length > 0 && !p[0].Equals("isFirstRequest", StringComparison.OrdinalIgnoreCase)
                        && !p[0].Equals("page", StringComparison.OrdinalIgnoreCase))
            .Select(p => p.Length == 2 ? $"{p[0]}={p[1]}" : p[0])
            .ToList();
        pairs.Add("ajax=true");
        pairs.Add($"page={page}");
        return $"{path}/?{string.Join("&", pairs)}";
    }
}
