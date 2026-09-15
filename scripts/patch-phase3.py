#!/usr/bin/env python3
"""Phase 3 + fixes: organization, url_input rename, ImgBB key, Product URL on all sheet nodes, stock-only updates."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"
IMGBB_KEY = "8e71e83fe03de0cd6e22c480fe344e9b"
PRODUCT_URL_EXPR = "={{ $('Active product row').item.json['Product URL'] || $('Active product row').item.json.source_product_url }}"

VARIANTS_JS = re.sub(r"\nif \(typeof module.*", "", (ROOT / "scripts/n8n-shopify-variants.js").read_text())
ORG_JS = re.sub(r"\nif \(typeof module.*", "", (ROOT / "scripts/n8n-shopify-organization.js").read_text())

BUILD_TAIL = r"""
const row = $('Active product row').first().json;
const aiRaw = $('AI write listing').first().json;
let listingText = aiRaw.output?.[0]?.content?.[0]?.text || aiRaw.text || '';
listingText = String(listingText).replace(/```json|```/g, '').trim();
let listing;
try {
  listing = JSON.parse(listingText);
} catch (e) {
  throw new Error(`Cannot parse AI listing for Shopify build: ${listingText.slice(0, 200)}`);
}

const built = VARIANTS.buildShopifyPayload(row, listing);
const org = ORG.enrichProduct(built.shopify_payload.product, row, listing);
built.category_gid = org.category_gid;
built.collection_handle = org.collection_handle;
return [{ json: built }];
"""

PREPARE_STOCK_JS = r"""
const created = $('Create a product').first().json;
const plan = $('Build Shopify product').first().json;
const updates = plan.inventory_updates || [];
const variants = created.variants || [];

if (variants.length === 0) {
  throw new Error('Shopify product has no variants after create');
}

const bySku = {};
for (const u of updates) bySku[u.sku] = u;

const items = [];
for (let i = 0; i < variants.length; i++) {
  const v = variants[i];
  const u = bySku[v.sku] || updates[i] || updates[0] || {};
  const qty = Number(u.inventory_quantity ?? 0);
  if (qty <= 0) continue;
  items.push({
    json: {
      variant_id: v.id,
      sku: v.sku,
      inventory_quantity: qty,
      multi_variant: plan.multi_variant,
      variant_profile: plan.variant_profile,
      variant_count: plan.variant_count,
    },
  });
}

