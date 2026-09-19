#!/usr/bin/env python3
"""Patch workflow: default sizes when scrape misses variants, Colors from lookup, Browserless docs."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

PREPARE_SCRAPE_WRITE_OLD = "'Colors': s.Colors || '',\n"
PREPARE_SCRAPE_WRITE_NEW = "    // Colors: lookup formula on sheet — do not write from scrape\n"

ACTIVE_SCRAPED_MERGE_OLD = """try {
  const scraped = $('Apply scraped data').first().json;
  if (scraped && typeof scraped === 'object') merged = { ...merged, ...scraped };
} catch { /* scrape branch did not run */ }"""

ACTIVE_SCRAPED_MERGE_NEW = """try {
  const scraped = $('Apply scraped data').first().json;
  if (scraped && typeof scraped === 'object') merged = { ...merged, ...scraped };
} catch { /* scrape branch did not run */ }
try {
  const freshRow = $('Re-read sheet after scrape').first().json;
  merged = overlaySheetFormulas(merged, freshRow);
} catch { /* formula overlay after scrape */ }"""


def patch_prepare_scrape_write(data: dict) -> None:
    for node in data["nodes"]:
        if node.get("name") != "Prepare sheet scrape write":
            continue
        js = node["parameters"]["jsCode"]
        js = js.replace("    'Colors': s.Colors || '',\n", PREPARE_SCRAPE_WRITE_NEW)
        node["parameters"]["jsCode"] = js


def patch_active_product_row_overlay(data: dict) -> None:
    for node in data["nodes"]:
        if node.get("name") != "Active product row":
            continue
        js = node["parameters"]["jsCode"]
        if "formula overlay after scrape" in js:
            return
        if ACTIVE_SCRAPED_MERGE_OLD in js:
            js = js.replace(ACTIVE_SCRAPED_MERGE_OLD, ACTIVE_SCRAPED_MERGE_NEW)
        node["parameters"]["jsCode"] = js


def ensure_colors_in_formula_keys(data: dict) -> None:
    for node in data["nodes"]:
        if node.get("name") not in ("Active product row", "Merge refreshed lookup"):
            continue
        js = node["parameters"]["jsCode"]
        if "'Colors'," not in js and "SHEET_FORMULA_KEYS" in js:
            js = js.replace(
                "  'Collection',\n  'Prompt ID',",
                "  'Collection',\n  'Colors',\n  'Prompt ID',",
            )
            node["parameters"]["jsCode"] = js


def main() -> None:
    scripts = ROOT / "scripts"
    subprocess.check_call([sys.executable, str(scripts / "patch-suggested-shopify-fallback.py")])
    subprocess.check_call([sys.executable, str(scripts / "patch-sheet-workflow-alignment.py")])

    data = json.loads(WORKFLOW.read_text())
    patch_prepare_scrape_write(data)
    patch_active_product_row_overlay(data)
    ensure_colors_in_formula_keys(data)
    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")

    build = next(n for n in data["nodes"] if n.get("name") == "Build Shopify product")
    if "DEFAULT_SIZES" not in build["parameters"]["jsCode"]:
        raise SystemExit("Build Shopify product missing DEFAULT_SIZES — patch failed")
    print("Patched variant defaults, sell colors lookup, and Browserless-safe sheet writes")

if __name__ == "__main__":
    main()
