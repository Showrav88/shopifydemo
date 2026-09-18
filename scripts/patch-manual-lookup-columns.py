#!/usr/bin/env python3
"""Vendor/category in C–F formulas; prompt manual + Suggested Prompt* fallback."""
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

// Vendor/category come from C–F sheet formulas (re-read fresh). Prompts: manual or Suggested*.
const promptPairs = [
  ['Prompt Title', 'Suggested Prompt Title'],
  ['Prompt Description', 'Suggested Prompt Description'],
  ['Prompt Tags', 'Suggested Prompt Tags'],
  ['Prompt SEO title', 'Suggested Prompt SEO title'],
  ['Prompt SEO description', 'Suggested Prompt SEO description'],
  ['Prompt Image alt', 'Suggested Prompt Image alt'],
  ['Prompt Category', 'Suggested Prompt Category'],
];
for (const [manual, suggested] of promptPairs) {
  row[manual] = pickManualOrSuggested(manual, suggested);
}

for (const key of ['Vendor', 'Product category', 'Variant profile', 'Collection']) {
  const v = String(fresh[key] ?? '').trim();
  if (v) row[key] = v;
}

const promptId = String(fresh['Prompt ID'] ?? row['Prompt ID'] ?? '').trim();
if (promptId) row['Prompt ID'] = promptId;

return [{ json: row }];
"""

RESOLVE_SNIPPET = r"""
function resolvePromptFields(obj) {
  const pairs = [
    ['Prompt Title', 'Suggested Prompt Title'],
    ['Prompt Description', 'Suggested Prompt Description'],
    ['Prompt Tags', 'Suggested Prompt Tags'],
    ['Prompt SEO title', 'Suggested Prompt SEO title'],
    ['Prompt SEO description', 'Suggested Prompt SEO description'],
    ['Prompt Image alt', 'Suggested Prompt Image alt'],
    ['Prompt Category', 'Suggested Prompt Category'],
  ];
  for (const [manual, suggested] of pairs) {
    const m = String(obj[manual] ?? '').trim();
    const s = String(obj[suggested] ?? '').trim();
    if (!m && s) obj[manual] = s;
  }
  return obj;
}
"""


def main():
    data = json.loads(WORKFLOW.read_text())

    merge = next(n for n in data["nodes"] if n.get("name") == "Merge refreshed lookup")
    merge["parameters"]["jsCode"] = MERGE_JS

    active = next(n for n in data["nodes"] if n.get("name") == "Active product row")
    js = active["parameters"]["jsCode"]
    js = js.replace("resolveLookupFields", "resolvePromptFields")
    if "function resolvePromptFields" not in js:
        js = js.replace(
            "merged.needs_browser_site = browserDomain",
            RESOLVE_SNIPPET + "merged = resolvePromptFields(merged);\n\nmerged.needs_browser_site = browserDomain",
        )
    else:
        start = js.find("function resolvePromptFields")
        end = js.find("}\n", start) + 2
        js = js[:start] + RESOLVE_SNIPPET.strip() + "\n\n" + js[end:]
    active["parameters"]["jsCode"] = js

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched workflow: C–F lookup + Suggested Prompt* only")


if __name__ == "__main__":
    main()
