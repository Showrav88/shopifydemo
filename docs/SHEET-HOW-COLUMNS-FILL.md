# How each column gets filled (simple)

## You only paste

| Column | You type |
|--------|----------|
| **A** Product URL | ✅ Paste URL |
| **R** Prompt ID | Optional — e.g. `mango-linen-qa90` |

Everything else is automatic.

---

## Vendor / category / collection (columns C–F)

**Not pre-stored text.** These are **formulas** that read **LookupTables** using:

1. **URL** — e.g. `mango.com` → Vendor `Mango`, `/men/shirts/linen/` → category keywords  
2. **Title + Description** (columns G–H) — after n8n scrape, formulas **recalculate** with better keyword match  

```
Paste URL in A
    → C shows Mango (from domain in LookupTables)
    → D–F show category from URL keywords (/shirts/, /linen/, /men/)
n8n scrapes → writes Title in G, Description in H
    → C–F formulas recalculate (may improve match)
n8n re-reads row before Shopify → uses latest C–F values
```

**You do not need Suggested Vendor columns** — lookup lives in **C–F directly**.

To override: click cell C (or D/E/F) → **Delete** → type your value.

---

## Title / Description / image / sizes (columns G+)

Filled by **n8n scrape** — not LookupTables.

---

## AI prompts

| Column | How it fills |
|--------|----------------|
| **R** Prompt ID | You type — picks row in **PromptLibrary** tab |
| **S–Y** Prompt Title … | Optional override (usually leave blank) |
| **Last 7 cols** Suggested Prompt* | Formulas from **PromptLibrary** — **hide these** |

n8n uses S–Y if you typed there; else **Suggested Prompt***.

---

## Tabs

| Tab | Role |
|-----|------|
| **Master_Sheetv1** | Your products |
| **LookupTables** | Rules for C–F (vendor, category, collection keywords) |
| **PromptLibrary** | AI instruction templates for prompts |

**PromptLibrary column names stay** `Prompt Title`, `Prompt Description`, etc. — do not rename to Suggested*.
