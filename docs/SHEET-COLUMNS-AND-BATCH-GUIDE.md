# Google Sheet Columns, SEO, Skip Logic & Batch Runs

## Which columns matter for SEO?

The workflow uses AI for columns that affect **search ranking and sales copy**. Other Shopify export columns are for shipping, tax, variants, or Google Shopping — not needed for basic listing automation.

### YOU type (input — AI reads these)

| Column | SEO impact | Why |
|--------|------------|-----|
| **Description** | High | Raw facts the AI must not invent |
| **Product image URL** | High | Vision checks the real product |
| **Product category** | Medium | **You set this** — type plain text e.g. `Casual Wear`. **Never** `=Casual Wear` (Google Sheets `#ERROR!`) |
| **Vendor** | Medium | Brand trust, filters |
| **Title** | Medium | Starting point; AI improves it |
| **Price** | Low for SEO | Required for Shopify + trigger |
| **SKU** | None for SEO | Required to find the row in the sheet |

### AI writes (output — these ARE your SEO)

| Column | SEO impact |
|--------|------------|
| **Title** | High — search + click-through |
| **Description** | High — on-page content |
| **SEO title** | High — Google `<title>` tag |
| **SEO description** | High — meta description snippet |
| **Image alt text** | Medium — image search + accessibility |
| **Tags** | Medium — Shopify search/filter |
| **QA Status / AI Score** | None for SEO — internal quality control |

### Columns we do NOT use (safe to hide)

These come from Shopify CSV export but this workflow ignores them:

- URL handle (written back after create)
- Compare-at price, Cost per item, Charge tax, Tax code
- Option1/2/3 names and values
- Barcode, Weight, Fulfillment service
- Google Shopping / Custom label 0–4
- Published on online store, Gift card, Color metafields
- Unit price measures, Inventory tracker settings

**Hiding them does not hurt SEO.** They only matter if you sell on Google Shopping, use multi-variant products, or need advanced shipping/tax.

---

## Analyze image flow (working V2)

```
Photoroom → Analyze image (binary) → Restore image binary → ImgBB → Message a model
```

**Why not ImgBB URL for vision?** n8n can reach `i.ibb.co`, but **OpenAI's servers often cannot** — you get `Unable to download content from the provided URL before the timeout` even when "Wait for CDN ready" passes.

**Analyze image settings:**
- Input Type: **Binary File(s)**
- Input Data Field Name: `data` (from Photoroom HTTP Request)

ImgBB still runs **after** analysis for Shopify upload and **Generated Image URL** in the sheet.

---

## Skip if already PASS (score ≥ 90)

The workflow now **stops early** if a row already has:

- `QA Status` = **PASS**
- `AI Score` ≥ **90**

No Photoroom, no AI, no duplicate Shopify product.

**To re-run a product:** clear `QA Status` and `AI Score`, or set `QA Status` to `RETRY`, then change **Price** to trigger again.

---

## How to run many products (batch)

This workflow uses a **Google Sheets Trigger** — it runs **one row per trigger** when **Price** changes.

### Add multiple products

| Row | SKU | Price | Image URL | Description |
|-----|-----|-------|-----------|-------------|
| 2 | TEST-001 | 29.99 | https://... | ... |
| 3 | TEST-002 | 39.99 | https://... | ... |
| 4 | TEST-003 | 49.99 | https://... | ... |

Each row needs a **unique SKU**.

### Trigger each row

The trigger watches **Price**. For each new product:

1. Fill row with SKU, image, description, etc.
2. Enter **Price** last (or change Price) — that fires the workflow for that row only.

### Timing

- Trigger polls about **every 1 minute**
- 10 products = enter Price on 10 rows → ~10 separate runs (not all in one second)
- n8n Cloud credits: each row = 1 full AI + image run (~$0.10–0.30 per product depending on models)

### Faster bulk (advanced, not in V2)

For hundreds of products at once you would need a different trigger (e.g. manual "Run workflow" with Read All Rows, or a Schedule + loop). V2 is designed for **one product per Price change** — safer for QA and credits.

---

## Hide or delete extra columns in Google Sheets

### Recommended: **Hide** (keeps Shopify export compatible)

1. Select columns you don't use (e.g. Google Shopping columns)
2. Right-click → **Hide column**
3. Your data stays; sheet looks cleaner

### **Delete** columns permanently

Only delete if you will **never** import this sheet back to Shopify as a full CSV.

**Do NOT delete these headers** (workflow needs them):

