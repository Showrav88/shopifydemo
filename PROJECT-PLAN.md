# Project Plan — UK Shopify Fashion Store + CSV Agent

**Updated:** September 9, 2026  
**Presenter / lead:** Showrav Karmakar  
**Store owner:** Ashik Bhai  
**Intention:** Internal UK test store for men's & women's fashion + automation to fill it from competitor/supplier sites.

---

## 1. What we are building (two tracks)

| Track | What | Status | Output |
|-------|------|--------|--------|
| **A — Shopify store** | UK sandbox store (Dawn theme, GBP, mobile-first) | Docs ready | Live `.myshopify.com` store |
| **B — Fashion CSV Agent** | Scrape sites → normalize → optional AI → Shopify CSV import | Spec + reference C# only | `.csv` → Shopify Admin import |

**Track B feeds Track A.** The agent is not a replacement for the store — it automates catalog creation.

```
Competitor URL → Algorithm parse (85%) → AI gap-fill (15%) → **Always AI-generate clean images (1–4)** → Shopify CSV → UK test store
```

---

## 2. Updated build order (aligned with intention)

### Phase 0 — Analysis (before code)
- [x] Client, location, customer analysis (UK, 22–45, mobile-first)
- [x] Shopify plan decision (Basic + Collaborators)
- [ ] Define 10–20 seed product URLs for parser testing
- [ ] Pick image AI provider (Gemini Imagen vs OpenAI vs reuse hosted only)

### Phase 1 — Shopify store shell (Track A)
- [ ] Create UK store (GBP, Basic)
- [ ] Dawn theme + brand from build kit prompts
- [ ] UK legal pages, Men/Women/Accessories nav
- [ ] Manual import of 5 test products (validate CSV format)

### Phase 2 — Core agent (Track B) — no AI
- [ ] `FashionCsvAgent.Core` project scaffold
- [ ] Port parsers from `ProductComparison/` (fix missing JewelryMS.Domain types)
- [ ] **Multi-variant Shopify parser** (current code only keeps first variant — must fix)
- [ ] `FashionCategoryNormalizer` + `fashion-categories.json`
- [ ] `ShopifyCsvBuilder` + `CsvValidator`
- [ ] CLI: `url in → csv out`

### Phase 3 — SQLite cache (from day 1)
- [ ] `fashion-agent.db` — tables: `scrape_jobs`, `products`, `generated_images`, `fetch_cache`
- [ ] Do not re-scrape or re-generate images on every page load
- [ ] See [docs/BUILD-SCOPE-SQLITE.md](./docs/BUILD-SCOPE-SQLITE.md)

### Phase 4 — AI image pipeline (always generate — v1 policy)
- [ ] Scraped `imageUrls` = **reference only** (competitor logos — never in CSV)
- [ ] Generate **1–4 clean images** per product via Gemini Imagen
- [ ] Prompt: metadata + "no logo, no watermark, no text"
- [ ] Optional reference URL for color/style match only
- [ ] Upload to CDN → store URL in SQLite → `Image Src` in CSV
- [ ] Template alt text: `{Color} {Category} for {Gender}`

### Phase 5 — AI text enrichment (minimal tokens)
- [ ] `ConfidenceScorer` — only call AI when field confidence < 0.7
- [ ] `AiEnrichmentService` — batched, 20 products per call, JSON response
- [ ] Fields: description, category, gender, tags, SEO (only if needed)
- [ ] Token budget cap per run + logging

### Phase 6 — Next.js UI + team workflow
- [ ] Preview table, edit before export
- [ ] Jira `SHOP` tickets for agent features
- [ ] Excel tracker: source URLs, image counts, token usage per run

---

## 3. Image strategy (1 minimum, 4 maximum) — **always AI-generate**

**Problem:** Scraped images usually have **competitor brand logos / watermarks** — cannot use in your store.

**v1 policy:** Never put scraped URLs in Shopify CSV. Always generate clean images.

