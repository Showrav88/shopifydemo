# Your sheet — pre-configured in workflow JSON

**Sheet URL:** https://docs.google.com/spreadsheets/d/1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo/edit?gid=975501836

| Setting | Value |
|---------|-------|
| Spreadsheet ID | `1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo` |
| Tab gid | `975501836` |
| Match column | **SKU** (all update nodes) |

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

1. **Stamp sheet SKU** — writes SKU to your row (matches Product URL from trigger once)
2. All other updates — match on **SKU** (reliable, no URL mismatch)
