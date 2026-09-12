# Build Scope — Node + Next.js + SQLite (Always AI Images)

**Stack:** JavaScript (Node.js API) + Next.js frontend + SQLite cache + Gemini (text + image)  
**Image policy v1:** Always generate 1–4 clean images per product. Scraped URLs = reference only (logos/watermarks unusable).

---

## What you are building (MVP)

```
Next.js UI  →  Node API  →  SQLite  →  Gemini  →  CDN  →  Shopify CSV
```

| Layer | Tech | Job |
|-------|------|-----|
| Frontend | Next.js | Paste URL, preview products, trigger export |
| Backend | Node.js + Express/Fastify | Scrape, parse, rules, AI calls |
| Cache | **SQLite** (`fashion-agent.db`) | Jobs, products, generated image URLs |
| Text AI | Gemini API | Description/tags only when needed |
| Image AI | Gemini Imagen (or image API) | **Every product**, 1–4 shots |
| Storage | Cloudinary / S3 / local `uploads/` for dev | Host generated images |
| Output | Shopify Product CSV | Import to UK test store |

---

## Build phases and effort

Rough effort for **1 developer** familiar with Node + Next.js. Phases can overlap if 2 devs (one backend, one frontend).

| Phase | What you build | Effort | Depends on |
|-------|----------------|--------|------------|
| **0** | Repo setup, SQLite schema, env config | Small | — |
| **1** | HTTP fetch + platform detect (port `ShopDiscoveryService`) | Medium | Phase 0 |
| **2** | Parsers: Shopify (all variants), JSON-LD, WooCommerce | **Large** | Phase 1 |
| **3** | Fashion rules: category, gender, size, color + confidence | Medium | Phase 2 |
| **4** | `ShopifyCsvBuilder` + validator (min 1 max 4 images) | Medium | Phase 3 |
| **5** | Gemini text enrichment (batched, gated) | Small | Phase 3 |
| **6** | **Image pipeline: always generate 1–4** + CDN upload | **Large** | Phase 3 |
| **7** | Next.js: URL input, product table, export button | Medium | Phase 4–6 |
| **8** | End-to-end test: 10 products → CSV → Shopify import | Small | All |

### Total scope (1 dev, focused)

| Scope | Relative size |
|-------|----------------|
| **MVP** (Shopify parser + SQLite + always-generate 1 image + CSV + basic UI) | Core — build this first |
| **Full v1** (multi-variant + 1–4 images + text AI gate + fetch cache) | MVP + polish |
| **Skip for now** | MongoDB, Shopify Admin API upload, jewelry vertical |

**Biggest time sinks:**
1. Porting parsers to JavaScript (especially multi-variant Shopify)
2. Image generation pipeline (prompt templates, upload, retries, 1–4 shots)
3. Next.js preview/edit UI

**Fastest path to something working:** Phase 0 → 1 → 2 (Shopify only) → 6 (1 image only) → 4 → 7. Skip WooCommerce and text AI until Shopify path works.

---

## Revised cost per 100 products (always generate images)

| Item | Before (use scraped URLs) | Now (always AI images) |
|------|---------------------------|-------------------------|
| Text tokens | 30k – 80k | 30k – 80k (unchanged) |
| Image API calls | 0–15 | **100 – 400** (1–4 per product) |
| Logo/watermark risk | High | **None** |
| n8n + Gemini (comparison) | 500k+ tokens + 100–400 images | Your agent still wins on **text tokens** |

---

## SQLite vs no database

| | No DB | SQLite (recommended) |
|--|-------|---------------------|
| Re-open app next day | Re-scrape + re-generate all images (£$$) | Resume from cache |
| Failed image on product 47 | Start over | Retry product 47 only |
| Export CSV again | Re-run everything | Read from DB |
| Setup time | 0 | ~1 hour (schema + queries) |

**Use SQLite from day 1** — image generation is slow and costs money; you must not repeat it on every page refresh.

---

## Image generation detail (no logos)

### Input to image AI (per product)

```json
{
  "title": "Men's Navy Cotton Oxford Shirt",
  "gender": "Men",
  "category": "Shirt",
  "color": "Navy",
  "material": "Cotton",
  "description": "Smart casual button-down...",
  "referenceImageUrl": "https://competitor.com/shirt.jpg",
  "rules": [
    "no brand logos",
    "no watermarks",
    "no text on image",
    "white or neutral background",
    "professional e-commerce product photo"
  ],
  "shots": [
    { "type": "flat_lay", "count": 1 },
    { "type": "lifestyle", "count": 1 }
  ]
}
```

`referenceImageUrl` helps Gemini match **color and shape** — output image has **no competitor logo**.

### Storage flow

```
Gemini returns image bytes
  → save to uploads/ (dev) or Cloudinary (prod)
  → store cdn_url in SQLite generated_images
  → ShopifyCsvBuilder reads cdn_url for Image Src
```

---

## MVP checklist (build in this order)

- [ ] `npm` monorepo: `apps/web` (Next.js) + `apps/api` (Node)
- [ ] SQLite + migrations (`scrape_jobs`, `products`, `generated_images`)
- [ ] `POST /api/scrape` — URL in, products in DB
- [ ] Shopify parser with **all variants** (not first-only)
- [ ] `POST /api/generate-images/:jobId` — 1 image per product minimum
- [ ] CDN upload helper
- [ ] `GET /api/export/:jobId.csv` — Shopify format
- [ ] Next.js: paste URL → table → download CSV
- [ ] Test import into UK Shopify store

---

## What you are NOT building yet

- MongoDB / PostgreSQL
- Logo detection ML (you skip scraped URLs entirely)
- Automatic Shopify Admin upload
- WooCommerce + Daraz parsers (add after Shopify works)
- Mobile app
