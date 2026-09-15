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

## Improving accuracy further (optional upgrades)

| Upgrade | When | How |
|---------|------|-----|
| Browserless node | Site is 100% client-rendered, no `__NEXT_DATA__` | Add before Prepare |
| Per-domain rules | Same supplier always | IF node + domain-specific Code |
| Shopify-only fast path | All URLs are Shopify | Skip AI when `shopify_json` OK |
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
