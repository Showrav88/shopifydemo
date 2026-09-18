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

## Row 1 headers

Copy from `sheet-input-template.csv`. Must include **Product URL** and **SKU**.

## How matching works

All sheet update nodes match on **Product URL** from the Google Sheets trigger row.

## Do you need to change your sheet columns?

**No** — if your Row 1 headers match `sheet-input-template.csv`, you are fine. The workflow matches columns **by name**, not position. You do not need to rearrange columns.

| Column | Required? | Notes |
|--------|-----------|-------|
| **Product URL** | Yes | Only column you must fill to start |
| **Sizes**, **Colors**, **Scraped variants** | Auto-filled by scrape | Lengths for jeans live inside **Scraped variants** JSON |
| **Variant profile** | Optional | e.g. `clothing_numeric` for jeans (Waist + Length + Color) |
| **Approve** | Optional | Not used in full-auto mode — safe to hide |
| **Lengths** | Not needed | Stored in Scraped variants; add only if you want to read inseams in the sheet |
