# VariantLibrary + Browserless guide

## Separate VariantLibrary sheet (not mixed with LookupTables)

Variants are configured on their own tab — **VariantLibrary** — like PromptLibrary.

| Tab | Purpose |
|-----|---------|
| **LookupTables** | Vendor, category, collection only |
| **VariantLibrary** | Size/color/option presets — any combo Shopify accepts |
| **PromptLibrary** | AI listing prompts |
| **Master_Sheetv1** | Product URLs + optional overrides |

Import `sheet-variant-library.csv` into a tab named **VariantLibrary**.

## How presets work

Each row in **VariantLibrary** is one preset:

| Column | Example |
|--------|---------|
| preset_id | `uk-shirts` |
| match_profile | `clothing_alpha` (auto-pick when preset blank) |
| option1_name | `Size` |
| option1_values | `XS,S,M,L,XL,XXL` |
| option2_name | `Color` |
| option2_values | `Black,Navy,White,Grey,Beige,Red,Olive,Tan,Blue,Burgundy` |
| option3_name | (optional) `Length` |
| option3_values | (optional) `30,32,34` |

The workflow builds **every combination** (cartesian product) — same as Shopify variant matrix.

### Built-in presets (edit freely)

| preset_id | Options | Notes |
|-----------|---------|-------|
| `uk-shirts` | Size + Color | UK alpha, 10 sell colors |
| `us-shirts` | Size + Color | US sizes incl. 2XL |
| `uk-jeans` | Waist + Length + Color | UK jeans grid |
| `us-jeans` | Waist + Length + Color | US waist range |
| `uk-shoes` | UK Size + Color | 10 colors |
| `us-shoes` | US Size + Color | 10 colors |
| `bags` | Color only | 10 colors, one size |
| `generic` | Size + Color | Fallback |
| `custom` | (empty) | You type options on the product row |

## What you type on the product sheet

| Column | You type? |
|--------|-----------|
| **Product URL** | Yes |
| **Variant preset ID** | Optional — e.g. `us-shirts`, `uk-jeans`. Leave blank = auto from profile |
| **Option 1/2/3 name + values** | Formulas — edit **VariantLibrary** instead |
| **Sizes / Colors / Lengths** | Display + scrape override (scrape can fill Sizes) |

### Custom combo (any Shopify options)

1. Set **Variant preset ID** = `custom`
2. Delete formulas in **Option 1 name**, **Option 1 values**, etc.
3. Type any names Shopify accepts, e.g. `Material` + `Cotton,Linen` or `US Size` + `8,9,10`

Or add a new row to **VariantLibrary** with your preset_id and import again.

## Priority when building variants

1. **Scraped variants** JSON (from competitor page)
2. **Option 1/2/3** columns (from VariantLibrary formulas)
3. Manual **Sizes / Colors / Lengths** on the row
4. Single-variant fallback

## Browserless (one-time n8n setup)

| Credential | Value |
|------------|-------|
| Type | HTTP Query Auth |
| Name | `Browserless API` |
| Query param | `token` = your browserless.io API key |

**Auto-routing (Browserless):** Mango, Macy's, Zara, Gap, Lululemon, Calvin Klein, Tommy Hilfiger, Abercrombie, Ralph Lauren, etc. — see `BROWSER_DOMAINS` in `scripts/n8n-scrape-extractors.js`.

**Shopify .json fast path:** Everlane, Skims, MATE, Tecovas, Fashion Nova, Dôen, Origin, LA Apparel, Black Halo, Universal Standard — see `SHOPIFY_JSON_DOMAINS` in the same file.

**Force browser** = `YES` on any row forces Browserless.

## Re-import checklist

1. `sheet-variant-library.csv` → **VariantLibrary** tab (new)
2. `sheet-lookup-tables.csv` → **LookupTables** (variant rows removed)
3. `sheet-products.csv` → **Master_Sheetv1**
4. `ShopifyProductAdd.V2.json` → n8n