- Title, Description, Vendor, Product category, Product image URL
- Price, SKU, Inventory quantity, Status
- Tags, SEO title, SEO description, Image alt text
- QA Status, AI Score, URL handle

**Safe to delete** if you don't use them:

- All `Google Shopping / ...` columns
- Option2, Option3 columns (if single-variant only)
- Barcode, Compare-at price (until you need them)

### URL columns — which link goes where?

| Column | Who fills it | Example |
|--------|--------------|---------|
| **Product image URL** | **You** (input) | `https://img.drz.lazcdn.com/...webp` (original CDN/scrape link) |
| **Generated Image URL** | **Workflow** (after ImgBB) | `https://i.ibb.co/.../edit.png` (clean image sent to Shopify) |
| **Shopify Image URL** | **Workflow** (after Shopify CDN ready) | `https://cdn.shopify.com/s/files/1/...` (image on Shopify servers) |
| **URL handle** | **Workflow** (after Shopify create) | `royal-blue-cotton-long-sleeves-...` |
| **Shopify Product URL** | **Workflow** (after Shopify create) | `https://8kqexi-2j.myshopify.com/products/royal-blue-...` |

Your lazcdn link stays in **Product image URL** — that is correct. The workflow does not replace it; it adds **Generated Image URL**, **Shopify Image URL**, and **Shopify Product URL** in separate columns.

**Add these column headers** to row 1 if missing: `Generated Image URL`, `Shopify Image URL`, `Shopify Product URL`

### Shopify PASS path (score ≥ 90)

```
Create a product (draft, no image yet)
  → Prepare Shopify image upload (ImgBB direct URL: i.ibb.co)
  → Upload image to Shopify (HTTP POST with image.src — Shopify fetches from ImgBB)
  → Update price, SKU and image link
  → Update row in sheet1 (Shopify Image URL, or ImgBB fallback if CDN not ready)
```

---

## How to re-run a product (score below 90 = FAIL)

| Step | What to do |
|------|------------|
| 1 | Find row where `QA Status` = **FAIL** or `AI Score` < 90 |
| 2 | Clear **QA Status** and **AI Score** (empty cells) |
| 3 | Optionally edit **Description** if QA failed quality |
| 4 | Change **Price** slightly (e.g. `29.99` → `30.00`) — this triggers the workflow |
| 5 | Workflow runs again from the start (Photoroom → AI → QA) |

You do **not** pick a step in n8n — changing **Price** re-runs the **whole** workflow for that row.

**Note:** If `QA Status` = PASS and score ≥ 90, the workflow **skips** that row (no duplicate Shopify product).

---

## Add products: all at once or one by one?

### Recommended workflow

**Phase 1 — Fill sheet (no trigger yet)**

Add as many rows as you want. Fill everything **except** leave **Price empty** OR do not change Price yet:

| Row | SKU | Product image URL | Description | Vendor | Category | Price |
|-----|-----|-------------------|-------------|--------|----------|-------|
| 2 | TEST-001 | https://... | ... | TestBrand | ... | *(empty)* |
| 3 | TEST-002 | https://... | ... | TestBrand | ... | *(empty)* |
| 4 | TEST-003 | https://... | ... | TestBrand | ... | *(empty)* |

**Phase 2 — Run one by one**

Enter **Price** on row 2 only → wait for run to finish (~2–5 min) → check QA Status.

Then enter **Price** on row 3 → wait → row 4 → etc.

### Why not all Prices at once?

The trigger fires **once per Price change**. If you paste prices on 10 rows quickly, you get 10 runs queued (OK) but harder to debug failures and uses credits faster.

### One product at a time (safest for learning)

1. Add **one full row** including Price  
2. Wait for PASS/FAIL  
3. Fix if FAIL  
4. Add next row  

---

### Minimal sheet (copy-paste headers only)

```
Title,Description,Vendor,Product category,Product image URL,Price,SKU,Inventory quantity,Status,Tags,SEO title,SEO description,Image alt text,QA Status,AI Score,URL handle,Generated Image URL,Shopify Product URL
```

Import as new tab or replace row 1 headers — keep one product per row.

---

## Quick reference

| Question | Answer |
|----------|--------|
| Why no AI on Google Shopping columns? | Not used for basic Shopify SEO listing |
| Duplicate product? | Skipped if PASS + score ≥ 90 |
| Many products one run? | One row per Price change; add rows with unique SKUs |
| Hide extra columns? | Yes — recommended |
| Delete extra columns? | Yes — only if you keep the required headers above |
