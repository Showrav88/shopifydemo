#!/usr/bin/env python3
"""Inject Phase 2 multi-variant nodes into ShopifyProductAdd.V2.json."""
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANTS_JS = (ROOT / "scripts" / "n8n-shopify-variants.js").read_text()
VARIANTS_JS = re.sub(r"\nif \(typeof module.*", "", VARIANTS_JS)
VARIANTS_JS = VARIANTS_JS.replace("const VARIANTS = {};", "const VARIANTS = {};")

BUILD_NODE_JS = VARIANTS_JS + r"""

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
return [{ json: built }];
"""

PREPARE_UPDATES_JS = r"""
const created = $('Create a product').first().json;
const plan = $('Build Shopify product').first().json;
const updates = plan.inventory_updates || plan.price_updates || [];
const variants = created.variants || [];

if (variants.length === 0) {
  throw new Error('Shopify product has no variants after create');
}

const bySku = {};
for (const u of updates) bySku[u.sku] = u;

const items = variants.map((v, i) => {
  const u = bySku[v.sku] || updates[i] || updates[0] || {};
  return {
    json: {
      variant_id: v.id,
      sku: v.sku,
      price: String(u.price ?? '0.00'),
      inventory_quantity: Number(u.inventory_quantity ?? 0),
      multi_variant: plan.multi_variant,
      variant_profile: plan.variant_profile,
      variant_count: plan.variant_count,
    },
  };
});

return items;
"""

BUILD_NODE_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
PREPARE_UPDATES_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"


def main():
    path = ROOT / "ShopifyProductAdd.V2.json"
    data = json.loads(path.read_text())

    build_node = {
        "parameters": {"jsCode": BUILD_NODE_JS},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-90, -120],
        "id": BUILD_NODE_ID,
        "name": "Build Shopify product",
    }

    prepare_updates_node = {
        "parameters": {"jsCode": PREPARE_UPDATES_JS},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [90, -120],
        "id": PREPARE_UPDATES_ID,
        "name": "Prepare variant price updates",
    }

    node_names = {n.get("name") for n in data["nodes"]}
    if "Build Shopify product" not in node_names:
        data["nodes"].append(build_node)
    if "Prepare variant price updates" not in node_names:
        data["nodes"].append(prepare_updates_node)

    for node in data["nodes"]:
        name = node.get("name", "")
        if name == "Build Shopify product":
            node["parameters"]["jsCode"] = BUILD_NODE_JS
        elif name == "Create a product API":
            node["parameters"]["jsonBody"] = "={{ $('Build Shopify product').item.json.shopify_payload }}"
        elif name == "Prepare variant price updates":
            node["parameters"]["jsCode"] = PREPARE_UPDATES_JS
        elif name in ("Set Shopify price and stock", "Set Shopify variant stock"):
            node["parameters"]["url"] = (
                "=https://8kqexi-2j.myshopify.com/admin/api/2025-01/variants/{{ $json.variant_id }}.json"
            )
            node["parameters"]["jsonBody"] = (
                '={\n  "variant": {\n    "id": {{ $json.variant_id }},\n'
                '    "price": "{{ $json.price }}",\n'
                '    "inventory_management": "shopify",\n'
                '    "inventory_quantity": {{ $json.inventory_quantity }}\n  }\n}'
            )

    conn = data["connections"]
    conn["QA score check 90"] = {
        "main": [
            [{"node": "Build Shopify product", "type": "main", "index": 0}],
            [{"node": "Update sheet QA failed", "type": "main", "index": 0}],
        ]
    }
    conn["Build Shopify product"] = {
        "main": [[{"node": "Create a product API", "type": "main", "index": 0}]]
    }
    conn["Create a product"] = {
        "main": [[{"node": "Prepare variant price updates", "type": "main", "index": 0}]]
    }
    conn["Prepare variant price updates"] = {
        "main": [[{"node": "Set Shopify price and stock", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched Phase 2 multi-variant into", path)


if __name__ == "__main__":
    main()
