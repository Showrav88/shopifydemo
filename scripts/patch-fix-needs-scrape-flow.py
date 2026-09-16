#!/usr/bin/env python3
"""Remove Stamp sheet SKU (strips needs_scrape) + match rows on trigger Product URL."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

SPREADSHEET_ID = "1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo"
SHEET_GID = "975501836"
TRIGGER_URL = "={{ $('Google Sheets Trigger').first().json['Product URL'] }}"
SKU_ACTIVE = "={{ $('Active product row').first().json.validated_sku }}"
SKU_VALIDATE = "={{ $('Validate sheet row').first().json.validated_sku }}"

URL_SCHEMA = [
    {
        "id": "Product URL",
        "displayName": "Product URL",
        "required": False,
        "defaultMatch": True,
        "canBeUsedToMatch": True,
        "type": "string",
    },
    {
        "id": "SKU",
        "displayName": "SKU",
        "required": False,
        "defaultMatch": False,
        "canBeUsedToMatch": True,
        "type": "string",
    },
]


def sheet_ref():
    return {
        "documentId": {"__rl": True, "value": SPREADSHEET_ID, "mode": "id"},
        "sheetName": {"__rl": True, "value": SHEET_GID, "mode": "id"},
    }


def apply_url_match(cols, sku_expr=None):
    vals = cols.setdefault("value", {})
    vals["Product URL"] = TRIGGER_URL
    if sku_expr:
        vals["SKU"] = sku_expr
    cols["value"] = {"Product URL": TRIGGER_URL, **{k: v for k, v in vals.items() if k != "Product URL"}}
    cols["matchingColumns"] = ["Product URL"]
    cols["schema"] = URL_SCHEMA


def main():
    data = json.loads(WORKFLOW.read_text())

    # Remove Stamp sheet SKU — it replaced full row with {Product URL, SKU} only
    data["nodes"] = [n for n in data["nodes"] if n.get("name") != "Stamp sheet SKU"]
    conn = data["connections"]
    conn.pop("Stamp sheet SKU", None)

    # Row ready → Needs scrape (full validated row preserved)
    conn["Row ready to process"] = {
        "main": [[{"node": "Needs scrape", "type": "main", "index": 0}], []]
    }

    update_sku = {
        "Update sheet listing": SKU_ACTIVE,
        "Update sheet QA score": SKU_ACTIVE,
        "Update sheet Shopify URLs": SKU_ACTIVE,
        "Update sheet QA failed": SKU_ACTIVE,
        "Update sheet scraped": SKU_VALIDATE,
    }

    for node in data["nodes"]:
        name = node.get("name", "")
        p = node.get("parameters", {})

        if name == "Needs scrape":
            for cond in p["conditions"]["conditions"]:
                if "needs_scrape" in str(cond.get("leftValue", "")):
                    cond["leftValue"] = "={{ $('Validate sheet row').first().json.needs_scrape }}"

        elif name == "Fetch product page":
            p["url"] = "={{ $('Validate sheet row').first().json.source_product_url || $json.source_product_url }}"

        elif name == "Google Sheets Trigger":
            p["documentId"] = sheet_ref()["documentId"]
            p["sheetName"] = sheet_ref()["sheetName"]

        elif "googleSheets" in node.get("type", "") and p.get("operation") == "update":
            p["documentId"] = sheet_ref()["documentId"]
            p["sheetName"] = sheet_ref()["sheetName"]
            apply_url_match(p["columns"], update_sku.get(name))

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Fixed needs_scrape flow:", WORKFLOW)


if __name__ == "__main__":
    main()
