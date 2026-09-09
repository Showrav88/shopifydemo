# Image, Stack & Cache — FAQ

Clear answers for the Fashion Shopify CSV Agent + UK test store project.

---

## 1. Images — how it actually works

### What are “hosted images”?

When you scrape a product page or Shopify `products.json`, the site already exposes **public image URLs** in metadata, for example:

- `products[].images[].src` (Shopify)
- JSON-LD `"image": "https://cdn.shopify.com/..."`
- Open Graph `og:image`

Anyone can open that URL in a browser. **No login, no download step required for v1.** You copy the URL into the Shopify CSV `Image Src` column.

```
Scrape product → imageUrls: [
  "https://cdn.store.com/shirt-front.jpg",
  "https://cdn.store.com/shirt-back.jpg"
] → pick 1–4 → paste into CSV
```

**Cost: £0. No Gemini. No tokens.**

---

### Can Gemini / AI Studio use those public URLs + name, color, description?

**Yes — two different jobs:**

| Job | What Gemini does | Input | Output | Cost type |
|-----|------------------|-------|--------|-----------|
| **A — Understand product** (multimodal) | Looks at reference image + text | Public image URL + title, color, description | Better tags, category, alt text | **Text tokens** (small) |
| **B — Create new images** (Imagen / image gen) | Generates new photos | Prompt built from name, color, description + optional reference URL | 1–4 new image files | **Per image** (not text tokens) |

**Job A** — optional, only when rules are unsure (e.g. category unknown).  
**Job B** — only when scraped images **< 1** OR you want extra lifestyle shots (up to 4 total).

Example prompt for **Job B** (image generation):

```
Men's navy cotton oxford shirt, smart casual, front flat lay on white background,
soft natural lighting, e-commerce product photo, no text, no watermark
Reference style similar to: [optional public URL]
```

Gemini/Imagen returns **new** image bytes → you **upload to your CDN** (S3, Cloudinary, Shopify Files) → put that stable URL in CSV.

---

### How do you get “a lot of images”? Do you need a photoshoot?

| Source | When to use | Photoshoot? |
|--------|-------------|-------------|
| **Scraped public URLs** | Supplier/competitor already has product photos | No |
| **AI generation** | Source has 0 images, or you want 2–4 consistent lifestyle shots | No |
| **Your own photos** | Public brand launch, copyright-safe catalog | Yes (later) |

**For your internal UK test store:** you do **not** need a studio or photoshoot.

1. Scrape 1–4 images per product from public metadata (free).
2. If a product has 0 images → Gemini generates **minimum 1**, up to **4**.
3. Import CSV into Shopify.

---

### Image count rules (min 1, max 4)

```
Step 1: Scrape imageUrls from site metadata
Step 2: ImageUrlSelector picks best 1–4 (HTTPS, big enough, not logo/banner)

IF scraped >= 1  → use scraped URLs in CSV (most products — FREE)
IF scraped == 0  → Gemini generates 1–4 from name + color + description
IF user wants more → generate up to (4 - scrapedCount) extra shots
```

**Shopify CSV:** first image on product row; extra images on extra rows (same Handle, blank Title).

---

### Copyright warning

| Store type | Scraped competitor images |
|------------|----------------------------|
| Internal test (password on) | Usually OK for testing |
| Public UK store | Risk — use AI-generated or owned photos |

---

## 2. Your algorithm vs n8n + Gemini (images + tokens)

### Text tokens (descriptions, tags, category)

| Approach | 100 products | Why |
|----------|--------------|-----|
| n8n + Gemini every step | 500k – 1M+ | AI runs 3–5× per product; repeats full HTML each node |
| n8n one AI node per product | 150k – 300k | Still AI on every product |
| **Your agent** | **30k – 80k** | Parse with code; AI only ~15% of products; batch 20 per call |
| Algo + hosted images only | **0** | No text AI at all |

### Image API calls (separate from text tokens)

| Approach | Image API calls (100 products) | Why |
|----------|-------------------------------|-----|
| n8n “AI everything” | 100–400 | Often generates images even when scrape already has URLs |
| **Your agent** | **0–15** | Use scraped URLs first; generate only when hosted count = 0 or user opts in |