| Step | What | Cost |
|------|------|------|
| 1 | Scrape metadata (name, color, description, variants) | Free (algorithm) |
| 2 | Scrape `imageUrls` | **Reference only** — sent to Gemini, not CSV |
| 3 | AI generate 1–4 clean shots (no logo, no text) | Image API per shot |
| 4 | Upload to your CDN → SQLite → CSV `Image Src` | Storage cost |
| 5 | Alt text from template | Free |

```
FOR each product:
  referenceUrl = first scraped image (optional, for color/style)
  generate 1–4 new images from metadata + reference
  CSV uses ONLY your CDN URLs
```

### What goes into AI image prompt (metadata only — not full page)

```json
{
  "title": "Men's Navy Cotton Oxford Shirt",
  "gender": "Men",
  "category": "Shirt",
  "color": "Navy",
  "material": "Cotton",
  "style": "Smart casual",
  "referenceImageUrl": "https://source.com/original.jpg",
  "shotsNeeded": 2,
  "shotTypes": ["front flat lay", "worn lifestyle"]
}
```

### Important legal note
- Scraped competitor images may have **copyright risk** for a public store
- For **internal testing**, hosted URLs in CSV are fine
- For **public launch**, re-host only licensed/owned images or AI-generated originals

---

## 4. What you are missing today (gap analysis)

### Already have
- UK Shopify build kit + presentation
- Full technical spec (`fashion-shopify-csv-agent-spec.md`)
- Reference parsers for Shopify, WooCommerce, Daraz, StoreX, JSON-LD
- Token-minimal AI strategy documented
- Team workflow (Jira + Excel)

### Missing — must build

| Gap | Impact | Priority |
|-----|--------|----------|
| Runnable C# project (`.csproj`) | Cannot compile or run parsers | P0 |
| Multi-variant fashion parser | CSV wrong for Size × Color | P0 |
| `ShopifyCsvBuilder` | No export | P0 |
| `fashion-categories.json` | Rules still jewelry-focused | P0 |
| `ImageUrlSelector` (1–4 cap) | Image column inconsistent | P1 |
| `AiEnrichmentService` | No text gap-fill | P1 |
| `ImageGenerationGate` | No AI images when source empty | P2 |
| Image re-hosting / CDN | Generated images need stable URLs | P2 |
| Unit tests + fixtures | Regressions on parser changes | P1 |
| React/CLI UI | Only spec, no interface | P2 |
| Live Shopify store | Track A not started | P0 |
| Copyright / image rights policy | Legal risk if store goes public | P2 |

### Missing — process / ops

| Gap | Notes |
|-----|-------|
| Seed URL list | Need 10–20 real fashion product URLs to test parsers |
| Token budget per run | Cap e.g. 100k tokens/run in config |
| Image API budget | Separate from text tokens — track per product |
| QA device matrix | Mobile/laptop checkout testing (in presentation) |
| Error handling for blocked scrapes | Rate limits, Cloudflare, 403 |

---

## 5. Pros and cons — full situation

### Your approach (algorithm-first + gated AI)

**Pros**
- ~85% products need **zero** text AI tokens
- Batched calls (20 products) vs one call per product per field
- Parsers work offline — no API cost for structured Shopify/WC JSON
- Reuses proven JewelryMS pipeline
- Image URLs from metadata = free (no generation cost)
- Predictable cost — you control when AI runs
- Same codebase for jewelry, shoes later (swap rule JSON)

**Cons**
- Requires building and maintaining C# parsers
- Scraping breaks when sites change layout
- First variant only in current ported code — must fix before fashion
- Image generation is a separate pipeline you haven't built yet
- No visual workflow editor (unlike n8n)
- Team needs .NET dev skills

### n8n + Gemini API (everything through AI)

**Pros**
- Visual workflow — non-devs can change flows
- Fast to prototype one product URL
- Gemini multimodal can see page HTML + images in one call
- Good for experiments and one-off automations
- Large connector ecosystem (Shopify, HTTP, Google Sheets)

**Cons**
- **Much higher token usage** — typical flow runs AI per product per step
- Every node often re-sends full product context (title, HTML, images description)
- 100 products × 5 AI nodes × ~2k tokens ≈ **1M tokens** vs your **30k–80k**
- Image generation via Gemini/Imagen = **separate billing**, not cheaper
- Scraping + parsing in n8n still needs HTTP nodes — not smarter than your parsers
- Harder to version-control business rules (category keywords)
- Workflow JSON in git is messy compared to `fashion-categories.json`
- Rate limits and retries harder to manage at scale