if (items.length === 0) {
  return [{ json: { skipped: true, reason: 'no inventory — set stock in sheet or Shopify admin' } }];
}
return items;
"""

PLAN_COLLECTION_JS = r"""
const plan = $('Build Shopify product').first().json;
const productId = $('Create a product').first().json.id;
const handle = String(plan.collection_handle || '').trim();
return [{ json: { product_id: productId, collection_handle: handle, has_collection: !!handle } }];
"""


def build_shopify_js():
    return VARIANTS_JS + "\n" + ORG_JS + "\n" + BUILD_TAIL.strip()


def rename_connections(conn, old, new):
    if old in conn:
        conn[new] = conn.pop(old)
    for key, val in list(conn.items()):
        for branch in val.get("main", []):
            for link in branch:
                if link.get("node") == old:
                    link["node"] = new


def main():
    data = json.loads(WORKFLOW.read_text())
    raw = json.dumps(data).replace("input_url.csv", "url_input.csv").replace('"input_url"', '"url_input"')
    data = json.loads(raw)

    for node in data["nodes"]:
        name = node.get("name", "")
        p = node.get("parameters", {})

        if name == "Upload to ImgBB":
            for q in p.get("queryParameters", {}).get("parameters", []):
                if q.get("name") == "key":
                    q["value"] = IMGBB_KEY

        elif name == "Build Shopify product":
            p["jsCode"] = build_shopify_js()

        elif name in ("Prepare variant price updates", "Prepare variant stock updates"):
            node["name"] = "Prepare variant stock updates"
            p["jsCode"] = PREPARE_STOCK_JS

        elif name in ("Set Shopify price and stock", "Set Shopify variant stock"):
            node["name"] = "Set Shopify variant stock"
            p["url"] = "=https://8kqexi-2j.myshopify.com/admin/api/2025-01/variants/{{ $json.variant_id }}.json"
            p["jsonBody"] = (
                '={\n  "variant": {\n    "id": {{ $json.variant_id }},\n'
                '    "inventory_management": "shopify",\n'
                '    "inventory_quantity": {{ $json.inventory_quantity }}\n  }\n}'
            )

        elif name.startswith("Update sheet"):
            cols = p.get("columns", {})
            if cols.get("mappingMode") == "defineBelow":
                vals = cols.setdefault("value", {})
                if "Product URL" not in vals:
                    cols["value"] = {"Product URL": PRODUCT_URL_EXPR, **vals}
                cols["matchingColumns"] = ["Product URL"]

    names = {n["name"] for n in data["nodes"]}

    def add_node(node):
        if node["name"] not in names:
            data["nodes"].append(node)
            names.add(node["name"])

    add_node({
        "parameters": {"jsCode": PLAN_COLLECTION_JS},
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [200, -120], "id": "d4e5f6a7-b8c9-4012-d345-6789abcdef02",
        "name": "Plan Shopify collection",
    })
    add_node({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                "conditions": [{
                    "id": "has-variant-stock",
                    "leftValue": "={{ $json.variant_id }}",
                    "rightValue": "",
                    "operator": {"type": "string", "operation": "notEmpty", "singleValue": True},
                }],
                "combinator": "and",
            },
            "looseTypeValidation": True, "options": {},
        },
        "type": "n8n-nodes-base.if", "typeVersion": 2.3,
        "position": [160, -120], "id": "a7b8c9d0-e1f2-3456-a789-bcdef0123457",
        "name": "Has variant stock",
    })
    add_node({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                "conditions": [{
                    "id": "has-collection-handle",
                    "leftValue": "={{ $json.has_collection }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                }],
                "combinator": "and",
            },
            "looseTypeValidation": True, "options": {},
        },
        "type": "n8n-nodes-base.if", "typeVersion": 2.3,
        "position": [280, -120], "id": "b8c9d0e1-f2a3-4567-b890-cdef01234568",
        "name": "Has collection handle",
    })
    add_node({
        "parameters": {
            "url": "=https://8kqexi-2j.myshopify.com/admin/api/2025-01/custom_collections.json?handle={{ $('Plan Shopify collection').item.json.collection_handle }}",
            "authentication": "predefinedCredentialType",
            "nodeCredentialType": "shopifyOAuth2Api", "options": {},
        },
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.5,
        "position": [400, -200], "id": "e5f6a7b8-c9d0-4123-e456-789abcdef013",
        "name": "Get collection by handle",
        "credentials": {"shopifyOAuth2Api": {"id": "RECONNECT_ME", "name": "Shopify account"}},
        "onError": "continueRegularOutput",
    })
    add_node({
        "parameters": {
            "method": "POST",
            "url": "https://8kqexi-2j.myshopify.com/admin/api/2025-01/collects.json",
            "authentication": "predefinedCredentialType",
            "nodeCredentialType": "shopifyOAuth2Api",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ { collect: { product_id: $('Plan Shopify collection').item.json.product_id, collection_id: $json.custom_collections[0].id } } }}",
            "options": {},
        },
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.5,
        "position": [520, -200], "id": "f6a7b8c9-d0e1-4234-f567-89abcdef0124",
        "name": "Add to Shopify collection",
        "credentials": {"shopifyOAuth2Api": {"id": "RECONNECT_ME", "name": "Shopify account"}},
        "onError": "continueRegularOutput",
    })

    conn = data["connections"]
    rename_connections(conn, "Prepare variant price updates", "Prepare variant stock updates")
    rename_connections(conn, "Set Shopify price and stock", "Set Shopify variant stock")

    conn["Create a product"] = {"main": [[{"node": "Prepare variant stock updates", "type": "main", "index": 0}]]}
    conn["Prepare variant stock updates"] = {"main": [[{"node": "Has variant stock", "type": "main", "index": 0}]]}
    conn["Has variant stock"] = {
        "main": [
            [{"node": "Set Shopify variant stock", "type": "main", "index": 0}],
            [{"node": "Plan Shopify collection", "type": "main", "index": 0}],
        ]
    }
    conn["Set Shopify variant stock"] = {"main": [[{"node": "Plan Shopify collection", "type": "main", "index": 0}]]}
    conn["Plan Shopify collection"] = {"main": [[{"node": "Has collection handle", "type": "main", "index": 0}]]}
    conn["Has collection handle"] = {
        "main": [
            [{"node": "Get collection by handle", "type": "main", "index": 0}],
            [{"node": "Download ImgBB for Shopify", "type": "main", "index": 0}],
        ]
    }
    conn["Get collection by handle"] = {"main": [[{"node": "Add to Shopify collection", "type": "main", "index": 0}]]}
    conn["Add to Shopify collection"] = {"main": [[{"node": "Download ImgBB for Shopify", "type": "main", "index": 0}]]}

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched Phase 3 into", WORKFLOW)


if __name__ == "__main__":
    main()
