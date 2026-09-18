# Prompt Library tab — separate AI prompts

Use a **PromptLibrary** tab for reusable AI instructions. Each product row picks a set by **Prompt ID**.

Same spreadsheet ID as your products sheet — no extra n8n config.

## Import (once)

1. Open your spreadsheet (`1iV7qRLtQ0hLrDUd6MA8cJCLz36kliDB28C3Y1rvX8JQ` or yours).
2. **File → Import → Upload** `sheet-prompt-library.csv`
3. **Insert new sheet**
4. Rename tab to **`PromptLibrary`** (exactly)

Also import/update **LookupTables** and **Products** from the latest CSVs (see `docs/SHEET-MASTER-GUIDE.md`).

## Tabs in one file

```
Spreadsheet
├── LookupTables     ← vendor / category / collection rules
├── PromptLibrary    ← AI prompt templates (this guide)
└── Master_Sheetv1   ← products (paste URLs here)
```

## How it connects

| Products column | You type? | What happens |
|-----------------|-----------|--------------|
| **Prompt ID** (col R) | ✅ Yes | e.g. `mango-linen-qa90` — blank = library uses `default` |
| **Prompt Title … Prompt Category** | Optional | Type here to **override**; leave blank = use **Suggested Prompt*** at end |
| **Suggested Prompt*** (last 7 cols) | ❌ Never | Formulas from **PromptLibrary** — **hide these columns** |

Same pattern as Vendor: you edit the main columns; lookup lives in hidden Suggested* columns at the end.

n8n reads the **computed** prompt text when the row triggers — same as before, but prompts live on one shared tab.

## Built-in prompt IDs

| prompt_id | Use for |
|-----------|---------|
| `default` | General UK fashion paraphrase |
| `mango-linen-qa90` | Mango linen shirt test — QA overlap targets |

Add your own rows at the bottom of **PromptLibrary** — never delete existing rows.

## Per product

1. Paste **Product URL** in column A.
2. Set **Prompt ID** (column R) if you want a non-default template.
3. Leave **Prompt Title … Prompt Category** alone — they are formulas.

Example row 2: URL + Prompt ID `mango-linen-qa90`.

## n8n

- Spreadsheet ID in workflow JSON is enough.
- Products tab gid (`2126173338`) stays the trigger tab.
- **PromptLibrary** is sheet-formula only — n8n does not need its gid.

## Why lookup columns (Vendor, Category) update in sheet but not in Shopify

**LookupTables** formulas in columns C–F **do** recalculate in Google Sheets when Title/Description are filled.

n8n, however, keeps the row snapshot from when the run **started**. It does not automatically re-read formula columns after scrape.

**Fix (workflow):** before **Build Shopify product**, the workflow **Re-read sheet row** and merges fresh Vendor / Product category / Variant profile / Collection from the sheet.

Re-import `ShopifyProductAdd.V2.json` after pulling latest changes.
