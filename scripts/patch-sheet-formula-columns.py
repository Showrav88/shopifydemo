#!/usr/bin/env python3
"""Stop n8n sheet writes from overwriting lookup formula columns (Vendor, Product category)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

# These columns are filled by sheet formulas from LookupTables — n8n must not overwrite.
FORMULA_COLUMNS = {"Vendor", "Product category", "Variant profile", "Collection"}


def strip_formula_columns(cols: dict) -> None:
    for key in FORMULA_COLUMNS:
        cols.pop(key, None)


def main():
    data = json.loads(WORKFLOW.read_text())
    for node in data["nodes"]:
        if "googleSheets" not in node.get("type", ""):
            continue
        if node.get("parameters", {}).get("operation") != "update":
            continue
        cols = node["parameters"].get("columns", {}).get("value", {})
        if cols:
            strip_formula_columns(cols)

    prep = next((n for n in data["nodes"] if n.get("name") == "Prepare sheet scrape write"), None)
    if prep:
        js = prep["parameters"]["jsCode"]
        for field in ("'Vendor': s.Vendor || '',\n    ", "'Product category': s['Product category'] || '',\n    "):
            js = js.replace(field, "")
        prep["parameters"]["jsCode"] = js

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched workflow: formula columns protected from n8n overwrites")


if __name__ == "__main__":
    main()
