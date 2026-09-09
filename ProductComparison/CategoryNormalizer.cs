using JewelryMS.Domain.Enums;

namespace JewelryMS.Application.Services.ProductComparison;



/// <summary>

/// Maps BD shop categories (Bracelance, Amour, Mahira Mart, Mirpur Jewelry City, JewelryMS)

/// to JewelryMS jewelry_category enum values.

/// </summary>

public static class CategoryNormalizer

{

    /// <summary>All imitation jewelry categories — matches <see cref="JewelryCategory"/> enum.</summary>

    public static readonly string[] FocusCategories = Enum.GetNames<JewelryCategory>();



    // Order matters — more specific rules first.

    private static readonly (string[] Keys, string Category)[] Rules =

    {

        // Brooch before chain/ring — ipromart "Hijab Brooch", "Chain brooch", etc.

        (new[] { "hijab brooch", "hijab-brooch", "brooch", "ব্রোচ" }, "Brooch"),



        // Payel / anklet (Mahira Mart, Mirpur, ipromart)

        (new[] { "payel", "payal", "anklet", "anglet", "পায়েল", "নূপুর", "nupur", "nunpur" }, "Anklet"),



        // Mirpur / bridal BD-specific

        (new[] { "shita har", "shita-har", "bridal-shita", "শীতা" }, "ShitaHar"),

        (new[] { "maang tikka", "maang-tikka", "maangtikka", "মাথার টিকলি" }, "MaangTikka"),

        (new[] { "tayra and tikli", "tayra-and-tikli", "tayra", "tikli", "তাইরা" }, "TayraTikli"),

        (new[] { "bridal chur", "bridal-chur", "bridal churi", "bridal-churi", "bridal-churi2", "bridal churi2" }, "BridalChuri"),

        (new[] { "churi-collection", "churi collection", "churi" }, "Churi"),

        (new[] { "bridal noth", "bridal-noth", "noth collection", "bridal nosepin" }, "BridalNosepin"),



        // Gender-specific rings (Mirpur Gents / Ladies)

        (new[] { "men's ring", "mens ring", "mens-ring", "men ring", "gents ring", "gents collection", "men's collection" }, "MensRing"),

        (new[] { "women's ring", "womens ring", "womens-ring", "ladies ring", "ladies' ring", "women ring", "lady ring" }, "WomensRing"),



        // Bangle before bracelet

        (new[] { "bangles", "bangle", "বেঙ্গল", "বালা" }, "Bangle"),



        // Bracelance bracelet sub-types

        (new[] { "stone bead", "stone-bead", "stone beads", "set bracelet", "set_bracelet",

                  "horoscope bracelet", "horoscope_bracelet", "leather bracelet", "leather-bracelet",

                  "charm bracelet", "charm_bracelet", "anchor bracelet", "anchor-bracelets",

                  "bracelets & bangles", "bracelets-bangles" }, "Bracelet"),



        // Belly / waist chain before bare "chain" — "Belly chain" must not map to Chain

        (new[] { "waist chain", "waist-chain", "waist chains", "belly chain", "belly-chain", "belly-chains", "bellychain", "body chain waist" }, "WaistChain"),



        // Locket = chain (Bracelance, Mirpur loket)

        (new[] { "locket", "loket", "লকেট", "chain-loket", "cuban chain", "chain", "চেইন" }, "Chain"),



        (new[] { "bracelet", "ব্রেসলেট" }, "Bracelet"),



        (new[] { "eartop", "ear top", "ear-top", "earring", "earrings", "কানের" }, "Earrings"),

        (new[] { "pendant", "prndant", "পেন্ডেন্ট" }, "Pendant"),

        (new[] { "amulet" }, "Pendant"),



        (new[] { "necklace", "bridal-necklace", "bridal necklace", "নেকলেস", "হার" }, "Necklace"),

        (new[] { "choker", "চোকার" }, "Choker"),

        (new[] { "mangalsutra", "মঙ্গলসূত্র" }, "Mangalsutra"),

        (new[] { "toe ring", "toe-ring", "toering", "পায়ের আংটি" }, "ToeRing"),

        (new[] { "cufflink", "cufflinks", "কাফলিঙ্ক" }, "Cufflinks"),

        (new[] { "tiara", "মুকুট" }, "Tiara"),

        (new[] { "kamarband", "kamar band", "কোমরবন্ধ" }, "Kamarband"),

        (new[] { "armlet", "বাজুবন্ধ" }, "Armlet"),

        (new[] { "body chain", "body-chain", "বডি চেইন" }, "BodyChain"),

        (new[] { "nosepin", "nose pin", "নথ", "নাক" }, "Nosepin"),



        (new[] { "jewelryset", "jewelry set", "combo set", "bridal collection", "combo-set" }, "JewelrySet"),

        // Bare "ring" LAST — it lives inside "earrings", "toe ring", "key ring" etc.,
        // so every more specific rule above must win first.
        (new[] { "ring" }, "WomensRing"),

    };



    private static readonly Dictionary<string, string> UrlHints = new(StringComparer.OrdinalIgnoreCase)

