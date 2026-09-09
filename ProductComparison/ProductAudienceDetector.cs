using System.Text.RegularExpressions;
using JewelryMS.Domain.DTOs.ProductComparison;

namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>Detects Men / Women / Baby / Children from competitor product titles at sync time.</summary>
public static class ProductAudienceDetector
{
    private static readonly (string Tag, string[] Keys)[] Rules =
    [
        ("Baby", ["baby", "infant", "newborn", "শিশু", "বেবি"]),
        ("Children", ["children", "child", "kids", "kid", "junior", "toddler", "বাচ্চা", "শিশুদের"]),
        ("Men", ["men's", "mens", "men ", " men", "gents", "gentleman", "groom", "groom's", "grooms", "bridegroom", "male", "পুরুষ", "ছেলেদের", "বর"]),
        ("Women", ["women's", "womens", "women ", " women", "woman", "lady", "ladies", "ladies'", "girls", "girl", "bride", "bridal", "female", "মহিলা", "নারী", "মেয়েদের", "কনে", "বৌদি"]),
    ];

    public static string[] DetectTags(string? name, string? extra = null)
    {
        var text = Normalize($"{name} {extra}");
        if (string.IsNullOrWhiteSpace(text)) return [];

        var tags = new List<string>();
        foreach (var (tag, keys) in Rules)
        {
            if (keys.Any(k => MatchesKeyword(text, k)))
                tags.Add(tag);
        }

        if ((MatchesKeyword(text, "boys") || MatchesKeyword(text, "boy"))
            && !tags.Contains("Men") && !tags.Contains("Children"))
            tags.Add("Children");

        // Wedding / pair sets — "bride groom set", "couple ring"
        if (MatchesKeyword(text, "couple"))
        {
            if (!tags.Contains("Men")) tags.Add("Men");
            if (!tags.Contains("Women")) tags.Add("Women");
        }

        return tags.Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
    }

    private static bool MatchesKeyword(string text, string keyword)
    {
        var k = Regex.Escape(Normalize(keyword));
        return Regex.IsMatch(text, $@"(?<![a-z0-9]){k}(?![a-z0-9])", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    }

    /// <summary>Ring category: nudge toward MensRing / WomensRing when title says so.</summary>
    public static string RefineCategory(string? name, string category, string[]? tags = null)
    {
        tags ??= DetectTags(name);
        if (tags.Length == 0) return category;

        var isRingish = category is "Ring" or "WomensRing" or "MensRing";
        if (!isRingish) return category;

        if (tags.Contains("Men", StringComparer.OrdinalIgnoreCase)
            && !tags.Contains("Women", StringComparer.OrdinalIgnoreCase))
            return "MensRing";

        if (tags.Contains("Women", StringComparer.OrdinalIgnoreCase)
            && !tags.Contains("Men", StringComparer.OrdinalIgnoreCase))
            return "WomensRing";

        return category;
    }

    private static string Normalize(string? text)
        => Regex.Replace((text ?? "").ToLowerInvariant(), @"\s+", " ").Trim();

    public static void Enrich(NormalizedExternalProduct p)
    {
        p.AudienceTags = DetectTags(p.Name, p.CategoryRaw);
        p.CategoryNormalized = RefineCategory(p.Name, p.CategoryNormalized, p.AudienceTags);
    }
}
