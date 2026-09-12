# ShopifyProductAdd.V1 — Fix Guide

Matches client doc: `Shopify_Product_Listing_AI_Bot_Procedure.pdf`

## Your current flow (what works)

```
Google Sheets Trigger
  → Code in JavaScript (validate)
  → HTTP Request (Photoroom — remove background)
  → HTTP Request1 (ImgBB — public URL)
  → Message a model (generate listing)      ← text only, no vision
  → Update row in sheet
  → Message a model1 (QA + SEO)           ← text only, no vision
  → Update row in sheet2
  → If (AI Score >= 80)                   ← should be 90
  → Create a product (Shopify)
  → Update row in sheet1
```

## Google Sheet columns to add

In your **Products** sheet (`AI Shopify Product Automation`), add if missing:

| Column | Values |
|--------|--------|
| QA Status | `NEW` → `PENDING_REVIEW` → `DRAFT_CREATED` → `REJECTED` → `FAILED` |
| Feedback | Human notes when rejecting (e.g. "Make SEO more aggressive") |
| Error Log | Filled by error workflow |
| AI Score | 0–100 |

---

## FIX 1 — OpenAI Vision (Message a model)

**Problem:** AI never sees the image — only text `Image URL: https://...`

**Fix:**
1. Open node **Message a model**
2. Change model from `gpt-4o-mini` → **`gpt-4o`** (vision required)
3. Replace prompt with two messages:

**System message:**
```
You are a product analyst. Look at the product image and raw text.
Extract ONLY verifiable facts. Do NOT invent specifications.
Return JSON only:
{
  "verified_facts": [],
  "material": "",
  "color": "",
  "gender": "",
  "title": "",
  "description_html": "",
  "tags": "",
  "seo_title": "",
  "meta_description": "",
  "image_alt_text": "",
  "collection": ""
}
```

**User message (enable Image / Vision):**
```
Brand: {{ $('Google Sheets Trigger').item.json.Vendor }}
Category: {{ $('Google Sheets Trigger').item.json['Product category'] }}
Raw info: {{ $('Google Sheets Trigger').item.json.Description }}
Image URL: {{ $('HTTP Request1').item.json.data.url }}
```

4. In n8n OpenAI node → add **Image** input:
   - Type: `Image URL`
   - URL: `={{ $('HTTP Request1').item.json.data.url }}`

> If gateway does not support vision on gpt-4o, use HTTP Request to OpenAI API directly with vision payload.

---

## FIX 2 — QA threshold 90+ and Draft only

### 2a — Change IF node

1. Open node **If**
2. Change condition: `AI Score` **>= 90** (not 80)

### 2b — False branch (score < 90)

Connect **If → FALSE** to new **Google Sheets Update** node:
- `QA Status` = `NEEDS_HUMAN_QA`
- Do NOT create Shopify product

### 2c — Shopify Create as DRAFT

1. Open **Create a product**
2. In Additional Fields add:
   - **Status:** `draft` (or use Shopify API `status: draft`)
3. Map **Title** from AI JSON `title` (not SEO title)
4. Map **Body HTML** from `description_html`
5. Image `src` = ImgBB URL from `HTTP Request1`

---

## FIX 3 — QA Status after Shopify create

In **Update row in sheet1**, change:
- `QA Status` = **`PENDING_REVIEW`** (not `DRAFT_CREATED`)

Client flow: draft created → human reviews in Shopify → publish manually.

---

## FIX 4 — Remove hardcoded ImgBB key

**Problem:** API key in JSON query `key=8e71e83fe03de0cd6e22c480fe344e9b`

**Fix:**
1. n8n → **Credentials** → **Query Auth** (or Generic Credential)
2. Name: `ImgBB API`
3. Add query param `key` = your key (stored securely)
4. Open **HTTP Request1**
5. Remove `key` from query parameters
6. Select credential **ImgBB API**
7. Re-export workflow — key should NOT appear in JSON

