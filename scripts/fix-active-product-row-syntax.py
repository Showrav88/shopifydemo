#!/usr/bin/env python3
"""Fix stray 'return obj' lines left in Active product row from bad patch merge."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

BROKEN = """function browserDomain(url) {
  const host = String(url || '').replace(/^https?:\\/\\//, '').split('/')[0].replace(/^www\\./, '').toLowerCase();
  const hard = ['macys.com', 'mango.com', 'express.com', 'nordstrom.com', 'zara.com', 'hm.com', 'asos.com'];
  return hard.some((d) => host === d || host.endsWith('.' + d));
}
  return obj;
}

  return obj;
}
merged.needs_browser_site"""

FIXED = """function browserDomain(url) {
  const host = String(url || '').replace(/^https?:\\/\\//, '').split('/')[0].replace(/^www\\./, '').toLowerCase();
  const hard = ['macys.com', 'mango.com', 'express.com', 'nordstrom.com', 'zara.com', 'hm.com', 'asos.com'];
  return hard.some((d) => host === d || host.endsWith('.' + d));
}

merged.needs_browser_site"""


def main():
    data = json.loads(WORKFLOW.read_text())
    active = next(n for n in data["nodes"] if n.get("name") == "Active product row")
    js = active["parameters"]["jsCode"]
    if BROKEN in js:
        js = js.replace(BROKEN, FIXED)
    # Generic cleanup of orphaned resolvePromptFields fragments
    js = re.sub(r"\n\s*return obj;\s*\}\s*\n\s*return obj;\s*\}\n", "\n", js)
    if "return obj;" in js and "function resolvePromptFields" not in js:
        raise SystemExit("Active product row still contains stray return obj — fix manually")
    active["parameters"]["jsCode"] = js
    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Fixed Active product row syntax")


if __name__ == "__main__":
    main()
