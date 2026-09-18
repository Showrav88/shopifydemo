# Lookup tables — one CSV, same Google Sheet

## One file to import (not 4 separate files)

Import **one** file into your **same** product spreadsheet:

| File | Tab name in Google Sheet |
|------|--------------------------|
| **`sheet-lookup-tables.csv`** | **Lookup Tables** |

Put it in the **same Google Sheet** as your product rows (the sheet that has `Product URL`, `Title`, etc.). Different **tab**, same **spreadsheet** — not a separate Google Sheet file.

```
Your Google Spreadsheet (one file)
├── Sheet1 (or "Products")     ← Product URL rows — workflow trigger
└── Lookup Tables              ← import sheet-lookup-tables.csv here
```

### How to import

1. Open your spreadsheet
2. **File → Import → Upload** `sheet-lookup-tables.csv`
3. Choose **Insert new sheet**
4. Rename tab to **Lookup Tables**
5. Row 1 must stay as headers

---

## Is n8n connected to this tab yet?

**Not yet.** Phase **5c** will add a Google Sheets node that reads **Lookup Tables** and fills empty columns on each row:

- Product category
- Collection
- Variant profile
- Vendor

Until Phase 5c: use the **Collection** column manually, or copy values from the lookup tab yourself.

---

## Column: `lookup_table`

All rows are in one CSV. The first column says which rule type:

| lookup_table value | What it does |
|--------------------|--------------|
| `shopify_collection` | Your Shopify collections checklist (you already created these) |
| `collection_map` | Keyword → collection handle |
| `product_type_map` | Keyword → product type + variant profile + collection |
| `vendor_map` | Domain → vendor name |

Filter the tab by `lookup_table` to see one section at a time (Google Sheets: Data → Create a filter).

---

## Your collections (shopify_collection rows)

| collection_handle | Use for |
|-------------------|---------|
| `kids` | Kids / boys / girls |
| `mens-shirts` | Men's shirts |
| `mens-pants` | Men's jeans, pants, shorts |
| `mens-outerwear` | Men's jackets, hoodies |
| `mens-shoes` | Men's footwear |
| `mens-accessories` | Men's bags, belts, watches |
| `womens-dresses` | Dresses |
| `womens-tops` | Tops, blouses, tees, sweaters |
| `womens-outerwear` | Jackets, coats, blazers, hoodies |
| `womens-bottoms` | Jeans, pants, skirts, leggings |
| `womens-intimates` | Underwear, bodysuits, bras |
| `womens-shoes` | Women's footwear |
| `womens-accessories` | Women's bags, jewelry |

**Manual collection in Shopify = correct.** Title + save, no conditions.

---

## Rules (Phase 5c automation)

1. Sheet column already filled → **never overwrite**
2. Empty → match keyword in URL / scraped title
3. Lowest `priority` number wins
4. `gender` must match (`men`, `women`, `kids`)

---

## Example: URL only

| Product URL | Product category | Collection |
|-------------|------------------|------------|
| mango linen shirt URL | *(empty)* | *(empty)* |

After Phase 5c lookup:

| Field | Value |
|-------|-------|
| Product category | `Men > Shirts > Linen` |
| Collection | `mens-shirts` |
| Vendor | `Mango` |

---

## Why same spreadsheet?

n8n already connects to **one** spreadsheet ID. One extra tab = no second credential, no second connection. Phase 5c reads **Lookup Tables** from the same document as the trigger row.

---

## `lookup/` folder (optional)

The `lookup/` folder holds split copies for developers. **You only need `sheet-lookup-tables.csv`** at the repo root.