---

## FIX 5 — Fix double equals typo

In **Update row in sheet**, fields show `=={{` — remove extra `=`:

| Wrong | Correct |
|-------|---------|
| `=={{ $('Google Sheets Trigger')...` | `={{ $('Google Sheets Trigger')...` |

Fix all 6 fields: Title, Product category, Description, Tags, SEO title, SEO description, Image alt text.

---

## FIX 6 — Reject & Regenerate loop (new workflow)

Create **second workflow**: `ShopifyProductRegenerate.V1`

### Trigger
- **Google Sheets Trigger** on sheet `AI Shopify Product Automation`
- Watch column: **QA Status**
- When value = `REJECTED`

### Flow
```
Google Sheets Trigger (QA Status = REJECTED)
  → OpenAI (regenerate ONLY fields mentioned in Feedback)
  → Google Sheets Update (new SEO, tags, etc.)
  → Shopify Update Product (by Shopify Product ID from sheet)
  → Google Sheets Update (QA Status = PENDING_REVIEW)
```

**Regeneration prompt:**
```
Product already exists. Do NOT change image or price.

Current listing:
Title: {{ $json.Title }}
SEO: {{ $json['SEO Title'] }}
Description: {{ $json['Description (HTML)'] }}

Human feedback: {{ $json.Feedback }}

Rewrite ONLY the fields mentioned in feedback.
Return JSON: { "seo_title": "", "meta_description": "", "description_html": "", "tags": "" }
```

**Skip:** Photoroom, ImgBB (saves credits)

---

## FIX 7 — Error workflow (new workflow)

Create **third workflow**: `ShopifyProductErrorHandler`

### Trigger
- **Error Trigger** node (built-in)

### Settings on main workflow
- Workflow Settings → **Error Workflow** → select `ShopifyProductErrorHandler`

### Error handler flow
```
Error Trigger
  → Google Sheets Update
      QA Status = FAILED
      Error Log = {{ $json.execution.error.message }}
```

Match row by `row_number` or `Product ID`.

---

## FIX 8 — Column name alignment

Your trigger sheet (`product_template`) uses Shopify export columns. Code node checks:

| Code expects | Trigger sheet has | Fix |
|--------------|-------------------|-----|
| `Image URL` | `Image Src` or `Product image URL` | Code already has fallback ✓ |
| `Brand` | `Vendor` | Update AI prompts to use `Vendor` |
| `Category` | `Product category` | Update prompts ✓ |
| `Raw Product Info` | `Description` | Update prompts |

In **Message a model1** QA prompt, change:
```
Brand: {{ $('Google Sheets Trigger').item.json.Vendor }}
Category: {{ $('Google Sheets Trigger').item.json['Product category'] }}
Raw Info: {{ $('Google Sheets Trigger').item.json.Description }}
```

---

## Corrected main flow (target)

```
Google Sheets Trigger (new/changed row)
  → Code (validate — image + description required)
  → Photoroom (remove background)
  → ImgBB (public URL)                    ← credential, not hardcoded
  → OpenAI Vision (analyze image + text)  ← gpt-4o + image URL
  → Update sheet (listing fields)
  → OpenAI QA (score + verify vs raw)     ← gpt-4o-mini OK here
  → Update sheet (AI Score, SEO, QA Status)
  → IF score >= 90?
      YES → Shopify Create (status=draft) → sheet PENDING_REVIEW
      NO  → sheet NEEDS_HUMAN_QA
```

---

## Priority order (do in this sequence)

1. Fix ImgBB credential (security) — 5 min
2. Fix `=={{` typos — 5 min
3. Change IF to 90 + false branch — 10 min
4. Shopify draft status — 5 min
5. Add Vision to Message a model — 20 min
6. Fix column names in prompts — 10 min
7. Error workflow — 15 min
8. Regenerate workflow — 30 min
