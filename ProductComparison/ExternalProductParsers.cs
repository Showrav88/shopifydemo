using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using JewelryMS.Domain.DTOs.ProductComparison;

namespace JewelryMS.Application.Services.ProductComparison;

public static class ExternalProductParsers
{
    public static IEnumerable<NormalizedExternalProduct> Parse(
        string platform, string json, string? siteUrl, string? apiUrl, string? urlHint = null)
    {
        // Alankar etc. are sometimes saved as "custom" — route by API URL shape.
        if (IsJewelryMsApi(platform, apiUrl))
            return ParseJewelryMs(json, siteUrl, apiUrl);
        if (IsDarazApi(platform, apiUrl))
            return ParseDaraz(json, siteUrl, urlHint);
        if (ZatiqEasyCatalog.IsZatiqApi(platform, apiUrl))
            return ParseZatiqProductHtml(json, siteUrl, urlHint);
        if (StoreXCatalog.IsStoreXApi(platform, apiUrl))
        {
            var fromApi = ParseStoreXProductsApi(json, siteUrl).ToList();
            if (fromApi.Count > 0) return fromApi;
            return ParseStoreXProductHtml(json, siteUrl, urlHint);
        }

        return platform.ToLowerInvariant() switch
        {
            "shopify"      => ParseShopify(json, siteUrl, urlHint),
            "woocommerce"  => ParseWooCommerce(json, urlHint),
            "jewelryms"    => ParseJewelryMs(json, siteUrl, apiUrl),
            "daraz"        => ParseDaraz(json, siteUrl, urlHint),
            "zatiq"        => ParseZatiqProductHtml(json, siteUrl, urlHint),
            "storex"       => ParseStoreXProductsApi(json, siteUrl).ToList() is { Count: > 0 } storexApi
                ? storexApi
                : ParseStoreXProductHtml(json, siteUrl, urlHint),
            _              => ParseGeneric(json, siteUrl, apiUrl, urlHint),
        };
    }

    /// <summary>schema.org Product JSON-LD embedded in Zatiq Easy product page HTML.</summary>
    public static IEnumerable<NormalizedExternalProduct> ParseZatiqProductHtml(
        string html, string? siteUrl, string? urlHint)
    {
        if (string.IsNullOrWhiteSpace(html)) yield break;

        foreach (Match m in Regex.Matches(
            html, @"<script\s+type=""application/ld\+json"">(.*?)</script>",
            RegexOptions.Singleline | RegexOptions.IgnoreCase))
        {
            JsonDocument doc;
            try
            {
                doc = JsonDocument.Parse(m.Groups[1].Value);
            }
            catch (JsonException)
            {
                continue;
            }

            using (doc)
            {
                var root = doc.RootElement;
                if (!root.TryGetProperty("@type", out var typeEl)) continue;
                var type = typeEl.GetString();
                if (!string.Equals(type, "Product", StringComparison.OrdinalIgnoreCase))
                    continue;

                var id = GetString(root, "id", "@id") ?? "";
                if (string.IsNullOrWhiteSpace(id))
                {
                    var url = GetString(root, "url");
                    var tail = url?.Split('/').LastOrDefault();
                    if (!string.IsNullOrWhiteSpace(tail)) id = tail;
                }
                if (string.IsNullOrWhiteSpace(id)) continue;

                var name = GetString(root, "name") ?? "Unknown";
                var desc = GetString(root, "description");

                string? imageUrl = null;
                if (root.TryGetProperty("image", out var imgEl))
                {
                    imageUrl = imgEl.ValueKind switch
                    {
                        JsonValueKind.String => imgEl.GetString(),
                        JsonValueKind.Array  => imgEl.EnumerateArray()
                            .Select(i => i.GetString())
                            .FirstOrDefault(s => !string.IsNullOrWhiteSpace(s)),
                        _ => null,
                    };
                }

                decimal price = 0;
                decimal? compareAt = null;
                var inStock = true;
                string? buyUrl = null;

                if (root.TryGetProperty("offers", out var offers))
                {
                    if (offers.TryGetProperty("price", out var pr))
                        price = pr.ValueKind == JsonValueKind.Number
                            ? pr.GetDecimal()
                            : ParseDecimal(pr.GetString());

                    if (offers.TryGetProperty("availability", out var av)
                        && av.ValueKind == JsonValueKind.String)
                    {
                        var avail = av.GetString() ?? "";
                        inStock = !avail.Contains("OutOfStock", StringComparison.OrdinalIgnoreCase)
                            && !avail.Contains("Discontinued", StringComparison.OrdinalIgnoreCase);
                    }

                    buyUrl = GetString(offers, "url");
                }

                if (string.IsNullOrEmpty(buyUrl) && !string.IsNullOrEmpty(siteUrl))
                    buyUrl = $"{siteUrl.TrimEnd('/')}/products/{id}";

                var catRaw = string.Join(" | ", new[] { urlHint, name }.Where(s => !string.IsNullOrWhiteSpace(s)));
                var (hasGuarantee, guaranteeSnippet) = GuaranteeTextDetector.Detect(name, desc);

                yield return new NormalizedExternalProduct
                {
                    ExternalId          = id,
                    Name                = name,
                    CategoryRaw         = catRaw,
                    CategoryNormalized  = CategoryNormalizer.Normalize(catRaw, name, urlHint),
                    Price               = price,
                    CompareAtPrice      = compareAt,
                    ImageUrl            = imageUrl,
                    ImageUrls           = imageUrl != null ? new[] { imageUrl } : Array.Empty<string>(),
                    InStock             = inStock,
                    BuyUrl              = buyUrl,
                    HasGuaranteeMention = hasGuarantee,
                    GuaranteeSnippet    = guaranteeSnippet,
                };
            }
        }
    }

