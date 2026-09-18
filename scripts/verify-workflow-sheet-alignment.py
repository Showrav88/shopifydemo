#!/usr/bin/env python3
"""Fail if ShopifyProductAdd.V2.json drifts from sheet-products.csv."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"
SHEET_CSV = ROOT / "sheet-products.csv"

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

REQUIRED_REFRESH_KEYS = FORMULA_COLUMNS | {"Prompt ID"}
SHEET_ID = "1iV7qRLtQ0hLrDUd6MA8cJCLz36kliDB28C3Y1rvX8JQ"
SHEET_GID = "2126173338"


def main() -> int:
    errors = []
    headers = next(csv.reader(SHEET_CSV.open(encoding="utf-8")))

    if "Suggested Vendor" in headers or "Suggested Prompt Title" in headers:
        errors.append("sheet-products.csv still has Suggested* columns")

    for col in FORMULA_COLUMNS:
        if col not in headers:
            errors.append(f"sheet missing formula column: {col}")

    data = json.loads(WORKFLOW.read_text())
    text = json.dumps(data)

    if "Suggested Vendor" in text or "Suggested Prompt" in text:
        errors.append("workflow still references Suggested* columns")

    for node in data["nodes"]:
        if node.get("type") != "n8n-nodes-base.googleSheets":
            continue
        params = node.get("parameters", {})
        if params.get("operation") == "update":
            overlap = FORMULA_COLUMNS & set(params.get("columns", {}).get("value", {}))
            if overlap:
                errors.append(f"{node['name']} writes formula columns: {sorted(overlap)}")
        doc = params.get("documentId", {}).get("value")
        sheet = params.get("sheetName", {}).get("value")
        if doc and doc != SHEET_ID:
            errors.append(f"{node['name']} wrong spreadsheet id: {doc}")
        if sheet and sheet != SHEET_GID and params.get("operation") in {"read", "update"}:
            errors.append(f"{node['name']} wrong sheet gid: {sheet}")

    merge = next(n for n in data["nodes"] if n.get("name") == "Merge refreshed lookup")
    merge_js = merge["parameters"]["jsCode"]
    for key in REQUIRED_REFRESH_KEYS:
        if key not in merge_js:
            errors.append(f"Merge refreshed lookup missing refresh key: {key}")

    active = next(n for n in data["nodes"] if n.get("name") == "Active product row")
    active_js = active["parameters"]["jsCode"]
    for col in ("Prompt Title", "Prompt Description", "Vendor", "Product category"):
        if col not in active_js:
            errors.append(f"Active product row missing column: {col}")
    if "return obj;" in active_js and "function resolvePromptFields" not in active_js:
        errors.append("Active product row has stray 'return obj' (SyntaxError)")
    if active_js.count("function browserDomain") != 1:
        errors.append("Active product row browserDomain function is broken/duplicated")

    names = {n.get("name") for n in data["nodes"]}
    if "Re-read sheet row" not in names:
        errors.append("missing Re-read sheet row node")
    if "Re-read sheet after scrape" not in names:
        errors.append("missing Re-read sheet after scrape node")

    if errors:
        print("WORKFLOW/SHEET MISALIGNMENT:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("OK: workflow aligned with sheet-products.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
