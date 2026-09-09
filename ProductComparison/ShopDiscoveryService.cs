using System.Text.Json;
using System.Text.RegularExpressions;
using JewelryMS.Domain.DTOs.ProductComparison;

namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>
/// Detect WooCommerce / Shopify public APIs from a storefront base URL and build sync URLs.
/// </summary>
public static class ShopDiscoveryService
{
    private sealed class DiscoveryAttemptState
    {
        public bool SawBotBlock { get; set; }
        public bool SawHtmlInsteadOfApi { get; set; }
    }

    private static readonly HashSet<string> SkipCategorySlugs = new(StringComparer.OrdinalIgnoreCase)
    {
        "new", "new-arrivals", "new-arrival", "discount-sale", "sale", "back-in-stock",
        "all", "all-products", "featured", "best-seller", "best-sellers", "clearance",
        "gift-item", "gift", "uncategorized", "accessories",
    };

    public static string NormalizeBaseUrl(string? input)
    {
        if (string.IsNullOrWhiteSpace(input)) throw new ArgumentException("Site URL is required.");
        var raw = input.Trim();
        if (!raw.StartsWith("http://", StringComparison.OrdinalIgnoreCase)
            && !raw.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            raw = "https://" + raw;

        if (!Uri.TryCreate(raw, UriKind.Absolute, out var uri))
            throw new ArgumentException("Invalid site URL.");

        var host = uri.Host;
        if (host.StartsWith("www.", StringComparison.OrdinalIgnoreCase))
            host = host[4..];

        return $"{uri.Scheme}://{host}".TrimEnd('/');
    }

    private static IEnumerable<string> GetBaseUrlCandidates(string siteUrlInput)
    {
        var primary = NormalizeBaseUrl(siteUrlInput);
        yield return primary;
    }

    private static bool LooksLikeJson(string? body)
    {
        if (string.IsNullOrWhiteSpace(body)) return false;
        var t = body.TrimStart();
        return t.StartsWith('{') || t.StartsWith('[');
    }

    private static bool IsBotBlockedResponse(string? body)
    {
        if (string.IsNullOrWhiteSpace(body)) return false;
        var lower = body.ToLowerInvariant();
        return lower.Contains("imunify360", StringComparison.Ordinal)
            || lower.Contains("bot-protection", StringComparison.Ordinal)
            || lower.Contains("access denied by", StringComparison.Ordinal)
            || lower.Contains("cf-browser-verification", StringComparison.Ordinal)
            || lower.Contains("cf-challenge", StringComparison.Ordinal)
            || lower.Contains("one moment, please", StringComparison.Ordinal)
            || lower.Contains("checking your browser", StringComparison.Ordinal)
            || lower.Contains("just a moment", StringComparison.Ordinal)
            || lower.Contains("ddos protection", StringComparison.Ordinal);
    }

    private static bool TryParseJson(string json, out JsonDocument? doc)
    {
        doc = null;
        if (!LooksLikeJson(json)) return false;
        try
        {
            doc = JsonDocument.Parse(json);
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    public static string GuessShopName(string baseUrl)
    {
        if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri))
            return "Shop";
        var host = uri.Host.Replace("www.", "", StringComparison.OrdinalIgnoreCase);
        var slug = host.Split('.')[0];
        var words = Regex.Split(slug, @"[-_]+")
            .Where(w => w.Length > 0)
            .Select(w => char.ToUpperInvariant(w[0]) + w[1..].ToLowerInvariant());
        return string.Join(" ", words);
    }

    private static readonly HashSet<string> SkipDarazSlugs = new(StringComparer.OrdinalIgnoreCase)
    {
        "unisex-accessories", "mens-chronograph", "womens-watches", "mens-watches",
        "toys-games", "mobile-phones", "laptops", "tv-audio",
    };

    public static async Task<ShopDiscoveryResultDto> DiscoverAsync(HttpClient client, string siteUrlInput)
    {
        var state = new DiscoveryAttemptState();

        foreach (var baseUrl in GetBaseUrlCandidates(siteUrlInput))
        {
            if (baseUrl.Contains("daraz.com.bd", StringComparison.OrdinalIgnoreCase))
            {
                var daraz = await TryDarazAsync(client, baseUrl);
                if (daraz != null) return daraz;
            }

            var wc = await TryWooCommerceAsync(client, baseUrl, state);
            if (wc != null) return wc;

            var shopify = await TryShopifyAsync(client, baseUrl, state);
            if (shopify != null) return shopify;

            var zatiq = await TryZatiqEasyAsync(client, baseUrl);
            if (zatiq != null) return zatiq;

            var storex = await TryStoreXAsync(client, baseUrl);
            if (storex != null) return storex;
        }

        if (state.SawBotBlock || state.SawHtmlInsteadOfApi)
        {
            throw new InvalidOperationException(
                "This shop blocks automated API access (Imunify360 / bot protection). " +
                "The server cannot read product JSON from this domain. " +
                "WooCommerce shops without bot protection (e.g. minimaljewelrybd.com) work with Analyze shop. " +
                "For blocked shops like barishka.com, sync is not possible until the host whitelists your server IP.");
        }

        throw new InvalidOperationException(
            "Could not detect WooCommerce, Shopify, Daraz, Zatiq Easy, or StoreX catalog on this domain. " +
            "Check the URL (use the bare domain, e.g. minimaljewelrybd.com) and see docs/price-compare-add-shop.md.");
    }

    private static async Task<ShopDiscoveryResultDto?> TryDarazAsync(HttpClient client, string baseUrl)
    {
        var probe = DarazCatalogUrls.JewelryDiscoveryProbe(baseUrl);
        using var probeRes = await client.GetAsync(probe);
        if (!probeRes.IsSuccessStatusCode) return null;

        var json = await probeRes.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);
        if (!doc.RootElement.TryGetProperty("mods", out var mods)
            || !mods.TryGetProperty("filter", out var filter)
            || !filter.TryGetProperty("filterItems", out var filterItems)
            || filterItems.ValueKind != JsonValueKind.Array)
            return null;

        var categories = new List<DiscoveredShopCategoryDto>();
        foreach (var item in filterItems.EnumerateArray())
        {
            if (item.TryGetProperty("name", out var nameEl)
                && nameEl.GetString() != "category")
                continue;
            if (!item.TryGetProperty("options", out var options) || options.ValueKind != JsonValueKind.Array)
                continue;

            foreach (var opt in options.EnumerateArray())
            {
                var slug = opt.TryGetProperty("value", out var val) ? val.GetString() ?? "" : "";
                var title = opt.TryGetProperty("title", out var tit) ? tit.GetString() ?? slug : slug;
                if (string.IsNullOrWhiteSpace(slug) || SkipDarazSlugs.Contains(slug)) continue;

                var mapped = CategoryNormalizer.Normalize(title, title, slug);
                var fetch = DarazCatalogUrls.CategoryFetchUrl(slug, baseUrl);
                var shopPage = DarazCatalogUrls.CategoryShopPage(slug, baseUrl);

                categories.Add(new DiscoveredShopCategoryDto
                {
                    ExternalId     = slug,
                    Slug           = slug,
                    Name           = title,
                    ProductCount   = 0,
                    MappedCategory = mapped,
                    FetchUrl       = fetch,
                    ShopPageUrl    = shopPage,
                    Suggested      = CategoryNormalizer.IsFocusCategory(mapped),
                });
            }
        }

        if (categories.Count == 0) return null;

        // Exact counts come from mainInfo.totalResults on each category's first ajax page.
        await Task.WhenAll(categories.Select(async cat =>
        {
            try
            {
                var pageJson = await client.GetStringAsync(cat.FetchUrl);
                cat.ProductCount = ExternalProductParsers.GetDarazTotalResults(pageJson);
            }
            catch
            {
                // leave 0 — UI shows a dash
            }
        }));

        var suggested = categories.Where(c => c.Suggested).ToList();
        var syncUrls  = suggested.Select(c => c.FetchUrl).ToArray();
        var apiUrl    = syncUrls.FirstOrDefault() ?? DarazCatalogUrls.CategoryFetchUrl("womens-bangles-bracelets", baseUrl);

        return new ShopDiscoveryResultDto
        {
            Platform          = "daraz",
            SiteUrl           = baseUrl,
            SuggestedName     = "Daraz Bangladesh",
            ApiUrl            = apiUrl,
            SuggestedSyncUrls = syncUrls,
            Categories        = categories.OrderByDescending(c => c.Suggested).ThenBy(c => c.Name).ToList(),
        };
    }

