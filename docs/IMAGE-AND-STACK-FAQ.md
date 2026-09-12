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

### Copyright warning + brand logos on images

| Problem | Reality |
|---------|---------|
| Competitor images have **brand logo / watermark** | Very common — cannot use in your store |
| Scraped URL in Shopify CSV | Shows their branding on your product |
| **Your decision (v1)** | **Always AI-generate clean images** — do not put scraped URLs in CSV |

**Scraped images are still useful** — but only as **reference input** to Gemini (multimodal), not as final `Image Src`:

```
Scrape imageUrl (has logo)  →  send to Gemini as reference only
                            →  Gemini generates NEW clean image (no logo)
                            →  upload to YOUR CDN
                            →  put YOUR URL in Shopify CSV
```

**Per product:** generate **1–4 new images** from metadata (+ optional reference for color/style).  
**Never** ship scraped competitor URLs to Shopify.

---

## 1b. Always-generate image flow (your v1 policy)

```
For each product:
  1. Scrape metadata (name, color, description, variants)     ← algorithm, 0 tokens
  2. Scrape imageUrls (may have logos)                          ← reference only, NOT for CSV
  3. Build prompt from: title, gender, category, color, material
  4. Optional: pass 1 reference URL to Gemini multimodal        ← small text tokens
  5. Generate 1–4 clean shots (flat lay, front, detail, lifestyle)
  6. Upload to CDN (S3 / Cloudinary / local folder for dev)
  7. CSV Image Src = YOUR hosted URLs only
```

### Shot types to generate (pick 1–4)

| # | Shot | Prompt idea |
|---|------|-------------|
| 1 | Front flat lay | Product on white, no text, no logo, e-commerce |
| 2 | Worn / lifestyle | Model or mannequin, neutral background |
| 3 | Detail | Fabric texture, buttons, stitching close-up |
| 4 | Angle / back | Side or back view |

### Cost when always generating (100 products)

| Item | Estimate |
|------|----------|
| Text tokens (metadata + optional reference look) | 30k – 80k (same as before) |
| **Image API calls** | **100 – 400** (1–4 images × 100 products) |
| Scraped URLs used in CSV | **0** (never) |

Still cheaper on **text** than n8n. Image cost is higher than “use scraped URLs” but **legally and visually correct** for your store.

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

### v1 recommendation: **SQLite only** (no MongoDB)

SQLite is enough for this project. One file on disk, zero server setup, works on laptop and cloud.

```
fashion-agent.db   ← single SQLite file
```

**Why SQLite fits:**
- Scraped product JSON fits in TEXT/JSON columns
- Generated image URLs + job status per product
- Re-run export without re-scraping or re-generating images
- No MongoDB install, no Atlas account, no extra cost

**You do NOT need MongoDB** unless you scale to multiple servers writing cache at the same time (not v1).

### SQLite tables (minimal)

```sql
-- One row per scrape job (user pastes shop URL)
CREATE TABLE scrape_jobs (
  id            TEXT PRIMARY KEY,
  source_url    TEXT NOT NULL,
  platform      TEXT,
  status        TEXT,          -- pending | scraped | images_done | exported
  created_at    TEXT,
  updated_at    TEXT
);

-- Parsed products (metadata from scrape — NOT final images)
CREATE TABLE products (
  id              TEXT PRIMARY KEY,
  job_id          TEXT REFERENCES scrape_jobs(id),
  external_id     TEXT,
  name            TEXT,
  description     TEXT,
  gender          TEXT,
  category        TEXT,
  colors          TEXT,          -- JSON array
  variants_json   TEXT,          -- JSON
  reference_urls  TEXT,          -- scraped URLs (logo — reference only)
  field_confidence TEXT,         -- JSON
  created_at      TEXT
);

-- AI-generated images (YOUR clean URLs for CSV)
CREATE TABLE generated_images (
  id           TEXT PRIMARY KEY,
  product_id   TEXT REFERENCES products(id),
  shot_index   INTEGER,          -- 1–4
  shot_type    TEXT,             -- flat_lay | lifestyle | detail | angle
  cdn_url      TEXT NOT NULL,    -- goes in Shopify CSV
  prompt_used  TEXT,
  created_at   TEXT
);

-- Optional: cache raw HTTP response to skip re-fetch
CREATE TABLE fetch_cache (
  url          TEXT PRIMARY KEY,
  body         TEXT,
  fetched_at   TEXT,
  expires_at   TEXT
);
```

### When each table is used

| Step | SQLite |
|------|--------|
| User pastes URL | Insert `scrape_jobs` |
| Parser runs | Insert `products` + `reference_urls` |
| Gemini generates images | Insert `generated_images` with `cdn_url` |
| User exports CSV | Read `products` + `generated_images` |
| User re-opens tomorrow | Skip scrape if `fetch_cache` still valid |

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
