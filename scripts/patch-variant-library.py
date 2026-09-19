#!/usr/bin/env python3
"""Patch workflow for separate VariantLibrary sheet + flexible Shopify options."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"


def patch_prepare_scrape_write(data: dict) -> None:
    for node in data["nodes"]:
        if node.get("name") != "Prepare sheet scrape write":
            continue
        js = node["parameters"]["jsCode"]
        for line in ["    'Colors': s.Colors || '',\n", "    'Lengths': s.Lengths || '',\n"]:
            js = js.replace(line, "")
        if "// Colors: lookup formula" not in js and "// VariantLibrary formulas" not in js:
            js = js.replace(
                "    'Sizes': s.Sizes || '',\n",
                "    'Sizes': s.Sizes || '',\n    // VariantLibrary formulas — do not write Colors/Lengths/Options\n",
            )
        node["parameters"]["jsCode"] = js


def ensure_option_formula_keys(data: dict) -> None:
    keys = [
        "'Option 1 name',", "'Option 1 values',", "'Option 2 name',", "'Option 2 values',",
        "'Option 3 name',", "'Option 3 values',", "'Lengths',",
    ]
    for node in data["nodes"]:
        if node.get("name") not in ("Active product row", "Merge refreshed lookup"):
            continue
        js = node["parameters"]["jsCode"]
        if "'Option 1 name'," in js:
            continue
        js = js.replace(
            "  'Collection',\n  'Colors',",
            "  'Collection',\n  'Option 1 name',\n  'Option 1 values',\n  "
            "'Option 2 name',\n  'Option 2 values',\n  'Option 3 name',\n  'Option 3 values',\n  "
            "'Colors',\n  'Lengths',",
        )
        node["parameters"]["jsCode"] = js


def main() -> None:
    scripts = ROOT / "scripts"
    subprocess.check_call([sys.executable, str(scripts / "patch-suggested-shopify-fallback.py")])
    subprocess.check_call([sys.executable, str(scripts / "patch-sheet-workflow-alignment.py")])

    data = json.loads(WORKFLOW.read_text())
    patch_prepare_scrape_write(data)
    ensure_option_formula_keys(data)

    sticky = next((n for n in data["nodes"] if n.get("name") == "Sheet Input Data"), None)
    if sticky:
        sticky["parameters"]["content"] = (
            "## Sheet tabs\n\n"
            "**Master_Sheetv1** — paste Product URL + optional Variant preset ID + Prompt ID\n\n"
            "**VariantLibrary** — edit presets (UK/US sizes, 10 colors, any Shopify option combo)\n\n"
            "**LookupTables** — vendor, category, collection only (no variant data)\n\n"
            "**PromptLibrary** — AI prompts by Prompt ID\n\n"
            "Variant preset ID examples: `uk-shirts`, `us-jeans`, `uk-shoes`, `bags`, `custom`"
        )

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")

    build = next(n for n in data["nodes"] if n.get("name") == "Build Shopify product")
    if "parseOptionConfig" not in build["parameters"]["jsCode"]:
        raise SystemExit("Build Shopify product missing parseOptionConfig")
    print("Patched VariantLibrary workflow")


if __name__ == "__main__":
    main()