    private static async Task<ShopDiscoveryResultDto?> TryWooCommerceAsync(
        HttpClient client, string baseUrl, DiscoveryAttemptState state)
    {
        var probe = $"{baseUrl}/wp-json/wc/store/v1/products?per_page=1";
        using var probeRes = await client.GetAsync(probe);
        if (!probeRes.IsSuccessStatusCode) return null;

        var probeJson = await probeRes.Content.ReadAsStringAsync();
        if (IsBotBlockedResponse(probeJson))
        {
            state.SawBotBlock = true;
            state.SawHtmlInsteadOfApi = true;
            return null;
        }
        if (!LooksLikeJson(probeJson)) return null;

        var catUrl = $"{baseUrl}/wp-json/wc/store/v1/products/categories?per_page=100";
        using var catRes = await client.GetAsync(catUrl);
        if (!catRes.IsSuccessStatusCode) return null;

        var json = await catRes.Content.ReadAsStringAsync();
        if (IsBotBlockedResponse(json))
        {
            state.SawBotBlock = true;
            state.SawHtmlInsteadOfApi = true;
            return null;
        }
        if (!TryParseJson(json, out var doc) || doc == null) return null;

        using (doc)
        {
            if (doc.RootElement.ValueKind != JsonValueKind.Array) return null;

            var categories = new List<DiscoveredShopCategoryDto>();
            foreach (var c in doc.RootElement.EnumerateArray())
            {
                var id    = c.GetProperty("id").GetRawText();
                var slug  = c.GetProperty("slug").GetString() ?? "";
                var name  = c.GetProperty("name").GetString() ?? slug;
                var count = c.TryGetProperty("count", out var ct) ? ct.GetInt32() : 0;
                if (count <= 0) continue;

                var mapped = CategoryNormalizer.Normalize(name, name, slug);
                var skip   = SkipCategorySlugs.Contains(slug);
                var fetch    = $"{baseUrl}/wp-json/wc/store/v1/products?category={id}&per_page=100";
                var shopPage = ResolveWooCategoryPageUrl(c, baseUrl, slug);

                categories.Add(new DiscoveredShopCategoryDto
                {
                    ExternalId     = id,
                    Slug           = slug,
                    Name           = name,
                    ProductCount   = count,
                    MappedCategory = mapped,
                    FetchUrl       = fetch,
                    ShopPageUrl    = shopPage ?? "",
                    Suggested      = !skip && CategoryNormalizer.IsFocusCategory(mapped),
                });
            }

            if (categories.Count == 0) return null;

            var suggested = categories.Where(c => c.Suggested).ToList();
            var syncUrls  = suggested.Select(c => c.FetchUrl).ToArray();
            var apiUrl    = syncUrls.FirstOrDefault()
                            ?? $"{baseUrl}/wp-json/wc/store/v1/products?per_page=100";

            return new ShopDiscoveryResultDto
            {
                Platform         = "woocommerce",
                SiteUrl          = baseUrl,
                SuggestedName    = GuessShopName(baseUrl),
                ApiUrl           = apiUrl,
                SuggestedSyncUrls = syncUrls,
                Categories       = categories.OrderByDescending(c => c.Suggested).ThenByDescending(c => c.ProductCount).ToList(),
            };
        }
    }

