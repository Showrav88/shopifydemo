#!/usr/bin/env python3
"""Skip Analyze image when no URL; mark Macy's/Mango as NEEDS_BROWSER / SCRAPED_PARTIAL."""
import json
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent

ACTIVE_APPEND = r"""
merged.has_valid_image = Boolean(resolvedImage);

function browserDomain(url) {
  const host = String(url || '').replace(/^https?:\/\//, '').split('/')[0].replace(/^www\./, '').toLowerCase();
  const hard = ['macys.com', 'mango.com', 'express.com', 'nordstrom.com', 'zara.com', 'hm.com', 'asos.com'];
  return hard.some((d) => host === d || host.endsWith('.' + d));
}
merged.needs_browser_site = browserDomain(merged['Product URL'] || merged.source_product_url || '');
"""

PREPARE_BLOCKED_JS = r"""const row = $('Active product row').first().json;
const productUrl = String(row['Product URL'] || row.source_product_url || '').trim();
const needsBrowser = row.needs_browser_site || String(row['Scrape Status'] || '').includes('NEEDS_BROWSER');
const scrapeStatus = needsBrowser ? 'NEEDS_BROWSER' : (row['Scrape Status'] || 'SCRAPED_NO_IMAGE');
const issue = needsBrowser
  ? 'Site blocks HTTP scraper (Akamai/Cloudflare). Phase 4: add Browserless node, or paste Product image URL manually.'
  : 'No product image found. Paste a direct image URL in Product image URL column, or re-scrape.';

return [{
  json: {
    'Product URL': productUrl,
    SKU: row.SKU || row.validated_sku || '',
    'Scrape Status': scrapeStatus,
    Status: 'NEEDS_BROWSER',
    'QA Status': 'BLOCKED_NO_IMAGE',
    'QA Issues': issue,
    'Scrape method': 'blocked',
    'Product image URL': '',
  },
}];
"""


def patch_active_product_row(code: str) -> str:
    if "has_valid_image" in code:
        return code
    return code.replace(
        "merged._run_id = merged._run_id || `${Date.now()}-${merged.processing_sku}`;",
        ACTIVE_APPEND + "\nmerged._run_id = merged._run_id || `${Date.now()}-${merged.processing_sku}`;",
    )


