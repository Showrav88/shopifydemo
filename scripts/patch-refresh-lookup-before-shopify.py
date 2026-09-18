#!/usr/bin/env python3
"""Re-read sheet lookup columns (Vendor, category, collection) before Shopify build."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

READ_NODE = {
    "parameters": {
        "operation": "read",
        "documentId": {
            "__rl": True,
            "value": "1iV7qRLtQ0hLrDUd6MA8cJCLz36kliDB28C3Y1rvX8JQ",
            "mode": "id",
        },
        "sheetName": {
            "__rl": True,
            "value": "2126173338",
            "mode": "id",
        },
        "filtersUI": {
            "values": [
                {
                    "lookupColumn": "Product URL",
                    "lookupValue": "={{ $('Google Sheets Trigger').first().json['Product URL'] }}",
                }
            ]
        },
        "options": {
            "outputFormatting": {
                "values": {
                    "general": "UNFORMATTED_VALUE",
                    "date": "FORMATTED_STRING",
                }
            },
            "returnFirstMatch": True,
        },
    },
    "type": "n8n-nodes-base.googleSheets",
    "typeVersion": 4.7,
    "position": [-200, -120],
    "id": "f1e2d3c4-b5a6-9788-7654-3210fedcba98",
    "name": "Re-read sheet row",
    "credentials": {
        "googleSheetsOAuth2Api": {
            "name": "Google Sheets account",
        }
    },
}

MERGE_JS = r"""const base = $('Active product row').first().json;
const row = { ...base };
const fresh = $('Re-read sheet row').first().json;
const lookupKeys = [
  'Vendor',
  'Product category',
  'Variant profile',
  'Collection',
  'Prompt ID',
  'Prompt Title',
  'Prompt Description',
  'Prompt Tags',
  'Prompt SEO title',
  'Prompt SEO description',
  'Prompt Image alt',
  'Prompt Category',
];
for (const key of lookupKeys) {
  const v = String(fresh[key] ?? '').trim();
  if (v) row[key] = v;
}
return [{ json: row }];
"""

MERGE_NODE = {
    "parameters": {"jsCode": MERGE_JS},
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-40, -120],
    "id": "a9b8c7d6-e5f4-3210-abcd-ef9876543210",
    "name": "Merge refreshed lookup",
}


def main():
    data = json.loads(WORKFLOW.read_text())
    names = {n.get("name") for n in data["nodes"]}

    if "Re-read sheet row" not in names:
        data["nodes"].append(READ_NODE)
    if "Merge refreshed lookup" not in names:
        data["nodes"].append(MERGE_NODE)

    build = next(n for n in data["nodes"] if n.get("name") == "Build Shopify product")
    js = build["parameters"]["jsCode"]
    if "$('Merge refreshed lookup')" not in js:
        js = js.replace(
            "const row = $('Active product row').first().json;",
            "const row = $('Merge refreshed lookup').first().json;",
        )
        build["parameters"]["jsCode"] = js

    data["connections"]["QA score check 90"] = {
        "main": [
            [
                {"node": "Re-read sheet row", "type": "main", "index": 0},
            ],
            data["connections"]["QA score check 90"]["main"][1],
        ]
    }
    data["connections"]["Re-read sheet row"] = {
        "main": [[{"node": "Merge refreshed lookup", "type": "main", "index": 0}]]
    }
    data["connections"]["Merge refreshed lookup"] = {
        "main": [[{"node": "Build Shopify product", "type": "main", "index": 0}]]
    }

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched workflow: re-read lookup columns before Shopify build")


if __name__ == "__main__":
    main()
