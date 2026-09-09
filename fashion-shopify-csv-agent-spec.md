# Fashion Shopify CSV Agent — Technical Specification

**Version:** 1.0  
**Date:** September 7, 2026  
**Purpose:** Blueprint for building an AI-assisted agent that scrapes product data from random websites and exports Shopify-ready CSV files optimized for AI-enabled product catalog and listing.  
**Initial vertical:** Men's and women's fashion (clothing + accessories).  
**Future verticals:** Jewelry, shoes, and any product category by swapping rule files.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Reference: JewelryMS Super Admin Parsing System](#2-reference-jewelryms-super-admin-parsing-system)
3. [New Tool Vision](#3-new-tool-vision)
4. [System Architecture](#4-system-architecture)
5. [Normalized Product Schema](#5-normalized-product-schema)
6. [Discovery Layer (No AI)](#6-discovery-layer-no-ai)
7. [Parsing Layer (No AI)](#7-parsing-layer-no-ai)
8. [Rule-Based Enrichment (No AI)](#8-rule-based-enrichment-no-ai)
9. [AI Enrichment Gate (Minimal Tokens)](#9-ai-enrichment-gate-minimal-tokens)
10. [Shopify CSV Export Format](#10-shopify-csv-export-format)
11. [Fashion Category Taxonomy](#11-fashion-category-taxonomy)
12. [Recommended Project Structure](#12-recommended-project-structure)
13. [What to Port from JewelryMS](#13-what-to-port-from-jewelryms)
14. [Build Order (Phased Plan)](#14-build-order-phased-plan)
15. [Token Budget Estimates](#15-token-budget-estimates)
16. [Key Code References in JewelryMS](#16-key-code-references-in-jewelryms)
17. [Appendix: Shopify CSV Column Reference](#17-appendix-shopify-csv-column-reference)

---

## 1. Executive Summary

JewelryMS already contains a production-grade, **100% algorithmic** product parsing pipeline in the **Price Compare / Super Admin Comparison** feature. It discovers e-commerce platforms from a domain URL, fetches public JSON or HTML, normalizes products into a common schema, applies keyword-based category and audience rules, and stores results in PostgreSQL.

This document describes how to **reuse that architecture** for a new standalone agent with a different goal:

| JewelryMS Price Compare | New Fashion CSV Agent |
|-------------------------|----------------------|
| Compare competitor prices | Create Shopify import CSV |
| Cache in PostgreSQL | Export `.csv` file |
| Jewelry categories | Fashion categories (extensible) |
| Zero AI | AI only for low-confidence gaps |
| Super admin UI in JewelryMS | Standalone agent / bot |

**Core principle:** Parse and structure as much as possible with algorithms. Use AI only when rule-based confidence is low, and batch AI calls to minimize token usage.

---

## 2. Reference: JewelryMS Super Admin Parsing System

### 2.1 Pipeline Overview

```
Domain URL
    → Shop Discovery (detect platform)
    → Fetch (HTTP GET: API, sitemap, HTML)
    → Parse (platform-specific → NormalizedExternalProduct)
    → Normalize (CategoryNormalizer keyword rules)
    → Enrich (ProductAudienceDetector, GuaranteeTextDetector)
    → Store (external_product_cache in PostgreSQL)
    → Manual comparison groups → Public /compare pages
```

### 2.2 Supported Platforms

| Platform | Detection method | Data source |
|----------|------------------|-------------|
| Shopify | `/collections.json`, `/products.json` | Public Storefront JSON API |
| WooCommerce | `/wp-json/wc/store/v1/products` | WC Store API v1 |
| Daraz | Domain contains `daraz.com.bd` | Ajax catalog API |
| Zatiq Easy | `/api/sitemaps.xml` + JSON-LD | Sitemap + product page HTML/RSC |
| StoreX | `/sitemap.xml` + meta tags | StoreX v4 API or HTML fallback |
| JewelryMS | Custom API URL shape | `{ items: [...] }` JSON |
| Custom | Generic fallback | Tries `items`, `products`, `data`, `results` arrays |

### 2.3 Key Backend Files (JewelryMS)

| File | Role |
|------|------|
| `src/JewelryMS.Application/Services/ProductComparison/ShopDiscoveryService.cs` | Platform detection + category discovery |
| `src/JewelryMS.Application/Services/ProductComparison/ExternalProductParsers.cs` | JSON/HTML/RSC parsers per platform |
| `src/JewelryMS.Application/Services/ProductComparison/CategoryNormalizer.cs` | Ordered keyword rules → category enum |
| `src/JewelryMS.Application/Services/ProductComparison/ProductAudienceDetector.cs` | Men/Women/Baby/Children from title |
| `src/JewelryMS.Application/Services/ProductComparison/GuaranteeTextDetector.cs` | Guarantee keyword detection |
| `src/JewelryMS.Application/Services/ProductComparison/ShopifyCatalog.cs` | Headless Shopify sync |
| `src/JewelryMS.Application/Services/ProductComparisonService.cs` | Orchestration: discover, test-fetch, sync |
| `src/JewelryMS.Domain/DTOs/ProductComparison/ProductComparisonDtos.cs` | DTOs including `NormalizedExternalProduct` |
| `src/JewelryMS.API/Controllers/SuperAdminProductComparisonController.cs` | Super-admin REST API |
| `jewelry-ms-frontend/src/pages/superadmin/SuperAdminComparisonPanel.jsx` | Super admin UI |

### 2.4 Normalized Schema (JewelryMS)

```csharp
public class NormalizedExternalProduct
{
    public string   ExternalId;
    public string   Name;
    public string?  Sku;
    public string?  CategoryRaw;
    public string   CategoryNormalized;
    public decimal  Price;
    public decimal? CompareAtPrice;
    public string?  ImageUrl;
    public string[] ImageUrls;
    public bool     InStock;
    public string?  ProductSlug;      // Shopify handle
    public string?  BuyUrl;
    public string?  CheckoutUrl;
    public string[] AudienceTags;    // Men, Women, Baby, Children
    public bool     HasGuaranteeMention;
    public string?  GuaranteeSnippet;
}
```

### 2.5 Design Patterns Worth Reusing

1. **Platform router first** — URL shape and HTTP probes decide the parser; never guess blindly.
2. **Fallback chain** — API JSON → JSON-LD → HTML meta tags → generic array scan.
3. **Ordered keyword rules** — More specific matches win (e.g. `"cargo pants"` before `"pants"`).
4. **Human review step** — Staff maps categories before final export (optional but recommended).
5. **Dedup by external ID** — Safe re-syncs without duplicates.
6. **No AI anywhere** — Entire JewelryMS pipeline is deterministic; proves the approach works at scale.

---

## 3. New Tool Vision

### 3.1 User Flow

```
1. User pastes: shop domain, category URL, or single product URL
2. Agent discovers platform and fetches products
3. Algorithmic parse → NormalizedFashionProduct (all variants)
4. Rule engines assign category, gender, size, color, material
5. Confidence scorer flags fields needing AI
6. (Optional) Batched AI fills gaps: description, SEO, tags
7. Preview table in UI — user reviews/edits
8. Export Shopify Product CSV → upload to Shopify Admin
9. Shopify AI catalog uses rich structured data for listing
```

### 3.2 Goals

- Work with **random websites** (Shopify, WooCommerce, custom HTML stores).
- Produce **Shopify-native CSV** with proper variant rows (Size × Color matrix).
- Optimize for **Shopify Magic / AI-enabled product catalog** via rich HTML, tags, Type, and metafields.
- **Minimize AI token usage** — target 85%+ algorithmic, 15% AI gap-fill.
- **Extensible** — swap category rule files for jewelry, shoes, etc. without rewriting parsers.

### 3.3 Out of Scope (v1)

- Direct Shopify Admin API upload (CSV import is sufficient for v1).
- Image downloading/re-hosting (use source image URLs in CSV).
- Real-time inventory sync (one-time export focus).

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│         (domain URL | category URL | product URL)                │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: DISCOVERY (algorithmic)                                │
│  PlatformDetector → SitemapCrawler → FetchUrlBuilder             │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: PARSERS (algorithmic)                                  │
│  Shopify | WooCommerce | JsonLd | OpenGraph | RSC | GenericHtml  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: NORMALIZE (algorithmic)                                │
│  NormalizedFashionProduct + all variants + confidence scores     │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: RULE ENRICHMENT (algorithmic)                          │
│  CategoryNormalizer | AudienceDetector | VariantParser           │
│  MaterialDetector | SizeNormalizer | BrandExtractor              │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: AI GATE (conditional — only low-confidence fields)     │
│  ConfidenceScorer → batched AiEnrichmentService                  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: EXPORT                                                 │
│  ShopifyCsvBuilder → validated .csv file                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Normalized Product Schema

### 5.1 NormalizedFashionProduct

```typescript
interface NormalizedFashionProduct {
  // ── Core identifiers ──
  externalId: string;
  sourceUrl: string;
  sourcePlatform: string;       // shopify | woocommerce | jsonld | html | ...

  // ── Product-level fields ──
  name: string;
  slug: string;                 // Shopify Handle
  descriptionHtml: string;
  brand?: string;
  vendor?: string;              // defaults to brand or "Imported"

  // ── Classification ──
  gender: "Men" | "Women" | "Unisex" | "Kids" | "Unknown";
  category: string;             // e.g. "T-Shirt", "Dress", "Handbag"
  subcategory?: string;         // e.g. "Oversized", "Crossbody"
  productType: string;          // Shopify Type column = "Gender > Category"
  tags: string[];               // flat list for Shopify Tags column

  // ── Attributes ──
  materials: string[];          // cotton, polyester, leather, ...
  colors: string[];             // extracted from variants or title
  sizes: string[];              // S, M, L, XL or 28, 30, 32, ...
  careInstructions?: string;

  // ── Media ──
  imageUrls: string[];

  // ── Variants (one entry per size/color combo) ──
  variants: FashionVariant[];

  // ── SEO ──
  seoTitle?: string;
  seoDescription?: string;

  // ── Confidence (drives AI gate) ──
  fieldConfidence: {
    category: number;           // 0.0 – 1.0
    gender: number;
    material: number;
    sizes: number;
    description: number;
  };
}

interface FashionVariant {
  externalVariantId: string;
  sku?: string;
  option1Name: string;          // "Size" or "Color" (Shopify standard)
  option1Value: string;
  option2Name?: string;         // "Color" when option1 is Size
  option2Value?: string;
  option3Name?: string;
  option3Value?: string;
  price: number;
  compareAtPrice?: number;
  inStock: boolean;
  weightGrams?: number;
  barcode?: string;
}
```

### 5.2 Variant Option Ordering Rule

Shopify expects consistent option names across a product:

- **Option1 = Size**, **Option2 = Color** (preferred for apparel)
- If product has only one dimension, use whichever applies
- Never mix option name order within the same product

---

## 6. Discovery Layer (No AI)

Port logic from `ShopDiscoveryService.cs`. Probe URLs in this order:

| Priority | Probe URL | Platform if 200 + valid JSON |
|----------|-----------|------------------------------|
| 1 | `{base}/products.json?limit=1` | Shopify |
| 2 | `{base}/collections.json?limit=1` | Shopify |
| 3 | `{base}/wp-json/wc/store/v1/products?per_page=1` | WooCommerce |
| 4 | `{base}/api/sitemaps.xml` with `/products/{id}` | Zatiq Easy |
| 5 | `{base}/sitemap.xml` | Generic sitemap crawl |
| 6 | Single product page | JSON-LD / Open Graph / HTML |

### 6.1 Bot Protection Detection

Reuse `IsBotBlockedResponse()` heuristics from JewelryMS:

- Cloudflare challenge pages
- Imunify360 / DDoS protection
- "Checking your browser" interstitials

When blocked: report to user, suggest manual URL list input.

### 6.2 Category Discovery

For shop-wide import, discover categories before fetching:

**Shopify:** `GET /collections.json?limit=250` → each collection's `handle`, `title`, product count.

**WooCommerce:** `GET /wp-json/wc/store/v1/products/categories?per_page=100` → `id`, `slug`, `name`, `count`, `permalink`.

**Sitemap:** Parse XML, filter URLs matching `/products/`, `/product/`, `/p/`.

---

## 7. Parsing Layer (No AI)

### 7.1 Parser Priority (per URL)

```
1. Platform API JSON     (Shopify products.json, WC Store API)
2. JSON-LD Product       (<script type="application/ld+json">)
3. Open Graph meta       (og:title, og:image, product:price:amount)
4. Next.js RSC payload   (regex on RSC strings — Zatiq pattern)
5. HTML meta + tables    (product title h1, price spans, img src)
6. Generic JSON scan     (items/products/data/results arrays)
```

### 7.2 Shopify Parser — Critical Enhancement

JewelryMS `ParseShopify()` only extracts the **first variant**. For fashion CSV you must extract **all variants** with full option matrix:

```
From Shopify JSON:
  products[].options[]     → [{ name: "Size", values: ["S","M","L"] }, { name: "Color", values: ["Black","White"] }]
  products[].variants[]    → one row per combo with option1/option2/option3, price, sku, available
  products[].images[]      → all image URLs
  products[].body_html     → description
  products[].product_type  → raw type
  products[].tags          → comma-separated tags
  products[].handle        → slug
```

### 7.3 JSON-LD Parser

Extract from schema.org `Product` type:

- `name`, `description`, `image`, `sku`
- `offers.price`, `offers.priceCurrency`, `offers.availability`
- `brand.name`
- `color`, `material` (when present)

### 7.4 WooCommerce Parser

From WC Store API v1:

- `id`, `name`, `description`, `permalink`
- `prices.regular_price`, `prices.sale_price`, `prices.currency_minor_unit`
- `images[].src`
- `categories[].name`
- `attributes[]` → map to Size/Color options
- `variations[]` when variable product

---

## 8. Rule-Based Enrichment (No AI)

### 8.1 FashionCategoryNormalizer

Same pattern as `CategoryNormalizer.cs` — ordered keyword rules, first match wins:

```
RULE ORDER (specific → general):

Tops:
  "oversized tee", "oversized t-shirt"  → T-Shirt > Oversized
  "polo shirt", "polo"                    → Polo
  "hoodie", "hooded sweatshirt"         → Hoodie
  "t-shirt", "tee", "tshirt"            → T-Shirt
  "blouse"                               → Blouse
  "crop top"                             → Crop Top
  "sweater", "pullover"                  → Sweater

Bottoms:
  "cargo pants", "cargo trouser"         → Pants > Cargo
  "chino", "chinos"                      → Pants > Chinos
  "jeans", "denim pants"                 → Jeans
  "joggers", "track pants"               → Joggers
  "shorts"                               → Shorts
  "skirt"                                → Skirt
  "leggings"                             → Leggings

Dresses & Outerwear:
  "maxi dress"                           → Dress > Maxi
  "mini dress"                           → Dress > Mini
  "dress"                                → Dress
  "blazer"                               → Blazer
  "jacket"                               → Jacket
  "coat"                                 → Coat
  "cardigan"                             → Cardigan

Accessories:
  "crossbody bag", "sling bag"           → Bags > Crossbody
  "handbag", "tote bag"                  → Bags > Handbag
  "clutch"                               → Bags > Clutch
  "backpack"                             → Bags > Backpack
  "belt"                                 → Belt
  "wallet"                               → Wallet
  "cap", "baseball cap"                  → Cap
  "sunglasses", "shades"                 → Sunglasses
  "watch", "wristwatch"                  → Watch
  "scarf"                                → Scarf
```

Also check URL slug hints (same as JewelryMS `urlHint` parameter).

### 8.2 FashionAudienceDetector

Port from `ProductAudienceDetector.cs` with additions:

```
Men:     men's, mens, men, gents, gentleman, male, boys (if not kids)
Women:   women's, womens, women, lady, ladies, female, girls (if not kids)
Kids:    kids, children, child, junior, toddler, baby
Unisex:  unisex, gender neutral, all gender
```

If both Men and Women keywords match → `Unisex`.

### 8.3 VariantParser

Regex patterns for variant title strings:

```
"Black / M"           → color=Black,  size=M
"Navy Blue - Large"   → color=Navy Blue, size=Large
"Size: 32, Color: Blue" → size=32, color=Blue
"One Size" / "Free Size" / "OS" → size=One Size
"32 Waist"            → size=32
```

Map size words: `Small→S`, `Medium→M`, `Large→L`, `Extra Large→XL`, `2XL→XXL`.

### 8.4 MaterialDetector

Scan title + description for keywords:

```
cotton, polyester, linen, denim, leather, suede, spandex, elastane,
rayon, viscose, wool, cashmere, nylon, silk, faux leather, pu leather,
canvas, mesh, fleece, corduroy, velvet, chiffon, satin
```

### 8.5 SizeNormalizer

```
"Free Size" / "Freesize" / "FS"  → "One Size"
"2XL" / "XXL"                    → "XXL"
"Extra Small" / "XS"             → "XS"
Numeric waist: 28, 30, 32, 34, 36, 38, 40
Standard alpha: XXS, XS, S, M, L, XL, XXL, XXXL
```

### 8.6 BrandExtractor

Priority order:

1. JSON/API `brand` or `vendor` field
2. JSON-LD `brand.name`
3. Open Graph `product:brand`
4. First word(s) of title if matches known brand list (optional curated list)
5. Domain name as fallback vendor

### 8.7 ConfidenceScorer

Assign 0.0–1.0 per field:

| Field | High confidence (≥ 0.8) | Low confidence (< 0.7) |
|-------|-------------------------|------------------------|
| category | API product_type matches rule | No match, title is generic ("New Item") |
| gender | Explicit keyword in title/category | No gender signal |
| material | Found in API attributes or description | No material mention |
| sizes | Structured variant options from API | Parsed from messy title string |
| description | body_html ≥ 100 chars | Empty or &lt; 50 chars |

Fields with confidence < 0.7 are candidates for AI enrichment.

---

## 9. AI Enrichment Gate (Minimal Tokens)

### 9.1 When to Call AI

```
IF fieldConfidence.category < 0.7  → ask AI for category only
IF fieldConfidence.description < 0.7 → ask AI for description only
IF fieldConfidence.gender < 0.7      → ask AI for gender only
IF user clicks "Enhance All"         → full enrichment pass
OTHERWISE                            → skip AI entirely
```

### 9.2 Batched Prompt Strategy

Send up to 20 products per API call. Request JSON array response. Only include fields marked `NEEDS_AI`:

```json
{
  "products": [
    {
      "id": "prod_123",
      "title": "Blue Cotton Shirt",
      "raw_description": "Nice shirt",
      "needs": ["description", "tags"]
    }
  ],
  "instructions": "Return JSON array. Only fill requested fields. Use HTML for description with bullet points for Material, Fit, Care. Tags: lowercase, comma-separated."
}
```

### 9.3 AI Tasks by Priority

| Task | Token cost | When |
|------|------------|------|
| Write product description (HTML) | Medium | Empty or short description |
| Generate SEO title + meta description | Low | Always use template first; AI only if user requests |
| Suggest tags | Low | When tags array is empty |
| Classify category | Low | confidence < 0.7 |
| Image alt text | Low | Template first: "{Color} {Category} for {Gender}" |
| Translate Bangla → English | Medium | When source text is Bengali |

### 9.4 What NEVER Needs AI

- Price, compare-at price, SKU, barcode
- Image URLs
- Variant matrix (size/color combos)
- Handle/slug generation (algorithmic slugify)
- In-stock status
- Platform detection and JSON parsing

---

## 10. Shopify CSV Export Format

### 10.1 Row Structure

Shopify Product CSV uses **one row per variant**. First row carries full product data; subsequent rows for same Handle leave Title/Body/Type blank.

Example for a T-Shirt with 3 sizes × 2 colors = 6 variant rows:

```
Row 1: Handle=t-shirt-blue | Title=... | Body=... | Option1=Size | Option1 Value=M | Option2=Color | Option2 Value=Blue | Variant Price=1200 | Image Src=url1
Row 2: Handle=t-shirt-blue | (blank title) | Option1=Size | Option1 Value=L | Option2=Color | Option2 Value=Blue | Variant Price=1200 | Image Src=url2
...
```

### 10.2 Required Columns for AI-Enabled Catalog

| Column | Source | Notes |
|--------|--------|-------|
| Handle | slugify(name) | Unique, lowercase, hyphens |
| Title | name (cleaned) | Max 255 chars |
| Body (HTML) | descriptionHtml | Rich HTML with bullets |
| Vendor | brand or "Imported" | |
| Type | `{Gender} > {Category}` | e.g. "Men > T-Shirt" |
| Tags | tags.join(", ") | gender, category, material, season |
| Published | TRUE | |
| Option1 Name | "Size" | |
| Option1 Value | variant.option1Value | |
| Option2 Name | "Color" | when applicable |
| Option2 Value | variant.option2Value | |
| Variant SKU | variant.sku | |
| Variant Price | variant.price | |
| Variant Compare At Price | variant.compareAtPrice | |
| Variant Inventory Qty | 0 or parsed qty | |
| Variant Inventory Policy | deny | |
| Image Src | imageUrls[n] | One image per row when possible |
| Image Alt Text | template or AI | Important for AI catalog |
| SEO Title | seoTitle | |
| SEO Description | seoDescription | |
| Status | active | |

### 10.3 ShopifyCsvBuilder Logic

```
for each NormalizedFashionProduct:
  handle = slugify(product.name)
  for i, variant in enumerate(product.variants):
    row = new CsvRow()
    if i == 0:
      row.Title = product.name
      row.Body = product.descriptionHtml
      row.Vendor = product.vendor
      row.Type = product.productType
      row.Tags = join(product.tags)
      row.SEOTitle = product.seoTitle
      row.SEODescription = product.seoDescription
    row.Handle = handle
    row.Option1Name = variant.option1Name
    row.Option1Value = variant.option1Value
    // ... option2, option3
    row.VariantPrice = variant.price
    row.VariantSKU = variant.sku
    row.ImageSrc = product.imageUrls[i % len(product.imageUrls)]
    row.ImageAltText = buildAltText(product, variant)
    append row to csv
```

### 10.4 Validation Before Export

- Every product has at least 1 variant
- Handle is unique across CSV
- Option names consistent within each product
- Prices are positive numbers
- At least 1 image URL per product
- No empty Title on first row of each product

---

## 11. Fashion Category Taxonomy

### 11.1 Men

```
Tops:       T-Shirt, Polo, Shirt, Hoodie, Sweater, Tank Top
Bottoms:    Jeans, Chinos, Shorts, Joggers, Cargo Pants
Outerwear:  Jacket, Coat, Blazer, Vest
Accessories: Belt, Wallet, Cap, Sunglasses, Watch, Bag, Tie, Socks
```

### 11.2 Women

```
Tops:       Blouse, T-Shirt, Crop Top, Sweater, Tank Top, Tunic
Dresses:    Casual Dress, Formal Dress, Maxi Dress, Mini Dress, Midi Dress
Bottoms:    Jeans, Skirt, Leggings, Pants, Shorts
Outerwear:  Jacket, Coat, Cardigan, Blazer, Vest
Accessories: Handbag, Clutch, Crossbody Bag, Scarf, Belt, Sunglasses, Watch, Jewelry
```

### 11.3 Shared / Unisex

```
Bags:       Backpack, Tote, Crossbody
Accessories: Sunglasses, Watch, Scarf, Hat
```

### 11.4 Future Verticals (swap rules file only)

```
Jewelry:    Use existing JewelryMS CategoryNormalizer rules
Shoes:      Sneakers, Loafers, Heels, Sandals, Boots, Flats
Electronics: (future — different attribute schema)
```

---

## 12. Recommended Project Structure

```
fashion-csv-agent/
├── README.md
├── docs/
│   └── fashion-shopify-csv-agent-spec.md    ← this document
│
├── src/
│   ├── FashionCsvAgent.API/                  ← REST API (or CLI)
│   │   ├── Controllers/
│   │   │   └── ScrapeController.cs         ← POST /discover, /scrape, /export
│   │   └── Program.cs
│   │
│   ├── FashionCsvAgent.Core/
│   │   ├── Discovery/
│   │   │   ├── PlatformDetector.cs         ← port ShopDiscoveryService
│   │   │   └── SitemapCrawler.cs
│   │   │
│   │   ├── Parsers/
│   │   │   ├── IProductParser.cs
│   │   │   ├── ShopifyParser.cs            ← port + ALL variants
│   │   │   ├── WooCommerceParser.cs
│   │   │   ├── JsonLdParser.cs
│   │   │   ├── OpenGraphParser.cs
│   │   │   ├── RscParser.cs                  ← Zatiq/Next.js pattern
│   │   │   └── GenericHtmlParser.cs
│   │   │
│   │   ├── Models/
│   │   │   ├── NormalizedFashionProduct.cs
│   │   │   └── FashionVariant.cs
│   │   │
│   │   ├── Normalize/
│   │   │   ├── FashionCategoryNormalizer.cs
│   │   │   ├── FashionAudienceDetector.cs
│   │   │   ├── VariantParser.cs
│   │   │   ├── MaterialDetector.cs
│   │   │   ├── SizeNormalizer.cs
│   │   │   └── BrandExtractor.cs
│   │   │
│   │   ├── Enrich/
│   │   │   ├── ConfidenceScorer.cs
│   │   │   └── AiEnrichmentService.cs      ← batched, field-targeted
│   │   │
│   │   ├── Export/
│   │   │   ├── ShopifyCsvBuilder.cs
│   │   │   └── CsvValidator.cs
│   │   │
│   │   └── Orchestration/
│   │       └── ScrapePipeline.cs             ← wires all layers
│   │
│   └── FashionCsvAgent.UI/                   ← optional React UI
│       ├── pages/
│       │   ├── ImportPage.jsx                ← URL input + preview
│       │   └── ExportPage.jsx                ← CSV download
│       └── components/
│           ├── ProductPreviewTable.jsx
│           └── CategoryMappingPanel.jsx      ← like SuperAdminComparisonPanel
│
├── rules/
│   ├── fashion-categories.json               ← keyword rules (editable)
│   ├── fashion-materials.json
│   └── fashion-sizes.json
│
└── tests/
    ├── Parsers/
    │   ├── ShopifyParserTests.cs
    │   └── JsonLdParserTests.cs
    └── Export/
        └── ShopifyCsvBuilderTests.cs
```

---

## 13. What to Port from JewelryMS

| JewelryMS Component | Reuse % | Adaptation Needed |
|---------------------|---------|-------------------|
| `ShopDiscoveryService.cs` | 90% | Add fashion shop presets; same probe logic |
| `ExternalProductParsers.ParseShopify` | 80% | Extract ALL variants + options array |
| `ExternalProductParsers.ParseWooCommerce` | 85% | Map WC attributes to Size/Color |
| `ExternalProductParsers.ParseZatiqProductHtml` | 95% | JSON-LD parser — use as-is |
| `ExternalProductParsers.ParseGeneric` | 90% | Generic fallback — use as-is |
| `CategoryNormalizer.cs` | Pattern only | New `fashion-categories.json` rules |
| `ProductAudienceDetector.cs` | 80% | Add Unisex, refine Kids vs Men/Women |
| `GuaranteeTextDetector.cs` | Optional | Replace with `CareInstructionDetector` |
| `ProductComparisonService.cs` | Pattern only | New `ScrapePipeline.cs` → CSV export |
| `SuperAdminComparisonPanel.jsx` | Pattern only | New preview/export UI |
| `ProductComparisonDtos.cs` | Pattern only | New `NormalizedFashionProduct` model |

### 13.1 Critical Fix: Multi-Variant Shopify Parsing

Current JewelryMS code (simplified):

```csharp
// ONLY keeps first variant — insufficient for fashion CSV
foreach (var v in p.GetProperty("variants").EnumerateArray()) {
    if (!hasVariant) { variant = v; hasVariant = true; }
}
```

Required enhancement:

```csharp
// Extract options definition
var options = p.GetProperty("options").EnumerateArray()
    .Select(o => new { Name = o.GetProperty("name").GetString(), ... })
    .ToList();

// Emit one FashionVariant per variant row
foreach (var v in p.GetProperty("variants").EnumerateArray()) {
    yield return new FashionVariant {
        Option1Name = options.ElementAtOrDefault(0)?.Name ?? "Size",
        Option1Value = v.GetProperty("option1").GetString(),
        Option2Name = options.ElementAtOrDefault(1)?.Name,
        Option2Value = v.TryGetProperty("option2", out var o2) ? o2.GetString() : null,
        Price = ParseDecimal(v.GetProperty("price").GetString()),
        Sku = v.TryGetProperty("sku", out var sk) ? sk.GetString() : null,
        InStock = v.TryGetProperty("available", out var av) && av.GetBoolean(),
    };
}
```

---

## 14. Build Order (Phased Plan)

### Phase 1 — Core Parsing (Week 1)

- [ ] Create project scaffold (`FashionCsvAgent.Core` class library)
- [ ] Port `PlatformDetector` from `ShopDiscoveryService`
- [ ] Port + enhance `ShopifyParser` (all variants)
- [ ] Port `WooCommerceParser`, `JsonLdParser`
- [ ] Define `NormalizedFashionProduct` + `FashionVariant` models
- [ ] Unit tests with real Shopify JSON fixtures

### Phase 2 — Rule Engines (Week 2)

- [ ] `FashionCategoryNormalizer` with `fashion-categories.json`
- [ ] `FashionAudienceDetector` (port + Unisex)
- [ ] `VariantParser` + `SizeNormalizer`
- [ ] `MaterialDetector` + `BrandExtractor`
- [ ] `ConfidenceScorer`
- [ ] Unit tests for rule matching edge cases

### Phase 3 — CSV Export (Week 3)

- [ ] `ShopifyCsvBuilder` with proper multi-row variant structure
- [ ] `CsvValidator` (pre-export checks)
- [ ] CLI or minimal API: URL in → CSV file out
- [ ] Test import into Shopify development store

### Phase 4 — AI Layer (Week 4)

- [ ] `AiEnrichmentService` with batched prompts
- [ ] Field-targeted enrichment (only low-confidence fields)
- [ ] Description HTML template + AI fallback
- [ ] SEO title/description templates
- [ ] Token usage logging and per-run budget cap

### Phase 5 — UI + Polish (Week 5+)

- [ ] React UI: URL input, category mapping, product preview table
- [ ] Edit-before-export flow
- [ ] Bulk domain import (CSV of URLs)
- [ ] Export history / job queue

### Phase 6 — Future Verticals

- [ ] `rules/jewelry-categories.json` (port from JewelryMS)
- [ ] `rules/shoes-categories.json`
- [ ] Vertical selector in UI

---

## 15. Token Budget Estimates

Based on 100 products from mixed e-commerce sites:

| Approach | Estimated tokens | Cost profile |
|----------|------------------|--------------|
| Naive: full AI rewrite per product (5 fields × 100 products) | 500,000 – 1,000,000 | Expensive |
| **Recommended: algo + AI gaps only (batched)** | **30,000 – 80,000** | **~90% savings** |
| Algorithm only (no AI enrichment) | 0 | Free |

Typical field resolution for 100 fashion products:

| Resolution | % of products | Method |
|------------|---------------|--------|
| Fully algorithmic | ~85% | Shopify/WC API sites with structured data |
| AI description only | ~10% | HTML scrape sites with poor descriptions |
| AI category + description | ~5% | Ugly/custom HTML with minimal structure |

---

## 16. Key Code References in JewelryMS

| What | File path |
|------|-----------|
| Platform discovery | `src/JewelryMS.Application/Services/ProductComparison/ShopDiscoveryService.cs` |
| All JSON/HTML parsers | `src/JewelryMS.Application/Services/ProductComparison/ExternalProductParsers.cs` |
| Shopify headless catalog | `src/JewelryMS.Application/Services/ProductComparison/ShopifyCatalog.cs` |
| Category keyword rules | `src/JewelryMS.Application/Services/ProductComparison/CategoryNormalizer.cs` |
| Audience detection | `src/JewelryMS.Application/Services/ProductComparison/ProductAudienceDetector.cs` |
| Guarantee detection | `src/JewelryMS.Application/Services/ProductComparison/GuaranteeTextDetector.cs` |
| Sync orchestration | `src/JewelryMS.Application/Services/ProductComparisonService.cs` |
| Normalized product DTO | `src/JewelryMS.Domain/DTOs/ProductComparison/ProductComparisonDtos.cs` |
| Super admin API | `src/JewelryMS.API/Controllers/SuperAdminProductComparisonController.cs` |
| Super admin UI | `jewelry-ms-frontend/src/pages/superadmin/SuperAdminComparisonPanel.jsx` |
| Architecture docs | `docs/price-compare-add-shop.md` |
| Daraz integration docs | `docs/price-compare-daraz.md` |
| Zatiq integration docs | `docs/price-compare-zatiq.md` |

---

## 17. Appendix: Shopify CSV Column Reference

Full column list for Shopify Product CSV import (v1 focus columns marked ★):

| Column | Required | Notes |
|--------|----------|-------|
| ★ Handle | Yes | Unique product identifier |
| ★ Title | Yes | Product name |
| ★ Body (HTML) | Recommended | Rich description for AI catalog |
| ★ Vendor | Recommended | Brand name |
| ★ Type | Recommended | Product category |
| ★ Tags | Recommended | Comma-separated |
| ★ Published | Yes | TRUE/FALSE |
| ★ Option1 Name | If variants | "Size" |
| ★ Option1 Value | If variants | "M" |
| ★ Option2 Name | If variants | "Color" |
| ★ Option2 Value | If variants | "Blue" |
| Option3 Name | Optional | e.g. "Material" |
| Option3 Value | Optional | |
| ★ Variant SKU | Recommended | |
| ★ Variant Grams | Optional | Weight |
| ★ Variant Inventory Tracker | Optional | shopify |
| ★ Variant Inventory Qty | Recommended | |
| ★ Variant Inventory Policy | Yes | deny/continue |
| ★ Variant Fulfillment Service | Yes | manual |
| ★ Variant Price | Yes | |
| ★ Variant Compare At Price | Optional | Sale pricing |
| Variant Requires Shipping | Yes | TRUE |
| Variant Taxable | Yes | TRUE |
| ★ Image Src | Recommended | Full URL |
| ★ Image Alt Text | Recommended | Important for AI |
| Gift Card | Yes | FALSE |
| ★ SEO Title | Recommended | |
| ★ SEO Description | Recommended | |
| Google Shopping fields | Optional | For Google channel |
| Status | Yes | active/archived/draft |

---

*End of specification. Use this document as the single source of truth when starting the Fashion Shopify CSV Agent project.*
