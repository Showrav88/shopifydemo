# Google Sheet setup — step by step (fix formula errors)

## Why you saw errors (#REF! or #N/A)

| Error | Cause | Fix |
|-------|-------|-----|
| **#REF!** | `LookupTables` tab missing or wrong name | Import lookup CSV first, rename tab exactly **`LookupTables`** |
| **#N/A** inside formula | No keyword matched yet | Normal before Title — fills after scrape or use URL with `/shirts/` etc. |
| **Blank** | Row has no URL in column A | Normal — not an error |
| **#NAME?** | Old tab name `Lookup Tables` (with space) | Use **`LookupTables`** (no space) — updated in latest CSV |

**You do NOT need to run n8n** for **Suggested Vendor** — it works from URL alone (e.g. `mango.com` → `Mango`).

**Suggested Category / Collection** improve when **Title** (column L) is filled by scrape.

---

## Import order (important)

### Step 1 — Lookup tab FIRST

1. Open your Google Spreadsheet
2. **File → Import → Upload** `sheet-lookup-tables.csv`
3. **Insert new sheet**
4. Rename tab to **`LookupTables`** (exactly — no space)

### Step 2 — Prompt Library SECOND

1. **File → Import → Upload** `sheet-prompt-library.csv`
2. **Insert new sheet**
3. Rename tab to **`PromptLibrary`**

### Step 3 — Products tab THIRD

1. **File → Import → Upload** `sheet-products.csv`
2. **Insert new sheet**
3. Rename tab to **`Master_Sheetv1`** (or **Products** — match your n8n trigger tab)

### Step 4 — Test

1. Go to **Products** tab, row 2 (Mango example URL)
2. Column **C** should show **`Mango`**
3. Column **E** may show **`mens-shirts`** (from `/shirts/` in URL)

If **#REF!** → go back to Step 1, check tab name is `LookupTables`.

---

## Your spreadsheet structure

```
One Google Spreadsheet (one file, multiple tabs)
│
├── Master_Sheetv1    ← you work here (paste URLs, delete rows OK)
├── LookupTables      ← vendor / category / collection rules (never delete rows)
└── PromptLibrary     ← AI prompt templates (never delete rows)
```

**Connected:** Products columns C–F read `LookupTables`. **Prompt ID** + Prompt columns read `PromptLibrary`. See **`docs/PROMPT-LIBRARY-GUIDE.md`**.

---

## What you type vs what auto-fills

| Column | Name | You type? | When it fills |
|--------|------|-----------|----------------|
| A | Product URL | ✅ Yes | — |
| C–F | **Vendor, Product category, Variant profile, Collection** | ✅ Optional | **You** type to override; leave blank = use Suggested* |
| G–H | Title, Description | No | **n8n scrape** |
| Last 4 cols | **Suggested Vendor … Suggested Collection** | ❌ Never | Formulas from LookupTables — **hide these columns** |

**Important:** C–F are **plain cells** (no formulas). Lookup auto-fill lives in **Suggested*** columns at the **end** of the sheet. n8n uses your typed value if present, otherwise Suggested*.

---

## Delete / add rows safely

| Tab | Delete row? |
|-----|-------------|
| **Products** | ✅ Safe — lookup not affected |
| **LookupTables** | ❌ Never delete — only add keywords at bottom |

**Add new product:** Insert row on Products → copy columns C–F formulas from row above (drag fill handle).

Rows 102+ have **no formulas** pre-loaded — copy from row 2–101 or insert row between existing products (Sheets copies formulas).

---

## Do errors show on empty rows?

**No** — if column A is empty, columns C–F should be **blank** (not red errors).

Errors only appear when:
- `LookupTables` tab is missing (**#REF!**)
- URL present but no rule matches (**blank** after IFERROR — not red)

---

## Files

| File | Tab name |
|------|----------|
| `sheet-lookup-tables.csv` | **LookupTables** |
| `sheet-prompt-library.csv` | **PromptLibrary** |
| `sheet-products.csv` | **Master_Sheetv1** |