**Important:** Image generation is billed **per image**, not as LLM text tokens. Your savings come from:

1. Not calling Gemini for prices, SKUs, variants, URLs (code does that).
2. Not generating images when scrape already has 1–4 URLs.
3. Batching text AI instead of one workflow execution per product.

---

## 3. JavaScript backend + Next.js frontend — is that OK?

**Yes.** The spec was written with C# because JewelryMS is C#. Your stack can be:

```
┌─────────────────────────────────────┐
│  Next.js (frontend)                 │
│  - Paste URL, preview products      │
│  - Edit before export               │
│  - Download CSV                     │
└──────────────┬──────────────────────┘
               │ REST API
┌──────────────▼──────────────────────┐
│  Node.js backend (JavaScript)       │
│  - Shop discovery + HTTP fetch      │
│  - Parsers (port from ProductComparison) │
│  - Rule engines + confidence score  │
│  - AI gate (Gemini SDK)             │
│  - ImageUrlSelector + optional Imagen │
│  - ShopifyCsvBuilder                │
└─────────────────────────────────────┘
```

Port `ProductComparison/*.cs` logic to JavaScript — same algorithm, different language.

**You do NOT need Pulse as a separate thing** unless you mean a specific Google product. Stack = **Next.js UI + Node API**.

---

## 4. Do you need MongoDB (or any database)?

### Short answer

| Use case | Database needed? |
|----------|------------------|
| One-time: paste URL → export CSV → done | **No** |
| Re-scrape same shops weekly, avoid re-fetching | **Yes — cache helps** |
| Team reviews products over days before export | **Yes** |
| Production agent with history | **Yes** |

### v1 recommendation (simplest path)

**No MongoDB for first version.**

```
User pastes URL → scrape in memory → process → download CSV
```

Session ends. No cache. Fastest to build.

### v2 when cache makes sense

Store each scrape as a document:

```json
{
  "sourceUrl": "https://brand.com",
  "platform": "shopify",
  "scrapedAt": "2026-09-09T08:00:00Z",
  "expiresAt": "2026-09-16T08:00:00Z",
  "products": [
    {
      "externalId": "123",
      "name": "Navy Oxford Shirt",
      "imageUrls": ["https://cdn.../1.jpg", "https://cdn.../2.jpg"],
      "variants": [...],
      "fieldConfidence": { "category": 0.95 }
    }
  ]
}
```

| Database | Good for |
|----------|----------|
| **SQLite** | Solo dev, file on disk, zero setup |
| **MongoDB** | Flexible JSON, same shape as scraped products |
| **PostgreSQL** | Same as JewelryMS, strong if you already use it |

**MongoDB is optional, not required.** Use it when you re-run imports and want to skip re-scraping unchanged products.

---

## 5. End-to-end image flow (one product)

```
1. User pastes: https://fashion-store.com/products/navy-shirt

2. Backend (NO AI):
   - Detect Shopify
   - GET /products/navy-shirt.json
   - Extract: name, price, variants, imageUrls[4]

3. ImageUrlSelector (NO AI):
   - Valid URLs: 3 found → pick top 3 (max 4)

4. Rules (NO AI):
   - category: Shirt, gender: Men, color: Navy

5. AI text (ONLY if description empty):
   - confidence.description = 0.3 → Gemini writes HTML body
   - ~500 tokens for this product only

6. AI images (ONLY if imageUrls.length === 0):
   - Prompt: "Men's navy cotton shirt, flat lay..."
   - Generate 1 image → upload to CDN → add URL
   - Per-image API cost, NOT text tokens

7. ShopifyCsvBuilder:
   - Image Src row 1: scraped or generated URL
   - Min 1, max 4 images

8. User downloads CSV → Shopify Admin → Import
```

**This product with 3 scraped images: 0 image API calls, possibly 0 text tokens.**

---

## 6. Quick decision chart

```
Do scraped imageUrls have >= 1 valid URL?
  YES → use them in CSV (stop — no image AI)
  NO  → Gemini generate 1–4 from metadata → re-host → CSV

Do we need text AI?
  ONLY IF description empty OR category confidence < 0.7

Do we need MongoDB?
  ONLY IF we cache scrapes or keep draft exports between sessions
```
