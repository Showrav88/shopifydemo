# Lookup Tables tab

Import **`sheet-lookup-tables.csv`** as tab **`Lookup Tables`** in the same spreadsheet as **`sheet-products.csv`**.

Full setup: **`docs/SHEET-MASTER-GUIDE.md`**

## Rules

- **Do not delete rows** on this tab — only add/edit keywords at the bottom
- Filter column `lookup_table`:
  - `vendor_map` — domain → vendor
  - `product_type_map` — keyword → product type
  - `collection_map` — keyword → collection handle
  - `shopify_collection` — your Shopify collection checklist

Products tab formulas read this tab automatically.
