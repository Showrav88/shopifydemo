# Full Google Sheet setup — Products + Lookup (2 CSV files, 1 spreadsheet)

Import **both** CSV files into the **same** Google Spreadsheet. Together they power **URL-only** rows: paste a link → lookup fills names → workflow scrapes the rest.

## Step 1 — Create / open your spreadsheet

Use your existing sheet or create a new one.

## Step 2 — Import tab 1: **Products** (your input rows)

| | |
|---|---|
| **File** | `sheet-input-template.csv` |
| **Tab name** | `Products` (or keep `Sheet1` — workflow uses spreadsheet ID) |
| **Row 1** | Headers — do not delete |
| **Row 2–3** | Example rows — delete before live use, or replace URLs |

### What YOU type vs what fills automatically

| Column | You type? | Who fills when empty |
|--------|-----------|----------------------|
| **Product URL** | ✅ **Yes** — only required column | — |
| **Force browser** | Optional `YES` | — |
| **Vendor** | Optional | **Lookup** (from domain) → then scrape may override |
| **Product category** | Optional | **Lookup** (product type path) |
| **Variant profile** | Optional | **Lookup** (`clothing_alpha`, etc.) |
| **Collection** | Optional | **Lookup** (collection handle) |
| **Shopify Category** | Optional GID | **Lookup** keyword → taxonomy |
| **Title, Description, image** | Optional manual mode | **Scrape** + AI |
| **Sizes, Colors, variants** | No | **Scrape** |
| **Scrape Status, QA, Shopify URL** | No | **Workflow** |

### URL-only flow (after Phase 5c)

```
1. Paste Product URL in row 4 (example rows deleted)
2. Leave Vendor, Product category, Collection, Variant profile EMPTY
3. Workflow reads Lookup Tables tab → fills those columns
4. Scrape runs → fills Title, Sizes, Colors, image, etc.
5. AI + Shopify draft created
```

If you **already typed** Product category or Collection, lookup **does not overwrite**.

### Example rows in template

| Row | Product URL | Category | Collection | Meaning |
|-----|-------------|----------|------------|---------|
| 2 | Mango linen shirt | *(empty)* | *(empty)* | URL-only — lookup will fill `Men > Shirts > Linen`, `mens-shirts`, `Mango` |
| 3 | Everlane jeans | `Women > Jeans > Straight` | `womens-bottoms` | Manual override — lookup skipped for those columns |

## Step 3 — Import tab 2: **Lookup Tables**

| | |
|---|---|
| **File** | `sheet-lookup-tables.csv` |
| **Tab name** | `Lookup Tables` |
| **Same spreadsheet** | Yes — same file as Products tab |

Filter column A (`lookup_table`) to edit rules:

| lookup_table | Purpose |
|--------------|---------|
| `shopify_collection` | Collections you created in Shopify |
| `collection_map` | Keyword → collection handle |
| `product_type_map` | Keyword → product type + variant profile |
| `vendor_map` | Domain → vendor name |

## Step 4 — Shopify collections (one-time)

Create manual collections in Shopify Admin matching handles in Lookup tab (`mens-shirts`, `womens-dresses`, `kids`, etc.). See `LOOKUP-SHEETS-GUIDE.md`.

## Step 5 — n8n workflow

1. Re-import `ShopifyProductAdd.V2.json` from latest `main`
2. Spreadsheet ID already in workflow JSON
3. **Lookup connection** — Phase **5c** (reads `Lookup Tables` tab automatically)
4. Until 5c: copy lookup values manually into Products row, or pre-fill Collection / Product category

## File checklist

| File | Tab name | Required |
|------|----------|----------|
| `sheet-input-template.csv` | Products | ✅ Yes |
| `sheet-lookup-tables.csv` | Lookup Tables | ✅ Yes for auto-fill |

Both files live in the repo root next to each other.

## Column order on Products tab

Input / lookup columns are **first** (left side) so you only scroll to Product URL:

`Product URL` → `Force browser` → `Vendor` → `Product category` → `Variant profile` → `Collection` → … → scrape/AI output columns on the right.