    /// <summary>StoreX v4 product pages expose price, title, and SKU via product:* and Open Graph meta tags.</summary>
    public static IEnumerable<NormalizedExternalProduct> ParseStoreXProductHtml(
        string html, string? siteUrl, string? urlHint)
    {
        if (string.IsNullOrWhiteSpace(html)) yield break;

        var name = GetMetaContent(html, "og:title", "property")
            ?? GetMetaContent(html, "twitter:title", "name");
        if (string.IsNullOrWhiteSpace(name)) yield break;

        var priceStr = GetMetaContent(html, "product:price:amount", "name");
        if (string.IsNullOrWhiteSpace(priceStr)) yield break;
        var price = ParseDecimal(priceStr);
        if (price <= 0) yield break;

        decimal? compareAt = null;
        var saleStr = GetMetaContent(html, "product:sale_price", "name");
        if (!string.IsNullOrWhiteSpace(saleStr))
        {
            var sale = ParseDecimal(saleStr);
            if (sale > price) compareAt = sale;
        }

        var buyUrl = GetLinkHref(html, "canonical") ?? urlHint;
        var externalId = GetMetaContent(html, "product:retailer_item_id", "name")
            ?? GetMetaContent(html, "product:item_group_id", "name");
        if (string.IsNullOrWhiteSpace(externalId))
            externalId = buyUrl?.TrimEnd('/').Split('/').LastOrDefault();
        if (string.IsNullOrWhiteSpace(externalId)) yield break;

        var imageUrl = GetMetaContent(html, "og:image", "property")
            ?? GetMetaContent(html, "twitter:image", "name");

        var availability = GetMetaContent(html, "product:availability", "name") ?? "";
        var inStock = ResolveStoreXStockFromHtml(html, availability);

        var desc = GetMetaContent(html, "og:description", "property")
            ?? GetMetaContent(html, "description", "name");
        var slug = buyUrl?.TrimEnd('/').Split('/').LastOrDefault();
        var catRaw = string.Join(" | ", new[] { urlHint, slug, name }.Where(s => !string.IsNullOrWhiteSpace(s)));
        var (hasGuarantee, guaranteeSnippet) = GuaranteeTextDetector.Detect(name, desc);

        if (string.IsNullOrWhiteSpace(buyUrl) && !string.IsNullOrEmpty(siteUrl) && !string.IsNullOrEmpty(slug))
            buyUrl = $"{siteUrl.TrimEnd('/')}/products/{slug}";

        yield return new NormalizedExternalProduct
        {
            ExternalId          = externalId,
            Name                = name,
            CategoryRaw         = catRaw,
            CategoryNormalized  = CategoryNormalizer.Normalize(catRaw, name, slug),
            Price               = price,
            CompareAtPrice      = compareAt,
            ImageUrl            = imageUrl,
            ImageUrls           = imageUrl != null ? new[] { imageUrl } : Array.Empty<string>(),
            InStock             = inStock,
            BuyUrl              = buyUrl,
            HasGuaranteeMention = hasGuarantee,
            GuaranteeSnippet    = guaranteeSnippet,
        };
    }

