# Variants + Browserless — quick guide

## No variant lookup table needed

You do **not** maintain a separate “variants lookup” sheet. The workflow auto-detects the **Variant profile** (column E) from **LookupTables** using URL + Title keywords:

| Detected profile | Product examples | Shopify options |
|------------------|------------------|-----------------|
| `clothing_alpha` | Shirts, tees, dresses, jackets | Size + Color |
| `clothing_numeric` | Jeans, trousers, chinos | Waist + Length + Color |
| `footwear_uk` | Shoes, boots, sneakers | UK Size + Color |
| `one_size` | Bags, belts, hats | Color only |
| `generic` | Fallback | Size + Color |

Column E is a **formula** — you normally leave it alone.

## When scrape misses sizes

If the competitor page does not return sizes (common on Mango, Macy’s, etc.), the workflow still creates a **full size grid** using safe defaults:

| Profile | Default sizes |
|---------|---------------|
| `clothing_alpha` | XS, S, M, L, XL, XXL |
| `clothing_numeric` | Waist 30–38 × Length 30, 32 |
| `footwear_uk` | UK 7–11 |
| `generic` | S, M, L, XL |

Scraped sizes always win when present. Defaults apply only when **Sizes** and **Scraped variants** are both empty.

## How many colors to sell (LookupTables)

Add or edit rows on the **LookupTables** tab with `lookup_table = sell_colors_map`:

| lookup_table | keyword (column B) | notes (column N) |
|--------------|-------------------|------------------|
| sell_colors_map | clothing_alpha | Black, Navy, White, Beige |
| sell_colors_map | clothing_numeric | Black, Indigo, Khaki, Stone |
| sell_colors_map | footwear_uk | Black, Brown, White |

Column **Colors** on the product sheet is a **formula** that reads `sell_colors_map` using the **Variant profile** in column E.

- Edit the color list in **LookupTables → notes** to control how many colors you sell per profile.
- To override one product: delete the formula in **Colors** and type your list (e.g. `Black, Olive`).
- n8n does **not** write **Colors** during scrape — your lookup formula stays intact.

Priority when building Shopify variants:

1. **Colors** column (lookup formula or manual)
2. Colors inside **Scraped variants** JSON (if lookup empty)

## Browserless — do you need to set it?

**Yes, once in n8n** — it is not automatic without a credential.

| Step | Action |
|------|--------|
| 1 | Sign up at [browserless.io](https://www.browserless.io) and copy your API token |
| 2 | In n8n → Credentials → **HTTP Query Auth** |
| 3 | Name: `Browserless API` |
| 4 | Query parameter: `token` = your API key |
| 5 | Re-import `ShopifyProductAdd.V2.json` if you have not already |

### Auto-routing (no manual pick per site)

The workflow chooses the fetch path automatically:

| Path | When |
|------|------|
| **shopify_json** | Shopify stores (e.g. Everlane) — fastest |
| **http** | Normal sites (Aarong, most HTML pages) |
| **browser** | Known bot-protected domains: `mango.com`, `macys.com`, `express.com`, `zara.com`, `hm.com`, `asos.com`, etc. |

**Force browser** (column B) = `YES` forces Browserless on any URL.

### If Browserless is not configured

- Mango / Macy’s rows may show **Scrape Status** = `NEEDS_BROWSER` or partial data (image only).
- Fix: add the credential above, or paste **Product image URL** manually and set **Force browser** = `YES` on retry.

## Sheet columns you touch

| Column | You type? |
|--------|-----------|
| **A** Product URL | Yes |
| **B** Force browser | Optional (`YES` for hard sites) |
| **R** Prompt ID | Optional |
| **C–F, Colors** | Formulas — edit **LookupTables** instead |
| **Sizes** | Usually scrape; override manually if needed |

## Re-import checklist

After pulling the latest repo:

1. Re-import `sheet-products.csv` → **Master_Sheetv1** (keeps formulas)
2. Re-import `sheet-lookup-tables.csv` → **LookupTables** (includes `sell_colors_map`)
3. Re-import `ShopifyProductAdd.V2.json` in n8n
4. Confirm **Browserless API** credential exists
