# Every sheet key — what it does

## YOU type (input)

| Sheet column | Required? | Used for | Goes to Shopify? |
|--------------|-----------|----------|------------------|
| **Product URL** | Start here | Triggers scrape | No (reference only) |
| **Price** | Before publish | **Your UK sell price** | Yes — **after** draft create |
| **Inventory quantity** | Before publish | Stock you ordered | Yes — **after** draft create |
| **SKU** | Recommended | Row match key | Yes — variant SKU |
| **Prompt Title** … **Prompt Category** | Optional | How AI writes each field | Via AI output |
| Product image URL | Manual mode | Image for Photoroom | Image upload |
| Description / Title | Manual mode | AI facts | Via AI listing |
| Vendor | Optional | Brand | Yes — `vendor` |
| Product category | Optional | Type/category | Yes — `product_type` |

## Scrape writes (competitor reference — NOT your shop price)

| Sheet column | Source | Shopify? |
|--------------|--------|----------|
| **Competitor price** | Scraped from URL page | **No** — reference only |
| **Competitor currency** | e.g. GBP, USD, BDT | **No** |
| **Sizes** | e.g. `S, M, L, XL` | No (v1: single variant; sizes stored for you) |
| **Colors** | e.g. `Blue, Black` | No (reference) |
| **Scraped variants** | JSON of size/color/sku from page | No (reference for future multi-variant) |
| Title, Description, Product image URL, Vendor, Product category, Tags | Scrape + AI | Yes — via listing |
| Scrape Status | `SCRAPED` | No |
| Source Product URL | URL that was scraped | No |

## AI listing writes

| Sheet column | Shopify field |
|--------------|---------------|
| Title | `product.title` |
| Description | `product.body_html` |
| Tags | `product.tags` |
| SEO title | metafield / theme |
| SEO description | metafield / theme |
| Image alt text | image alt |

## QA writes

| Sheet column | Meaning |
|--------------|---------|
| QA Status | PASS / PASS_NO_IMAGE / FAIL |
| AI Score | 0–100 |

## Shopify writes

| Sheet column | Meaning |
|--------------|---------|
| URL handle | product handle |
| Shopify Product URL | your store product link |
| Shopify Image URL | CDN image |
| Generated Image URL | ImgBB staging URL |
| Status | `draft` |

---

## Shopify API keys (Create a product API)

| JSON key | Sheet / source |
|----------|----------------|
| `product.title` | AI write listing → `title` |
| `product.body_html` | AI → `description_html` |
| `product.vendor` | Vendor |
| `product.product_type` | Product category |
| `product.tags` | AI → `tags` |
| `product.status` | always `draft` |
| `variants[0].sku` | SKU |
| `variants[0].price` | `0` at create → **Set Shopify price and stock** |
| `variants[0].inventory_quantity` | `0` at create → **Set Shopify price and stock** |

## Set Shopify price and stock (after draft)

| JSON key | Sheet column |
|----------|--------------|
| `variant.price` | **Price** (your sell price) |
| `variant.inventory_quantity` | **Inventory quantity** |

---

## Size / multi-variant (v1 limit)

| What | Today |
|------|--------|
| Scrape | Reads all sizes/colors → **Sizes**, **Colors**, **Scraped variants** columns |
| Shopify create | **One variant** per row (default title) |
| Multi-size shop | Future: one row per size OR GraphQL multi-variant |

---

## Typical workflow

```
1. Paste Product URL          → scrape fills competitor price + sizes + description
2. You set Price              → your margin (not competitor price)
3. You set Inventory quantity → stock you ordered
4. Run completes              → draft on Shopify + price + stock applied
```

If **Price** or **Inventory** empty at run time → Shopify gets `0` until you fill sheet and re-trigger.
