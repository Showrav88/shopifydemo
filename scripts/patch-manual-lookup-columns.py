#!/usr/bin/env python3
"""Manual Vendor/Category cols + Suggested* formula fallback in workflow."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

MERGE_JS = r"""const base = $('Active product row').first().json;
const row = { ...base };
const fresh = $('Re-read sheet row').first().json;

function pickManualOrSuggested(manualKey, suggestedKey) {
  const manual = String(fresh[manualKey] ?? row[manualKey] ?? '').trim();
  if (manual) return manual;
  return String(fresh[suggestedKey] ?? row[suggestedKey] ?? '').trim();
}

row.Vendor = pickManualOrSuggested('Vendor', 'Suggested Vendor');
row['Product category'] = pickManualOrSuggested('Product category', 'Suggested Product category');
row['Variant profile'] = pickManualOrSuggested('Variant profile', 'Suggested Variant profile');
row.Collection = pickManualOrSuggested('Collection', 'Suggested Collection');

const promptKeys = [
  'Prompt ID',
  'Prompt Title',
  'Prompt Description',
  'Prompt Tags',
  'Prompt SEO title',
  'Prompt SEO description',
  'Prompt Image alt',
  'Prompt Category',
];
for (const key of promptKeys) {
  const v = String(fresh[key] ?? '').trim();
  if (v) row[key] = v;
}
return [{ json: row }];
"""

RESOLVE_SNIPPET = r"""
function resolveLookupFields(obj) {
  const pairs = [
    ['Vendor', 'Suggested Vendor'],
    ['Product category', 'Suggested Product category'],
    ['Variant profile', 'Suggested Variant profile'],
    ['Collection', 'Suggested Collection'],
  ];
  for (const [manual, suggested] of pairs) {
    const m = String(obj[manual] ?? '').trim();
    const s = String(obj[suggested] ?? '').trim();
    if (!m && s) obj[manual] = s;
  }
  return obj;
}
"""

ACTIVE_MARKER = "merged.needs_browser_site = browserDomain"
ACTIVE_INJECT = "merged = resolveLookupFields(merged);\n\nmerged.needs_browser_site = browserDomain"


def main():
    data = json.loads(WORKFLOW.read_text())

    merge = next(n for n in data["nodes"] if n.get("name") == "Merge refreshed lookup")
    merge["parameters"]["jsCode"] = MERGE_JS

    active = next(n for n in data["nodes"] if n.get("name") == "Active product row")
    js = active["parameters"]["jsCode"]
    if "resolveLookupFields" not in js:
        js = js.replace(
            "merged.needs_browser_site = browserDomain",
            RESOLVE_SNIPPET + ACTIVE_INJECT,
        )
        active["parameters"]["jsCode"] = js

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched workflow: manual Vendor/Category with Suggested* fallback")


if __name__ == "__main__":
    main()
