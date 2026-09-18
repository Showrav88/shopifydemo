#!/usr/bin/env python3
"""Align ShopifyProductAdd.V2.json with sheet-products.csv column layout."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"
SHEET_CSV = ROOT / "sheet-products.csv"

SHEET_ID = "1iV7qRLtQ0hLrDUd6MA8cJCLz36kliDB28C3Y1rvX8JQ"
SHEET_GID = "2126173338"

# Columns with sheet formulas — n8n must never write these.
FORMULA_COLUMNS = {
    "Vendor",
    "Product category",
    "Variant profile",
    "Collection",
    "Prompt Title",
    "Prompt Description",
    "Prompt Tags",
    "Prompt SEO title",
    "Prompt SEO description",
    "Prompt Image alt",
    "Prompt Category",
}

SHEET_FORMULA_KEYS_JS = """const SHEET_FORMULA_KEYS = [
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

function overlaySheetFormulas(target, source) {
  if (!source || typeof source !== 'object') return target;
  for (const key of SHEET_FORMULA_KEYS) {
    const v = String(source[key] ?? '').trim();
    if (v) target[key] = v;
  }
  return target;
}
"""

READ_NODE_TEMPLATE = {
    "parameters": {
        "operation": "read",
        "documentId": {"__rl": True, "value": SHEET_ID, "mode": "id"},
        "sheetName": {"__rl": True, "value": SHEET_GID, "mode": "id"},
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
                "values": {"general": "UNFORMATTED_VALUE", "date": "FORMATTED_STRING"}
            },
            "returnFirstMatch": True,
        },
    },
    "type": "n8n-nodes-base.googleSheets",
    "typeVersion": 4.7,
    "position": [-340, -40],
    "id": "c7d8e9f0-a1b2-3456-7890-abcdef123456",
    "name": "Re-read sheet after scrape",
    "credentials": {"googleSheetsOAuth2Api": {"name": "Google Sheets account"}},
}

ACTIVE_OVERLAY_MARKER = "let merged = { ...v };"
ACTIVE_OVERLAY_REPLACEMENT = """let merged = { ...v };
try {
  const freshRow = $('Re-read sheet after scrape').first().json;
  merged = overlaySheetFormulas(merged, freshRow);
} catch { /* scrape write + re-read did not run */ }"""

MERGE_JS = r"""const base = $('Active product row').first().json;
let row = { ...base };
const fresh = $('Re-read sheet row').first().json;
row = overlaySheetFormulas(row, fresh);
return [{ json: row }];
"""


def sheet_headers() -> list[str]:
    with SHEET_CSV.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def strip_formula_writes(data: dict) -> None:
    for node in data["nodes"]:
        if "googleSheets" not in node.get("type", ""):
            continue
        if node.get("parameters", {}).get("operation") != "update":
            continue
        cols = node["parameters"].get("columns", {}).get("value", {})
        for key in FORMULA_COLUMNS:
            cols.pop(key, None)


def patch_active_product_row(data: dict) -> None:
    active = next(n for n in data["nodes"] if n.get("name") == "Active product row")
    js = active["parameters"]["jsCode"]
    # Strip old overlay header only (do not touch body — avoids breaking browserDomain tail).
    if js.startswith("const SHEET_FORMULA_KEYS"):
        end = js.find("function isDirectImageUrl")
        if end != -1:
            js = js[end:]
    # Remove leftover resolvePromptFields fragments from older patches.
    js = js.replace("\n  return obj;\n}\n\n  return obj;\n}\n", "\n")
    js = SHEET_FORMULA_KEYS_JS + "\n" + js.lstrip()
    if "Re-read sheet after scrape" not in js:
        js = js.replace(ACTIVE_OVERLAY_MARKER, ACTIVE_OVERLAY_REPLACEMENT)
    active["parameters"]["jsCode"] = js


def patch_merge_node(data: dict) -> None:
    merge = next(n for n in data["nodes"] if n.get("name") == "Merge refreshed lookup")
    merge["parameters"]["jsCode"] = SHEET_FORMULA_KEYS_JS + "\n" + MERGE_JS.strip()


def ensure_scrape_reread_node(data: dict) -> None:
    names = {n.get("name") for n in data["nodes"]}
    if "Re-read sheet after scrape" not in names:
        data["nodes"].append(READ_NODE_TEMPLATE.copy())

    data["connections"]["Update sheet scraped"] = {
        "main": [[{"node": "Re-read sheet after scrape", "type": "main", "index": 0}]]
    }
    data["connections"]["Re-read sheet after scrape"] = {
        "main": [[{"node": "Active product row", "type": "main", "index": 0}]]
    }


def patch_sticky_note(data: dict) -> None:
    headers = sheet_headers()
    user_cols = "A URL | B Force browser | C-F lookup | G-H scrape | R Prompt ID | S-Y prompts"
    formula_cols = ", ".join(sorted(FORMULA_COLUMNS))
    text = (
        "## Sheet columns (Master_Sheetv1)\n\n"
        f"**You type:** {user_cols}\n\n"
        f"**Formula cols (never write from n8n):** {formula_cols}\n\n"
        f"**Tabs:** LookupTables + PromptLibrary + this sheet\n\n"
        f"**Total columns:** {len(headers)}"
    )
    for node in data["nodes"]:
        if node.get("name") == "Sheet Input Data":
            node["parameters"]["content"] = text
            break


def main():
    data = json.loads(WORKFLOW.read_text())
    strip_formula_writes(data)
    ensure_scrape_reread_node(data)
    patch_active_product_row(data)
    patch_merge_node(data)
    patch_sticky_note(data)
    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Aligned workflow with sheet-products.csv")


if __name__ == "__main__":
    main()
