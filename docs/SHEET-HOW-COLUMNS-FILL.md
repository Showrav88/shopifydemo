# How each column gets filled (simple)

## You only paste

| Column | You type |
|--------|----------|
| **A** Product URL | ✅ Paste URL |
| **R** Prompt ID | Optional — e.g. `mango-linen-qa90` (blank = `default`) |

No **Suggested*** columns. Formulas live in the real columns.

---

## Lookup (columns C–F)

Formulas read **LookupTables** using URL + Title + Description:

| Column | Source |
|--------|--------|
| **C** Vendor | URL domain (`mango.com` → Mango) |
| **D** Product category | URL/title keywords |
| **E** Variant profile | URL/title keywords |
| **F** Collection | URL/title keywords |

After n8n scrapes Title (G) and Description (H), C–F recalculate with better matches.

---

## AI prompts (columns S–Y)

Formulas read **PromptLibrary** using **Prompt ID** (column R):

| Column | Source |
|--------|--------|
| **S–Y** Prompt Title … Prompt Category | PromptLibrary row matching Prompt ID |

Leave **Prompt ID** blank → library uses `default` prompts.

---

## Scrape output (columns G+)

Title, Description, image, sizes, etc. — filled by **n8n scrape**, not formulas.

After scrape writes Title/Description, n8n **re-reads the sheet row** so C–F lookup formulas (with new keywords) flow into Shopify.

---

## Tabs

| Tab | Role |
|-----|------|
| **Master_Sheetv1** | Products — paste URL + Prompt ID |
| **LookupTables** | Rules for C–F |
| **PromptLibrary** | Templates for S–Y (keep names: `Prompt Title`, etc.) |
