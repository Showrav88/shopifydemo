# Lookup sheets — setup guide

Use these CSV files as **separate tabs** in your Google Sheet. They auto-fill **Product category**, **Collection**, and **Variant profile** when those columns are empty on the main input row.

## Files to import (4 tabs)

| CSV file | Tab name in Google Sheet | Purpose |
|----------|--------------------------|---------|
| `lookup/lookup-shopify-collections.csv` | **Shopify Collections** | Master list — create these once in Shopify Admin |
| `lookup/lookup-collection-map.csv` | **Collection Map** | Keyword → collection handle |
| `lookup/lookup-product-type-map.csv` | **Product Type Map** | Keyword → product type + variant profile + collection |
| `lookup/lookup-vendor-domain-map.csv` | **Vendor Map** | Domain → default vendor (optional) |

## How to add tabs in Google Sheets

1. Open your spreadsheet: [your sheet](https://docs.google.com/spreadsheets/d/1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo/edit?gid=975501836)
2. **File → Import** (or new sheet → paste)
3. Upload each CSV → **Insert new sheet**
4. Rename tabs exactly:
   - `Shopify Collections`
   - `Collection Map`
   - `Product Type Map`
   - `Vendor Map`
5. Keep **row 1 as headers** — do not delete

Your main product input tab stays as **Sheet1** (or whatever you use today) with columns from `sheet-input-template.csv`.

---

## What each lookup does

### 1. Shopify Collections (reference only — you create in Admin)

This is **not** used by automation yet. It is the checklist of collections to create in Shopify.

**Your store (already created — good to go):**

| Handle | Use for |
|--------|---------|
| `kids` | All kids / boys / girls |
| `mens-shirts` | Men's shirts |
| `mens-pants` | Men's jeans, pants, shorts |
| `mens-outerwear` | Men's jackets, hoodies, fleece |
| `mens-shoes` | Men's footwear |
| `mens-accessories` | Men's bags, belts, hats, watches |
| `womens-dresses` | Dresses, jumpsuits |
| `womens-tops` | Tops, shirts, sweaters, women's jackets (until you add womens-outerwear) |
| `womens-bottoms` | Jeans, pants, skirts, leggings |
| `womens-intimates` | Underwear, bodysuits, bras |
| `womens-shoes` | Women's footwear |
| `womens-accessories` | Women's bags, belts, jewelry |

**Manual collection = correct.** You only need:
1. **Title** (e.g. `mens-shirts`)
2. **Type: Manual** (default when you don't add conditions)
3. **Save**

No conditions, no product rules, no automated tags needed. The workflow adds each product to the collection using the **handle** from the sheet **Collection** column (or lookup).

```
Shopify Admin → Products → Collections → Create collection
Title: mens-shirts
Handle: mens-shirts   ← auto from title if you use lowercase + hyphens
Type: Manual          ← leave empty conditions = manual ✓
```

### 2. Product Type Map (fills Product category)

When main row **Product category** is **empty**, workflow (Phase 5) will match keywords from:

| Source | match_where value |
|--------|-------------------|
| Product URL path | `url` — e.g. `/shirts/`, `/dresses/` |
| Scraped title | `title` — e.g. `linen shirt`, `midi dress` |
| Any text | `any` — title + URL + scraped category |

**Lowest priority number wins** (5 beats 10).

**Output columns used:**

| Column | Goes to main sheet / Shopify |
|--------|------------------------------|
| `product_type` | **Product category** → Shopify `product_type` |
| `variant_profile` | **Variant profile** → Size/Color options |
| `collection_handle` | **Collection** (if Collection empty) |
| `shopify_taxonomy_keyword` | Helps pick taxonomy GID (shirt, jean, dress) |

**Gender:** `men`, `women`, `unisex`, or leave blank. Detected from URL (`/men/`, `/women/`, `/mujer/`) or sheet if you add a Gender column later.

### 3. Collection Map (fills Collection only)

Use when **Product category** is already set but **Collection** is empty.

Matches keywords in the product type path or title → `collection_handle`.

Example: title contains `bodysuit` → `womens-intimates`

### 4. Vendor Map (fills Vendor)

When **Vendor** is empty, match domain from Product URL:

`shop.mango.com` → `Mango`

---

## Can lookup replace manual Product category?

**Yes — when the column is empty.**

| Main sheet column | Client types | Lookup fills when empty |
|-------------------|--------------|-------------------------|
| Product category | Optional | ✅ Product Type Map |
| Collection | Optional | ✅ Product Type Map or Collection Map |
| Variant profile | Optional | ✅ Product Type Map |
| Vendor | Optional | ✅ Vendor Map |

**If client already typed a value, lookup does NOT overwrite** (sheet wins).

---

## Example: client only pastes URL

| Product URL | Product category | Collection | Vendor |
|-------------|------------------|------------|--------|
| `https://shop.mango.com/.../linen-shirt/37031400` | *(empty)* | *(empty)* | *(empty)* |

**After lookup (Phase 5):**

| Field | Value | Why |
|-------|-------|-----|
| Product category | `Men > Shirts > Linen` | URL `/linen/` + `/shirts/` + title |
| Collection | `mens-shirts` | From product type map |
| Variant profile | `clothing_alpha` | Size + Color |
| Vendor | `Mango` | Domain map |

Client did **not** pick collection manually in Shopify.

---

## Example: client overrides

| Product URL | Product category | Collection |
|-------------|------------------|------------|
| mango URL | `Men > Shirts > Oxford` | `mens-shirts` |

Lookup **skipped** — sheet values used as-is.

---

## Lookup priority rules (for Phase 5 code)

```
1. Sheet column filled?     → use sheet (never overwrite)
2. match_where = title      → check scraped title first
3. match_where = url        → check Product URL path
4. match_where = any        → check title + URL + scrape category
5. Lowest priority number   → wins when multiple keywords match
6. gender must match        → men rule won't apply to women's URL
```

---

## Editing the maps

Add rows at the bottom of each tab. Do not change header names.

**Collection Map row example:**

```csv
kimono,any,10,women,womens-tops,Women's Tops,New category you sell
```

**Product Type Map row example:**

```csv
kimono,any,10,women,Women > Tops > Kimono,clothing_alpha,womens-tops,shirt,
```

---

## Phase 5 implementation plan (next)

| Step | What we build |
|------|----------------|
| **5a** | Add missing sites to Browserless list |
| **5b** | Add Shopify sites to `.json` routing |
| **5c** | **Lookup resolver** — read 4 tabs, fill empty columns on Validate row |
| **5d** | Levi's / Zara custom parsers |
| **5e** | Fashion Nova / Everlane color fixes |

Lookup sheets are ready now; workflow wiring comes in **5c**.

---

## Quick client cheat sheet (print this)

| I sell… | Product category (or leave blank) | Collection handle |
|---------|-----------------------------------|-------------------|
| Women's dress | `Women > Dresses > Midi` | `womens-dresses` |
| Men's linen shirt | `Men > Shirts > Linen` | `mens-shirts` |
| Women's jeans | `Women > Jeans > Straight` | `womens-bottoms` |
| Skims bodysuit | *(blank — lookup fills)* | `womens-intimates` |
| Men's boots | `Men > Shoes > Boots` | `mens-shoes` |
| Bag | `Accessories > Bags > Tote` | `accessories` |

**Minimum mode:** paste **Product URL only** — after Phase 5c lookup fills the rest.