---

## 6. Token usage: your algorithm vs n8n + Gemini

### Typical 100-product fashion import

| Approach | Text tokens (est.) | Image API calls | Total cost profile |
|----------|-------------------|-----------------|-------------------|
| **n8n naive** (AI every step, every product) | 500k – 1M+ | 100–400 if generating images | **Highest** |
| **n8n semi-smart** (AI per product, one combined prompt) | 150k – 300k | 100–400 | High |
| **Your spec: algo + batched AI gaps** | **30k – 80k** | 0–15 (only missing images) | **Lowest** |
| **Your spec: algo only, hosted images** | **0** | 0 | **Free** |

### Why your approach uses fewer tokens

| Factor | n8n + Gemini | Your algorithm |
|--------|--------------|----------------|
| Platform detection | Often sent to AI | HTTP probes — 0 tokens |
| Price, SKU, variants | Often sent to AI | JSON parse — 0 tokens |
| Image URLs | May describe images to AI | Direct URL extract — 0 tokens |
| Category | AI every product | Keyword rules — 0 tokens for ~85% |
| Description | AI every product | Use `body_html` when present; AI only if short |
| Batching | Usually 1 product per execution | 20 products per API call |
| Context repetition | High (each node repeats input) | Low (only missing fields in prompt) |

### When n8n + Gemini is better
- One-off: "scrape this one weird site today"
- Non-technical team owns the workflow
- Site has zero structured data and you accept high token cost
- You need quick glue between 5 SaaS tools without coding

### When your approach is better (your case)
- Repeated imports from Shopify/WooCommerce fashion sites
- 100+ products per run
- Internal test store with cost control
- Same pipeline for jewelry/shoes later
- **You already have the parser code** — n8n would redo this worse

### Recommended hybrid (best of both)
- **Your C# agent** = production pipeline (parse, rules, CSV, gated AI)
- **n8n** = optional trigger only (webhook on new URL → call your API → notify Slack)
- **Do not** put parsing or category logic inside n8n AI nodes

---

## 7. Image generation decision matrix

| Scenario | Action | AI images? |
|----------|--------|------------|
| Shopify source, 4+ images scraped | Use top 4 hosted URLs | No |
| Shopify source, 1 image scraped | Use 1 hosted + optionally generate 1–3 more | Optional |
| HTML-only site, 0 images | Generate minimum 1 from metadata | **Yes (required)** |
| User wants consistent brand style | Generate lifestyle shots from metadata + reference | Yes (1–4) |
| Internal test only | Hosted URLs enough | No |

**Token rule:** Image generation uses **image API credits**, not LLM text tokens. Keep text AI separate from image AI in budget tracking.

---

## 8. Immediate next actions

| # | Action | Owner | Track |
|---|--------|-------|-------|
| 1 | Create Shopify UK store (Basic) | Ashik Bhai | A |
| 2 | Scaffold `FashionCsvAgent.Core` + fix variant parser | Dev | B |
| 3 | Add `fashion-categories.json` (replace jewelry rules) | Dev | B |
| 4 | Build `ImageUrlSelector` (min 1, max 4) | Dev | B |
| 5 | Collect 10 test product URLs (Shopify + WC + HTML) | Team | B |
| 6 | First CSV export → manual Shopify import test | Dev + QA | A+B |
| 7 | Add `AiEnrichmentService` with token cap | Dev | B |
| 8 | Add `ImageGenerationGate` (Phase 5) | Dev | B |

---

## 9. File map (after pull)

| Path | Purpose |
|------|---------|
| `shopify-uk-build-kit/` | Store setup prompts |
| `presentation/presentation.html` | Team kickoff deck |
| `fashion-shopify-csv-agent-spec.md` | Full agent technical spec |
| `ProductComparison/*.cs` | Reference parsers (port from JewelryMS) |
| `PROJECT-PLAN.md` | This file — master plan |
