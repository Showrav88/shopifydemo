# Product URL scrape — how it works

## What you do

1. Add column **Product URL** to your sheet (first column recommended).
2. Paste a **public product page URL** (competitor / supplier site).
3. Workflow triggers automatically (~1 minute) or use **Execute step** on the trigger.
4. Everything else is filled by scrape + AI → Shopify draft.

**One URL = one run = one product.** For batch: paste URL on row 2 after row 1 is PASS.

## Flow

```
Product URL (trigger)
  → Validate sheet row (skip PASS rows)
  → Needs scrape? 
      YES → Fetch page → AI scrape → save to sheet
  → Active product row (THIS run only — no cache)
  → Photoroom → Analyze image → AI listing → QA → Shopify
```

## Sheet columns

| You type | Workflow writes |
|----------|-----------------|
| **Product URL** | triggers scrape |
| **Inventory quantity** | YOU set stock — **not** from scrape |
| **Prompt Title**, **Prompt Description**, etc. | optional — control how AI writes each field (see `docs/AI-FIELD-PROMPTS.md`) |
| SKU (optional) | auto `CATEGORY-XXXXXX` if empty (written after scrape) |
| Price (optional) | **your** sell price — not scraped |
| Manual: image + description + price + SKU | still works without URL |

| Written by workflow |
|---------------------|
| Title, Description, Vendor, Product category, Product image URL, Price, Tags |
| Scrape Status = `SCRAPED`, Source Product URL |
| SEO fields, QA Status, AI Score, Shopify URLs |

## No cache between runs

- Each run gets unique `_run_id`.
- **Active product row** holds only the current product.
- AI prompts say: use **THIS run only** — fixes duplicate description bug.

## When workflow stops (safe)

- All rows PASS → `nothing_to_process`
- Scrape blocked (403) → fix URL or try manual image + description
- QA score &lt; 90 → FAIL on sheet, no Shopify product

## Re-scrape

Change **Product URL** on a row → `Scrape Status` resets logic → scrapes again on next trigger.

## Troubleshooting: Update sheet scraped errors or messy columns

### Error: `The 'Column to Match On' parameter is required`

**Cause:** **Product URL** is selected as match column but has **no expression/value**, OR your Google Sheet row 1 does not have a column literally named `Product URL`.

**Fix:**
1. Row 1 of your sheet = copy **only** from `sheet-input-template.csv` (36 columns). Do not add workflow fields (`validated_sku`, `_run_id`, `scrape_context`, etc.).
2. Re-import latest `ShopifyProductAdd.V2.json` — flow is now: `Apply scraped data` → **Prepare sheet scrape write** → `Update sheet scraped`.
3. **Prepare sheet scrape write** outputs clean sheet columns only; **Update sheet scraped** uses auto-map from that node.

### Messy columns in the Google Sheets node (processing_sku, validated_sku, …)

**Cause:** n8n "auto match" pulled **internal workflow fields** from `Apply scraped data` into the sheet mapping. Those are for the workflow, not your spreadsheet.

**Fix:** Delete those extra columns from your Google Sheet row 1 if you added them. Use only `sheet-input-template.csv` headers. In n8n, remove all manual mappings and use the new **Prepare sheet scrape write** node instead.

### Sheet empty after "success" (`[ {} ]`)

Match column was **SKU** while sheet SKU was blank. Fixed by matching on **Product URL** (the value you paste first).
