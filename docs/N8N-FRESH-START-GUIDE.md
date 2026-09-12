# n8n Fresh Start Guide — ShopifyProductAdd.V1

Use this when cleaning your Google Sheet and testing one blouse product for free.

---

## Part A — Clean your Google Sheet (keep headers only)

### Sheet: `product_template` (trigger sheet)

**Keep row 1 headers exactly as Shopify export.** Minimum columns you need:

| Column name (header) | Required for test? |
|---------------------|-------------------|
| Title | Optional (AI can generate) |
| Description | **Yes** |
| Vendor | **Yes** (brand) |
| Product category | **Yes** |
| Product image URL | **Yes** (or Image Src) |
| Price | **Yes** — trigger watches this column |
| SKU | Optional |
| Inventory quantity | Optional |

### Test row (row 2) — paste this data

| Column | Value |
|--------|-------|
| Title | Blue Floral Blouse |
| Description | Women's blue floral print blouse. Lightweight polyester blend. Casual summer top. V-neck. Short sleeves. Available for UK delivery. |
| Vendor | TestBrand |
| Product category | Women > Tops > Blouse |
| Product image URL | `https://img.drz.lazcdn.com/static/bd/p/9b1c9180c912312813c3acb6f0158ee8.jpg_720x720q80.jpg_.webp` |
| Price | `29.99` |
| SKU | TEST-BLOUSE-001 |
| Inventory quantity | `10` |
| Status | `draft` |

**Important:** Your trigger watches **Price** column. You must enter a price or change price to fire the workflow.

---

## Part B — Do you need `=` sign?

| Field type | What to type |
|------------|--------------|
| **Fixed text** (e.g. `draft`) | Just type: `draft` — no `=` |
| **Expression** (pull from another node) | Click **Expression** toggle (or type `=`) then: `{{ $('Node Name').item.json.field }}` |
| **Full expression format** | `={{ $('HTTP Request1').item.json.data.url }}` |

**Rule:** If you see the `fx` icon or "Expression" mode ON → use `{{ }}`.  
If field says "Fixed" → plain text only, no `=`.

**Bug in your workflow:** `Update row in sheet` has `=={{` (double equals) — change to single `={{`.

---

## Part C — Connect IF false branch (step by step)

1. On canvas, click the **If** node
2. You see **two output dots** on the right:
   - **Top dot** = `true` (already goes to Create a product)
   - **Bottom dot** = `false` ← this is empty on your screenshot
3. Click the **bottom dot** (false) OR click the **+** on the false line
4. Search **Google Sheets** → **Update Row**
5. Configure:
   - **Document:** `AI Shopify Product Automation` (or your tracking sheet)
   - **Sheet:** Products
   - **Matching column:** `row_number`
   - **Values:**
     - `QA Status` = `NEEDS_HUMAN_QA` (fixed text)
     - `AI Score` = `={{ $json['AI Score'] }}`
     - `row_number` = `={{ $('Google Sheets Trigger').item.json.row_number }}`

**Result:** Score < 90 → sheet updated, **no Shopify product created**.

---

## Part D — Shopify Create a product (from your screenshot)

Your **Title** is empty (red error). Fix:

### Title field
Click **Expression** → paste:
```
={{ JSON.parse($('Message a model').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()).title }}
```

### Additional Fields — click **Add Field**

| Field to add | Value |
|--------------|-------|
| **Body HTML** | `={{ JSON.parse($('Message a model').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()).description_html }}` |
| **Product Type** | `={{ $('Google Sheets Trigger').item.json['Product category'] }}` |
| **Tags** | `={{ JSON.parse($('Message a model').item.json.output[0].content[0].text.replace(/```json|```/g, '').trim()).tags }}` |
| **Status** | `draft` ← fixed text, no expression |

### Images (already in your node)
```
src: {{ $('HTTP Request1').item.json.data.url }}
```

> If **Status** is not in Add Field dropdown, use **HTTP Request** to Shopify Admin API instead, or set `published: false` — draft products are unpublished by default in some Shopify node versions.

---

## Part E — Analyze image node (why not green?)

Green = node ran successfully. Red/orange = not run yet or error.

### Fix checklist

1. **Run nodes in order** — click **Execute workflow** from trigger, OR click each node → **Execute previous nodes**
2. **HTTP Request1 must succeed first** — it must return `data.url`
3. **Fix URL expression** — remove extra space:
   ```
   ={{ $('HTTP Request1').item.json.data.url }}
   ```
   (no space before `}}`)
