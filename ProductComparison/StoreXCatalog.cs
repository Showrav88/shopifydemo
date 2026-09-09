using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using JewelryMS.Domain.DTOs.ProductComparison;

namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>
/// StoreX v4 storefronts (Next.js, api-live.storex.com.bd) expose products at
/// /products/{slug}, categories at /categories/{slug}, and list both in /sitemap.xml.
/// Product pages use product:* meta tags; live stock/price comes from api-live.storex.com.bd (x-tenant-id).
/// </summary>
public static class StoreXCatalog
{
    public const string ApiBase = "https://api-live.storex.com.bd";
    /// <summary>StoreX v4 categories endpoint rejects page sizes above 50.</summary>
    public const int MaxCategoriesPageSize = 50;
    public const int MaxProductsPageSize = 100;
    private static readonly HashSet<string> SkipCategorySlugs = new(StringComparer.OrdinalIgnoreCase)
    {
        "all", "categories", "products", "blogs", "checkout", "cart", "account",
        "sale", "new", "featured", "best-seller", "best-sellers",
    };

    public static string SitemapUrl(string baseUrl)
        => $"{baseUrl.TrimEnd('/')}/sitemap.xml";

    public static string CategoryBrowseUrl(string baseUrl, string slug)
        => $"{baseUrl.TrimEnd('/')}/categories/{slug}";

    public static bool IsStoreXPlatform(string platform)
        => platform.Equals("storex", StringComparison.OrdinalIgnoreCase);

