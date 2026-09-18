#!/usr/bin/env python3
"""Use Suggested * sheet columns as fallback when Vendor/Collection empty in Shopify build."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

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


def main():
    build_js = VARIANTS_JS + "\n" + ORG_JS + "\n" + BUILD_TAIL.strip()
    data = json.loads(WORKFLOW.read_text())
    for node in data["nodes"]:
        if node.get("name") == "Build Shopify product":
            node["parameters"]["jsCode"] = build_js
    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched Build Shopify product with Suggested column fallbacks")


if __name__ == "__main__":
    main()
