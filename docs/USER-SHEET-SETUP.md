# Your sheet — pre-configured in workflow JSON

**Sheet URL:** https://docs.google.com/spreadsheets/d/1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo/edit?gid=975501836

| Setting | Value |
|---------|-------|
| Spreadsheet ID | `1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo` |
| Tab gid | `975501836` |
| Match column | **Product URL** (all update nodes) |

## Re-import workflow — credential names (one-time)

Name your n8n credentials **exactly** like this so re-import auto-connects:

| Credential type | Name in n8n |
|-----------------|-------------|
| Google Sheets | `Google Sheets account` |
| Shopify OAuth | `Shopify account` |
| Photoroom | `Photoroom Header Auth` |

You do **not** need to re-pick the spreadsheet on each import — ID is baked into JSON.

## Google Sheet setup — 2 tabs, 1 spreadsheet

| File | Tab name |
|------|----------|
| `sheet-products.csv` | **Products** — paste URLs, delete rows freely |
| `sheet-lookup-tables.csv` | **LookupTables** — import FIRST, never delete rows |
| `sheet-setup-readme.csv` | **README** — setup instructions (optional) |

See **`docs/SHEET-MASTER-GUIDE.md`**. Suggested columns (C–F) connect to Lookup tab via formulas.

## Row 1 headers

Copy from `sheet-master.csv` row 1 headers. Must include **Product URL**. SKU auto-generates if empty.

## How matching works

All sheet update nodes match on **Product URL** from the Google Sheets trigger row.

## Do you need to change your sheet columns?

**Add 2 new columns** from `sheet-input-template.csv` (insert after Product URL):

| Column | You type? | What it means |
|--------|-----------|---------------|
| **Force browser** | Optional | Set `YES` to force Browserless on any URL (override bot protection) |
| **Scrape method** | No — workflow writes | `http`, `browser`, `shopify_json`, or `blocked` |

### Bot protection — how it is recorded (no separate column needed)

| Column | Value when bot-blocked | Meaning |
|--------|---------------------|---------|
| **Scrape Status** | `NEEDS_BROWSER` | Site blocked HTTP scraper (Macy's, etc.) |
| **Scrape Status** | `SCRAPED_BROWSER` | Browserless succeeded |
| **Scrape Status** | `SCRAPED_PARTIAL` | Image OK but variants need browser |
| **Scrape method** | `browser` | Used Browserless |
| **Scrape method** | `http` | Plain HTTP (free, fast) |
| **QA Issues** | Message | Explains what to do next |

### How to override bot protection

1. **Automatic** — Macy's, Mango, Express route to Browserless when credential is set
2. **Force browser = YES** — on any row, forces Browserless even for unknown sites
3. **Re-trigger** — clear `Scrape Status`, paste URL again; rows with `NEEDS_BROWSER` auto-retry with browser
4. **Manual** — paste **Product image URL** directly and skip scrape image step

### Browserless credential (one-time in n8n)

| Credential type | Name in n8n | Value |
|-----------------|-------------|-------|
| HTTP Query Auth | `Browserless API` | Query param `token` = your [browserless.io](https://www.browserless.io) API key |

| Column | Required? | Notes |
|--------|-----------|-------|
| **Product URL** | Yes | Only column you must fill to start |
| **Sizes**, **Colors**, **Scraped variants** | Auto-filled by scrape | Lengths for jeans live inside **Scraped variants** JSON |
| **Variant profile** | Optional | e.g. `clothing_numeric` for jeans (Waist + Length + Color) |
| **Approve** | Optional | Not used in full-auto mode — safe to hide |

Lookup rules are **inside** `sheet-master.csv` (columns AU–BH, hidden). No second tab needed.
