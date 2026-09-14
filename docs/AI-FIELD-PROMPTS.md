# Per-field AI prompts + inventory

## Control how each field is generated

Add these **optional** columns to your sheet. Leave blank to use defaults.

| Sheet column | Controls JSON key | Default if empty |
|--------------|-------------------|------------------|
| **Prompt Title** | `title` | UK fashion title, max 70 chars, colour + garment type |
| **Prompt Description** | `description_html` | HTML paragraphs, facts only, no invented specs |
| **Prompt Tags** | `tags` | Comma-separated, max 10 UK fashion keywords |
| **Prompt SEO title** | `seo_title` | Google title, max 60 chars |
| **Prompt SEO description** | `meta_description` | Meta snippet, max 160 chars |
| **Prompt Image alt** | `image_alt_text` | Accessibility alt for the product image |
| **Prompt Category** | `collection` | UK category path e.g. Men > Shirts > Casual |

### Copyright-safe rewrites (recommended)

Scraped title/description are **reference facts only**. AI must **paraphrase** before Shopify.

**Defaults already say:** rewrite in new words, do not copy competitor phrasing.

| Prompt Title | Prompt Description |
|--------------|-------------------|
| Completely new title. Never reuse competitor words. Max 60 chars. | Rewrite all sentences. Keep only material/colour/fit facts. Zero copied phrases. |

**QA score** fails if listing is too close to source text.

### Example — custom tone

| Prompt Title | Prompt Description |
|--------------|-------------------|
| Short punchy name for TikTok audience, max 50 chars, no brand name | *(leave empty = copyright-safe default)* |

The **AI write listing** node reads `ai_field_prompts` from **Active product row**.

### Where to edit in n8n

1. **Active product row** — builds `ai_field_prompts` from sheet + defaults
2. **AI write listing** — user message lists each key + its prompt

To change **defaults for all products**, edit the Code in **Active product row** (`defaults` object).

---

## Inventory (stock) — not from scrape

| Step | What happens |
|------|----------------|
| Scrape | Gets title, description, price, image, vendor, category — **no stock** |
| You | Type **Inventory quantity** on the sheet (e.g. `10`) |
| Create draft | Product created with `inventory_quantity: 0` |
| **Set Shopify inventory** | PUT variant with your sheet stock **after** draft exists |

If **Inventory quantity** is empty → Shopify gets `0`. Update the sheet and re-run, or set stock in Shopify admin.
