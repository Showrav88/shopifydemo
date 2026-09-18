# Production scrape architecture (n8n + JavaScript)

How this workflow scrapes product pages — and how that compares to what e-commerce / automation teams typically do in **n8n + JS** (no separate Python at runtime).

## Industry pattern (n8n + Code node)

Most production n8n scrapers use a **layered stack**, not “AI reads the whole page”:

| Tier | Method | Trust | Cost |
|------|--------|-------|------|
| 1 | **Shopify `.json` API** | Highest | Free HTTP |
| 2 | **Schema.org JSON-LD** (`Product`) | Very high | Code node |
| 3 | **OpenGraph / meta product tags** | High | Code node |
| 4 | **Platform payloads** (`__NEXT_DATA__`, embedded JSON) | High | Code node |
| 5 | **HTML heuristics** (image URL regex, price near currency) | Medium | Code node |
| 6 | **AI enrichment** | Fills gaps only | OpenAI tokens |

Companies like **e-commerce ops teams**, **price monitoring startups**, and **PIM (product information management)** vendors follow this order because:

- Structured data is **faster and cheaper** than LLM calls
- AI **hallucinates** prices/images if it is the only source
- Code extraction is **repeatable** and testable in git

### What n8n does NOT usually use in Code nodes

- **Python at runtime** — n8n Code nodes run **JavaScript** (or Python in newer n8n, but JS is standard)
- **Cheerio** — available on some self-hosted n8n installs via `require('cheerio')`; we use regex + JSON parsing for cloud compatibility
- **Headless browser** — Browserless / Playwright nodes for heavy JS sites (Aarong works without it because images are in `__NEXT_DATA__`)

### What the `.py` files in this repo are

`scripts/patch-production-scrape.py` and `scripts/n8n-scrape-extractors.js` are **developer tools**:

```
n8n-scrape-extractors.js  →  logic source of truth (testable with Node)
patch-production-scrape.py →  injects JS into ShopifyProductAdd.V2.json
ShopifyProductAdd.V2.json  →  you import into n8n
```

**Python never runs when you paste a Product URL.** Only n8n runs.

---

## Our node pipeline

```
Product URL (sheet)
    ↓
Validate sheet row          [JS] pick row, SKU, needs_scrape
    ↓
Fetch product page          [HTTP] download HTML (browser-like headers)
    ↓
Prepare page for scrape     [JS] production extractor (tiers 1–5)
    ↓                         + optional Shopify .json fetch
AI scrape product           [OpenAI] fill gaps only (tier 6)
    ↓
Apply scraped data          [JS] merge structured + AI (structured wins)
    ↓
Prepare sheet scrape write  [JS] clean columns for Google Sheets
    ↓
Update sheet scraped        [Sheets API]
```

---

## Prepare page for scrape (core)

Source: `scripts/n8n-scrape-extractors.js`

Builds `scrape_context.structured`:

```json
{
  "title": "Black Cotton T-Shirt",
  "image_url": "https://mcprod.aarong.com/media/catalog/product/...jpg",
  "competitor_price": "1290",
  "competitor_currency": "BDT",
  "candidate_images": ["..."],
  "_sources": {
    "title": "json_ld",
    "image_url": "heuristic"
  }
}
```

### Per-site behaviour

| Site type | Primary tier | Example |
|-----------|--------------|---------|
| Shopify store | `shopify_json` | `.../products/foo.json` |
| WooCommerce | `json_ld` + `wp-content/uploads` | easyfashion.com.bd |
| Magento / Aarong | `next_data` + `catalog/product` images | aarong.com |
| Generic | `open_graph` + heuristics | most blogs |

---

## Apply scraped data (merge rules)

1. **Structured extract wins** over AI for title, price, image, vendor, SKU
2. **AI fills** empty fields (tags, colors, description polish)
3. **Image URL** must pass `isDirectImageUrl()` — rejects `.html` page URLs
4. **Scrape Status** = `SCRAPED` or `SCRAPED_NO_IMAGE` if image missing

---

## HTTP vs Browserless — when to use which

**Do not use Browserless for every site.** It is 10–30× slower and costs credits. Use a **smart router**:

