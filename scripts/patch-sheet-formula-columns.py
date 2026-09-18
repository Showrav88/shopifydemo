#!/usr/bin/env python3
"""Protect lookup formula columns from n8n overwrites."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

FORMULA_COLUMNS = {
    "Vendor",
    "Product category",
    "Variant profile",
    "Collection",
    "Suggested Prompt Title",
    "Suggested Prompt Description",
    "Suggested Prompt Tags",
    "Suggested Prompt SEO title",
    "Suggested Prompt SEO description",
    "Suggested Prompt Image alt",
    "Suggested Prompt Category",
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
    print("Patched workflow: C–F + Suggested Prompt* protected from overwrites")


if __name__ == "__main__":
    main()