    /// <summary>
    /// WC Store API exposes the real storefront path in <c>permalink</c>
    /// (e.g. pearlartistry.com/category/earrings/ — not always /product-category/).
    /// </summary>
    private static string ResolveWooCategoryPageUrl(JsonElement category, string baseUrl, string slug)
    {
        if (category.TryGetProperty("permalink", out var perm))
        {
            var url = perm.GetString();
            if (!string.IsNullOrWhiteSpace(url)) return url.Trim();
        }
        if (category.TryGetProperty("link", out var link))
        {
            var url = link.GetString();
            if (!string.IsNullOrWhiteSpace(url)) return url.Trim();
        }
        return $"{baseUrl}/product-category/{slug}/";
    }

    private sealed class HeadlessStorefrontInfo
    {
        public HashSet<string> CategorySlugs { get; } = new(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, HeadlessCategoryConfig> Categories { get; } =
            new(StringComparer.OrdinalIgnoreCase);
    }

    private static async Task<ShopDiscoveryResultDto?> TryShopifyAsync(
        HttpClient client, string baseUrl, DiscoveryAttemptState state)
    {
        var direct = await TryShopifyOnDomainAsync(client, baseUrl, baseUrl, state);
        if (direct != null) return direct;

        if (baseUrl.Contains(".myshopify.com", StringComparison.OrdinalIgnoreCase))
            return null;

        var backend = await ResolveHeadlessShopifyBackendAsync(client, baseUrl);
        if (backend == null) return null;

        var storefront = await ExtractHeadlessStorefrontAsync(client, baseUrl);
        if (storefront != null)
        {
            var fromStorefront = await DiscoverHeadlessStorefrontCategoriesAsync(
                client, backend, baseUrl, storefront);
            if (fromStorefront != null) return fromStorefront;
        }

        return await TryShopifyOnDomainAsync(client, backend, baseUrl, state);
    }

