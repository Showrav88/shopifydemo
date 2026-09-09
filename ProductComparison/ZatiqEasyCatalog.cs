using System.Net;
using System.Text.RegularExpressions;
using JewelryMS.Domain.DTOs.ProductComparison;

namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>
/// Zatiq Easy storefronts use /categories/{id} URLs (with query params) and embed real category
/// ids on each product page RSC payload. Sync filters by numeric category id, not collection name.
/// </summary>
public static class ZatiqEasyCatalog
{
    private static readonly HashSet<string> SkipCategoryNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "all", "categories", "best sellers", "weekend offer", "box", "premium bags", "perfume oil",
    };

    public static string SitemapUrl(string baseUrl)
        => $"{baseUrl.TrimEnd('/')}/api/sitemaps.xml";

    /// <summary>Same URL for sync key and shop browse link — Zatiq uses numeric category id.</summary>
    public static string CategoryBrowseUrl(string baseUrl, int categoryId)
        => $"{baseUrl.TrimEnd('/')}/categories/{categoryId}?selected_category={categoryId}&category_id={categoryId}";

    public static string CategoryFetchUrl(string baseUrl, int categoryId)
        => CategoryBrowseUrl(baseUrl, categoryId);

    public static bool IsZatiqPlatform(string platform)
        => platform.Equals("zatiq", StringComparison.OrdinalIgnoreCase);

    public static bool IsZatiqApi(string platform, string? apiUrl)
    {
        if (IsZatiqPlatform(platform))
            return true;
        if (string.IsNullOrWhiteSpace(apiUrl)) return false;
        return apiUrl.Contains("/api/sitemaps.xml", StringComparison.OrdinalIgnoreCase)
            || IsCategoryFetchUrl(apiUrl);
    }

    public static bool IsCategoryFetchUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url)) return false;
        return Regex.IsMatch(url, @"/categories/\d+", RegexOptions.IgnoreCase);
    }

    public static bool TryParseCategoryId(string? url, out int categoryId)
    {
        categoryId = 0;
        if (string.IsNullOrWhiteSpace(url)) return false;
        var m = Regex.Match(url, @"/categories/(\d+)", RegexOptions.IgnoreCase);
        if (!m.Success || !int.TryParse(m.Groups[1].Value, out categoryId))
            return false;
        return true;
    }

    public static bool UsesCategoryFeeds(string platform, IEnumerable<string> urls)
        => IsZatiqPlatform(platform)
           && urls.Any(u => IsCategoryFetchUrl(u));

    /// <summary>Keep products tagged with Zatiq category id (from product page RSC).</summary>
    public static IEnumerable<NormalizedExternalProduct> FilterForCategoryId(
        IEnumerable<NormalizedExternalProduct> catalog, int categoryId)
    {
        var needle = $"{categoryId}|";
        return catalog.Where(p =>
            !string.IsNullOrEmpty(p.CategoryRaw)
            && p.CategoryRaw.Split(',', StringSplitOptions.RemoveEmptyEntries)
                .Any(part => part.StartsWith(needle, StringComparison.Ordinal)));
    }

    public static IEnumerable<string> ExtractProductUrlsFromSitemap(string xml, string baseUrl)
    {
        if (string.IsNullOrWhiteSpace(xml)) yield break;
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (Match m in Regex.Matches(xml, @"<loc>\s*(https?://[^<]+/products/\d+)\s*</loc>", RegexOptions.IgnoreCase))
        {
            var url = m.Groups[1].Value.Trim();
            if (seen.Add(url))
                yield return url;
        }

        if (seen.Count == 0)
        {
            foreach (Match m in Regex.Matches(xml, @"<loc>\s*([^<]*?/products/\d+)\s*</loc>", RegexOptions.IgnoreCase))
            {
                var path = m.Groups[1].Value.Trim();
                var url = path.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                    ? path
                    : $"{baseUrl.TrimEnd('/')}{(path.StartsWith('/') ? path : "/" + path)}";
                if (seen.Add(url))
                    yield return url;
            }
        }
    }

    /// <summary>Categories with real product counts from shopAllCategoryFlattenList in RSC payload.</summary>
    public static List<DiscoveredShopCategoryDto> ExtractCategoriesFromRsc(string rsc, string baseUrl)
    {
        var categories = new List<DiscoveredShopCategoryDto>();
        var seen = new HashSet<int>();

        foreach (Match m in Regex.Matches(
            rsc,
            @"\{""id"":(\d+),""name"":""([^""]+)""[^}]*""total_inventories"":(\d+)",
            RegexOptions.IgnoreCase))
        {
            if (!int.TryParse(m.Groups[1].Value, out var id) || seen.Contains(id)) continue;
            if (!int.TryParse(m.Groups[3].Value, out var count) || count <= 0) continue;

            var rawName = WebUtility.HtmlDecode(m.Groups[2].Value).Trim();
            if (string.IsNullOrWhiteSpace(rawName) || SkipCategoryNames.Contains(rawName)) continue;

            seen.Add(id);
            var slug   = Slugify(rawName);
            var mapped = CategoryNormalizer.Normalize(rawName, rawName, slug);
            var browse = CategoryBrowseUrl(baseUrl, id);

            categories.Add(new DiscoveredShopCategoryDto
            {
                ExternalId     = id.ToString(),
                Slug           = slug,
                Name           = rawName,
                ProductCount   = count,
                MappedCategory = mapped,
                FetchUrl       = browse,
                ShopPageUrl    = browse,
                Suggested      = CategoryNormalizer.IsFocusCategory(mapped),
            });
        }

        return categories;
    }

    private static string Slugify(string name)
    {
        var s = name.ToLowerInvariant();
        s = Regex.Replace(s, @"[^a-z0-9]+", "-");
        return s.Trim('-');
    }
}
