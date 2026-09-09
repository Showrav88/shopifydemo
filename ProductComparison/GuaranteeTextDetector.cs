using System.Text.RegularExpressions;

namespace JewelryMS.Application.Services.ProductComparison;

/// <summary>Detects guarantee / warranty wording in competitor product text (sync-time).</summary>
public static class GuaranteeTextDetector
{
    private static readonly string[] Keywords =
    [
        "guarantee", "guaranteed", "warranty", "warrantee",
        "গ্যারান্টি", "ওয়ারেন্টি", "ওয়ারেন্টি", "ওয়ারেন্টি",
        "colour guarantee", "color guarantee", "year colour", "years colour",
        "year color", "years color", "রং উঠবে না", "রং ফেড",
    ];

    public static (bool HasMention, string? Snippet) Detect(params string?[] parts)
    {
        var text = StripHtml(string.Join(' ', parts.Where(p => !string.IsNullOrWhiteSpace(p))));
        if (string.IsNullOrWhiteSpace(text))
            return (false, null);

        var lower = text.ToLowerInvariant();
        string? matched = null;
        foreach (var kw in Keywords)
        {
            var idx = lower.IndexOf(kw, StringComparison.OrdinalIgnoreCase);
            if (idx < 0) continue;
            matched = kw;
            var start = Math.Max(0, idx - 40);
            var len   = Math.Min(text.Length - start, matched.Length + 80);
            var slice = text.Substring(start, len).Trim();
            slice = Regex.Replace(slice, @"\s+", " ");
            if (slice.Length > 120) slice = slice[..117] + "…";
            return (true, slice);
        }

        return (false, null);
    }

    public static string StripHtml(string? html)
    {
        if (string.IsNullOrWhiteSpace(html)) return string.Empty;
        var s = Regex.Replace(html, "<[^>]+>", " ");
        s = System.Net.WebUtility.HtmlDecode(s);
        return Regex.Replace(s, @"\s+", " ").Trim();
    }
}