    /// <summary>
    /// Headless Shopify storefronts (Lovable/Vite SPAs) serve HTML on the custom domain but expose
    /// collections.json on the *.myshopify.com backend referenced in their JS bundle.
    /// </summary>
    private static async Task<string?> ResolveHeadlessShopifyBackendAsync(HttpClient client, string storefrontUrl)
    {
        var myshopify = await ExtractMyshopifyHostAsync(client, storefrontUrl);
        if (string.IsNullOrWhiteSpace(myshopify)) return null;

        var backend = NormalizeBaseUrl($"https://{myshopify}");
        using var probe = await client.GetAsync($"{backend}/collections.json?limit=1");
        if (!probe.IsSuccessStatusCode) return null;

        var json = await probe.Content.ReadAsStringAsync();
        if (!LooksLikeJson(json)) return null;

        return backend;
    }

    private static async Task<string?> ExtractMyshopifyHostAsync(HttpClient client, string pageUrl)
    {
        using var pageRes = await client.GetAsync(pageUrl);
        if (!pageRes.IsSuccessStatusCode) return null;

        var html = await pageRes.Content.ReadAsStringAsync();
        var host = FindMyshopifyHost(html);
        if (!string.IsNullOrWhiteSpace(host)) return host;

        foreach (Match sm in Regex.Matches(
            html, @"<script[^>]+src=[""']([^""']+\.js)[""']", RegexOptions.IgnoreCase))
        {
            var src = sm.Groups[1].Value.Trim();
            if (string.IsNullOrWhiteSpace(src)) continue;

            var jsUrl = src.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                ? src
                : new Uri(new Uri(pageUrl), src).ToString();

            try
            {
                var js = await client.GetStringAsync(jsUrl);
                host = FindMyshopifyHost(js);
                if (!string.IsNullOrWhiteSpace(host)) return host;
            }
            catch
            {
                // try next bundle
            }
        }

        return null;
    }

    private static string? FindMyshopifyHost(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        var m = Regex.Match(text, @"([a-z0-9][a-z0-9-]*\.myshopify\.com)", RegexOptions.IgnoreCase);
        return m.Success ? m.Groups[1].Value.ToLowerInvariant() : null;
    }