    /// <summary>StoreX v4 JSON from /api/v4/products/all or /api/v4/products/{slug}.</summary>
    public static IEnumerable<NormalizedExternalProduct> ParseStoreXProductsApi(
        string json, string? siteUrl)
    {
        if (string.IsNullOrWhiteSpace(json)) yield break;

        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(json);
        }
        catch (JsonException)
        {
            yield break;
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (!root.TryGetProperty("success", out var ok) || !ok.GetBoolean())
                yield break;
            if (!root.TryGetProperty("data", out var data)) yield break;

            if (data.TryGetProperty("products", out var products) && products.ValueKind == JsonValueKind.Array)
            {
                foreach (var p in products.EnumerateArray())
                {
                    var mapped = MapStoreXProduct(p, siteUrl);
                    if (mapped != null) yield return mapped;
                }
                yield break;
            }

            if (data.TryGetProperty("slug", out _) || data.TryGetProperty("title", out _))
            {
                var single = MapStoreXProduct(data, siteUrl);
                if (single != null) yield return single;
            }
        }
    }

    private static NormalizedExternalProduct? MapStoreXProduct(JsonElement p, string? siteUrl)
    {
        var slug = GetString(p, "slug");
        var name = GetString(p, "title") ?? slug;
        if (string.IsNullOrWhiteSpace(slug) || string.IsNullOrWhiteSpace(name)) return null;

        var listPrice = p.TryGetProperty("price", out var pr)
            ? pr.ValueKind == JsonValueKind.Number ? pr.GetDecimal() : ParseDecimal(pr.GetString())
            : 0m;
        var salePrice = p.TryGetProperty("discountprice", out var sp)
            ? sp.ValueKind == JsonValueKind.Number ? sp.GetDecimal() : ParseDecimal(sp.GetString())
            : 0m;

        var price = salePrice > 0 ? salePrice : listPrice;
        if (price <= 0) return null;

        decimal? compareAt = listPrice > price ? listPrice : null;

        var externalId = GetString(p, "productid", "_id") ?? slug;
        var storeId    = GetString(p, "storeId");
        var imageUrl   = BuildStoreXImageUrl(p, storeId, siteUrl);

        var inStock = true;
        if (p.TryGetProperty("availability", out var av))
        {
            inStock = av.ValueKind switch
            {
                JsonValueKind.Number => av.GetInt32() > 0,
                JsonValueKind.True   => true,
                JsonValueKind.False  => false,
                JsonValueKind.String => !av.GetString()?.Contains("out", StringComparison.OrdinalIgnoreCase) ?? true,
                _                    => true,
            };
        }

        var storeCats = StoreXCatalog.ParseStoreXCategorySlugs(p);
        var baseUrl   = ShopDiscoveryService.NormalizeBaseUrl(siteUrl ?? "");
        var catRaw    = StoreXCatalog.FormatCategoryRaw(storeCats, slug, name);
        var normHint  = storeCats.Count > 0
            ? CategoryNormalizer.HintFromFetchUrl(StoreXCatalog.CategoryBrowseUrl(baseUrl, storeCats[0]))
              ?? CategoryNormalizer.Normalize(storeCats[0], name, slug)
            : slug;
        var buyUrl  = $"{baseUrl}/products/{slug}";
        var desc    = GetString(p, "metaDesc", "descLayout");
        var (hasGuarantee, guaranteeSnippet) = GuaranteeTextDetector.Detect(name, desc);

        return new NormalizedExternalProduct
        {
            ExternalId          = externalId,
            Name                = name,
            CategoryRaw         = catRaw,
            CategoryNormalized  = CategoryNormalizer.Normalize(normHint, name, slug),
            Price               = price,
            CompareAtPrice      = compareAt,
            ImageUrl            = imageUrl,
            ImageUrls           = imageUrl != null ? new[] { imageUrl } : Array.Empty<string>(),
            InStock             = inStock,
            BuyUrl              = buyUrl,
            HasGuaranteeMention = hasGuarantee,
            GuaranteeSnippet    = guaranteeSnippet,
        };
    }

    private static string? BuildStoreXImageUrl(JsonElement p, string? storeId, string? siteUrl)
    {
        if (!p.TryGetProperty("gallery", out var gallery) || gallery.ValueKind != JsonValueKind.Array)
            return null;

        var file = gallery.EnumerateArray()
            .Select(g => g.GetString())
            .FirstOrDefault(s => !string.IsNullOrWhiteSpace(s));
        if (string.IsNullOrWhiteSpace(file)) return null;

        var folder = GetString(p, "gallery_folder");
        if (string.IsNullOrWhiteSpace(folder)) return null;

        storeId ??= TryStoreIdFromSiteUrl(siteUrl);
        if (string.IsNullOrWhiteSpace(storeId)) return null;

        return $"https://media-cdn.storex.dev/{storeId}/images/products/{folder}/{file}";
    }

    private static string? TryStoreIdFromSiteUrl(string? siteUrl)
    {
        if (string.IsNullOrWhiteSpace(siteUrl)) return null;
        if (!Uri.TryCreate(ShopDiscoveryService.NormalizeBaseUrl(siteUrl), UriKind.Absolute, out var uri))
            return null;
        var host = uri.Host.Replace("www.", "", StringComparison.OrdinalIgnoreCase);
        return host.Split('.')[0];
    }

    private static bool ResolveStoreXStockFromHtml(string html, string? availabilityMeta)
    {
        if (Regex.IsMatch(html, @"STATUS:\s*STOCK\s*IN", RegexOptions.IgnoreCase))
            return true;
        if (Regex.IsMatch(html, @"STATUS:\s*STOCK\s*OUT", RegexOptions.IgnoreCase))
            return false;

        if (!string.IsNullOrWhiteSpace(availabilityMeta))
        {
            var a = availabilityMeta.ToLowerInvariant();
            if (a.Contains("in stock", StringComparison.Ordinal)) return true;
            if (a.Contains("out of stock", StringComparison.Ordinal)) return false;
        }

        return true;
    }

    /// <summary>
    /// Zatiq product pages embed full inventory JSON in the Next.js RSC payload (includes real category ids).
    /// CategoryRaw stores "id|name" pairs comma-separated for per-category filtering.
    /// </summary>
    public static NormalizedExternalProduct? ParseZatiqProductRsc(
        string rsc, string? siteUrl, string? expectedProductId)
    {
        if (string.IsNullOrWhiteSpace(rsc) || string.IsNullOrWhiteSpace(expectedProductId))
            return null;

        var anchor = $@"""id"":{expectedProductId},""name"":""";
        var positions = new List<int>();
        var pos = 0;
        while ((pos = rsc.IndexOf(anchor, pos, StringComparison.Ordinal)) >= 0)
        {
            positions.Add(pos);
            pos += anchor.Length;
        }

        // Prefer the full product-page inventory block (usually the last match).
        for (var i = positions.Count - 1; i >= 0; i--)
        {
            var slice = rsc.Substring(positions[i], Math.Min(5000, rsc.Length - positions[i]));
            var parsed = TryParseZatiqInventorySlice(slice, expectedProductId, siteUrl);
            if (parsed != null)
                return parsed;
        }

        return null;
    }

    private static NormalizedExternalProduct? TryParseZatiqInventorySlice(
        string slice, string expectedProductId, string? siteUrl)
    {
        var head = Regex.Match(slice,
            $@"""id"":{Regex.Escape(expectedProductId)},""name"":""([^""]+)"".*?""price"":(\d+).*?""quantity"":(\d+)",
            RegexOptions.Singleline);
        if (!head.Success) return null;

        var name     = head.Groups[1].Value;
        var price    = decimal.Parse(head.Groups[2].Value, CultureInfo.InvariantCulture);
        var quantity = int.Parse(head.Groups[3].Value, CultureInfo.InvariantCulture);

        decimal? compareAt = null;
        var oldMatch = Regex.Match(slice, @"""old_price"":(null|(\d+))");
        if (oldMatch.Success && oldMatch.Groups[2].Success
            && decimal.TryParse(oldMatch.Groups[2].Value, NumberStyles.Any, CultureInfo.InvariantCulture, out var old)
            && old > price)
            compareAt = old;

        string? imageUrl = null;
        var imageUrlMatch = Regex.Match(slice, @"""image_url"":""(https?://[^""]+)""");
        if (imageUrlMatch.Success)
            imageUrl = imageUrlMatch.Groups[1].Value;
        else
        {
            var imgMatch = Regex.Match(slice, @"""images"":\[(.*?)\]", RegexOptions.Singleline);
            if (imgMatch.Success)
            {
                imageUrl = Regex.Matches(imgMatch.Groups[1].Value, @"""(https?://[^""]+)""")
                    .Select(m => m.Groups[1].Value)
                    .FirstOrDefault();
            }
        }

        var catParts = new List<string>();
        string? primaryCatName = null;
        var catsJson = ExtractJsonArray(slice, "categories");
        if (!string.IsNullOrEmpty(catsJson))
        {
            foreach (Match cm in Regex.Matches(catsJson, @"\{""id"":(\d+),""name"":""([^""]+)"""))
            {
                catParts.Add($"{cm.Groups[1].Value}|{cm.Groups[2].Value}");
                primaryCatName ??= cm.Groups[2].Value;
            }
        }

        if (catParts.Count == 0)
            return null;

        var baseUrl = (siteUrl ?? "").TrimEnd('/');
        var buyUrl  = !string.IsNullOrEmpty(baseUrl)
            ? $"{baseUrl}/products/{expectedProductId}"
            : null;

        var catRaw = string.Join(",", catParts);
        var (hasGuarantee, guaranteeSnippet) = GuaranteeTextDetector.Detect(name, null);

        return new NormalizedExternalProduct
        {
            ExternalId          = expectedProductId,
            Name                = name,
            CategoryRaw         = catRaw,
            CategoryNormalized  = CategoryNormalizer.Normalize(primaryCatName, name, primaryCatName),
            Price               = price,
            CompareAtPrice      = compareAt,
            ImageUrl            = imageUrl,
            ImageUrls           = imageUrl != null ? new[] { imageUrl } : Array.Empty<string>(),
            InStock             = quantity > 0,
            BuyUrl              = buyUrl,
            HasGuaranteeMention = hasGuarantee,
            GuaranteeSnippet    = guaranteeSnippet,
        };
    }

    private static string? ExtractJsonArray(string text, string propertyName)
    {
        var key = $"\"{propertyName}\":[";
        var start = text.IndexOf(key, StringComparison.Ordinal);
        if (start < 0) return null;
        start += key.Length - 1;

        var depth = 0;
        for (var i = start; i < text.Length; i++)
        {
            if (text[i] == '[') depth++;
            else if (text[i] == ']')
            {
                depth--;
                if (depth == 0)
                    return text[start..(i + 1)];
            }
        }

        return null;
    }

    public static bool IsDarazApi(string platform, string? apiUrl)
    {
        if (platform.Equals("daraz", StringComparison.OrdinalIgnoreCase))
            return true;
        return apiUrl?.Contains("daraz.com.bd", StringComparison.OrdinalIgnoreCase) == true
            && apiUrl.Contains("ajax=true", StringComparison.OrdinalIgnoreCase);
    }

    public static bool IsJewelryMsApi(string platform, string? apiUrl)
    {
        if (platform.Equals("jewelryms", StringComparison.OrdinalIgnoreCase))
            return true;
        return apiUrl?.Contains("/imitation-store/", StringComparison.OrdinalIgnoreCase) == true;
    }

    /// <summary>sellingPrice minus online + campaign discounts (same math as the imitation store).</summary>
    private static (decimal Price, decimal? CompareAt) ComputeJewelryMsPrice(JsonElement p)
    {
        if (!p.TryGetProperty("sellingPrice", out var spEl))
            return (0, null);

        var sellingPrice = spEl.GetDecimal();
        var onlineDisc   = p.TryGetProperty("onlineDiscountPercentage", out var od) ? od.GetDecimal() : 0;
        var campaignDisc = p.TryGetProperty("campaignDiscountPercentage", out var cd) ? cd.GetDecimal() : 0;
        var price = Math.Round(sellingPrice * (1 - onlineDisc / 100m) * (1 - campaignDisc / 100m), 2);
        decimal? compareAt = (onlineDisc > 0 || campaignDisc > 0) && sellingPrice > price
            ? sellingPrice
            : null;
        return (price, compareAt);
    }

    // Shopify public products.json — amour.com.bd/products.json
    private static IEnumerable<NormalizedExternalProduct> ParseShopify(string json, string? siteUrl, string? urlHint)
    {
        using var doc = JsonDocument.Parse(json);
        if (!doc.RootElement.TryGetProperty("products", out var products))
            yield break;

        var baseUrl = (siteUrl ?? "").TrimEnd('/');

        foreach (var p in products.EnumerateArray())
        {
            var id     = p.GetProperty("id").GetRawText();
            var title  = p.GetProperty("title").GetString() ?? "";
            var handle = p.GetProperty("handle").GetString() ?? "";
            var type   = p.TryGetProperty("product_type", out var pt) ? ReadStringOrArray(pt) : null;
            var tags   = p.TryGetProperty("tags", out var tg) ? ReadStringOrArray(tg) : null;
            var categoryRaw = string.Join(", ", new[] { urlHint, type, tags }.Where(s => !string.IsNullOrWhiteSpace(s)));

            JsonElement variant = default;
            var hasVariant = false;
            var inStock = false;
            foreach (var v in p.GetProperty("variants").EnumerateArray())
            {
                if (!hasVariant)
                {
                    variant = v;
                    hasVariant = true;
                }

                if (v.TryGetProperty("available", out var av) && av.GetBoolean())
                    inStock = true;
            }

            if (!hasVariant) continue;

            var variantId = variant.GetProperty("id").GetRawText();
            var priceStr = variant.GetProperty("price").GetString() ?? "0";
            decimal.TryParse(priceStr, NumberStyles.Any, CultureInfo.InvariantCulture, out var price);

            decimal? compareAt = null;
            if (variant.TryGetProperty("compare_at_price", out var cap) &&
                cap.ValueKind == JsonValueKind.String)
            {
                var capStr = cap.GetString();
                if (!string.IsNullOrEmpty(capStr) &&
                    decimal.TryParse(capStr, NumberStyles.Any, CultureInfo.InvariantCulture, out var capVal) &&
                    capVal > price)
                    compareAt = capVal;
            }

            var sku = variant.TryGetProperty("sku", out var sk) ? sk.GetString() : null;

            string? imageUrl = null;
            var imageUrls = new List<string>();
            if (p.TryGetProperty("images", out var images))
            {
                foreach (var img in images.EnumerateArray())
                {
                    var src = img.GetProperty("src").GetString();
                    if (!string.IsNullOrEmpty(src))
                    {
                        imageUrls.Add(src);
                        imageUrl ??= src;
                    }
                }
            }

            var buyUrl = !string.IsNullOrEmpty(baseUrl) && !string.IsNullOrEmpty(handle)
                ? $"{baseUrl}/products/{handle}"
                : null;
            var checkoutUrl = !string.IsNullOrEmpty(baseUrl) && !string.IsNullOrEmpty(variantId)
                ? $"{baseUrl}/cart/{variantId}:1"
                : null;

            var bodyHtml = p.TryGetProperty("body_html", out var bh) ? bh.GetString() : null;
            var (hasGuarantee, guaranteeSnippet) = GuaranteeTextDetector.Detect(title, bodyHtml, tags);

            yield return new NormalizedExternalProduct
            {
                ExternalId         = id,
                Name               = title,
                Sku                = sku,
                ProductSlug        = handle,
                CategoryRaw        = categoryRaw,
                CategoryNormalized = CategoryNormalizer.Normalize(categoryRaw, title, urlHint),
                Price              = price,
                CompareAtPrice     = compareAt,
                ImageUrl           = imageUrl,
                ImageUrls          = imageUrls.ToArray(),
                InStock            = inStock,
                BuyUrl             = buyUrl,
                CheckoutUrl        = checkoutUrl,
                HasGuaranteeMention = hasGuarantee,
                GuaranteeSnippet    = guaranteeSnippet,
            };
        }
    }

    // WooCommerce Store API v1 — bracelance.com/wp-json/wc/store/v1/products
    private static IEnumerable<NormalizedExternalProduct> ParseWooCommerce(string json, string? urlHint)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var items = root.ValueKind == JsonValueKind.Array
            ? root.EnumerateArray()
            : root.TryGetProperty("products", out var wrapped)
                ? wrapped.EnumerateArray()
                : Enumerable.Empty<JsonElement>();

        foreach (var p in items)
        {
            var id   = p.GetProperty("id").GetRawText();
            var name = p.GetProperty("name").GetString() ?? "";
            var sku  = p.TryGetProperty("sku", out var sk) ? sk.GetString() : null;

            decimal price = 0;
            decimal? compareAt = null;
            if (p.TryGetProperty("prices", out var prices))
            {
                var minorUnit = prices.TryGetProperty("currency_minor_unit", out var mu)
                    ? mu.GetInt32() : 2;
                var divisor = (decimal)Math.Pow(10, minorUnit);

                static decimal ParseMinor(string? raw, decimal divisor)
                    => decimal.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out var minor)
                        ? minor / divisor : 0;

                var saleRaw    = prices.TryGetProperty("sale_price", out var sp) ? sp.GetString() : null;
                var regularRaw = prices.TryGetProperty("regular_price", out var rp) ? rp.GetString() : null;
                var priceRaw   = prices.GetProperty("price").GetString() ?? "0";

                var onSale = !string.IsNullOrEmpty(saleRaw) && saleRaw != "0";
                if (onSale)
                {
                    price     = ParseMinor(saleRaw, divisor);
                    compareAt = ParseMinor(regularRaw, divisor);
                    if (compareAt <= price) compareAt = null;
                }
                else
                {
                    price = ParseMinor(priceRaw, divisor);
                    if (price == 0) price = ParseMinor(regularRaw, divisor);
                }
            }

            string? categoryRaw = null;
            if (p.TryGetProperty("categories", out var cats))
            {
                var names = cats.EnumerateArray()
                    .Select(c => c.GetProperty("name").GetString())
                    .Where(n => !string.IsNullOrWhiteSpace(n));
                categoryRaw = string.Join(", ", names);
            }
            if (!string.IsNullOrWhiteSpace(urlHint))
                categoryRaw = string.IsNullOrWhiteSpace(categoryRaw) ? urlHint : $"{urlHint}, {categoryRaw}";

            string? imageUrl = null;
            var imageUrls = new List<string>();
            if (p.TryGetProperty("images", out var images))
            {
                foreach (var img in images.EnumerateArray())
                {
                    var src = img.GetProperty("src").GetString();
                    if (!string.IsNullOrEmpty(src))
                    {
                        imageUrls.Add(src);
                        imageUrl ??= src;
                    }
                }
            }

            var inStock = p.TryGetProperty("is_in_stock", out var st) && st.GetBoolean();
            var permalink = p.TryGetProperty("permalink", out var pl) ? pl.GetString() : null;
            string? checkoutUrl = null;
            if (!string.IsNullOrEmpty(permalink))
            {
                var siteRoot = permalink;
                var pathIdx = siteRoot.IndexOf('/', siteRoot.IndexOf("://", StringComparison.Ordinal) + 3);
                if (pathIdx > 0) siteRoot = siteRoot[..pathIdx];
                checkoutUrl = $"{siteRoot}/?add-to-cart={id}";
            }

            decimal rating = 0;
            int reviewCount = 0;
            if (p.TryGetProperty("average_rating", out var ar) &&
                decimal.TryParse(ar.GetString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var r))
                rating = r;
            if (p.TryGetProperty("review_count", out var rc))
                reviewCount = rc.GetInt32();

            var shortDesc = p.TryGetProperty("short_description", out var sd) ? sd.GetString() : null;
            var longDesc  = p.TryGetProperty("description", out var ld) ? ld.GetString() : null;
            var (hasGuarantee, guaranteeSnippet) = GuaranteeTextDetector.Detect(name, shortDesc, longDesc);

            yield return new NormalizedExternalProduct
            {
                ExternalId         = id,
                Name               = name,
                Sku                = sku,
                CategoryRaw        = categoryRaw,
                CategoryNormalized = CategoryNormalizer.Normalize(categoryRaw, name, urlHint),
                Price              = price,
                CompareAtPrice     = compareAt,
                ImageUrl           = imageUrl,
                ImageUrls          = imageUrls.ToArray(),
                InStock            = inStock,
                BuyUrl             = permalink,
                CheckoutUrl        = checkoutUrl,
                RatingAverage      = rating,
                RatingCount        = reviewCount,
                HasGuaranteeMention = hasGuarantee,
                GuaranteeSnippet    = guaranteeSnippet,
            };
        }
    }

    // JewelryMS imitation store public API
    private static IEnumerable<NormalizedExternalProduct> ParseJewelryMs(
        string json, string? siteUrl, string? apiUrl)
    {
        using var doc = JsonDocument.Parse(json);
        if (!doc.RootElement.TryGetProperty("items", out var items))
            yield break;

        var slug    = JewelryMsUrlHelper.ExtractSlug(apiUrl);
        var baseUrl = JewelryMsUrlHelper.ResolveCustomerBaseUrl(siteUrl, apiUrl);

        foreach (var p in items.EnumerateArray())
        {
            var id   = p.GetProperty("id").GetString() ?? "";
            var name = p.GetProperty("name").GetString() ?? "";
            var sku  = p.TryGetProperty("sku", out var sk) ? sk.GetString() : null;
            var cat  = p.TryGetProperty("category", out var c) ? c.GetString() : null;

            var (price, compareAt) = ComputeJewelryMsPrice(p);

            var qty = p.TryGetProperty("quantity", out var q) ? q.GetInt32() : 0;

            string? imageUrl = null;
            var imageUrls = new List<string>();
            if (p.TryGetProperty("primaryImageUrl", out var piu))
            {
                imageUrl = piu.GetString();
                if (!string.IsNullOrEmpty(imageUrl)) imageUrls.Add(imageUrl);
            }
            if (p.TryGetProperty("imageUrls", out var iu))
            {
                foreach (var img in iu.EnumerateArray())
                {
                    var src = img.GetString();
                    if (!string.IsNullOrEmpty(src) && !imageUrls.Contains(src))
                        imageUrls.Add(src);
                }
                imageUrl ??= imageUrls.FirstOrDefault();
            }

            string? buyUrl = null;
            string? checkoutUrl = null;
            if (!string.IsNullOrEmpty(baseUrl) && !string.IsNullOrEmpty(slug) && Guid.TryParse(id, out _))
            {
                buyUrl      = $"{baseUrl}/imitation-store/{slug}/product/{id}";
                checkoutUrl = JewelryMsUrlHelper.BuildCheckoutUrl(siteUrl, apiUrl, id);
            }

            var desc = p.TryGetProperty("description", out var descEl) ? descEl.GetString() : null;
            var guaranteeMonths = p.TryGetProperty("colorGuaranteeMonths", out var cgm) ? cgm.GetInt32() : 0;
            var (hasGuarantee, guaranteeSnippet) = guaranteeMonths > 0
                ? (true, $"{guaranteeMonths} months color guarantee")
                : GuaranteeTextDetector.Detect(name, desc);

            yield return new NormalizedExternalProduct
            {
                ExternalId         = id,
                Name               = name,
                Sku                = sku,
                CategoryRaw        = cat,
                CategoryNormalized = CategoryNormalizer.Normalize(cat, name,
                    CategoryNormalizer.IsFocusCategory(cat ?? "") || cat is "Necklace" or "Earrings" or "Nosepin" ? cat : null),
                Price              = price,
                CompareAtPrice     = compareAt,
                ImageUrl           = imageUrl,
                ImageUrls          = imageUrls.ToArray(),
                InStock            = qty > 0,
                BuyUrl             = buyUrl,
                CheckoutUrl        = checkoutUrl,
                HasGuaranteeMention = hasGuarantee,
                GuaranteeSnippet    = guaranteeSnippet,
            };
        }
    }

    /// <summary>Root <c>mainInfo.totalResults</c> on Daraz ajax pages — exact category product count.</summary>
    public static int GetDarazTotalResults(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("mainInfo", out var mainInfo))
                return 0;
            if (!mainInfo.TryGetProperty("totalResults", out var total))
                return 0;
            return total.ValueKind switch
            {
                JsonValueKind.Number => total.GetInt32(),
                JsonValueKind.String => int.TryParse(total.GetString(), out var n) ? n : 0,
                _ => 0,
            };
        }
        catch
        {
            return 0;
        }
    }

    // Daraz Bangladesh catalog ajax — www.daraz.com.bd/{slug}/?ajax=true&page=1
    private static IEnumerable<NormalizedExternalProduct> ParseDaraz(
        string json, string? siteUrl, string? urlHint)
    {
        using var doc = JsonDocument.Parse(json);
        if (!doc.RootElement.TryGetProperty("mods", out var mods)
            || !mods.TryGetProperty("listItems", out var listItemsMod))
            yield break;

        // Daraz returns mods.listItems as a flat array; tolerate a nested object too.
        JsonElement products;
        if (listItemsMod.ValueKind == JsonValueKind.Array)
            products = listItemsMod;
        else if (listItemsMod.ValueKind == JsonValueKind.Object
                 && listItemsMod.TryGetProperty("listItems", out var inner)
                 && inner.ValueKind == JsonValueKind.Array)
            products = inner;
        else
            yield break;

        var baseUrl = (siteUrl ?? "https://www.daraz.com.bd").TrimEnd('/');

        foreach (var p in products.EnumerateArray())
        {
            if (p.ValueKind != JsonValueKind.Object) continue;

            var name = GetString(p, "name", "title") ?? "Unknown";
            var itemId = GetString(p, "itemId", "item_id");
            if (string.IsNullOrEmpty(itemId) && p.TryGetProperty("itemId", out var idEl))
                itemId = idEl.GetRawText().Trim('"');
            var skuId = GetString(p, "skuId", "sku_id");
            if (string.IsNullOrEmpty(skuId) && p.TryGetProperty("skuId", out var skuEl))
                skuId = skuEl.GetRawText().Trim('"');
            if (string.IsNullOrEmpty(itemId)) continue;

            var externalId = string.IsNullOrEmpty(skuId) ? itemId : $"{itemId}:{skuId}";

            decimal price = 0;
            if (p.TryGetProperty("price", out var pr))
                price = pr.ValueKind == JsonValueKind.Number ? pr.GetDecimal() : ParseDecimal(pr.GetString());

            decimal? compareAt = null;
            if (p.TryGetProperty("originalPrice", out var op))
            {
                var orig = op.ValueKind == JsonValueKind.Number ? op.GetDecimal() : ParseDecimal(op.GetString());
                if (orig > price) compareAt = orig;
            }

            var imageUrl = GetString(p, "image", "img", "imageUrl");
            if (string.IsNullOrEmpty(imageUrl) && p.TryGetProperty("images", out var imgs)
                && imgs.ValueKind == JsonValueKind.Array)
                imageUrl = imgs.EnumerateArray().Select(i => i.GetString()).FirstOrDefault(s => !string.IsNullOrEmpty(s));

            var itemUrl = GetString(p, "itemUrl", "productUrl", "url", "link");
            if (!string.IsNullOrEmpty(itemUrl))
            {
                if (itemUrl.StartsWith("//", StringComparison.Ordinal))
                    itemUrl = "https:" + itemUrl;
                else if (itemUrl.StartsWith("/", StringComparison.Ordinal))
                    itemUrl = baseUrl + itemUrl;
            }

            var brand = GetString(p, "brandName", "brand");
            var catRaw = string.Join(" | ", new[] { urlHint, brand }.Where(s => !string.IsNullOrWhiteSpace(s)));

            yield return new NormalizedExternalProduct
            {
                ExternalId         = externalId,
                Name               = name,
                Sku                = skuId,
                CategoryRaw        = catRaw,
                CategoryNormalized = CategoryNormalizer.Normalize(catRaw, name, urlHint),
                Price              = price,
                CompareAtPrice     = compareAt,
                ImageUrl           = imageUrl,
                ImageUrls          = imageUrl != null ? new[] { imageUrl } : Array.Empty<string>(),
                InStock            = true,
                BuyUrl             = itemUrl,
                HasGuaranteeMention = false,
            };
        }
    }

    // Best-effort for custom JSON arrays (also handles JewelryMS-shaped payloads)
    private static IEnumerable<NormalizedExternalProduct> ParseGeneric(
        string json, string? siteUrl, string? apiUrl, string? urlHint)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        IEnumerable<JsonElement> EnumerateItems()
        {
            if (root.ValueKind == JsonValueKind.Array) return root.EnumerateArray();
            foreach (var key in new[] { "items", "products", "data", "results" })
            {
                if (root.TryGetProperty(key, out var arr) && arr.ValueKind == JsonValueKind.Array)
                    return arr.EnumerateArray();
            }
            return Enumerable.Empty<JsonElement>();
        }

        var slug    = JewelryMsUrlHelper.ExtractSlug(apiUrl);
        var baseUrl = JewelryMsUrlHelper.ResolveCustomerBaseUrl(siteUrl, apiUrl);

        foreach (var p in EnumerateItems())
        {
            var id = GetString(p, "id", "productId", "external_id") ?? Guid.NewGuid().ToString();
            var name = GetString(p, "name", "title", "productName") ?? "Unknown";
            var sku  = GetString(p, "sku", "SKU");
            var cat  = GetString(p, "category", "product_type", "productType", "type");

            decimal price = 0;
            decimal? compareAt = null;
            if (p.TryGetProperty("sellingPrice", out _))
            {
                (price, compareAt) = ComputeJewelryMsPrice(p);
            }
            else if (p.TryGetProperty("price", out var pr))
            {
                price = pr.ValueKind == JsonValueKind.Number ? pr.GetDecimal() : ParseDecimal(pr.GetString());
            }

            string? imageUrl = GetString(p, "imageUrl", "image_url", "primaryImageUrl", "image", "thumbnail");
            var buyUrl = GetString(p, "buyUrl", "buy_url", "permalink", "url", "link");

            string? checkoutUrl = null;
            if (string.IsNullOrEmpty(buyUrl) && !string.IsNullOrEmpty(slug) && Guid.TryParse(id, out _))
            {
                buyUrl      = JewelryMsUrlHelper.BuildProductUrl(siteUrl, apiUrl, id);
                checkoutUrl = JewelryMsUrlHelper.BuildCheckoutUrl(siteUrl, apiUrl, id);
            }

            var qty = p.TryGetProperty("quantity", out var q) ? q.GetInt32() : (int?)null;
            var inStock = qty.HasValue ? qty > 0 : true;

            var desc = GetString(p, "description", "body_html", "short_description");
            var guaranteeMonths = p.TryGetProperty("colorGuaranteeMonths", out var cgm) ? cgm.GetInt32() : 0;
            var (hasGuarantee, guaranteeSnippet) = guaranteeMonths > 0
                ? (true, $"{guaranteeMonths} months color guarantee")
                : GuaranteeTextDetector.Detect(name, desc);

            yield return new NormalizedExternalProduct
            {
                ExternalId         = id,
                Name               = name,
                Sku                = sku,
                CategoryRaw        = cat,
                CategoryNormalized = CategoryNormalizer.Normalize(cat, name, urlHint),
                Price              = price,
                CompareAtPrice     = compareAt,
                ImageUrl           = imageUrl,
                ImageUrls          = imageUrl != null ? new[] { imageUrl } : Array.Empty<string>(),
                InStock            = inStock,
                BuyUrl             = buyUrl,
                CheckoutUrl        = checkoutUrl,
                HasGuaranteeMention = hasGuarantee,
                GuaranteeSnippet    = guaranteeSnippet,
            };
        }
    }

    /// <summary>Shopify legacy API uses comma-separated strings; newer stores (e.g. Amour) use JSON arrays.</summary>
    private static string? ReadStringOrArray(JsonElement el)
    {
        return el.ValueKind switch
        {
            JsonValueKind.String => el.GetString(),
            JsonValueKind.Array  => string.Join(", ", el.EnumerateArray()
                .Select(item => item.ValueKind == JsonValueKind.String ? item.GetString() : item.ToString())
                .Where(s => !string.IsNullOrWhiteSpace(s))),
            _ => null,
        };
    }

    private static string? GetString(JsonElement el, params string[] names)
    {
        foreach (var n in names)
        {
            if (el.TryGetProperty(n, out var v) && v.ValueKind == JsonValueKind.String)
                return v.GetString();
        }
        return null;
    }

    private static decimal ParseDecimal(string? s)
        => decimal.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d) ? d : 0;

    private static string? GetMetaContent(string html, string key, string attr)
    {
        foreach (var pattern in new[]
        {
            $@"<meta\s+[^>]*{attr}=[""']{Regex.Escape(key)}[""'][^>]*content=[""']([^""']*)[""']",
            $@"<meta\s+[^>]*content=[""']([^""']*)[""'][^>]*{attr}=[""']{Regex.Escape(key)}[""']",
        })
        {
            var m = Regex.Match(html, pattern, RegexOptions.IgnoreCase | RegexOptions.Singleline);
            if (m.Success)
                return m.Groups[1].Value.Trim();
        }
        return null;
    }

    private static string? GetLinkHref(string html, string rel)
    {
        foreach (var pattern in new[]
        {
            $@"<link\s+[^>]*rel=[""']{Regex.Escape(rel)}[""'][^>]*href=[""']([^""']*)[""']",
            $@"<link\s+[^>]*href=[""']([^""']*)[""'][^>]*rel=[""']{Regex.Escape(rel)}[""']",
        })
        {
            var m = Regex.Match(html, pattern, RegexOptions.IgnoreCase | RegexOptions.Singleline);
            if (m.Success)
                return m.Groups[1].Value.Trim();
        }
        return null;
    }
}