    public static bool IsStoreXSitemapUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url)) return false;
        return url.Contains("/sitemap.xml", StringComparison.OrdinalIgnoreCase)
            && !url.Contains("/api/sitemaps.xml", StringComparison.OrdinalIgnoreCase);
    }

    public static bool IsStoreXCategoryUrl(string? url)
        => TryParseCategorySlug(url, out _);

    public static bool IsStoreXApi(string platform, string? apiUrl)
    {
        if (IsStoreXPlatform(platform))
            return true;
        return IsStoreXSitemapUrl(apiUrl) || IsStoreXCategoryUrl(apiUrl);
    }

    public static bool TryParseCategorySlug(string? url, out string slug)
    {
        slug = "";
        if (string.IsNullOrWhiteSpace(url)) return false;
        var m = Regex.Match(url, @"/categories/([a-z0-9][a-z0-9\-]*)", RegexOptions.IgnoreCase);
        if (!m.Success) return false;
        slug = m.Groups[1].Value.Trim();
        return !string.IsNullOrWhiteSpace(slug);
    }

    public static IEnumerable<string> ExtractProductUrlsFromSitemap(string xml, string baseUrl)
    {
        if (string.IsNullOrWhiteSpace(xml)) yield break;

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (Match m in Regex.Matches(
            xml,
            @"<loc>\s*(https?://[^<]+/products/[a-z0-9][a-z0-9\-]*)\s*</loc>",
            RegexOptions.IgnoreCase))
        {
            var url = m.Groups[1].Value.Trim();
            if (seen.Add(url))
                yield return url;
        }

        if (seen.Count > 0) yield break;

        foreach (Match m in Regex.Matches(
            xml,
            @"<loc>\s*([^<]*?/products/[a-z0-9][a-z0-9\-]*)\s*</loc>",
            RegexOptions.IgnoreCase))
        {
            var path = m.Groups[1].Value.Trim();
            var url = path.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                ? path
                : $"{baseUrl.TrimEnd('/')}{(path.StartsWith('/') ? path : "/" + path)}";
            if (seen.Add(url))
                yield return url;
        }
    }

    public static IEnumerable<(string Slug, string BrowseUrl)> ExtractCategorySlugsFromSitemap(
        string xml, string baseUrl)
    {
        if (string.IsNullOrWhiteSpace(xml)) yield break;

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (Match m in Regex.Matches(
            xml,
            @"<loc>\s*(https?://[^<]+/categories/([a-z0-9][a-z0-9\-]*))\s*</loc>",
            RegexOptions.IgnoreCase))
        {
            var slug = m.Groups[2].Value.Trim();
            if (!seen.Add(slug) || ShouldSkipCategorySlug(slug)) continue;
            yield return (slug, m.Groups[1].Value.Trim());
        }

        if (seen.Count > 0) yield break;

        foreach (Match m in Regex.Matches(
            xml,
            @"<loc>\s*([^<]*?/categories/([a-z0-9][a-z0-9\-]*))\s*</loc>",
            RegexOptions.IgnoreCase))
        {
            var slug = m.Groups[2].Value.Trim();
            if (!seen.Add(slug) || ShouldSkipCategorySlug(slug)) continue;

            var path = m.Groups[1].Value.Trim();
            var browse = path.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                ? path
                : $"{baseUrl.TrimEnd('/')}{(path.StartsWith('/') ? path : "/" + path)}";
            yield return (slug, browse);
        }
    }

    /// <summary>Build Analyze-shop rows from sitemap category URLs; counts use product slug heuristics.</summary>
    public static List<DiscoveredShopCategoryDto> ExtractCategoriesFromSitemap(string xml, string baseUrl)
    {
        var productUrls = ExtractProductUrlsFromSitemap(xml, baseUrl).ToList();
        var categories  = new List<DiscoveredShopCategoryDto>();

        foreach (var (slug, browse) in ExtractCategorySlugsFromSitemap(xml, baseUrl))
        {
            var displayName = SlugToDisplayName(slug);
            var mapped      = CategoryNormalizer.Normalize(displayName, displayName, slug);
            var count       = productUrls.Count(u => ProductUrlMatchesCategorySlug(u, slug));

            categories.Add(new DiscoveredShopCategoryDto
            {
                ExternalId     = slug,
                Slug           = slug,
                Name           = displayName,
                ProductCount   = count,
                MappedCategory = mapped,
                FetchUrl       = browse,
                ShopPageUrl    = browse,
                Suggested      = CategoryNormalizer.IsFocusCategory(mapped) && count > 0,
            });
        }

        return categories;
    }

    /// <summary>Filter a full StoreX catalog fetch to one storefront category slug.</summary>
    public static IEnumerable<NormalizedExternalProduct> FilterForCategorySlug(
        IEnumerable<NormalizedExternalProduct> catalog, string categorySlug, string? mappedCategory = null)
    {
        foreach (var p in catalog)
        {
            if (ProductBelongsToStoreCategory(p, categorySlug))
                yield return p;
        }
    }

    public static bool ProductBelongsToStoreCategory(NormalizedExternalProduct p, string categorySlug)
    {
        var storeCats = ParseStoreCategorySlugsFromRaw(p.CategoryRaw);
        if (storeCats.Any(c => c.Equals(categorySlug, StringComparison.OrdinalIgnoreCase)))
            return true;

        var productSlug = ExtractProductSlug(p.BuyUrl) ?? "";
        return ProductSlugMatchesCategorySlug(productSlug, p.Name, categorySlug);
    }

    public static int CountProductsForCatalogCategory(
        IEnumerable<NormalizedExternalProduct> catalog, string categorySlug)
        => catalog.Count(p => ProductBelongsToStoreCategory(p, categorySlug));

    /// <summary>
    /// Accurate StoreX category count without loading the full enriched catalog.
    /// Matches slug/name first (fast); detail API only when the name does not hint the category.
    /// </summary>
    public static async Task<int> CountProductsForStoreCategoryAsync(
        HttpClient client, string baseUrl, string tenantId, string categorySlug)
    {
        var counts = await CountAllStoreCategoriesAsync(client, baseUrl, tenantId, [categorySlug]);
        return counts.GetValueOrDefault(categorySlug);
    }

    /// <summary>One list-API pass + detail fallback for unmatched rows; used by Analyze.</summary>
    public static async Task<Dictionary<string, int>> CountAllStoreCategoriesAsync(
        HttpClient client, string baseUrl, string tenantId, IEnumerable<string> categorySlugs)
    {
        var members = await MapProductsByStoreCategoryAsync(client, baseUrl, tenantId, categorySlugs);
        return members.ToDictionary(kv => kv.Key, kv => kv.Value.Count, StringComparer.OrdinalIgnoreCase);
    }

    /// <summary>Product slugs per storefront category — same rules as Analyze counts.</summary>
    public static async Task<Dictionary<string, HashSet<string>>> MapProductsByStoreCategoryAsync(
        HttpClient client, string baseUrl, string tenantId, IEnumerable<string> categorySlugs)
    {
        var targets = categorySlugs
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
        var members = targets.ToDictionary(
            s => s, _ => new HashSet<string>(StringComparer.OrdinalIgnoreCase), StringComparer.OrdinalIgnoreCase);
        if (targets.Count == 0) return members;

        var detailCandidates = new List<(string Slug, string Name)>();

        for (var page = 1; page <= 20; page++)
        {
            var json = await GetJsonWithTenantAsync(client, ProductsAllUrl(page, MaxProductsPageSize), tenantId, baseUrl);
            if (string.IsNullOrWhiteSpace(json)) break;

            using var doc = JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("data", out var data)
                || !data.TryGetProperty("products", out var arr)
                || arr.ValueKind != JsonValueKind.Array)
                break;

            var batch = 0;
            foreach (var p in arr.EnumerateArray())
            {
                var slug = p.TryGetProperty("slug", out var s) ? s.GetString() ?? "" : "";
                var name = p.TryGetProperty("title", out var t) ? t.GetString() ?? "" : slug;
                if (string.IsNullOrWhiteSpace(slug)) continue;

                batch++;
                var matched = false;
                foreach (var cat in targets)
                {
                    if (!ProductSlugMatchesCategorySlug(slug, name, cat)) continue;
                    members[cat].Add(slug);
                    matched = true;
                }

                if (!matched)
                    detailCandidates.Add((slug, name));
            }

            if (batch == 0) break;
            if (arr.GetArrayLength() < MaxProductsPageSize) break;
        }

        if (detailCandidates.Count == 0) return members;

        using var gate = new SemaphoreSlim(15);
        var tasks = detailCandidates.Select(async item =>
        {
            await gate.WaitAsync();
            try
            {
                for (var attempt = 1; attempt <= 2; attempt++)
                {
                    try
                    {
                        var json = await GetJsonWithTenantAsync(client, ProductApiUrl(item.Slug), tenantId, baseUrl);
                        if (string.IsNullOrWhiteSpace(json)) return;

                        using var doc = JsonDocument.Parse(json);
                        if (!doc.RootElement.TryGetProperty("data", out var data)) return;

                        foreach (var cat in ParseStoreXCategorySlugs(data))
                        {
                            if (members.ContainsKey(cat))
                                members[cat].Add(item.Slug);
                        }
                        return;
                    }
                    catch when (attempt < 2)
                    {
                        await Task.Delay(attempt * 150);
                    }
                }
            }
            finally
            {
                gate.Release();
            }
        });

        await Task.WhenAll(tasks);
        return members;
    }

    /// <summary>Resolve Analyze member slugs to products — fetches detail API when missing from catalog parse.</summary>
    public static async Task<List<NormalizedExternalProduct>> ResolveMemberProductsAsync(
        HttpClient client, string baseUrl, string siteUrl, string tenantId,
        IEnumerable<NormalizedExternalProduct> catalog, IReadOnlySet<string> memberSlugs)
    {
        var bySlug = catalog
            .Select(p => (Slug: ExtractProductSlug(p.BuyUrl), Product: p))
            .Where(x => !string.IsNullOrWhiteSpace(x.Slug))
            .GroupBy(x => x.Slug!, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(g => g.Key, g => g.First().Product, StringComparer.OrdinalIgnoreCase);

        var results = new List<NormalizedExternalProduct>();
        var missing = new List<string>();

        foreach (var slug in memberSlugs)
        {
            if (bySlug.TryGetValue(slug, out var cached))
                results.Add(cached);
            else
                missing.Add(slug);
        }

        if (missing.Count == 0) return results;

        using var gate = new SemaphoreSlim(10);
        var fetched = new List<NormalizedExternalProduct>();
        var tasks = missing.Select(async slug =>
        {
            await gate.WaitAsync();
            try
            {
                for (var attempt = 1; attempt <= 2; attempt++)
                {
                    try
                    {
                        var json = await GetJsonWithTenantAsync(client, ProductApiUrl(slug), tenantId, baseUrl);
                        if (string.IsNullOrWhiteSpace(json)) return;

                        var p = ExternalProductParsers.ParseStoreXProductsApi(json, siteUrl).FirstOrDefault();
                        if (p != null)
                            lock (fetched) { fetched.Add(p); }
                        return;
                    }
                    catch when (attempt < 2)
                    {
                        await Task.Delay(attempt * 150);
                    }
                }
            }
            finally
            {
                gate.Release();
            }
        });

        await Task.WhenAll(tasks);
        results.AddRange(fetched);
        return results;
    }

    public const string StoreCategoryRawPrefix = "storex:";

    public static List<string> ParseStoreXCategorySlugs(JsonElement product)
    {
        var slugs = new List<string>();
        if (!product.TryGetProperty("category", out var cat)) return slugs;

        if (cat.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in cat.EnumerateArray())
                AddStoreXCategorySlug(item, slugs);
            return slugs;
        }

        if (cat.ValueKind == JsonValueKind.Object)
            AddStoreXCategorySlug(cat, slugs);

        return slugs;
    }

    private static void AddStoreXCategorySlug(JsonElement item, List<string> slugs)
    {
        if (!item.TryGetProperty("slug", out var slugEl)) return;
        var slug = slugEl.GetString()?.Trim();
        if (!string.IsNullOrWhiteSpace(slug))
            slugs.Add(slug);
    }

    public static List<string> ParseStoreCategorySlugsFromRaw(string? categoryRaw)
    {
        if (string.IsNullOrWhiteSpace(categoryRaw)) return [];
        var first = categoryRaw.Split('|')[0].Trim();
        if (!first.StartsWith(StoreCategoryRawPrefix, StringComparison.OrdinalIgnoreCase))
            return [];

        var payload = first[StoreCategoryRawPrefix.Length..];
        if (string.IsNullOrWhiteSpace(payload)) return [];
        return payload.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).ToList();
    }

    public static string FormatCategoryRaw(IReadOnlyList<string> storeSlugs, string productSlug, string name)
    {
        if (storeSlugs.Count > 0)
            return $"{StoreCategoryRawPrefix}{string.Join(",", storeSlugs)}|{productSlug}|{name}";
        return $"{productSlug}|{name}";
    }

    public static int CountProductsForCategorySlug(IEnumerable<string> productUrls, string categorySlug)
        => productUrls.Count(u => ProductUrlMatchesCategorySlug(u, categorySlug));

    public static bool ProductUrlMatchesCategorySlug(string productUrl, string categorySlug)
    {
        var slug = ExtractProductSlug(productUrl);
        return !string.IsNullOrWhiteSpace(slug)
            && ProductSlugMatchesCategorySlug(slug, null, categorySlug);
    }

    public static bool ProductSlugMatchesCategorySlug(
        string productSlug, string? productName, string categorySlug)
    {
        var haystack = $"{productSlug} {productName}".ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(haystack)) return false;

        foreach (var token in CategorySlugTokens(categorySlug))
        {
            if (categorySlug is "ring-set" or "rings" && haystack.Contains("earring", StringComparison.Ordinal))
                continue;

            if (token.Length < 3)
            {
                if (Regex.IsMatch(haystack, $@"(?<![a-z]){Regex.Escape(token)}(?![a-z])"))
                    return true;
            }
            else if (haystack.Contains(token, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    private static IEnumerable<string> CategorySlugTokens(string categorySlug)
    {
        var slug = categorySlug.ToLowerInvariant();
        yield return slug.Replace("-", "");

        switch (slug)
        {
            case "necklace":
            case "necklaces":
                yield return "necklace";
                yield return "choker";
                break;
            case "bracelet":
            case "bracelets":
                yield return "bracelet";
                yield return "bangle";
                break;
            case "ring-set":
            case "rings":
                yield return "ring";
                break;
            case "anklet":
            case "anklets":
                yield return "anklet";
                yield return "ankle";
                break;
            case "earrings":
            case "earring":
                yield return "earring";
                break;
            case "belly-chain":
                yield return "belly-chain";
                yield return "bellychain";
                yield return "belly";
                yield return "waist";
                break;
            case "jewllery-set":
            case "jewellery-set":
            case "jewelry-set":
                yield return "set";
                break;
            default:
                yield return slug;
                break;
        }
    }

    private static bool ShouldSkipCategorySlug(string slug)
    {
        if (SkipCategorySlugs.Contains(slug)) return true;
        // Price-band collections like 50-to-99-tk
        return Regex.IsMatch(slug, @"^\d+(-to-\d+)?(-tk)?$", RegexOptions.IgnoreCase);
    }

    private static string SlugToDisplayName(string slug)
    {
        var words = slug.Split('-', StringSplitOptions.RemoveEmptyEntries);
        return string.Join(" ", words.Select(w =>
            w.Length > 0 ? char.ToUpperInvariant(w[0]) + w[1..] : w));
    }

    public static string? ExtractProductSlug(string? url)
    {
        if (string.IsNullOrWhiteSpace(url)) return null;
        var m = Regex.Match(url, @"/products/([a-z0-9][a-z0-9\-]*)", RegexOptions.IgnoreCase);
        return m.Success ? m.Groups[1].Value : url.TrimEnd('/').Split('/').LastOrDefault();
    }

    public static string ProductsAllUrl(int page, int limit)
        => $"{ApiBase}/api/v4/products/all?page={page}&limit={limit}";

    public static string CategoriesAllUrl(int page, int limit)
        => $"{ApiBase}/api/v4/categories/all?page={page}&limit={limit}";

    public static string ProductApiUrl(string slug)
        => $"{ApiBase}/api/v4/products/{slug}";

    public static async Task<string?> ResolveTenantIdAsync(HttpClient client, string baseUrl)
    {
        var siteUrl = ShopDiscoveryService.NormalizeBaseUrl(baseUrl);
        var body    = JsonSerializer.Serialize(new { siteUrl });
        using var content = new StringContent(body, Encoding.UTF8, "application/json");
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{ApiBase}/api/v4/stores/store-id")
        {
            Content = content,
        };
        req.Headers.TryAddWithoutValidation("site-url", siteUrl);

        using var res = await client.SendAsync(req);
        if (!res.IsSuccessStatusCode) return null;

        var json = await res.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        if (!doc.RootElement.TryGetProperty("success", out var ok) || !ok.GetBoolean())
            return null;
        if (!doc.RootElement.TryGetProperty("data", out var data)) return null;
        if (!data.TryGetProperty("storeId", out var storeId)) return null;

        var id = storeId.GetString();
        return string.IsNullOrWhiteSpace(id) ? null : id.Trim();
    }

    public static void ApplyTenantHeaders(HttpRequestMessage request, string tenantId, string siteUrl)
    {
        request.Headers.TryAddWithoutValidation("x-tenant-id", tenantId);
        request.Headers.TryAddWithoutValidation("site-url", ShopDiscoveryService.NormalizeBaseUrl(siteUrl));
    }

    public static async Task<string?> GetJsonWithTenantAsync(
        HttpClient client, string url, string tenantId, string siteUrl)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, url);
        ApplyTenantHeaders(req, tenantId, siteUrl);
        req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

        using var res = await client.SendAsync(req);
        if (!res.IsSuccessStatusCode) return null;
        return await res.Content.ReadAsStringAsync();
    }

    /// <summary>Category rows from StoreX API; counts via list slug/name + detail API fallback.</summary>
    public static async Task<List<DiscoveredShopCategoryDto>> DiscoverCategoriesFromApiAsync(
        HttpClient client, string baseUrl, string tenantId)
    {
        var rows       = new List<(string Slug, string Name)>();
        var page       = 1;

        while (page <= 20)
        {
            var json = await GetJsonWithTenantAsync(client, CategoriesAllUrl(page, MaxCategoriesPageSize), tenantId, baseUrl);
            if (string.IsNullOrWhiteSpace(json)) break;

            using var doc = JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("data", out var data)
                || !data.TryGetProperty("categories", out var arr)
                || arr.ValueKind != JsonValueKind.Array)
                break;

            var batch = 0;
            foreach (var c in arr.EnumerateArray())
            {
                var slug = c.TryGetProperty("slug", out var slugEl) ? slugEl.GetString() ?? "" : "";
                if (string.IsNullOrWhiteSpace(slug) || ShouldSkipCategorySlug(slug)) continue;

                var name = c.TryGetProperty("name", out var nameEl) ? nameEl.GetString() ?? slug : slug;
                rows.Add((slug, name));
                batch++;
            }

            if (batch == 0) break;
            page++;
        }

        if (rows.Count == 0) return [];

        var counts = await CountAllStoreCategoriesAsync(client, baseUrl, tenantId, rows.Select(r => r.Slug));

        return rows.Select(r =>
        {
            var mapped = CategoryNormalizer.Normalize(r.Name, r.Name, r.Slug);
            var browse = CategoryBrowseUrl(baseUrl, r.Slug);
            counts.TryGetValue(r.Slug, out var count);
            return new DiscoveredShopCategoryDto
            {
                ExternalId     = r.Slug,
                Slug           = r.Slug,
                Name           = r.Name,
                ProductCount   = count,
                MappedCategory = mapped,
                FetchUrl       = browse,
                ShopPageUrl    = browse,
                Suggested      = CategoryNormalizer.IsFocusCategory(mapped) && count > 0,
            };
        }).ToList();
    }

    public static Task<List<NormalizedExternalProduct>> FetchCatalogAsync(
        HttpClient client, string baseUrl, int maxProducts = 800)
        => FetchCatalogAsync(client, baseUrl, tenantId: null, maxProducts);

    public static async Task<List<NormalizedExternalProduct>> FetchCatalogAsync(
        HttpClient client, string baseUrl, string? tenantId, int maxProducts = 800)
    {
        tenantId ??= await ResolveTenantIdAsync(client, baseUrl);
        if (string.IsNullOrWhiteSpace(tenantId)) return [];

        var results = new List<NormalizedExternalProduct>();
        var seen    = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        const int limit = MaxProductsPageSize;

        for (var page = 1; page <= 20 && results.Count < maxProducts; page++)
        {
            var json = await GetJsonWithTenantAsync(client, ProductsAllUrl(page, limit), tenantId, baseUrl);
            if (string.IsNullOrWhiteSpace(json)) break;

            var batch = ExternalProductParsers.ParseStoreXProductsApi(json, baseUrl).ToList();
            if (batch.Count == 0) break;

            foreach (var p in batch)
            {
                if (!seen.Add(p.ExternalId)) continue;
                results.Add(p);
                if (results.Count >= maxProducts) break;
            }

            if (batch.Count < limit) break;
        }

        await EnrichWithStoreCategoriesAsync(client, baseUrl, tenantId, results);
        return results;
    }

    private static async Task EnrichWithStoreCategoriesAsync(
        HttpClient client, string baseUrl, string tenantId, List<NormalizedExternalProduct> products)
    {
        using var gate = new SemaphoreSlim(10);
        var tasks = products.Select(async p =>
        {
            if (ParseStoreCategorySlugsFromRaw(p.CategoryRaw).Count > 0) return;

            var slug = ExtractProductSlug(p.BuyUrl);
            if (string.IsNullOrWhiteSpace(slug)) return;

            await gate.WaitAsync();
            try
            {
                for (var attempt = 1; attempt <= 3; attempt++)
                {
                    try
                    {
                        var json = await GetJsonWithTenantAsync(client, ProductApiUrl(slug), tenantId, baseUrl);
                        if (string.IsNullOrWhiteSpace(json)) break;

                        using var doc = JsonDocument.Parse(json);
                        if (!doc.RootElement.TryGetProperty("data", out var data)) break;

                        var storeCats = ParseStoreXCategorySlugs(data);
                        if (storeCats.Count == 0) break;

                        p.CategoryRaw = FormatCategoryRaw(storeCats, slug, p.Name);
                        var primary   = storeCats[0];
                        var mapped    = CategoryNormalizer.HintFromFetchUrl(CategoryBrowseUrl(baseUrl, primary))
                            ?? CategoryNormalizer.Normalize(primary, p.Name, slug);
                        p.CategoryNormalized = mapped;
                        break;
                    }
                    catch when (attempt < 3)
                    {
                        await Task.Delay(attempt * 200);
                    }
                }
            }
            catch
            {
                // Keep list-row data when detail fetch fails
            }
            finally
            {
                gate.Release();
            }
        });

        await Task.WhenAll(tasks);
    }
}
