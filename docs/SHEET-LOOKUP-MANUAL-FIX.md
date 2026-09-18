# Fix: can't delete Vendor / Category formulas

## Why it happened

Older CSV versions put **formulas inside** columns C–F (Vendor, Product category, etc.).  
In Google Sheets you **cannot type over a formula** in the same cell — Delete clears it but re-import or drag-fill brings formulas back.

## New layout (latest `sheet-products.csv`)

| Columns | What |
|---------|------|
| **C–F** | Vendor, Product category, Variant profile, Collection — **blank, you type here** |
| **R** | **Prompt ID** — you type e.g. `mango-linen-qa90` (blank = `default`) |
| **S–Y** | Prompt Title … Prompt Category — **blank, optional override** |
| **Last 11 columns** | Suggested Vendor … + Suggested Prompt* — **formulas only** (hide these) |

n8n uses: **your typed value if filled**, else **Suggested*** from lookup / PromptLibrary.

## Fix your existing sheet (no full wipe)

### Option A — Add 4 columns at the end (keep your data)

1. Insert **4 blank columns** after **Shopify Product URL**
2. Name them exactly: `Suggested Vendor`, `Suggested Product category`, `Suggested Variant profile`, `Suggested Collection`
3. In row 2, copy the **formula** from old C into new Suggested Vendor (adjust row number)
4. Repeat for D→Suggested Category, E→Suggested Variant, F→Suggested Collection
5. **Clear C–F** (select → Delete) — now plain cells you can type in
6. **Hide** the four Suggested columns (right-click column header → Hide)

### Option B — Re-import products CSV (easiest if few rows)

1. Keep **LookupTables** and **PromptLibrary** tabs
2. Export/back up any URLs you need
3. Re-import `sheet-products.csv` into **Master_Sheetv1**
4. Paste URLs again in column A

### Option C — One-time override without changing sheet

Leave lookup as-is; before Shopify run, paste **values only** into C–F:

1. Type your vendor in an empty cell elsewhere
2. Copy → select C2 → **Paste special → Values only**

## Do not

- Re-import `sheet-products.csv` on top of a sheet you edited manually without backup
- Edit **Suggested*** columns (formulas) — edit **C–F** instead