def patch_is_direct_image_url(code: str) -> str:
    needle = "if (/scene7\\.com/i.test(u)) return true;"
    add = needle + "\n  if (/media\\.mango\\.com/i.test(u)) return true;"
    if "media.mango.com" not in code and needle in code:
        code = code.replace(needle, add)
    return code


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "patch-production-scrape.py")], check=True)

    # Patch apply scrape status in V2 after production scrape patch
    path = ROOT / "ShopifyProductAdd.V2.json"
    data = json.loads(path.read_text())

    apply_status = r"""
const scrapeMethodUsed = row.scrape_context?.scrape_method || row.scrape_method_planned || row.fetch_method || 'http';
const botBypassed = Boolean(row.scrape_context?.bot_protection_bypassed);
const productUrl = row.source_product_url || row['Product URL'] || '';
const fetchStrategy = SCRAPE.pickFetchStrategy(productUrl);
const variantList = structured.variants || scraped.variants || [];
const hasVariants = variantList.length > 0;
const hasSizes = (Array.isArray(sizesArr) ? sizesArr.length : 0) > 0 || String(sizes || '').trim().length > 0;
const hasColors = (Array.isArray(colorsArr) ? colorsArr.length : 0) > 0 || String(colors || '').trim().length > 0;
let scrapeStatus = 'SCRAPED';
if (!imageUrl) {
  scrapeStatus = fetchStrategy === 'browser' ? 'NEEDS_BROWSER' : 'SCRAPED_NO_IMAGE';
} else if (scrapeMethodUsed === 'browser' && botBypassed) {
  scrapeStatus = 'SCRAPED_BROWSER';
} else if (fetchStrategy === 'browser' && !hasVariants && !hasSizes && !hasColors) {
  scrapeStatus = 'SCRAPED_PARTIAL';
}
"""

    for node in data["nodes"]:
        name = node.get("name", "")
        if name == "Active product row":
            code = node["parameters"]["jsCode"]
            code = patch_active_product_row(code)
            code = patch_is_direct_image_url(code)
            node["parameters"]["jsCode"] = code
        elif name == "Validate sheet row":
            node["parameters"]["jsCode"] = patch_is_direct_image_url(node["parameters"]["jsCode"])
        elif name == "Prepare scrape blocked":
            node["parameters"]["jsCode"] = PREPARE_BLOCKED_JS.strip()
        elif name == "Apply scraped data":
            code = node["parameters"]["jsCode"]
            if "let scrapeStatus = 'SCRAPED'" not in code:
                code = code.replace(
                    "'Scrape Status': imageUrl ? 'SCRAPED' : 'SCRAPED_NO_IMAGE',",
                    "'Scrape Status': scrapeStatus,\n    'Scrape method': scrapeMethodUsed,",
                )
                insert_at = "const extractionSources = structured._sources || {};"
                code = code.replace(insert_at, insert_at + "\n" + apply_status)
                node["parameters"]["jsCode"] = code

    # New nodes
    if not any(n.get("name") == "Has product image?" for n in data["nodes"]):
        data["nodes"].extend([
            {
                "parameters": {
                    "conditions": {
                        "options": {
                            "caseSensitive": True,
                            "leftValue": "",
                            "typeValidation": "loose",
                            "version": 3,
                        },
                        "conditions": [{
                            "id": "has-valid-image",
                            "leftValue": "={{ $json.has_valid_image }}",
                            "rightValue": True,
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        }],
                        "combinator": "and",
                    },
                    "looseTypeValidation": True,
                    "options": {},
                },
                "type": "n8n-nodes-base.if",
                "typeVersion": 2.3,
                "position": [-1140, 120],
                "id": str(uuid4()),
                "name": "Has product image?",
            },
            {
                "parameters": {"jsCode": PREPARE_BLOCKED_JS},
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [-1140, 280],
                "id": str(uuid4()),
                "name": "Prepare scrape blocked",
            },
            {
                "parameters": {
                    "operation": "update",
                    "documentId": {
                        "__rl": True,
                        "value": "1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo",
                        "mode": "id",
                    },
                    "sheetName": {
                        "__rl": True,
                        "value": "975501836",
                        "mode": "id",
                    },
                    "columns": {
                        "mappingMode": "defineBelow",
                        "value": {
                            "Product URL": "={{ $('Google Sheets Trigger').first().json['Product URL'] }}",
                            "SKU": "={{ $json.SKU }}",
                            "Scrape Status": "={{ $json['Scrape Status'] }}",
                            "Status": "={{ $json.Status }}",
                            "QA Status": "={{ $json['QA Status'] }}",
                            "QA Issues": "={{ $json['QA Issues'] }}",
                            "Product image URL": "={{ $json['Product image URL'] }}",
                        },
                        "matchingColumns": ["Product URL"],
                        "schema": [{
                            "id": "Product URL",
                            "displayName": "Product URL",
                            "required": False,
                            "defaultMatch": True,
                            "canBeUsedToMatch": True,
                            "type": "string",
                        }],
                    },
                    "options": {},
                },
                "type": "n8n-nodes-base.googleSheets",
                "typeVersion": 4.7,
                "position": [-960, 280],
                "id": str(uuid4()),
                "name": "Update sheet scrape blocked",
                "credentials": {
                    "googleSheetsOAuth2Api": {"name": "Google Sheets account"},
                },
            },
        ])

    data["connections"]["Active product row"] = {
        "main": [[{"node": "Has product image?", "type": "main", "index": 0}]]
    }
    data["connections"]["Has product image?"] = {
        "main": [
            [{"node": "Analyze image", "type": "main", "index": 0}],
            [{"node": "Prepare scrape blocked", "type": "main", "index": 0}],
        ]
    }
    data["connections"]["Prepare scrape blocked"] = {
        "main": [[{"node": "Update sheet scrape blocked", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched skip-no-image flow into", path)


if __name__ == "__main__":
    main()
