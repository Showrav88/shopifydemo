#!/usr/bin/env python3
"""Phase 1: stop after QA PASS — set Status READY_FOR_CLIENT, do not create Shopify yet."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

STATUS_READY_EXPR = (
    "={{ (() => { const o = $('Check text overlap').item.json; "
    "if (o.overlap_fail) return ''; "
    "const score = Number(JSON.parse($('AI QA score listing').item.json.output[0].content[0].text"
    ".replace(/```json|```/g, '').trim()).quality_score); "
    "return score >= 90 ? 'READY_FOR_CLIENT' : ''; })() }}"
)

IS_ROW_DONE_PATCH = """function isRowDone(row) {
  const status = String(row['Status'] || '').trim().toUpperCase();
  if (['READY_FOR_CLIENT', 'APPROVED', 'LIVE_DRAFT', 'PUBLISHED'].includes(status)) return true;
  const qa = String(row['QA Status'] || '').trim().toUpperCase();
  const score = Number(row['AI Score'] || 0);
  return (qa === 'PASS' || qa === 'PASS_NO_IMAGE') && score >= 90;
}"""

STICKY = (
    "## Phase 1 — scrape + listing + QA (stops here)\n\n"
    "**START:** Paste **Product URL** → scrape → AI listing → QA.\n\n"
    "**On QA PASS:** sheet **Status** = `READY_FOR_CLIENT` — workflow **stops**. "
    "Client fills **Price**, **Inventory quantity**, **Sizes** (confirm/override), then **Approve** (Phase 2).\n\n"
    "**On QA FAIL:** Status = `NEEDS_REVIEW`.\n\n"
    "Sheet: `url_input` / `url_input.csv` | Match column: **Product URL**"
)


def main():
    data = json.loads(WORKFLOW.read_text())

    for node in data["nodes"]:
        name = node.get("name", "")
        p = node.get("parameters", {})

        if name == "Validate sheet row":
            code = p["jsCode"]
            old = code.split("function isRowDone(row)")[1].split("}")[0]
            p["jsCode"] = code.replace(
                "function isRowDone(row)" + old + "}",
                IS_ROW_DONE_PATCH,
                1,
            )

        elif name == "Update sheet QA score":
            p["columns"]["value"]["Status"] = STATUS_READY_EXPR

        elif name == "Update sheet QA failed":
            p["columns"]["value"]["Status"] = "NEEDS_REVIEW"

        elif name == "Setup Instructions":
            p["content"] = STICKY

        elif name == "Sheet Input Data":
            p["content"] = (
                "## Sheet columns\n\n"
                "### Phase 1 — automation writes:\n"
                "Title, Description, image URL, Sizes, Colors, competitor price, QA Status, AI Score\n\n"
                "### Phase 1 — client waits for Status = `READY_FOR_CLIENT` then fills:\n"
                "| Price | Your sell price |\n"
                "| Inventory quantity | Stock to list |\n"
                "| Sizes / Colors | Confirm or override scrape |\n"
                "| Approve | `YES` when ready (Phase 2) |\n\n"
                "### YOU start with:\n"
                "| Product URL | Triggers scrape |"
            )

    # Phase 1: QA pass does NOT continue to Shopify create
    conn = data["connections"]
    conn["QA score check 90"]["main"][0] = []

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched Phase 1 client gate into", WORKFLOW)


if __name__ == "__main__":
    main()
