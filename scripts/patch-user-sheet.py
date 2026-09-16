#!/usr/bin/env python3
"""Hardcode user Google Sheet + fix SKU matching on all update nodes."""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

# User sheet: https://docs.google.com/spreadsheets/d/1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo/edit?gid=975501836
SPREADSHEET_ID = "1_GFtwtZR4RlpDGsEGsG6oJ1c-ztvlW1PIRi_WOHUgZo"
SHEET_GID = "975501836"

TRIGGER_URL = "={{ $('Google Sheets Trigger').first().json['Product URL'] }}"
SKU_VALIDATE = "={{ $('Validate sheet row').first().json.validated_sku }}"
SKU_ACTIVE = "={{ $('Active product row').first().json.validated_sku }}"

SKU_SCHEMA = [
    {
        "id": "SKU",
        "displayName": "SKU",
        "required": False,
        "defaultMatch": True,
        "canBeUsedToMatch": True,
        "type": "string",
    }
]

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

STAMP_NODE = {
    "parameters": {
        "operation": "update",
        "documentId": {"__rl": True, "value": SPREADSHEET_ID, "mode": "id"},
        "sheetName": {"__rl": True, "value": SHEET_GID, "mode": "id"},
        "columns": {
            "mappingMode": "defineBelow",
            "value": {
                "Product URL": TRIGGER_URL,
                "SKU": SKU_VALIDATE,
            },
            "matchingColumns": ["Product URL"],
            "schema": URL_SCHEMA,
        },
        "options": {},
    },
    "type": "n8n-nodes-base.googleSheets",
    "typeVersion": 4.7,
    "position": [-1440, 0],
    "id": "f1a2b3c4-d5e6-7890-abcd-ef1234567899",
    "name": "Stamp sheet SKU",
    "credentials": {
        "googleSheetsOAuth2Api": {"name": "Google Sheets account"},
    },
}


def sheet_ref():
    return {
        "documentId": {"__rl": True, "value": SPREADSHEET_ID, "mode": "id"},
        "sheetName": {"__rl": True, "value": SHEET_GID, "mode": "id"},
    }


def apply_sku_match(cols, sku_expr=SKU_ACTIVE):
    vals = cols.setdefault("value", {})
    # SKU must be first — n8n uses matchingColumns value from mapping
    cols["value"] = {"SKU": sku_expr, **{k: v for k, v in vals.items() if k != "SKU"}}
    cols["matchingColumns"] = ["SKU"]
    cols["schema"] = SKU_SCHEMA


def strip_reconnect_ids(node):
    creds = node.get("credentials")
    if not creds:
        return
    for key, val in creds.items():
        if isinstance(val, dict) and val.get("id") == "RECONNECT_ME":
            del val["id"]


def main():
    data = json.loads(WORKFLOW.read_text())
    names = {n["name"] for n in data["nodes"]}

    if "Stamp sheet SKU" not in names:
        data["nodes"].append(STAMP_NODE)
        names.add("Stamp sheet SKU")

    update_nodes = {
        "Update sheet listing": SKU_ACTIVE,
        "Update sheet QA score": SKU_ACTIVE,
        "Update sheet Shopify URLs": SKU_ACTIVE,
        "Update sheet QA failed": SKU_ACTIVE,
        "Update sheet scraped": SKU_VALIDATE,
    }

    for node in data["nodes"]:
        strip_reconnect_ids(node)
        name = node.get("name", "")
        p = node.get("parameters", {})

        if name == "Google Sheets Trigger":
            p["documentId"] = sheet_ref()["documentId"]
            p["sheetName"] = sheet_ref()["sheetName"]
            node["credentials"] = {
                "googleSheetsTriggerOAuth2Api": {"name": "Google Sheets account"},
            }

        elif "googleSheets" in node.get("type", "") and p.get("operation") == "update":
            p["documentId"] = sheet_ref()["documentId"]
            p["sheetName"] = sheet_ref()["sheetName"]
            if name in update_nodes:
                apply_sku_match(p["columns"], update_nodes[name])
            node["credentials"] = {
                "googleSheetsOAuth2Api": {"name": "Google Sheets account"},
            }

        elif name == "Prepare sheet scrape write":
            old = p["jsCode"]
            p["jsCode"] = old.replace(
                "'SKU': s.SKU || '',",
                "'SKU': s.SKU || s.validated_sku || s.processing_sku || '',",
            )

    # Row ready → Stamp sheet SKU → Needs scrape
    conn = data["connections"]
    conn["Row ready to process"] = {
        "main": [[{"node": "Stamp sheet SKU", "type": "main", "index": 0}], []]
    }
    conn["Stamp sheet SKU"] = {
        "main": [[{"node": "Needs scrape", "type": "main", "index": 0}]]
    }

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched user sheet ID + SKU matching into", WORKFLOW)


if __name__ == "__main__":
    main()