    private static async Task<HeadlessStorefrontInfo?> ExtractHeadlessStorefrontAsync(
        HttpClient client, string storefrontUrl)
    {
        using var pageRes = await client.GetAsync(storefrontUrl);
        if (!pageRes.IsSuccessStatusCode) return null;

        var texts = new List<string> { await pageRes.Content.ReadAsStringAsync() };
        foreach (Match sm in Regex.Matches(
            texts[0], @"<script[^>]+src=[""']([^""']+\.js)[""']", RegexOptions.IgnoreCase))
        {
            var src = sm.Groups[1].Value.Trim();
            if (string.IsNullOrWhiteSpace(src)) continue;

            var jsUrl = src.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                ? src
                : new Uri(new Uri(storefrontUrl), src).ToString();

            try { texts.Add(await client.GetStringAsync(jsUrl)); }
            catch { /* try next bundle */ }
        }

        var info = new HeadlessStorefrontInfo();
        foreach (var text in texts)
            ParseHeadlessStorefrontText(text, info);

        return info.CategorySlugs.Count > 0 ? info : null;
    }

    /// <summary>Storefront /category/{slug} → title searchQuery (for sync when mapping JSON lacks it).</summary>
    public static async Task<IReadOnlyDictionary<string, HeadlessCategoryConfig>> GetHeadlessCategoryConfigsAsync(
        HttpClient client, string siteUrl)
    {
        var info = await ExtractHeadlessStorefrontAsync(client, NormalizeBaseUrl(siteUrl));
        return info?.Categories ?? new Dictionary<string, HeadlessCategoryConfig>();
    }

