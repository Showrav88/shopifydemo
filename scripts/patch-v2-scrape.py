#!/usr/bin/env python3
"""Patch ShopifyProductAdd.V2.json with Product URL scrape pipeline."""
import json
import uuid
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / "ShopifyProductAdd.V2.json"

VALIDATE_JS = r'''const rows = $input.all().map((i) => i.json);

function isRowDone(row) {
  const qa = String(row['QA Status'] || '').trim().toUpperCase();
  const score = Number(row['AI Score'] || 0);
  return (qa === 'PASS' || qa === 'PASS_NO_IMAGE') && score >= 90;
}

function getPrice(row) {
  const p = row['Price'] ?? row['Variant Price'] ?? null;
  if (p === null || p === undefined || String(p).trim() === '') return null;
  return p;
}

function getProductUrl(row) {
  return String(row['Product URL'] || row['Source URL'] || '').trim();
}

function urlToSku(url) {
  let h = 0;
  for (let i = 0; i < url.length; i++) h = ((h << 5) - h + url.charCodeAt(i)) | 0;
  return `SCRAPE-${Math.abs(h)}`;
}

function needsScrape(row, productUrl) {
  if (!productUrl) return false;
  const status = String(row['Scrape Status'] || '').trim().toUpperCase();
  const lastUrl = String(row['Source Product URL'] || '').trim();
  if (status !== 'SCRAPED') return true;
  if (lastUrl && lastUrl !== productUrl) return true;
  const imageUrl = String(row['Product image URL'] || '').trim();
  const title = String(row['Title'] || '').trim();
  if (!imageUrl || !title) return true;
  return false;
}

function normalizeRow(item) {
  const productUrl = getProductUrl(item);
  let sku = String(item['SKU'] || item['Variant SKU'] || '').trim();
  if (!sku && productUrl) sku = urlToSku(productUrl);
  const imageUrl = String(item['Product image URL'] || item['Image Src'] || item['Image URL'] || '').trim();
  const rawInfo = String(item['Description'] || item['Title'] || '').trim();
  let category = String(item['Product category'] || item['Type'] || '').trim();
  const vendor = item['Vendor'] || item['Brand'] || '';
  const price = getPrice(item);
  const rowNumber = item.row_number ?? item.__rowNumber ?? item.__row ?? null;
  if (category.startsWith('#') || /error/i.test(category)) category = '';
  return {
    sku, productUrl, imageUrl, rawInfo, category, vendor, price, rowNumber, item,
    needsScrape: needsScrape(item, productUrl),
  };
}

let chosen = null;
const skipped = [];

for (const raw of rows) {
  if (isRowDone(raw)) {
    skipped.push({ sku: raw['SKU'] || '', reason: 'already PASS' });
    continue;
  }
  const r = normalizeRow(raw);
  const hasUrl = !!r.productUrl;
  const hasManual = r.imageUrl && r.rawInfo && r.price !== null && r.sku;

  if (!hasUrl && !hasManual) {
    skipped.push({ sku: r.sku || '(no sku)', reason: 'no Product URL and incomplete manual row' });
    continue;
  }

  if (hasUrl && r.needsScrape) {
    chosen = { ...r, mode: 'scrape' };
    break;
  }

  if (!r.imageUrl || !r.rawInfo) {
    skipped.push({ sku: r.sku, reason: 'missing image or description after scrape' });
    continue;
  }
  if (r.price === null && !hasUrl) {
    skipped.push({ sku: r.sku, reason: 'no Price' });
    continue;
  }

  chosen = { ...r, mode: hasUrl ? 'url_pipeline' : 'manual' };
  break;
}

if (!chosen) {
  return [{
    json: {
      _workflow_status: 'nothing_to_process',
      _message: 'No row to run. Add a Product URL or complete manual row (image + description + price + SKU).',
      _skipped_rows: skipped,
      _rows_checked: rows.length,
    },
  }];
}

const runId = `${Date.now()}-${chosen.sku}`;

return [{
  json: {
    ...chosen.item,
    row_number: chosen.rowNumber,
    processing_sku: chosen.sku,
    validated_sku: chosen.sku,
    source_product_url: chosen.productUrl,
    scrape_mode: chosen.mode,
    validated_image_url: chosen.imageUrl,
    validated_raw_info: chosen.rawInfo,
    validated_category: chosen.category,
    validated_vendor: chosen.vendor,
    validated_price: chosen.price,
    validated_inventory: item['Inventory quantity'] || item['Variant Inventory Qty'] || item['Inventory Qty'] || null,
    needs_scrape: chosen.mode === 'scrape',
    _run_id: runId,
    _skipped_rows: skipped,
  },
}];'''

