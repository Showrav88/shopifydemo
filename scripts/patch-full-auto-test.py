#!/usr/bin/env python3
"""Full auto test mode: Product URL only → QA pass → Shopify create (no client gate)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

IS_ROW_DONE = """function isRowDone(row) {
  const shopifyUrl = String(row['Shopify Product URL'] || '').trim();
  if (shopifyUrl) return true;
  const status = String(row['Status'] || '').trim().toUpperCase();
  if (['LIVE_DRAFT', 'PUBLISHED'].includes(status)) return true;
  const qa = String(row['QA Status'] || '').trim().toUpperCase();
  const score = Number(row['AI Score'] || 0);
  return (qa === 'PASS' || qa === 'PASS_NO_IMAGE') && score >= 90 && shopifyUrl;
}"""

STICKY = (
    "## Full auto test — Product URL only\n\n"
    "**Paste Product URL** → scrape → AI listing → QA → **Shopify draft** (no manual input).\n\n"
    "**Auto defaults when sheet empty:**\n"
    "- **Price** → Competitor price from scrape\n"
    "- **Inventory** → 10 (split across variants)\n"
    "- **Sizes** → from scrape\n\n"
    "Sheet: `url_input` / `url_input.csv`"
)

SHEET_STICKY = (
    "## Sheet — you only type Product URL\n\n"
    "| Product URL | Paste once — everything else is automatic |\n\n"
    "Workflow writes: Title, Description, Sizes, Price (from competitor), stock, Shopify URLs"
)


def main():
    data = json.loads(WORKFLOW.read_text())

    for node in data["nodes"]:
        name = node.get("name", "")
        p = node.get("parameters", {})

        if name == "Validate sheet row":
            code = p["jsCode"]
            start = code.index("function isRowDone(row)")
            end = code.index("}", start) + 1
            p["jsCode"] = code[:start] + IS_ROW_DONE + code[end:]

        elif name == "Setup Instructions":
            p["content"] = STICKY

        elif name == "Sheet Input Data":
            p["content"] = SHEET_STICKY

        elif name == "Update sheet QA score":
            vals = p["columns"]["value"]
            vals.pop("Status", None)

        elif name == "Update sheet QA failed":
            vals = p["columns"]["value"]
            vals["Status"] = "NEEDS_REVIEW"

        elif name == "Update sheet Shopify URLs":
            vals = p["columns"]["value"]
            vals["Status"] = "LIVE_DRAFT"
            vals["Price"] = "={{ $('Build Shopify product').item.json.shopify_payload.product.variants[0].price || '' }}"
            vals["Inventory quantity"] = (
                "={{ $('Build Shopify product').item.json.inventory_updates[0].inventory_quantity || '' }}"
            )

    data["connections"]["QA score check 90"]["main"][0] = [
        {"node": "Build Shopify product", "type": "main", "index": 0}
    ]

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched full auto test mode into", WORKFLOW)


if __name__ == "__main__":
    main()
