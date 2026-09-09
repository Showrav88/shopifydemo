using System.Text.RegularExpressions;
using JewelryMS.Domain.DTOs.ProductComparison;

namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>
/// Headless Shopify SPAs (e.g. vibewear.com.bd) expose /category/{slug} pages that filter
/// products by title searchQuery in their JS — not 1:1 with Shopify collection handles.
/// </summary>
public static class ShopifyCatalog
{
    public const string ShopCategoryQueryParam = "_shopCategory";
    public const int PageSize = 250;
    private const int MaxPages = 40;

    private static readonly Regex TitleClauseRegex = new(
        @"title:\s*(.+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex CollectionProductsRegex = new(
        @"/collections/([a-z0-9][a-z0-9-]*)/products\.json",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly HashSet<string> InvalidHeadlessSlugs = new(StringComparer.OrdinalIgnoreCase)
    {
        "hash", "sha", "sha256", "sha-256", "label", "sortkey", "reverse", "name", "type",
    };

    private static readonly string[] ExcludedProductTypeHints =
    [
        "clothes", "clothing", "apparel", "pant", "pants", "trouser", "jeans", "shorts",
        "shirt", "top", "tee", "dress", "hoodie", "sweater", "skirt", "bag", "bags", "eyewear",
    ];

    public static bool IsInvalidHeadlessSlug(string slug)
        => string.IsNullOrWhiteSpace(slug)
           || slug.Length < 2
           || InvalidHeadlessSlugs.Contains(slug);

    public static string GetApiBase(string url)
    {
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri))
            return url.TrimEnd('/');
        return $"{uri.Scheme}://{uri.Host}";
    }

    public static string BuildTitleFilterFetchUrl(string apiBase, string categorySlug)
        => $"{apiBase.TrimEnd('/')}/products.json?limit={PageSize}&{ShopCategoryQueryParam}={Uri.EscapeDataString(categorySlug)}";

    public static bool TryParseTitleFilterFetchUrl(string url, out string productsApiUrl, out string categorySlug)
    {
        productsApiUrl = "";
        categorySlug   = "";
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) return false;

        foreach (var part in uri.Query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var eq = part.IndexOf('=');
            if (eq <= 0) continue;
            var key = part[..eq];
            if (!key.Equals(ShopCategoryQueryParam, StringComparison.OrdinalIgnoreCase)) continue;
            categorySlug = Uri.UnescapeDataString(part[(eq + 1)..]);
            break;
        }

        if (string.IsNullOrWhiteSpace(categorySlug)) return false;
        productsApiUrl = $"{uri.Scheme}://{uri.Host}/products.json?limit={PageSize}";
        return true;
    }

    public static bool TryParseCollectionHandle(string fetchUrl, out string handle)
    {
        handle = "";
        var m = CollectionProductsRegex.Match(fetchUrl);
        if (!m.Success) return false;
        handle = m.Groups[1].Value;
        return true;
    }

    /// <summary>Shopify-style title query, e.g. title:Necklace OR title:Pendant.</summary>
    public static bool MatchesTitleSearch(string? productTitle, string? searchQuery)
    {
        if (string.IsNullOrWhiteSpace(searchQuery)) return false;
        if (string.IsNullOrWhiteSpace(productTitle)) return false;

        var title = productTitle.ToLowerInvariant();
        foreach (var clause in searchQuery.Split(" OR ", StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            if (MatchesTitleClause(title, clause)) return true;
        }

        return false;
    }

    private static bool MatchesTitleClause(string titleLower, string clause)
    {
        var m = TitleClauseRegex.Match(clause);
        var term = (m.Success ? m.Groups[1].Value : clause).Trim().ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(term)) return false;

        if (term.Contains(' '))
            return titleLower.Contains(term);

        if (term is "waist" or "belly")
        {
            if (Regex.IsMatch(titleLower, @"\b(pant|pants|trouser|jeans|shorts|skirt|dress|top|tee|shirt)\b"))
                return false;
        }

        if (term == "ring" && Regex.IsMatch(titleLower, @"\bearring"))
            return false;

        return Regex.IsMatch(
            titleLower,
            $@"(?<![a-z0-9]){Regex.Escape(term)}(?![a-z0-9])",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    }

    public static bool IsJewelryCatalogProduct(NormalizedExternalProduct p)
    {
        var haystack = $"{p.CategoryRaw} {p.Name}".ToLowerInvariant();
        foreach (var hint in ExcludedProductTypeHints)
        {
            if (haystack.Contains(hint, StringComparison.Ordinal))
                return false;
        }

        return true;
    }

    /// <summary>
    /// Headless SPAs (vibewear) use /category/ pages and title searchQuery; classic Shopify uses
    /// /collections/ and always /products/{handle} — including custom domains on myshopify.com.
    /// </summary>
    public static bool UsesHeadlessProductPaths(string? displaySiteUrl, IEnumerable<CategoryMappingEntry>? mappings)
    {
        if (string.IsNullOrWhiteSpace(displaySiteUrl)) return false;
        if (displaySiteUrl.Contains(".myshopify.com", StringComparison.OrdinalIgnoreCase)) return false;
        if (mappings == null) return false;

        foreach (var m in mappings)
        {
            if (!string.IsNullOrWhiteSpace(m.TitleSearchQuery)) return true;
            if (TryParseTitleFilterFetchUrl(m.FetchUrl, out _, out _)) return true;
            if (m.ShopPageUrl.Contains("/category/", StringComparison.OrdinalIgnoreCase)) return true;
        }

        return false;
    }

    public static string? BuildStorefrontProductUrl(string? displaySiteUrl, string? handle, bool useSingularProductPath)
    {
        if (string.IsNullOrWhiteSpace(displaySiteUrl) || string.IsNullOrWhiteSpace(handle))
            return null;

        var storefront = ShopDiscoveryService.NormalizeBaseUrl(displaySiteUrl);
        var segment    = useSingularProductPath ? "product" : "products";
        return $"{storefront}/{segment}/{handle.Trim()}";
    }

    public static void ApplyStorefrontBuyUrls(
        IEnumerable<NormalizedExternalProduct> products,
        string? displaySiteUrl,
        bool useSingularProductPath)
    {
        if (string.IsNullOrWhiteSpace(displaySiteUrl)) return;

        foreach (var p in products)
        {
            var url = BuildStorefrontProductUrl(displaySiteUrl, p.ProductSlug, useSingularProductPath);
            if (!string.IsNullOrWhiteSpace(url))
                p.BuyUrl = url;
        }
    }

    private static async Task<List<NormalizedExternalProduct>> FetchSinglePageAsync(
        HttpClient client, string url, string? displaySiteUrl = null, bool useSingularProductPath = false)
    {
        try
        {
            using var res = await client.GetAsync(url);
            if (!res.IsSuccessStatusCode) return [];
            var json = await res.Content.ReadAsStringAsync();
            var products = ExternalProductParsers.Parse("shopify", json, displaySiteUrl, url).ToList();
            ApplyStorefrontBuyUrls(products, displaySiteUrl, useSingularProductPath);
            return products;
        }
        catch
        {
            return [];
        }
    }

    /// <summary>All store products — title-filter categories need the full catalog, not page 1 only.</summary>
    public static async Task<List<NormalizedExternalProduct>> FetchAllStoreProductsAsync(
        HttpClient client, string apiBase, string? displaySiteUrl = null, bool useSingularProductPath = false)
    {
        var baseUrl = apiBase.TrimEnd('/');
        var seen    = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var results = new List<NormalizedExternalProduct>();

        for (var page = 1; page <= MaxPages; page++)
        {
            var url = page == 1
                ? $"{baseUrl}/products.json?limit={PageSize}"
                : $"{baseUrl}/products.json?limit={PageSize}&page={page}";

            var batch = await FetchSinglePageAsync(client, url, displaySiteUrl, useSingularProductPath);
            if (batch.Count == 0) break;

            var added = 0;
            foreach (var p in batch)
            {
                if (seen.Add(p.ExternalId))
                {
                    results.Add(p);
                    added++;
                }
            }

            if (batch.Count < PageSize) break;
            if (added == 0) break;
        }

        return results;
    }

    public static async Task<List<NormalizedExternalProduct>> FetchCollectionProductsAsync(
        HttpClient client, string apiBase, string collectionHandle,
        string? displaySiteUrl = null, bool useSingularProductPath = false)
    {
        var baseUrl = apiBase.TrimEnd('/');
        var seen    = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var results = new List<NormalizedExternalProduct>();

        for (var page = 1; page <= MaxPages; page++)
        {
            var url = page == 1
                ? $"{baseUrl}/collections/{collectionHandle}/products.json?limit={PageSize}"
                : $"{baseUrl}/collections/{collectionHandle}/products.json?limit={PageSize}&page={page}";

            var batch = await FetchSinglePageAsync(client, url, displaySiteUrl, useSingularProductPath);
            if (batch.Count == 0) break;

            var added = 0;
            foreach (var p in batch)
            {
                if (seen.Add(p.ExternalId))
                {
                    results.Add(p);
                    added++;
                }
            }

            if (batch.Count < PageSize) break;
            if (added == 0) break;
        }

        return results;
    }

    public static async Task<List<NormalizedExternalProduct>> FetchProductsAsync(
        HttpClient client, string fetchUrl, string? displaySiteUrl = null)
    {
        if (TryParseTitleFilterFetchUrl(fetchUrl, out _, out _))
            return await FetchAllStoreProductsAsync(client, GetApiBase(fetchUrl), displaySiteUrl, useSingularProductPath: true);

        if (TryParseCollectionHandle(fetchUrl, out var handle))
            return await FetchCollectionProductsAsync(client, GetApiBase(fetchUrl), handle, displaySiteUrl);

        return await FetchSinglePageAsync(client, fetchUrl, displaySiteUrl);
    }

    /// <summary>
    /// Headless storefront categories filter by title searchQuery and show in-stock items only
    /// (matches vibewear.com.bd category page counts).
    /// </summary>
    public static IEnumerable<NormalizedExternalProduct> ApplyHeadlessFilters(
        IEnumerable<NormalizedExternalProduct> products, string? titleSearchQuery)
    {
        if (string.IsNullOrWhiteSpace(titleSearchQuery))
            return [];

        return products.Where(p =>
            p.InStock
            && MatchesTitleSearch(p.Name, titleSearchQuery));
    }

    public static async Task<List<NormalizedExternalProduct>> FetchForMappingAsync(
        HttpClient client, CategoryMappingEntry mapping, string? siteUrl = null,
        List<NormalizedExternalProduct>? storeCatalog = null, bool useSingularProductPath = false)
    {
        await EnsureMappingSearchQueryAsync(client, siteUrl, mapping);
        var apiBase = GetApiBase(mapping.FetchUrl);

        if (!string.IsNullOrWhiteSpace(mapping.TitleSearchQuery))
        {
            storeCatalog ??= await FetchAllStoreProductsAsync(client, apiBase, siteUrl, useSingularProductPath);
            return ApplyHeadlessFilters(storeCatalog, mapping.TitleSearchQuery).ToList();
        }

        if (TryParseCollectionHandle(mapping.FetchUrl, out var handle))
        {
            var products = await FetchCollectionProductsAsync(
                client, apiBase, handle, siteUrl, useSingularProductPath);
            return products.Where(p => p.InStock && IsJewelryCatalogProduct(p)).ToList();
        }

        if (TryParseTitleFilterFetchUrl(mapping.FetchUrl, out _, out _))
            return [];

        var page = await FetchSinglePageAsync(client, mapping.FetchUrl, siteUrl, useSingularProductPath);
        return page.Where(IsJewelryCatalogProduct).ToList();
    }

    public static async Task EnsureMappingSearchQueryAsync(
        HttpClient client, string? siteUrl, CategoryMappingEntry mapping)
    {
        if (!string.IsNullOrWhiteSpace(mapping.TitleSearchQuery)) return;
        if (string.IsNullOrWhiteSpace(siteUrl)) return;
        if (!TryParseTitleFilterFetchUrl(mapping.FetchUrl, out _, out var slug)) return;

        var configs = await ShopDiscoveryService.GetHeadlessCategoryConfigsAsync(client, siteUrl);
        if (configs.TryGetValue(slug, out var cfg) && !string.IsNullOrWhiteSpace(cfg.SearchQuery))
            mapping.TitleSearchQuery = cfg.SearchQuery;
    }

    public static async Task EnsureMappingSearchQueriesAsync(
        HttpClient client, string? siteUrl, IEnumerable<CategoryMappingEntry> mappings)
    {
        foreach (var m in mappings)
            await EnsureMappingSearchQueryAsync(client, siteUrl, m);
    }

    public static HashSet<string> BuildSyncUrlSet(string apiUrl, string[]? syncUrls)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (!string.IsNullOrWhiteSpace(apiUrl)) set.Add(apiUrl.Trim());
        if (syncUrls != null)
        {
            foreach (var u in syncUrls.Where(u => !string.IsNullOrWhiteSpace(u)))
                set.Add(u.Trim());
        }

        return set;
    }

    public static async Task<List<NormalizedExternalProduct>> FetchAllForMappingsAsync(
        HttpClient client,
        string? siteUrl,
        string apiUrl,
        string[]? syncUrls,
        IReadOnlyList<CategoryMappingEntry> categoryMappings,
        IReadOnlySet<string> allowedFocus)
    {
        await EnsureMappingSearchQueriesAsync(client, siteUrl, categoryMappings);

        var syncSet       = BuildSyncUrlSet(apiUrl, syncUrls);
        var ordered       = categoryMappings
            .Where(m => !string.IsNullOrWhiteSpace(m.FetchUrl) && syncSet.Contains(m.FetchUrl.Trim()))
            .ToList();
        var all           = new Dictionary<string, NormalizedExternalProduct>(StringComparer.Ordinal);
        List<NormalizedExternalProduct>? storeCatalog = null;
        var useSingularProductPath = UsesHeadlessProductPaths(siteUrl, ordered);

        foreach (var mapping in ordered)
        {
            if (!string.IsNullOrWhiteSpace(mapping.TitleSearchQuery))
                storeCatalog ??= await FetchAllStoreProductsAsync(
                    client, GetApiBase(mapping.FetchUrl), siteUrl, useSingularProductPath);

            var batch    = await FetchForMappingAsync(
                client, mapping, siteUrl, storeCatalog, useSingularProductPath);
            var staffCat = mapping.Category.Trim();
            foreach (var p in batch)
            {
                p.CategoryNormalized = staffCat;
                ProductAudienceDetector.Enrich(p);
                if (!allowedFocus.Contains(p.CategoryNormalized, StringComparer.OrdinalIgnoreCase))
                    continue;
                all[p.ExternalId] = p;
            }
        }

        return all.Values.ToList();
    }

    public static async Task<int> CountForHeadlessCategoryAsync(
        HttpClient client, string apiBase, HeadlessCategoryConfig config,
        List<NormalizedExternalProduct>? storeCatalog = null)
        => (await FetchForHeadlessCategoryAsync(client, apiBase, config, storeCatalog)).Count;

    public static async Task<List<NormalizedExternalProduct>> FetchForHeadlessCategoryAsync(
        HttpClient client, string apiBase, HeadlessCategoryConfig config,
        List<NormalizedExternalProduct>? storeCatalog = null)
    {
        if (!string.IsNullOrWhiteSpace(config.CollectionHandle))
        {
            var products = await FetchCollectionProductsAsync(client, apiBase, config.CollectionHandle);
            return products.Where(p => p.InStock && IsJewelryCatalogProduct(p)).ToList();
        }

        if (string.IsNullOrWhiteSpace(config.SearchQuery))
            return [];

        storeCatalog ??= await FetchAllStoreProductsAsync(client, apiBase);
        return ApplyHeadlessFilters(storeCatalog, config.SearchQuery).ToList();
    }
}

public sealed class HeadlessCategoryConfig
{
    public string Slug { get; set; } = "";
    public string Name { get; set; } = "";
    public string? SearchQuery { get; set; }
    public string? CollectionHandle { get; set; }
}