# Fix typo in validate - chosen.item not item
VALIDATE_JS = VALIDATE_JS.replace(
    "validated_inventory: item['Inventory quantity']",
    "validated_inventory: chosen.item['Inventory quantity']",
)

PREPARE_SCRAPE_JS = r'''const row = $('Validate sheet row').first().json;
const http = $input.first().json;
const productUrl = row.source_product_url || row['Product URL'] || '';
let body = http.data ?? http.body ?? '';

if (typeof body !== 'string') {
  try { body = JSON.stringify(body); } catch { body = String(body); }
}

function extractJsonLd(html) {
  const out = [];
  const re = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    try { out.push(JSON.parse(m[1])); } catch { /* skip */ }
  }
  return out;
}

function meta(html, prop) {
  const re = new RegExp(`<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`, 'i');
  const m = html.match(re);
  return m ? m[1] : '';
}

const jsonLd = extractJsonLd(body);
const snippet = {
  product_url: productUrl,
  run_id: row._run_id,
  json_ld: jsonLd.slice(0, 3),
  og_title: meta(body, 'og:title'),
  og_description: meta(body, 'og:description'),
  og_image: meta(body, 'og:image'),
  html_excerpt: body.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/\s+/g, ' ').slice(0, 12000),
};

return [{ json: { ...row, scrape_context: snippet } }];'''

APPLY_SCRAPED_JS = r'''const row = $('Prepare page for scrape').first().json;
const ai = $input.first().json;
let text = ai.output?.[0]?.content?.[0]?.text || ai.text || ai.message?.content || '';
text = String(text).replace(/```json|```/g, '').trim();
let scraped;
try {
  scraped = JSON.parse(text);
} catch (e) {
  throw new Error(`AI scrape returned invalid JSON: ${text.slice(0, 300)}`);
}

const sku = row.validated_sku || row.processing_sku;
const price = scraped.price ?? scraped.variant_price ?? row.validated_price;
const imageUrl = scraped.image_url || scraped.product_image_url || row.validated_image_url;
const title = scraped.title || row.Title || '';
const description = scraped.description_plain || scraped.description || row.Description || '';
const vendor = scraped.vendor || scraped.brand || row.validated_vendor || '';
const category = scraped.product_category || scraped.category || row.validated_category || '';
const tags = scraped.tags || '';
const inventory = scraped.inventory_quantity ?? row.validated_inventory ?? 10;

return [{
  json: {
    ...row,
    Title: title,
    Description: description,
    'Product image URL': imageUrl,
    Price: price,
    Vendor: vendor,
    'Product category': category,
    Tags: tags,
    SKU: sku,
    'Inventory quantity': inventory,
    'Scrape Status': 'SCRAPED',
    'Source Product URL': row.source_product_url,
    scraped_raw_description: description,
    validated_image_url: imageUrl,
    validated_raw_info: description || title,
    validated_category: category,
    validated_vendor: vendor,
    validated_price: price,
    validated_sku: sku,
    validated_inventory: inventory,
    needs_scrape: false,
  },
}];'''

ACTIVE_ROW_JS = r'''const v = $('Validate sheet row').first().json;
let merged = { ...v };
try {
  const scraped = $('Apply scraped data').first().json;
  if (scraped?.validated_sku) merged = { ...merged, ...scraped };
} catch { /* scrape branch did not run */ }

if (!merged.validated_image_url) {
  merged.validated_image_url = merged['Product image URL'] || '';
}
if (!merged.validated_raw_info) {
  merged.validated_raw_info = merged.Description || merged.Title || '';
}

merged._run_id = merged._run_id || `${Date.now()}-${merged.processing_sku}`;
return [{ json: merged }];'''


def nid():
    return str(uuid.uuid4())


