#!/usr/bin/env python3
"""Inject production scrape pipeline into ShopifyProductAdd.V2.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTORS = (ROOT / "scripts" / "n8n-scrape-extractors.js").read_text()
EXTRACTORS = re.sub(r"\nif \(typeof module.*", "", EXTRACTORS)
EXTRACTORS = EXTRACTORS.replace("const SCRAPE_EXTRACTORS = {};", "const SCRAPE = {};")
EXTRACTORS = EXTRACTORS.replace("SCRAPE_EXTRACTORS.", "SCRAPE.")

PREPARE_WRAPPER = r"""
const row = $('Validate sheet row').first().json;
const http = $input.first().json;
const productUrl = row.source_product_url || row['Product URL'] || '';
let body = http.data ?? http.body ?? '';

if (typeof body !== 'string') {
  try { body = JSON.stringify(body); } catch { body = String(body); }
}

async function tryShopifyJson(url) {
  const jsonUrl = SCRAPE.shopifyJsonUrl(url);
  if (!jsonUrl) return null;
  try {
    const res = await this.helpers.httpRequest({
      method: 'GET',
      url: jsonUrl,
      json: true,
      timeout: 15000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept: 'application/json',
      },
    });
    return SCRAPE.normalizeShopifyProduct(res, url);
  } catch {
    return null;
  }
}

const shopifyLayer = await tryShopifyJson(productUrl);
const structured = SCRAPE.buildStructuredProduct(body, productUrl, shopifyLayer);
const candidateImages = structured.candidate_images || [];

const scrapeMethod = http.scrape_method || row.scrape_method_planned || row.fetch_method || 'http';

const snippet = {
  product_url: productUrl,
  run_id: row._run_id,
  structured,
  extraction_sources: structured._sources || {},
  scrape_method: scrapeMethod,
  bot_protection_bypassed: Boolean(http.bot_protection_bypassed),
  bot_protection_expected: Boolean(row.bot_protection_expected),
  og_title: structured.title || SCRAPE.meta(body, 'og:title'),
  og_description: structured.description || SCRAPE.meta(body, 'og:description'),
  og_image: structured.image_url || SCRAPE.meta(body, 'og:image'),
  candidate_images: candidateImages.slice(0, 10),
  json_ld: SCRAPE.extractJsonLd(body).slice(0, 3),

const scrapeMethod = http.scrape_method || row.scrape_method_planned || row.fetch_method || 'http';
snippet.scrape_method = scrapeMethod;
snippet.bot_protection_bypassed = Boolean(http.bot_protection_bypassed);
snippet.bot_protection_expected = Boolean(row.bot_protection_expected);

  html_excerpt: body.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/\s+/g, ' ').slice(0, 8000),
};

return [{ json: { ...row, scrape_context: snippet } }];
"""

AI_SYSTEM = (
    "You extract product data from a scraped web page for UK fashion e-commerce.\n"
    "IMPORTANT: structured_extract is pre-parsed by code (high accuracy). "
    "Use structured_extract values AS-IS when present. Only fill fields that are empty/null.\n"
    "Use ONLY facts present in structured_extract, JSON-LD, OpenGraph, or HTML excerpt.\n"
    "Do NOT invent specs. Do NOT copy from memory or prior products.\n"
    "competitor_price = their listed price (reference only). competitor_currency = ISO code e.g. GBP, USD, BDT.\n"
    "Do NOT set our sell price or stock.\n"
    "image_url MUST be a direct image file URL (.jpg/.png/.webp) from candidate_images or structured_extract — "
    "NEVER use the product page URL.\n"
    "Return ONLY valid JSON (no markdown):\n"
    "{\n"
    '  "title": "",\n'
    '  "description_plain": "",\n'
    '  "competitor_price": "",\n'
    '  "competitor_currency": "",\n'
    '  "image_url": "",\n'
    '  "vendor": "",\n'
    '  "product_category": "",\n'
    '  "tags": "",\n'
    '  "sizes": [],\n'
    '  "colors": [],\n'
    '  "variants": [{"size": "", "color": "", "sku": "", "price": ""}]\n'
    "}"
)

AI_USER_SUFFIX = (
    "\nstructured_extract (TRUST FIRST — code-parsed):\n"
    "{{ JSON.stringify($json.scrape_context.structured) }}"
)

APPLY_MERGE_BLOCK = r"""
const structured = row.scrape_context?.structured || {};
const category = SCRAPE.mergeField(structured, scraped, 'product_category', ['category']) || row.validated_category || '';
let sku = String(structured.sku || row.SKU || row.validated_sku || row.processing_sku || '').trim();
if (!sku) sku = generateSku(category);
const competitorPrice = SCRAPE.mergeField(structured, scraped, 'competitor_price', ['price', 'variant_price']);
const competitorCurrency = SCRAPE.mergeField(structured, scraped, 'competitor_currency', ['currency']);
const imageUrl = SCRAPE.pickImageUrl(scraped, row);
const title = SCRAPE.mergeField(structured, scraped, 'title') || row.Title || '';
const description = SCRAPE.mergeField(structured, scraped, 'description_plain', ['description']) || row.Description || '';
const vendor = SCRAPE.mergeField(structured, scraped, 'vendor', ['brand']) || row.validated_vendor || '';
const tags = scraped.tags || '';
const sizesArr = structured.sizes || scraped.sizes || [];
const sizes = Array.isArray(sizesArr) ? sizesArr.join(', ') : String(sizesArr || '');
let colorsArr = structured.colors?.length ? structured.colors : (scraped.colors || []);
if ((!colorsArr || colorsArr.length === 0) && (structured.variants || scraped.variants)) {
  const vars = structured.variants || scraped.variants || [];
  colorsArr = [...new Set(vars.map((v) => v.color).filter(Boolean))];
}
const colors = Array.isArray(colorsArr) ? colorsArr.join(', ') : String(colorsArr || '');
const lengthsArr = structured.lengths?.length ? structured.lengths : (scraped.lengths || []);
const lengths = Array.isArray(lengthsArr) ? lengthsArr.join(', ') : String(lengthsArr || '');
const scrapedVariants = JSON.stringify(structured.variants || scraped.variants || []);
const extractionSources = structured._sources || {};
"""


def build_apply_js(extractors: str) -> str:
    sku_block = r"""function categoryCode(category) {
  const raw = String(category || '').trim();
  if (!raw) return 'GEN';
  const words = raw.split(/[\s>|/,\-\u2013]+/).map((w) => w.replace(/[^a-zA-Z]/g, '')).filter((w) => w.length > 0);
  if (words.length === 0) return 'GEN';
  if (words.length >= 2) {
    const code = (words[0].slice(0, 2) + words[words.length - 1].slice(0, 2)).toUpperCase();
    return code || 'GEN';
  }
  return words[0].slice(0, 4).toUpperCase() || 'GEN';
}
function randomSkuSuffix(length = 6) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let out = '';
  for (let i = 0; i < length; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}
