#!/usr/bin/env python3
"""Stop n8n sheet writes from overwriting Suggested* lookup formula columns."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

# Formulas live on Suggested* columns — Vendor/Category/Collection are manual overrides.
FORMULA_COLUMNS = {
    "Suggested Vendor",
    "Suggested Product category",
    "Suggested Variant profile",
    "Suggested Collection",
}


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
    print("Patched workflow: Suggested* columns protected; Vendor/Category stay manual")


if __name__ == "__main__":
    main()