```
Product URL
    ↓
Route scrape method          [Code] pickFetchStrategy(url)
    ↓
┌─────────────────┬──────────────────────┬─────────────────────────┐
│ shopify_json    │ http (default)       │ browser (hard domains)  │
│ Try .json API   │ Fetch product page   │ Browserless content API │
│ HTML optional   │ [HTTP Request]       │ [HTTP Request]          │
└────────┬────────┴──────────┬───────────┴────────────┬────────────┘
         └───────────────────┴────────────────────────┘
                             ↓
                  Prepare page for scrape
                             ↓
              needsBrowserRetry? ──YES──→ Browserless (retry once)
                             NO
                             ↓
                    AI scrape → Apply → Sheet
```

### Site classification

| Category | Examples | Method | Why |
|----------|----------|--------|-----|
| **Shopify .json works** | Everlane, MATE the Label, Gymshark | `shopify_json` or `http` | `product.json` has title, images, variants — no browser |
| **HTTP + embedded JSON** | Aarong, many Magento/WooCommerce | `http` | `__NEXT_DATA__`, JSON-LD, `catalog/product` images in HTML |
| **HTTP works, .json blocked** | Fashion Nova (Hydrogen) | `http` | HTML has og:image + meta; `.json` returns login page |
| **Browser required** | Macy's, Mango, Express, Zara | `browser` | Cloudflare bot check + 100% client-rendered |
| **Browser maybe** | Lululemon | `http` first → retry `browser` if no image | SPA; sometimes og:image in initial HTML |

### Decision rules (in code)

Source: `scripts/n8n-scrape-extractors.js`

```javascript
SCRAPE.pickFetchStrategy(url)
// → 'shopify_json' | 'http' | 'browser'

SCRAPE.needsBrowserRetry(structured, html, url)
// → true if HTTP got bot-blocked or missing title+image
```

| Signal | Action |
|--------|--------|
| URL is `/products/...` on known Shopify store | Try `.json` first — **skip browser** |
| `shopify_json` returned title + image | **Done** — never open browser |
| HTML contains `checking your browser` / `cf-challenge` | **Browserless** |
| HTTP returned page but no title and no image | **Browserless retry** (once) |
| Domain in `BROWSER_DOMAINS` list | **Browserless** immediately |

### How to add Browserless in n8n

1. Sign up at [browserless.io](https://www.browserless.io) (free tier: ~1,000 sessions/month)
2. Add credential: HTTP Header Auth or query token
3. Add **HTTP Request** node (only on browser path):

```
POST https://production-sfo.browserless.io/content?token=YOUR_TOKEN
Content-Type: application/json

{
  "url": "={{ $json.source_product_url }}",
  "gotoOptions": {
    "waitUntil": "networkidle2",
    "timeout": 30000
  }
}
```

Response body = full rendered HTML → pass to **Prepare page for scrape** (same as HTTP fetch).

4. Wire workflow:

```
Needs scrape (TRUE)
  → Route scrape method [Code]
  → Switch / IF:
       browser  → Browserless fetch → Prepare page
       default  → Fetch product page → Prepare page
  → IF needsBrowserRetry → Browserless fetch → Prepare page (merge)
  → AI scrape → Apply → Sheet
```

### Cost comparison (per product)

| Method | Speed | Cost |
|--------|-------|------|
| Shopify `.json` | ~1 s | Free |
| HTTP fetch | ~2 s | Free |
| Browserless | ~10–30 s | ~1 credit/session |

**Target:** 80%+ of your fashion URLs should never touch Browserless.

---

## Improving accuracy further (optional upgrades)

| Upgrade | When | How |
|---------|------|-----|
| Browserless node | `pickFetchStrategy` = `browser` OR `needsBrowserRetry` | HTTP Request to Browserless content API |
| Per-domain rules | Same supplier always | Extend `BROWSER_DOMAINS` / `SHOPIFY_JSON_DOMAINS` in extractors |
| Shopify-only fast path | `.json` returns full product | Skip AI when `shopify_json` OK |
| Rate limiting | Many URLs | n8n Wait node + queue sheet |

---

## How to update scrape logic

1. Edit `scripts/n8n-scrape-extractors.js`
2. Test locally: `node -e "const S=require('./scripts/n8n-scrape-extractors.js'); ..."`
3. Run `python3 scripts/patch-production-scrape.py`
4. Commit + re-import `ShopifyProductAdd.V2.json` into n8n

---

## Mental model

| You think… | Reality |
|------------|---------|
| Python scrapes websites | Python only **patches** the workflow file |
| AI does the scraping | **JS code** extracts; AI **fills gaps** |
| One method fits all sites | **Layered stack** with merge priority |
| n8n talks to Python | n8n nodes pass **JSON** to each other |