    private static void ParseHeadlessStorefrontText(string text, HeadlessStorefrontInfo info)
    {
        foreach (Match m in Regex.Matches(text, @"/category/([a-z0-9][a-z0-9-]*)", RegexOptions.IgnoreCase))
        {
            var slug = m.Groups[1].Value;
            if (!ShopifyCatalog.IsInvalidHeadlessSlug(slug))
                info.CategorySlugs.Add(slug);
        }

        // vibewear SI={necklaces:{name:...},...},hv=[ — ignore crypto hash:{name:"SHA-256"} elsewhere in bundle
        var siMatch = Regex.Match(text, @"SI=\{(.*)\},hv=\[", RegexOptions.Singleline);
        var configText = siMatch.Success ? siMatch.Groups[1].Value : "";

        foreach (Match m in Regex.Matches(
            configText,
            @"""?([a-z0-9][a-z0-9-]*)""?\s*:\s*\{name:""([^""]+)""(?:,searchQuery:""([^""]*)"")?(?:,collectionHandle:""([^""]*)"")?\}",
            RegexOptions.IgnoreCase))
        {
            var slug = m.Groups[1].Value;
            if (ShopifyCatalog.IsInvalidHeadlessSlug(slug)) continue;

            info.CategorySlugs.Add(slug);
            info.Categories[slug] = new HeadlessCategoryConfig
            {
                Slug              = slug,
                Name              = m.Groups[2].Value,
                SearchQuery       = string.IsNullOrWhiteSpace(m.Groups[3].Value) ? null : m.Groups[3].Value,
                CollectionHandle  = string.IsNullOrWhiteSpace(m.Groups[4].Value) ? null : m.Groups[4].Value,
            };
        }
    }

    private static async Task<ShopDiscoveryResultDto?> DiscoverHeadlessStorefrontCategoriesAsync(
        HttpClient client, string apiBaseUrl, string displaySiteUrl, HeadlessStorefrontInfo storefront)
    {
        var slugs = storefront.CategorySlugs
            .Where(s => !ShouldSkipCategorySlug(s) && !ShopifyCatalog.IsInvalidHeadlessSlug(s))
            .Where(s => storefront.Categories.TryGetValue(s, out var cfg)
                && (!string.IsNullOrWhiteSpace(cfg!.SearchQuery)
                    || !string.IsNullOrWhiteSpace(cfg.CollectionHandle)))
            .OrderBy(s => s, StringComparer.OrdinalIgnoreCase)
            .ToList();
        if (slugs.Count == 0) return null;

        var categories = new List<DiscoveredShopCategoryDto>();
        List<NormalizedExternalProduct>? storeCatalog = null;
        foreach (var slug in slugs)
        {
            var cfg  = storefront.Categories[slug];
            var name = cfg.Name;
            var mapped = CategoryNormalizer.Normalize(name, name, slug);
            var shopPage = $"{displaySiteUrl.TrimEnd('/')}/category/{slug}";

            string fetchUrl;
            if (!string.IsNullOrWhiteSpace(cfg.CollectionHandle))
                fetchUrl = $"{apiBaseUrl.TrimEnd('/')}/collections/{cfg.CollectionHandle}/products.json?limit=250";
            else
                fetchUrl = ShopifyCatalog.BuildTitleFilterFetchUrl(apiBaseUrl, slug);

            if (!string.IsNullOrWhiteSpace(cfg.SearchQuery))
                storeCatalog ??= await ShopifyCatalog.FetchAllStoreProductsAsync(client, apiBaseUrl);

            var count = await ShopifyCatalog.CountForHeadlessCategoryAsync(
                client, apiBaseUrl, cfg, storeCatalog);

            categories.Add(new DiscoveredShopCategoryDto
            {
                ExternalId       = slug,
                Slug             = slug,
                Name             = name,
                ProductCount     = count,
                MappedCategory   = mapped,
                FetchUrl         = fetchUrl,
                ShopPageUrl      = shopPage,
                TitleSearchQuery = cfg.SearchQuery,
                Suggested        = CategoryNormalizer.IsFocusCategory(mapped) && count > 0,
            });
        }

        if (categories.Count == 0) return null;

        var suggested = categories.Where(c => c.Suggested).ToList();
        return new ShopDiscoveryResultDto
        {
            Platform          = "shopify",
            SiteUrl           = displaySiteUrl,
            SuggestedName     = GuessShopName(displaySiteUrl),
            ApiUrl            = suggested.FirstOrDefault()?.FetchUrl ?? categories[0].FetchUrl,
            SuggestedSyncUrls = suggested.Select(c => c.FetchUrl).ToArray(),
            Categories        = categories
                .OrderByDescending(c => c.Suggested)
                .ThenByDescending(c => c.ProductCount)
                .ThenBy(c => c.Name)
                .ToList(),
        };
    }

    private static bool ShouldSkipCategorySlug(string slug)
        => SkipCategorySlugs.Contains(slug)
           || Regex.IsMatch(slug, @"^\d+(-to-\d+)?(-tk)?$", RegexOptions.IgnoreCase);

    private static string HeadlessCategoryDisplayName(string categorySlug)
    {
        var words = categorySlug.Split('-', StringSplitOptions.RemoveEmptyEntries);
        return string.Join(" ", words.Select(w =>
            w.Length > 0 ? char.ToUpperInvariant(w[0]) + w[1..] : w));
    }

    private static async Task<ShopDiscoveryResultDto?> TryShopifyOnDomainAsync(
        HttpClient client, string apiBaseUrl, string displaySiteUrl, DiscoveryAttemptState state)
    {
        var collectionsUrl = $"{apiBaseUrl.TrimEnd('/')}/collections.json?limit=250";
        using var colRes = await client.GetAsync(collectionsUrl);
        if (!colRes.IsSuccessStatusCode) return null;

        var json = await colRes.Content.ReadAsStringAsync();
        if (IsBotBlockedResponse(json))
        {
            state.SawBotBlock = true;
            state.SawHtmlInsteadOfApi = true;
            return null;
        }
        if (!TryParseJson(json, out var doc) || doc == null) return null;

        using (doc)
        {
            if (doc.RootElement.TryGetProperty("message", out var msg)
                && msg.ValueKind == JsonValueKind.String
                && IsBotBlockedResponse(msg.GetString()))
            {
                state.SawBotBlock = true;
                return null;
            }

            if (!doc.RootElement.TryGetProperty("collections", out var collections)
                || collections.ValueKind != JsonValueKind.Array)
                return null;

            var categories = new List<DiscoveredShopCategoryDto>();
            foreach (var c in collections.EnumerateArray())
            {
                var handle = c.GetProperty("handle").GetString() ?? "";
                var title  = c.GetProperty("title").GetString() ?? handle;
                var id     = c.GetProperty("id").GetRawText();
                var count  = c.TryGetProperty("products_count", out var pc) ? pc.GetInt32() : 0;
                var skip   = SkipCategorySlugs.Contains(handle);
                var mapped = CategoryNormalizer.Normalize(title, title, handle);
                var fetch  = $"{apiBaseUrl.TrimEnd('/')}/collections/{handle}/products.json?limit=250";

                categories.Add(new DiscoveredShopCategoryDto
                {
                    ExternalId     = id,
                    Slug           = handle,
                    Name           = title,
                    ProductCount   = count,
                    MappedCategory = mapped,
                    FetchUrl       = fetch,
                    ShopPageUrl    = $"{displaySiteUrl.TrimEnd('/')}/collections/{handle}",
                    Suggested      = !skip && CategoryNormalizer.IsFocusCategory(mapped) && count > 0,
                });
            }

            if (categories.Count == 0) return null;

            var suggested = categories.Where(c => c.Suggested).ToList();
            var syncUrls  = suggested.Select(c => c.FetchUrl).ToArray();
            var apiUrl    = syncUrls.FirstOrDefault()
                            ?? $"{apiBaseUrl.TrimEnd('/')}/products.json?limit=250";

            return new ShopDiscoveryResultDto
            {
                Platform          = "shopify",
                SiteUrl           = displaySiteUrl,
                SuggestedName     = GuessShopName(displaySiteUrl),
                ApiUrl            = apiUrl,
                SuggestedSyncUrls = syncUrls,
                Categories        = categories
                    .OrderByDescending(c => c.Suggested)
                    .ThenByDescending(c => c.ProductCount)
                    .ThenBy(c => c.Name)
                    .ToList(),
            };
        }
    }

    private static async Task<ShopDiscoveryResultDto?> TryZatiqEasyAsync(HttpClient client, string baseUrl)
    {
        var sitemapUrl = ZatiqEasyCatalog.SitemapUrl(baseUrl);
        using var mapRes = await client.GetAsync(sitemapUrl);
        if (!mapRes.IsSuccessStatusCode) return null;

        var xml = await mapRes.Content.ReadAsStringAsync();
        var productUrls = ZatiqEasyCatalog.ExtractProductUrlsFromSitemap(xml, baseUrl).Take(5).ToList();
        if (productUrls.Count == 0) return null;

        using var probeRes = await client.GetAsync(productUrls[0]);
        if (!probeRes.IsSuccessStatusCode) return null;
        var probeHtml = await probeRes.Content.ReadAsStringAsync();
        if (!probeHtml.Contains("application/ld+json", StringComparison.OrdinalIgnoreCase)
            || ExternalProductParsers.ParseZatiqProductHtml(probeHtml, baseUrl, null).FirstOrDefault() == null)
            return null;

        var categories = new List<DiscoveredShopCategoryDto>();
        try
        {
            using var rscReq = new HttpRequestMessage(HttpMethod.Get, $"{baseUrl}/");
            rscReq.Headers.TryAddWithoutValidation("RSC", "1");
            rscReq.Headers.TryAddWithoutValidation("Accept", "text/x-component");
            using var rscRes = await client.SendAsync(rscReq);
            if (rscRes.IsSuccessStatusCode)
            {
                var rsc = await rscRes.Content.ReadAsStringAsync();
                categories = ZatiqEasyCatalog.ExtractCategoriesFromRsc(rsc, baseUrl);
            }
        }
        catch
        {
            // Fall back to sitemap-only row below
        }

        if (categories.Count == 0)
        {
            categories.Add(new DiscoveredShopCategoryDto
            {
                ExternalId     = "all-products",
                Slug           = "all-products",
                Name           = "All products (sitemap)",
                ProductCount   = ZatiqEasyCatalog.ExtractProductUrlsFromSitemap(xml, baseUrl).Count(),
                MappedCategory = "Other",
                FetchUrl       = sitemapUrl,
                ShopPageUrl    = $"{baseUrl}/products",
                Suggested      = true,
            });
        }

        var suggested = categories.Where(c => c.Suggested).ToList();
        var syncUrls  = suggested.Select(c => c.FetchUrl).ToArray();
        var apiUrl    = syncUrls.FirstOrDefault() ?? sitemapUrl;

        return new ShopDiscoveryResultDto
        {
            Platform          = "zatiq",
            SiteUrl           = baseUrl,
            SuggestedName     = GuessShopName(baseUrl),
            ApiUrl            = apiUrl,
            SuggestedSyncUrls = syncUrls.Length > 0 ? syncUrls : new[] { sitemapUrl },
            Categories        = categories.OrderByDescending(c => c.Suggested).ThenByDescending(c => c.ProductCount).ToList(),
        };
    }

    private static async Task<ShopDiscoveryResultDto?> TryStoreXAsync(HttpClient client, string baseUrl)
    {
        var sitemapUrl = StoreXCatalog.SitemapUrl(baseUrl);
        using var mapRes = await client.GetAsync(sitemapUrl);
        if (!mapRes.IsSuccessStatusCode) return null;

        var xml = await mapRes.Content.ReadAsStringAsync();
        var productUrls = StoreXCatalog.ExtractProductUrlsFromSitemap(xml, baseUrl).Take(5).ToList();
        if (productUrls.Count == 0) return null;

        using var probeRes = await client.GetAsync(productUrls[0]);
        if (!probeRes.IsSuccessStatusCode) return null;
        var probeHtml = await probeRes.Content.ReadAsStringAsync();
        if (ExternalProductParsers.ParseStoreXProductHtml(probeHtml, baseUrl, productUrls[0]).FirstOrDefault() == null)
            return null;

        var tenantId   = await StoreXCatalog.ResolveTenantIdAsync(client, baseUrl);
        var categories = tenantId != null
            ? await StoreXCatalog.DiscoverCategoriesFromApiAsync(client, baseUrl, tenantId)
            : new List<DiscoveredShopCategoryDto>();

        if (categories.Count == 0)
            categories = StoreXCatalog.ExtractCategoriesFromSitemap(xml, baseUrl);
        if (categories.Count == 0)
        {
            var totalProducts = StoreXCatalog.ExtractProductUrlsFromSitemap(xml, baseUrl).Count();
            categories.Add(new DiscoveredShopCategoryDto
            {
                ExternalId     = "all-products",
                Slug           = "all-products",
                Name           = "All products (sitemap)",
                ProductCount   = totalProducts,
                MappedCategory = "Other",
                FetchUrl       = sitemapUrl,
                ShopPageUrl    = $"{baseUrl}/products",
                Suggested      = true,
            });
        }

        var suggested = categories.Where(c => c.Suggested).ToList();
        var syncUrls  = suggested.Select(c => c.FetchUrl).ToArray();
        var apiUrl    = syncUrls.FirstOrDefault() ?? sitemapUrl;

        return new ShopDiscoveryResultDto
        {
            Platform          = "storex",
            SiteUrl           = baseUrl,
            SuggestedName     = GuessShopName(baseUrl),
            ApiUrl            = apiUrl,
            SuggestedSyncUrls = syncUrls.Length > 0 ? syncUrls : new[] { sitemapUrl },
            Categories        = categories.OrderByDescending(c => c.Suggested).ThenByDescending(c => c.ProductCount).ToList(),
        };
    }
}
