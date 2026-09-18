# One Google Sheet file — `sheet-master.csv`

This is **the only file** you import. One tab. Paste a **Product URL** — the sheet suggests Vendor, Category, Collection automatically.

## Import (one time)

1. Google Sheets → **File → Import**
2. Upload **`sheet-master.csv`**
3. **Insert new sheet** or replace existing
4. Rename tab to **Products** (optional)
5. **Hide columns AU–BH** (lookup rules — right side of sheet)  
   Select columns AU–BH → Right-click → **Hide columns**

You do **not** need `sheet-input-template.csv` or `sheet-lookup-tables.csv` anymore — everything is inside `sheet-master.csv`.

---

## What you do

| Step | Action |
|------|--------|
| 1 | Paste **Product URL** in column **A** (any row from 2 down) |
| 2 | Watch **Suggested** columns fill (C–F) from URL immediately |
| 3 | Workflow runs → fills **Title**, **Description** (columns L, M) |
| 4 | **Suggested** columns update again using title + description |
| 5 | Workflow sends product to **Shopify** |

**You only type column A** (Product URL). Optional: **Force browser** column B = `YES`.

---

## Column map (left side — your view)

| Col | Name | You type? | Who fills |
|-----|------|-----------|-----------|
| **A** | Product URL | ✅ Yes | You |
| **B** | Force browser | Optional | You |
| **C** | Suggested Vendor | No | **Sheet formula** (from URL domain) |
| **D** | Suggested Category | No | **Sheet formula** (URL + title + description) |
| **E** | Suggested Collection | No | **Sheet formula** |
| **F** | Suggested Variant profile | No | **Sheet formula** |
| **G** | Vendor | Optional override | You, or n8n copies from **C** |
| **H** | Product category | Optional override | You, or n8n copies from **D** |
| **I** | Variant profile | Optional override | You, or n8n copies from **F** |
| **J** | Collection | Optional override | You, or n8n copies from **E** |
| **L** | Title | No | **Scrape** → sheet updates → suggestions improve |
| **M** | Description | No | **Scrape** |
| … | Sizes, Colors, QA, Shopify URL | No | **Workflow** |

---

## How lookup works in ONE sheet

```
Column A (URL)  ──┐
Column L (Title) ─┼──► Formulas in C–F search hidden lookup rules (cols AU–BH)
Column M (Desc)  ──┘
                           │
                           ▼
              Suggested Vendor / Category / Collection
                           │
              n8n scrape writes Title ──► formulas recalculate
                           │
              n8n copies Suggested → final columns (Phase 5c)
                           │
                           ▼
                     Shopify draft
```

Lookup rules live in **columns AU–BH** (same rows as the sheet). Hidden from view. Edit there to add keywords (same data as old lookup table).

---

## Flow timeline

| When | What happens |
|------|----------------|
| **Paste URL** | Suggested Vendor = `Mango` (from domain). Collection may hint from `/shirts/` in URL |
| **After scrape** | Title = `Regular-fit 100% linen shirt` → Suggested Category updates to `Men > Shirts > Linen` |
| **Phase 5c (n8n)** | If Vendor/Category/Collection empty → copy from Suggested columns |
| **Shopify** | Uses Product category, Collection, Vendor for product_type and collection |

---

## Override

Type directly in **G, H, I, J** (Vendor, Product category, Variant profile, Collection). Your value wins over Suggested.

---

## Edit lookup rules

1. Unhide columns **AU–BH**
2. Filter **lk_table** column:
   - `vendor_map` — domain → vendor
   - `product_type_map` — keyword → product type
   - `collection_map` — keyword → collection handle
3. Add a new row with keyword + handles
4. Hide columns again

---

## n8n connection

| Status | What |
|--------|------|
| **Today** | Formulas work in Google Sheets after import. Re-import `ShopifyProductAdd.V2.json` |
| **Phase 5c** | n8n copies Suggested → final columns after scrape, before Shopify |

Same spreadsheet ID — one tab, no second file.

---

## Delete example rows

Rows 2–3 have sample URLs. Delete or replace before live use.