4. **Change prompt** from `What's in this image?` to:

```
Analyze this fashion product image. Extract ONLY what you can see.
Do NOT invent specifications.

Return JSON only:
{
  "verified_facts": ["fact1", "fact2"],
  "color": "",
  "material": "",
  "product_type": "",
  "gender": ""
}
```

5. **Model:** GPT-4O (you have this correct ✓)
6. **Input Type:** Image URL(s) ✓

### Where to put Analyze image in flow

**Best position** — BEFORE listing generation:

```
ImgBB (HTTP Request1)
  → Analyze image (vision — sees photo)
  → Message a model (uses verified_facts + sheet text to write listing)
```

Currently you may have it after listing — that's OK for QA but client wants vision **before** generating specs.

---

## Part F — Message a model (listing) — full prompt

Replace prompt in **Message a model**:

**System message (first content block):**
```
You are a UK fashion e-commerce copywriter.
Use ONLY verified facts from the image analysis and raw product info.
Do NOT invent specifications.
Return ONLY valid JSON, no markdown:
{
  "title": "",
  "description_html": "<p>...</p><ul><li>Material: </li></ul>",
  "tags": "women, blouse, blue, floral",
  "seo_title": "",
  "meta_description": "",
  "image_alt_text": "",
  "collection": "Women > Tops"
}
```

**User message (second content block):**
```
Verified from image:
{{ $('Analyze image').item.json.output[0].content[0].text }}

From sheet:
Title: {{ $('Google Sheets Trigger').item.json.Title }}
Description: {{ $('Google Sheets Trigger').item.json.Description }}
Category: {{ $('Google Sheets Trigger').item.json['Product category'] }}
Vendor: {{ $('Google Sheets Trigger').item.json.Vendor }}
```

---

## Part G — Message a model1 (QA score) — full prompt

```
Compare ORIGINAL sheet data vs GENERATED listing.
Score 0-100. Flag any invented claims.

Original:
{{ $('Google Sheets Trigger').item.json.Description }}

Generated:
{{ $('Message a model').item.json.output[0].content[0].text }}

Return JSON only:
{
  "quality_score": 85,
  "seo_title": "max 60 chars",
  "meta_description": "max 160 chars",
  "image_alt_text": "",
  "issues": []
}
```

---

## Part H — Free testing tips (save credits)

1. Use **one test row** only in sheet
2. **Disable workflow** when not testing (toggle off top-right)
3. Use **Execute workflow** manually — don't leave polling every minute
4. **Skip Photoroom** temporarily: connect Code → Message a model directly with image URL from sheet (saves Photoroom credits)
5. For free image hosting skip: use sheet image URL directly in Analyze image:
   ```
   ={{ $('Google Sheets Trigger').item.json['Product image URL'] }}
   ```
   Skip ImgBB until listing works

### Minimal free test flow (no Photoroom, no ImgBB)

```
Google Sheets Trigger
  → Code (validate)
  → Analyze image (use sheet image URL directly)
  → Message a model (listing)
  → IF score >= 90
      → Google Sheets update only (skip Shopify until ready)
```

---

## Part I — Execution order to get green nodes

1. Clear sheet except headers + 1 test row (Part A)
2. **Execute workflow** (manual button top-right)
3. Watch each node turn green left to right
4. If red — click node → read **Error** in OUTPUT panel
5. Common errors:
   - Title empty on Shopify node → fix Part D
   - ImgBB failed → use sheet URL directly for testing
   - JSON parse error → AI returned markdown, add `.replace(/```json|```/g,'')`

---

## Quick reference — what connects where

```
[Trigger] Google Sheets
    ↓
[Code] Validate
    ↓
[HTTP] Photoroom (optional for free test)
    ↓
[HTTP] ImgBB (optional for free test)
    ↓
[AI] Analyze image ← vision, GPT-4O
    ↓
[AI] Message a model ← listing JSON
    ↓
[Sheets] Update row in sheet
    ↓
[AI] Message a model1 ← QA score
    ↓
[Sheets] Update row in sheet2
    ↓
[IF] score >= 90?
    ├─ TRUE  → [Shopify] Create draft → [Sheets] Update
    └─ FALSE → [Sheets] QA Status = NEEDS_HUMAN_QA
```
