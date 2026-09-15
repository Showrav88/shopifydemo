# Every sheet key — what it does

## YOU type (input)

| Sheet column | Required? | Used for | Goes to Shopify? |
|--------------|-----------|----------|------------------|
| **Product URL** | Start here | Triggers scrape | No (reference only) |
| **Price** | Reference only | Your planned sell price — **set manually in Shopify admin after QA PASS** | No (workflow leaves £0.00) |
| **Inventory quantity** | Optional | Stock — applied to variants if &gt; 0 | Yes — if filled |
| **Shopify Category** | Optional | Shopify taxonomy GID (or auto-mapped from Product category) | Yes — on create |
| **Collection** | Optional | Collection handle e.g. `mens-shirts` | Yes — if collection exists in store |
| **SKU** | Optional | Auto if empty: `CATEGORY-XXXXXX` (4-letter category code + 6 random letters/numbers) | Yes — variant SKU |
| **Prompt Title** … **Prompt Category** | Optional | How AI writes each field | Via AI output |
| Product image URL | Manual mode | Image for Photoroom | Image upload |
| Description / Title | Manual mode | AI facts | Via AI listing |
| Vendor | Optional | Brand | Yes — `vendor` |
| Product category | Optional | Type/category | Yes — `product_type` |

## Scrape writes (competitor reference — NOT your shop price)

| Sheet column | Source | Shopify? |
|--------------|--------|----------|
| **Competitor price** | Scraped from URL page | **No** — reference only |
| **Competitor currency** | e.g. GBP, USD, BDT | **No** |
| **Sizes** | e.g. `S, M, L, XL` | No (v1: single variant; sizes stored for you) |
| **Colors** | e.g. `Blue, Black` | No (reference) |
| **Scraped variants** | JSON of size/color/sku from page | No (reference for future multi-variant) |
| Title, Description, Product image URL, Vendor, Product category, Tags | Scrape + AI | Yes — via listing |
| Scrape Status | `SCRAPED` | No |
| Source Product URL | URL that was scraped | No |

## AI listing writes

| Sheet column | Shopify field |
|--------------|---------------|
| Title | `product.title` |
| Description | `product.body_html` |
| Tags | `product.tags` |
| SEO title | metafield / theme |
| SEO description | metafield / theme |
| Image alt text | image alt |

## QA writes

| Sheet column | Meaning |
|--------------|---------|
| QA Status | PASS / PASS_NO_IMAGE / FAIL |
| AI Score | 0–100 |

## Shopify writes

| Sheet column | Meaning |
|--------------|---------|
| URL handle | product handle |
| Shopify Product URL | your store product link |
| Shopify Image URL | CDN image |
| Generated Image URL | ImgBB staging URL |
| Status | `draft` |

---

## Shopify API keys (Create a product API)

| JSON key | Sheet / source |
|----------|----------------|
| `product.title` | AI write listing → `title` |
| `product.body_html` | AI → `description_html` |
| `product.vendor` | Vendor |
| `product.product_type` | Product category |
| `product.tags` | AI → `tags` |
| `product.status` | always `draft` |
| `options` | From **Build Shopify product** (Size, Color, UK Size, etc.) |
| `variants[]` | One per size/color from **Scraped variants** / Sizes / Colors |
| `variants[].sku` | Base SKU + size/color suffix |
| `variants[].price` | Always `0.00` at create — **client sets in Shopify admin** |
| `variants[].inventory_quantity` | Split from sheet **Inventory quantity** (if &gt; 0) |
| `category` | **Shopify Category** GID or auto-mapped |

## Set Shopify variant stock (after draft)

| JSON key | Sheet column |
|----------|--------------|
| `variant.inventory_quantity` | **Inventory quantity** (split across variants) |

Price is **not** updated by workflow — set manually in Shopify after reviewing the draft.

---

## Multi-variant (Phase 2)

| Sheet column | Meaning |
|--------------|---------|
| **Sizes** | e.g. `S, M, L, XL` (scrape writes) |
| **Colors** | e.g. `Black, Navy` (scrape writes) |
| **Scraped variants** | JSON array from scrape — preferred source |
| **Variant profile** | Optional override: `clothing_alpha`, `footwear_uk`, `clothing_numeric`, `one_size`, `color_only` |
| **Price** | Reference for you — **not pushed to Shopify** (set price in admin after PASS) |
| **Inventory quantity** | Total stock — split evenly across variants (only if &gt; 0) |

**Auto profile** from Product category: shirts → `clothing_alpha`, shoes → `footwear_uk`, bags → `one_size`.

**Shopify gets:** `options` (Size, Color, etc.) + one variant per size/color combo with unique SKU (`BASE-S-BLACK`).

**Fallback:** no sizes/colors scraped → single variant (same as v1).

---

## Typical workflow

```
1. Paste Product URL          → scrape fills competitor price + sizes + description
2. Run completes              → draft on Shopify at £0.00 (+ stock if Inventory quantity filled)
3. Review QA PASS             → check listing quality score ≥ 90
4. You set sell price         → manually in Shopify admin (sheet Price is reference only)
```

If **Inventory quantity** is empty → variants stay at 0 stock until you set stock in sheet or Shopify admin.