function generateSku(category) {
  return `${categoryCode(category).slice(0, 4)}-${randomSkuSuffix(6)}`;
}

const row = $('Prepare page for scrape').first().json;
const ai = $input.first().json;
let text = ai.output?.[0]?.content?.[0]?.text || ai.text || ai.message?.content || '';
text = String(text).replace(/```json|```/g, '').trim();
let scraped;
try {
  scraped = JSON.parse(text);
} catch (e) {
  throw new Error(`AI scrape returned invalid JSON: ${text.slice(0, 300)}`);
}
"""
    tail = r"""
const sheetPrice = row['Price'] ?? row.validated_price;
const sellPrice = sheetPrice === '' || sheetPrice === null || sheetPrice === undefined ? null : String(sheetPrice);
const sheetInv = row['Inventory quantity'] ?? row.validated_inventory;
const inventory = sheetInv === '' || sheetInv === null || sheetInv === undefined ? null : Number(sheetInv);

return [{
  json: {
    ...row,
    Title: title,
    Description: description,
    'Product image URL': imageUrl,
    'Competitor price': competitorPrice,
    'Competitor currency': competitorCurrency,
    Sizes: sizes,
    Colors: colors,
    'Scraped variants': scrapedVariants,
    Vendor: vendor,
    'Product category': category,
    Tags: tags,
    SKU: sku,
    'Scrape Status': imageUrl ? 'SCRAPED' : 'SCRAPED_NO_IMAGE',
    'Source Product URL': row.source_product_url,
    scraped_raw_description: description,
    validated_image_url: imageUrl,
    validated_raw_info: description || title,
    validated_category: category,
    validated_vendor: vendor,
    validated_price: sellPrice,
    validated_sku: sku,
    validated_inventory: inventory,
    needs_scrape: false,
    extraction_sources: extractionSources,
  },
}];
"""
    return extractors + "\n" + sku_block + "\n" + APPLY_MERGE_BLOCK + "\n" + tail


def main():
    path = ROOT / "ShopifyProductAdd.V2.json"
    data = json.loads(path.read_text())

    prepare_js = EXTRACTORS + "\n" + PREPARE_WRAPPER.strip()
    apply_js = build_apply_js(EXTRACTORS)

    for node in data["nodes"]:
        name = node.get("name", "")
        if name == "Prepare page for scrape":
            node["parameters"]["jsCode"] = prepare_js
        elif name == "Apply scraped data":
            node["parameters"]["jsCode"] = apply_js
        elif name == "Fetch product page":
            headers = node["parameters"].get("headerParameters", {}).get("parameters", [])
            for h in headers:
                if h.get("name") == "User-Agent":
                    h["value"] = (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
            extra = {p["name"]: p for p in headers}
            if "Accept" not in extra:
                headers.append({
                    "name": "Accept",
                    "value": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })
            if "Accept-Language" not in extra:
                headers.append({"name": "Accept-Language", "value": "en-GB,en;q=0.9"})
        elif name == "AI scrape product":
            vals = node["parameters"]["responses"]["values"]
            if vals:
                vals[0]["content"] = AI_SYSTEM
                user = vals[1]["content"]
                if "structured_extract" not in user:
                    vals[1]["content"] = user.rstrip() + AI_USER_SUFFIX

    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched production scrape pipeline into", path)


if __name__ == "__main__":
    main()