    {

        // Amour — men

        ["men-bracelets"]      = "Bracelet",

        ["men-pendants"]       = "Chain",

        // Bracelance

        ["bracelet"]           = "Bracelet",

        ["bangles"]            = "Bangle",

        ["locket"]             = "Chain",

        ["stone-beads"]        = "Bracelet",

        ["set_bracelet"]       = "Bracelet",

        ["horoscope_bracelet"] = "Bracelet",

        ["leather-bracelet"]   = "Bracelet",

        ["charm_bracelet"]     = "Bracelet",

        ["anchor-bracelets"]   = "Bracelet",

        // Mahira Mart — women

        ["payel"]              = "Anklet",

        ["anklet"]             = "Anklet",

        // ipromart.xyz

        ["hijab-brooch"]       = "Brooch",

        ["pendent"]            = "Chain",

        ["earrings"]           = "Earrings",

        ["braslate"]           = "Bracelet",

        ["gift-item"]          = "Other",

        ["bracelets-bangles"]  = "Bracelet",

        ["earring"]            = "Earrings",

        ["jewellery"]          = "Necklace",

        // Mirpur Jewelry City — women + gents

        ["bridal-shita"]       = "ShitaHar",

        ["tayra-and-tikli"]    = "TayraTikli",

        ["bridal-chur"]        = "BridalChuri",

        ["churi-collection"]   = "Churi",

        ["bridal-noth"]        = "BridalNosepin",

        ["mens-ring"]          = "MensRing",

        ["chain-loket"]        = "Chain",

        ["bridal-necklace"]    = "Necklace",

        ["eartop"]             = "Earrings",

        ["earring-1"]          = "Earrings",

        ["chain-1"]            = "Chain",

        ["combo-set"]          = "JewelrySet",

        ["ring"]               = "WomensRing",

        // 4 O'Clock Official (Shopify)

        ["cuff-bangles"]       = "Bangle",

        ["handcuff-bangles"]   = "Bangle",

        ["enamel-bangles"]     = "Bangle",

        ["cloisonne"]          = "Bangle",

        ["boho-bangles"]       = "Bangle",

        ["finger-rings"]       = "WomensRing",

        ["finger-ring-bracelet"] = "Bracelet",

        ["finger-ringer-sets"] = "JewelrySet",

        ["waist-chains"]       = "WaistChain",

        ["necklaces"]          = "Necklace",

        ["bracelets"]          = "Bracelet",

        // Daraz Bangladesh category slugs

        ["womens-necklaces-chains"] = "Necklace",

        ["womens-bangles-bracelets"] = "Bracelet",

        ["shop-mens-bracelets"]      = "Bracelet",

        ["mens-necklaces-chains"]    = "Necklace",

        ["womens-rings"]             = "WomensRing",

        ["mens-rings"]               = "MensRing",

        ["womens-brooches"]          = "Brooch",

        ["womens-jewellery-sets"]    = "JewelrySet",

        ["womens-earrings"]          = "Earrings",

        ["womens-anklets"]           = "Anklet",

        ["womens-nose-rings"]        = "Nosepin",

        ["womens-pendants"]          = "Pendant",

        ["womens-chokers"]           = "Choker",

        // StoreX v4 category slugs

        ["necklace"]                 = "Necklace",

        ["ring-set"]                 = "JewelrySet",

        ["belly-chain"]              = "WaistChain",

        ["body-jewelry"]             = "WaistChain",

        ["jewllery-set"]             = "JewelrySet",

        ["jewellery-set"]            = "JewelrySet",

    };



    public static string? HintFromFetchUrl(string? url)

    {

        if (string.IsNullOrWhiteSpace(url)) return null;

        var lower = url.ToLowerInvariant();



        foreach (var (slug, category) in UrlHints.OrderByDescending(kv => kv.Key.Length))

        {

            if (lower.Contains(slug, StringComparison.OrdinalIgnoreCase))

                return category;

        }



        return null;

    }



    public static string Normalize(string? categoryRaw, string? productName, string? urlHint = null)

    {

        if (!string.IsNullOrWhiteSpace(urlHint) && IsFocusCategory(urlHint))

            return RefineWithTitle(urlHint, productName, categoryRaw);



        var haystack = $"{categoryRaw} {productName}".ToLowerInvariant();



        foreach (var (keys, category) in Rules)

        {

            if (keys.Any(k => haystack.Contains(k, StringComparison.OrdinalIgnoreCase)))

                return category;

        }



        if (!string.IsNullOrWhiteSpace(categoryRaw))

        {

            var trimmed = categoryRaw.Trim();

            if (FocusCategories.Contains(trimmed, StringComparer.OrdinalIgnoreCase))

                return trimmed;

        }



        return "Other";

    }



    public static bool IsFocusCategory(string category)

        => FocusCategories.Contains(category, StringComparer.OrdinalIgnoreCase);



    private static string RefineWithTitle(string hint, string? productName, string? categoryRaw)

    {

        var haystack = $"{categoryRaw} {productName}".ToLowerInvariant();

        foreach (var (keys, category) in Rules)

        {

            if (keys.Any(k => haystack.Contains(k, StringComparison.OrdinalIgnoreCase)))

            {

                if (category != hint)

                    return category;

                break;

            }

        }

        return hint;

    }

}

