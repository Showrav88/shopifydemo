#!/usr/bin/env python3
"""Patch workflow: re-inject scrape extractors + sync isDirectImageUrl in Active product row."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Re-run production scrape patch (Prepare + Apply nodes)
subprocess.run([sys.executable, str(ROOT / "scripts" / "patch-production-scrape.py")], check=True)

path = ROOT / "ShopifyProductAdd.V2.json"
data = json.loads(path.read_text())

CDN_IMAGE_CHECKS = r"""
  if (/\\/cdn\\/shop\\//i.test(u)) return true;
  if (/\\/is\\/image\\//i.test(u)) return true;
  if (/images\\.(lululemon|scene7)\\./i.test(u)) return true;
  if (/scene7\\.com/i.test(u)) return true;
  if (/[?&](?:wid|width|hei|height|fmt|format)=/i.test(u) && /\\/(?:is\\/image|images?)\\//i.test(u)) return true;
  return false;
"""

for node in data["nodes"]:
    name = node.get("name", "")
    if name not in ("Active product row", "Validate sheet row"):
        continue
    code = node["parameters"].get("jsCode", "")
    if "/is/image/" in code:
        continue
    # Replace old isDirectImageUrl tail (before return false)
    old_tail = r"if \(/\\/media\\/catalog\\/product\\//i\.test\(u\)\) return true;\s*return false;"
    if re.search(old_tail, code):
        new_tail = (
            "if (/\\/media\\/catalog\\/product\\//i.test(u)) return true;\n"
            "  if (/\\/cdn\\/shop\\//i.test(u)) return true;\n"
            "  if (/\\/is\\/image\\//i.test(u)) return true;\n"
            "  if (/images\\.(lululemon|scene7)\\./i.test(u)) return true;\n"
            "  if (/scene7\\.com/i.test(u)) return true;\n"
            "  if (/[?&](?:wid|width|hei|height|fmt|format)=/i.test(u) && /\\/(?:is\\/image|images?)\\//i.test(u)) return true;\n"
            "  return false;"
        )
        code = re.sub(old_tail, new_tail, code, count=1)
        node["parameters"]["jsCode"] = code
        print(f"Patched isDirectImageUrl in {name}")

# Re-inject variant + organization builders into Build Shopify product node
variants_js = (ROOT / "scripts" / "n8n-shopify-variants.js").read_text()
variants_js = re.sub(r"\nif \(typeof module.*", "", variants_js)
org_js = (ROOT / "scripts" / "n8n-shopify-organization.js").read_text()
org_js = re.sub(r"\nif \(typeof module.*", "", org_js)

for node in data["nodes"]:
    if node.get("name") == "Build Shopify product":
        existing = node["parameters"].get("jsCode", "")
        marker = "const row = $('Active product row')"
        if marker in existing:
            tail = existing[existing.index(marker):]
            node["parameters"]["jsCode"] = variants_js + "\n\n" + org_js + "\n\n" + tail
            print("Patched Build Shopify product variant builder")

path.write_text(json.dumps(data, indent=2) + "\n")
print("Done:", path)
