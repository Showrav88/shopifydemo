#!/usr/bin/env python3
"""Re-read sheet row before Shopify — C–F lookup + prompt columns from formulas."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

MERGE_JS = r"""const base = $('Active product row').first().json;
const row = { ...base };
const fresh = $('Re-read sheet row').first().json;

const refreshKeys = [
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
for (const key of refreshKeys) {
  const v = String(fresh[key] ?? '').trim();
  if (v) row[key] = v;
}

return [{ json: row }];
"""


def main():
    data = json.loads(WORKFLOW.read_text())

    merge = next(n for n in data["nodes"] if n.get("name") == "Merge refreshed lookup")
    merge["parameters"]["jsCode"] = MERGE_JS

    active = next(n for n in data["nodes"] if n.get("name") == "Active product row")
    js = active["parameters"]["jsCode"]
    # Remove resolvePromptFields — prompts read directly from sheet columns
    if "function resolvePromptFields" in js:
        start = js.find("\nfunction resolvePromptFields")
        end = js.find("}\n\n", start) + 3
        js = js[:start] + js[end:]
    js = js.replace("merged = resolvePromptFields(merged);\n\n", "")
    active["parameters"]["jsCode"] = js

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched workflow: direct sheet columns only (no Suggested* fallback)")


if __name__ == "__main__":
    main()
