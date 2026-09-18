# Google Sheet setup — 2 tabs, 1 spreadsheet (professional)

Use **one Google Spreadsheet** with **two tabs** connected by formulas.  
Delete product rows anytime — **lookup data never gets deleted**.

## Files to import

| File | Tab name in Google Sheets | Purpose |
|------|---------------------------|---------|
| **`sheet-products.csv`** | **Products** | Paste Product URL here — add/delete rows freely |
| **`sheet-lookup-tables.csv`** | **Lookup Tables** | Rules only — edit keywords, **do not delete rows** |

Same spreadsheet file. Two imports → two tabs.

---

## Step-by-step import

### 1. Create or open your spreadsheet

### 2. Import Products tab

- **File → Import** → `sheet-products.csv`
- **Insert new sheet** (or replace Sheet1)
- Rename tab: **`Products`**

### 3. Import Lookup tab (same spreadsheet)

- **File → Import** → `sheet-lookup-tables.csv`
- **Insert new sheet**
- Rename tab: **`Lookup Tables`** (name must match exactly — formulas use this)

### 4. Check formulas work

On **Products** tab row 2 (Mango example URL):

| Column | Should show |
|--------|-------------|
| C Suggested Vendor | `Mango` |
| E Suggested Collection | `mens-shirts` (from URL `/shirts/`) |

If formulas show `#REF!` → Lookup tab is not named **`Lookup Tables`**.

---

## What you do day to day

| Action | Where |
|--------|-------|
| Paste **Product URL** | **Products** tab, column A |
| Add new product | **Insert row** on Products tab (formulas copy down) |
| Delete finished product | **Delete row** on Products tab only — safe |
| Edit lookup rules | **Lookup Tables** tab — add keyword rows at bottom |
| Never | Delete rows on Lookup Tables tab |

---

## How tabs connect

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  Products tab               │     │  Lookup Tables tab           │
│  A: Product URL  (you type) │────►│  keyword → vendor            │
│  C–F: Suggested  (formulas) │◄────│  keyword → category          │
│  L: Title        (n8n)      │────►│  keyword → collection        │
│  M: Description  (n8n)      │     │  (static rules, 193 rows)    │
└─────────────────────────────┘     └──────────────────────────────┘
              │
              ▼
         n8n workflow → Shopify
```

**Suggested** columns (C–F) use formulas like:

`=INDEX('Lookup Tables'!$K:$K, MATCH(... SEARCH in URL/title ...))`

When n8n writes **Title** (column L), suggestions in D and E **update automatically**.

---

## Column guide (Products tab)

| Col | Name | You type? |
|-----|------|-----------|
| A | Product URL | ✅ Yes |
| B | Force browser | Optional |
| C–F | Suggested … | Formulas (auto) |
| G–J | Vendor, Category, Collection | Optional override |
| L–M | Title, Description | n8n scrape |
| Rest | Sizes, QA, Shopify URL | n8n workflow |

---

## Professional layout tips

1. **Freeze row 1** on both tabs (View → Freeze → 1 row)
2. **Hide** prompt columns you don't use (columns U onward)
3. **Color** column A header yellow = "input here"
4. **Color** columns C–F header light blue = "auto suggestions"
5. Keep **Lookup Tables** tab at the end — don't use it daily

---

## n8n (Phase 5c)

After scrape, n8n will copy **Suggested** → **Vendor / Product category / Collection** if those are still empty, then create Shopify draft.

---

## Do NOT use `sheet-master.csv`

The old single-tab file mixed product rows with lookup data — deleting a product row deleted lookup rules. **Deprecated.** Use `sheet-products.csv` + `sheet-lookup-tables.csv` instead.