def main():
    wf = json.loads(WORKFLOW.read_text())

    nodes_by_name = {n["name"]: n for n in wf["nodes"]}

    # Trigger: Product URL
    nodes_by_name["Google Sheets Trigger"]["parameters"]["options"]["columnsToWatch"] = ["Product URL"]

    # Validate
    nodes_by_name["Validate sheet row"]["parameters"]["jsCode"] = VALIDATE_JS

    # Row ready: sku OR source url for scrape-only rows
    cond = nodes_by_name["Row ready to process"]["parameters"]["conditions"]
    cond["conditions"] = [
        {
            "id": nid(),
            "leftValue": "={{ $json.processing_sku || $json.source_product_url }}",
            "rightValue": "",
            "operator": {"type": "string", "operation": "notEmpty", "singleValue": True},
        }
    ]

    # New scrape nodes
    scrape_nodes = [
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [{
                        "id": nid(),
                        "leftValue": "={{ $json.needs_scrape }}",
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                },
                "looseTypeValidation": True,
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [-1440, 0],
            "id": nid(),
            "name": "Needs scrape",
        },
        {
            "parameters": {
                "url": "={{ $json.source_product_url }}",
                "options": {
                    "redirect": {"redirect": {"followRedirects": True}},
                    "response": {"response": {"responseFormat": "text"}},
                    "timeout": 30000,
                },
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [{
                        "name": "User-Agent",
                        "value": "Mozilla/5.0 (compatible; ShopifyProductBot/1.0)",
                    }]
                },
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.5,
            "position": [-1260, -120],
            "id": nid(),
            "name": "Fetch product page",
            "onError": "continueRegularOutput",
        },
        {
            "parameters": {"jsCode": PREPARE_SCRAPE_JS},
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [-1080, -120],
            "id": nid(),
            "name": "Prepare page for scrape",
        },
        {
            "parameters": {
                "modelId": {"__rl": True, "value": "gpt-4o-mini", "mode": "list", "cachedResultName": "GPT-4O-MINI"},
                "responses": {
                    "values": [
                        {
                            "content": (
                                "You extract product data from a scraped web page for UK fashion e-commerce.\n"
                                "Use ONLY facts present in the JSON-LD, OpenGraph, or HTML excerpt.\n"
                                "Do NOT invent specs. Do NOT copy from memory or prior products.\n"
                                "Return ONLY valid JSON (no markdown):\n"
                                "{\n"
                                '  "title": "",\n'
                                '  "description_plain": "",\n'
                                '  "price": "",\n'
                                '  "image_url": "",\n'
                                '  "vendor": "",\n'
                                '  "product_category": "",\n'
                                '  "tags": "",\n'
                                '  "inventory_quantity": 10,\n'
                                '  "variants": []\n'
                                "}"
                            ),
                        },
                        {
                            "content": (
                                "=RUN ID (this execution only): {{ $json._run_id }}\n"
                                "Source Product URL: {{ $json.source_product_url }}\n"
                                "Scrape context:\n{{ JSON.stringify($json.scrape_context) }}"
                            ),
                        },
                    ]
                },
                "builtInTools": {},
                "options": {},
            },
            "type": "@n8n/n8n-nodes-langchain.openAi",
            "typeVersion": 2.3,
            "position": [-900, -120],
            "id": nid(),
            "name": "AI scrape product",
            "credentials": {"openAiApi": {"id": None, "name": "", "__aiGatewayManaged": True}},
        },
        {
            "parameters": {"jsCode": APPLY_SCRAPED_JS},
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [-720, -120],
            "id": nid(),
            "name": "Apply scraped data",
        },
        {
            "parameters": {
                "operation": "update",
                "documentId": {
                    "__rl": True,
                    "value": "1ayWn9AcmgLqmxaL6BOzHzzuZSSVwhqbJCCtzIcwXaZ4",
                    "mode": "list",
                    "cachedResultName": "product_template",
                },
                "sheetName": {
                    "__rl": True,
                    "value": 1922248105,
                    "mode": "list",
                    "cachedResultName": "product_template.csv",
                },
                "columns": {
                    "mappingMode": "defineBelow",
                    "value": {
                        "Title": "={{ $('Apply scraped data').item.json.Title }}",
                        "Description": "={{ $('Apply scraped data').item.json.Description }}",
                        "Product image URL": "={{ $('Apply scraped data').item.json['Product image URL'] }}",
                        "Price": "={{ $('Apply scraped data').item.json.Price }}",
                        "Vendor": "={{ $('Apply scraped data').item.json.Vendor }}",
                        "Product category": "={{ $('Apply scraped data').item.json['Product category'] }}",
                        "Tags": "={{ $('Apply scraped data').item.json.Tags }}",
                        "SKU": "={{ $('Apply scraped data').item.json.SKU }}",
                        "Inventory quantity": "={{ $('Apply scraped data').item.json['Inventory quantity'] }}",
                        "Scrape Status": "SCRAPED",
                        "Source Product URL": "={{ $('Apply scraped data').item.json['Source Product URL'] }}",
                    },
                    "matchingColumns": ["SKU"],
                },
                "options": {},
            },
            "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4.7,
            "position": [-540, -120],
            "id": nid(),
            "name": "Update sheet scraped",
            "credentials": {"googleSheetsOAuth2Api": {"id": "RECONNECT_ME", "name": "Google Sheets account"}},
        },
        {
            "parameters": {"jsCode": ACTIVE_ROW_JS},
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [-1260, 120],
            "id": nid(),
            "name": "Active product row",
        },
    ]

    # Shift photoroom right
    nodes_by_name["Remove background Photoroom"]["position"][0] = -1080

    wf["nodes"].extend(scrape_nodes)

    # Sticky notes
    nodes_by_name["Setup Instructions"]["parameters"]["content"] = (
        "## ShopifyProductAdd.V2 + Product URL scrape\n\n"
        "**START:** Paste **Product URL** on a row (competitor/public product page) → workflow auto-scrapes → listing → Shopify draft.\n"
        "**Manual mode still works:** image URL + description + price + SKU (no Product URL).\n\n"
        "**4 AI steps:** AI scrape product → Analyze image → AI write listing → AI QA score\n"
        "**No cache:** each run uses `_run_id` + **Active product row** — never reuses prior row text.\n"
        "**Unpin** Google Sheets Trigger before manual test.\n"
        "**Scrape Status:** SCRAPED = done | empty = will scrape on next trigger\n"
        "**All PASS + run again:** stops safely (nothing_to_process)"
    )
    nodes_by_name["Sheet Input Data"]["parameters"]["content"] = (
        "## Sheet columns\n\n"
        "### YOU type:\n"
        "| Product URL | Paste public product page (triggers scrape) |\n"
        "| SKU | Optional — auto-generated if empty |\n"
        "| Price | Optional if scrape finds price |\n\n"
        "### OR manual (no URL):\n"
        "Product image URL + Description/Title + Price + SKU\n\n"
        "### Workflow writes:\n"
        "Title, Description, Vendor, category, Tags, SEO fields, Scrape Status, Source Product URL, QA Status, AI Score, Shopify URLs"
    )

    # Replace Validate sheet row → Active product row only on downstream nodes (not scrape branch)
    downstream = {
        "Remove background Photoroom", "AI write listing", "Update sheet listing",
        "AI QA score listing", "Update sheet QA score", "Create a product API",
        "Update price, SKU and image link", "Update sheet Shopify URLs", "Update sheet QA failed",
    }
    for n in wf["nodes"]:
        if n["name"] in downstream:
            params = json.dumps(n.get("parameters", {}))
            params = params.replace("$('Validate sheet row')", "$('Active product row')")
            n["parameters"] = json.loads(params)

    # Photoroom uses active row fields
    for n in wf["nodes"]:
        if n["name"] == "Remove background Photoroom":
            n["parameters"]["queryParameters"]["parameters"][0]["value"] = (
                "={{ $json['Product image URL'] || $json.validated_image_url }}"
            )

    # AI write listing anti-cache prompt
    for n in wf["nodes"]:
        if n["name"] == "AI write listing":
            n["parameters"]["responses"]["values"][0]["content"] = (
                "You are a UK fashion e-commerce copywriter.\n"
                "Use ONLY facts from THIS run's image analysis and scraped/sheet data below.\n"
                "Do NOT reuse or copy text from any previous product or run.\n"
                "Do NOT invent specifications.\n"
                "Return ONLY valid JSON (no markdown fences):\n"
                "{\n  \"title\": \"\",\n  \"description_html\": \"<p></p>\",\n"
                "  \"tags\": \"\",\n  \"seo_title\": \"\",\n  \"meta_description\": \"\",\n"
                "  \"image_alt_text\": \"\",\n  \"collection\": \"\"\n}"
            )
            n["parameters"]["responses"]["values"][1]["content"] = (
                "=RUN ID (unique — do not reuse other runs): {{ $('Active product row').item.json._run_id }}\n"
                "Source URL: {{ $('Active product row').item.json.source_product_url || 'manual row' }}\n\n"
                "Verified from image analysis:\n"
                "{{ $('Analyze image').item.json.output[0].content[0].text || $('Analyze image').item.json.text || $('Analyze image').item.json.message?.content }}\n\n"
                "Scraped / sheet facts (THIS product only):\n"
                "Title: {{ $('Active product row').item.json.Title }}\n"
                "Description: {{ $('Active product row').item.json.Description }}\n"
                "Category: {{ $('Active product row').item.json['Product category'] }}\n"
                "Vendor: {{ $('Active product row').item.json.Vendor }}\n"
                "Price: {{ $('Active product row').item.json.Price }}"
            )
        if n["name"] == "AI QA score listing":
            n["parameters"]["responses"]["values"][0]["content"] = (
                "=RUN ID: {{ $('Active product row').item.json._run_id }}\n"
                "You are a strict QA reviewer. Compare ORIGINAL scraped/sheet facts vs GENERATED listing.\n\n"
                "Original Description: {{ $('Active product row').item.json.scraped_raw_description || $('Active product row').item.json.Description }}\n"
                "Generated listing: {{ $('AI write listing').item.json.output[0].content[0].text }}\n\n"
                "Rules:\n- Score 90-100 ONLY if accurate, no invented specs, good SEO\n"
                "- Score below 90 if anything is invented, wrong, or weak\n"
                "- Do NOT default to 85. Score honestly.\n\n"
                "Return JSON only:\n"
                "{\n  \"quality_score\": 0,\n  \"seo_title\": \"max 60 chars\",\n"
                "  \"meta_description\": \"max 160 chars\",\n  \"image_alt_text\": \"\",\n  \"issues\": []\n}"
            )

    # Remove legacy Update price node — connect image result → sheet
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != "Update price, SKU and image link"]

    wf["connections"] = {
        "Google Sheets Trigger": {"main": [[{"node": "Validate sheet row", "type": "main", "index": 0}]]},
        "Validate sheet row": {"main": [[{"node": "Row ready to process", "type": "main", "index": 0}]]},
        "Row ready to process": {
            "main": [[{"node": "Needs scrape", "type": "main", "index": 0}], []],
        },
        "Needs scrape": {
            "main": [
                [{"node": "Fetch product page", "type": "main", "index": 0}],
                [{"node": "Active product row", "type": "main", "index": 0}],
            ],
        },
        "Fetch product page": {"main": [[{"node": "Prepare page for scrape", "type": "main", "index": 0}]]},
        "Prepare page for scrape": {"main": [[{"node": "AI scrape product", "type": "main", "index": 0}]]},
        "AI scrape product": {"main": [[{"node": "Apply scraped data", "type": "main", "index": 0}]]},
        "Apply scraped data": {"main": [[{"node": "Update sheet scraped", "type": "main", "index": 0}]]},
        "Update sheet scraped": {"main": [[{"node": "Active product row", "type": "main", "index": 0}]]},
        "Active product row": {"main": [[{"node": "Remove background Photoroom", "type": "main", "index": 0}]]},
        "Remove background Photoroom": {"main": [[{"node": "Analyze image", "type": "main", "index": 0}]]},
        "Analyze image": {"main": [[{"node": "Restore image binary", "type": "main", "index": 0}]]},
        "Restore image binary": {"main": [[{"node": "Upload to ImgBB", "type": "main", "index": 0}]]},
        "Upload to ImgBB": {"main": [[{"node": "AI write listing", "type": "main", "index": 0}]]},
        "AI write listing": {"main": [[{"node": "Update sheet listing", "type": "main", "index": 0}]]},
        "Update sheet listing": {"main": [[{"node": "AI QA score listing", "type": "main", "index": 0}]]},
        "AI QA score listing": {"main": [[{"node": "Update sheet QA score", "type": "main", "index": 0}]]},
        "Update sheet QA score": {"main": [[{"node": "QA score check 90", "type": "main", "index": 0}]]},
        "QA score check 90": {
            "main": [
                [{"node": "Create a product API", "type": "main", "index": 0}],
                [{"node": "Update sheet QA failed", "type": "main", "index": 0}],
            ],
        },
        "Create a product API": {"main": [[{"node": "Create a product", "type": "main", "index": 0}]]},
        "Create a product": {"main": [[{"node": "Download ImgBB for Shopify", "type": "main", "index": 0}]]},
        "Download ImgBB for Shopify": {"main": [[{"node": "Prepare Shopify image upload", "type": "main", "index": 0}]]},
        "Prepare Shopify image upload": {"main": [[{"node": "Upload image to Shopify", "type": "main", "index": 0}]]},
        "Upload image to Shopify": {"main": [[{"node": "Shopify image result", "type": "main", "index": 0}]]},
        "Shopify image result": {"main": [[{"node": "Update sheet Shopify URLs", "type": "main", "index": 0}]]},
    }

    WORKFLOW.write_text(json.dumps(wf, indent=2))
    print("Patched", WORKFLOW)


if __name__ == "__main__":
    main()
