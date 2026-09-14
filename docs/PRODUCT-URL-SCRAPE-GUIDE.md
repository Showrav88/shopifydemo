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
| SKU (optional) | auto `SCRAPE-…` if empty |
| Price (optional) | from scrape if found |
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
