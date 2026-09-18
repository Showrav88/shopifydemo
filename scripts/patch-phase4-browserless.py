#!/usr/bin/env python3
"""Phase 4: Browserless routing for bot-protected sites (Macy's, Mango, etc.)."""
import json
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
EXTRACTORS = (ROOT / "scripts" / "n8n-scrape-extractors.js").read_text()
EXTRACTORS = re.sub(r"\nif \(typeof module.*", "", EXTRACTORS)
EXTRACTORS = EXTRACTORS.replace("const SCRAPE_EXTRACTORS = {};", "const SCRAPE = {};")
EXTRACTORS = EXTRACTORS.replace("SCRAPE_EXTRACTORS.", "SCRAPE.")

ROUTE_JS = EXTRACTORS + r"""

const row = $('Validate sheet row').first().json;
const productUrl = row.source_product_url || row['Product URL'] || '';
const forceBrowser = SCRAPE.isForceBrowser(row);
const prevStatus = String(row['Scrape Status'] || '').trim().toUpperCase();
const retryBrowser = prevStatus === 'NEEDS_BROWSER' || prevStatus === 'SCRAPED_PARTIAL';

let fetchMethod = SCRAPE.pickFetchStrategy(productUrl, { forceBrowser, row });
if (retryBrowser) fetchMethod = 'browser';

const useBrowser = fetchMethod === 'browser' || forceBrowser || retryBrowser;
const botProtectionExpected = SCRAPE.BROWSER_DOMAINS.some((d) => {
  const host = SCRAPE.hostname(productUrl);
  return host === d || host.endsWith('.' + d);
});

return [{
  json: {
    ...row,
    fetch_method: fetchMethod,
    force_browser: forceBrowser,
    use_browser: useBrowser,
    bot_protection_expected: botProtectionExpected,
    scrape_method_planned: useBrowser ? 'browser' : fetchMethod,
  },
}];
"""

WRAP_BROWSER_JS = r"""const raw = $input.first().json;
let body = '';
if (typeof raw === 'string') body = raw;
else body = raw.data ?? raw.body ?? raw.content ?? '';
if (typeof body !== 'string') {
  try { body = JSON.stringify(body); } catch { body = String(body); }
}
const route = $('Route scrape method').first().json;
return [{
  json: {
    data: body,
    body,
    scrape_method: 'browser',
    bot_protection_bypassed: body.length > 500 && !/access denied|checking your browser/i.test(body),
  },
  pairedItem: { item: 0 },
}];
"""

NORMALIZE_HTTP_JS = r"""const raw = $input.first().json;
let body = raw.data ?? raw.body ?? '';
if (typeof body !== 'string') {
  try { body = JSON.stringify(body); } catch { body = String(body); }
}
return [{
  json: {
    data: body,
    body,
    scrape_method: 'http',
    bot_protection_bypassed: false,
  },
}];
"""

PREPARE_APPEND = r"""
const scrapeMethod = http.scrape_method || row.scrape_method_planned || row.fetch_method || 'http';
snippet.scrape_method = scrapeMethod;
snippet.bot_protection_bypassed = Boolean(http.bot_protection_bypassed);
snippet.bot_protection_expected = Boolean(row.bot_protection_expected);
"""

APPLY_SCRAPE_METHOD = r"""
const scrapeMethodUsed = row.scrape_context?.scrape_method || row.scrape_method_planned || row.fetch_method || 'http';
const botBypassed = Boolean(row.scrape_context?.bot_protection_bypassed);
"""


def patch_prepare_wrapper(wrapper: str) -> str:
    if "snippet.scrape_method" in wrapper:
        return wrapper
    return wrapper.replace(
        "  html_excerpt: body.replace",
        PREPARE_APPEND + "\n  html_excerpt: body.replace",
    )


def main():
    # Refresh extractors in prepare/apply
    prep = ROOT / "scripts" / "patch-production-scrape.py"
    prep_text = prep.read_text()
    old = 'PREPARE_WRAPPER = r"""\nconst row = $('
    if "snippet.scrape_method" not in prep_text:
        # patch prepare in production scrape script permanently
        prep.write_text(prep_text.replace(
            "  html_excerpt: body.replace",
            PREPARE_APPEND + "\n  html_excerpt: body.replace",
        ))
    subprocess.run([sys.executable, str(prep)], check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "patch-skip-no-image.py")], check=True)

    path = ROOT / "ShopifyProductAdd.V2.json"
    data = json.loads(path.read_text())

    browserless_node = {
        "parameters": {
            "method": "POST",
            "url": "https://production-sfo.browserless.io/content",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpQueryAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                "={{ JSON.stringify({ "
                "url: $('Route scrape method').first().json.source_product_url "
                "|| $('Route scrape method').first().json['Product URL'], "
                "gotoOptions: { waitUntil: 'networkidle2', timeout: 45000 } "
                "}) }}"
            ),
            "options": {
                "timeout": 90000,
                "response": {"response": {"responseFormat": "text"}},
            },
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.5,
        "position": [-1440, -240],
        "id": str(uuid4()),
        "name": "Browserless fetch page",
        "onError": "continueRegularOutput",
        "credentials": {"httpQueryAuth": {"name": "Browserless API"}},
    }

    route_node = {
        "parameters": {"jsCode": ROUTE_JS},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-1440, -120],
        "id": str(uuid4()),
        "name": "Route scrape method",
    }

    use_browser_if = {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "loose",
                    "version": 3,
                },
                "conditions": [{
                    "id": "use-browser",
                    "leftValue": "={{ $json.use_browser }}",
                    "rightValue": True,
                    "operator": {
                        "type": "boolean",
                        "operation": "true",
                        "singleValue": True,
                    },
                }],
                "combinator": "and",
            },
            "looseTypeValidation": True,
            "options": {},
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.3,
        "position": [-1320, -120],
        "id": str(uuid4()),
        "name": "Use browser?",
    }

    wrap_node = {
        "parameters": {"jsCode": WRAP_BROWSER_JS},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-1180, -240],
        "id": str(uuid4()),
        "name": "Wrap browser HTML",
    }

    normalize_node = {
        "parameters": {"jsCode": NORMALIZE_HTTP_JS},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-1180, -40],
        "id": str(uuid4()),
        "name": "Normalize HTTP page",
    }

    # Replace or add nodes
    names_to_replace = {
        "Route scrape method", "Use browser?", "Browserless fetch page",
        "Wrap browser HTML", "Normalize HTTP page",
    }
    data["nodes"] = [n for n in data["nodes"] if n.get("name") not in names_to_replace]
    data["nodes"].extend([route_node, use_browser_if, browserless_node, wrap_node, normalize_node])

    # Patch Apply scraped data for scrape method + SCRAPED_BROWSER
    apply_status_patch = r"""
if (!imageUrl) {
  scrapeStatus = fetchStrategy === 'browser' ? 'NEEDS_BROWSER' : 'SCRAPED_NO_IMAGE';
} else if (scrapeMethodUsed === 'browser' && botBypassed) {
  scrapeStatus = 'SCRAPED_BROWSER';
} else if (fetchStrategy === 'browser' && !hasVariants && !hasSizes && !hasColors) {
  scrapeStatus = 'SCRAPED_PARTIAL';
}
"""
    for node in data["nodes"]:
        if node.get("name") == "Apply scraped data":
            code = node["parameters"]["jsCode"]
            if "scrapeMethodUsed" not in code:
                code = code.replace(
                    "const extractionSources = structured._sources || {};",
                    APPLY_SCRAPE_METHOD + "\nconst extractionSources = structured._sources || {};\n",
                )
                code = re.sub(
                    r"let scrapeStatus = 'SCRAPED';[\s\S]*?scrapeStatus = 'SCRAPED_PARTIAL';",
                    apply_status_patch.strip(),
                    code,
                    count=1,
                )
                code = code.replace(
                    "'Scrape Status': scrapeStatus,",
                    "'Scrape Status': scrapeStatus,\n    'Scrape method': scrapeMethodUsed,",
                )
                node["parameters"]["jsCode"] = code
        elif node.get("name") == "Prepare sheet scrape write":
            code = node["parameters"]["jsCode"]
            if "'Scrape method'" not in code:
                code = code.replace(
                    "'Scrape Status': s['Scrape Status']",
                    "'Scrape Status': s['Scrape Status'],\n    'Scrape method': s['Scrape method'] || ''",
                )
                node["parameters"]["jsCode"] = code
        elif node.get("name") == "Update sheet scraped":
            cols = node["parameters"]["columns"]["value"]
            cols["Scrape method"] = "={{ $json['Scrape method'] }}"
        elif node.get("name") == "Update sheet scrape blocked":
            cols = node["parameters"]["columns"]["value"]
            cols["Scrape method"] = "={{ $json['Scrape method'] || 'blocked' }}"
            cols["Scrape Status"] = "={{ $json['Scrape Status'] }}"
        elif node.get("name") == "Prepare scrape blocked":
            node["parameters"]["jsCode"] = node["parameters"]["jsCode"].replace(
                "? 'Site blocks HTTP scraper (Akamai/Cloudflare). Phase 4: add Browserless node, or paste Product image URL manually.'",
                "? 'Bot protection (Akamai/Cloudflare). Set Force browser=YES and add Browserless API credential, or paste Product image URL manually.'",
            ).replace(
                "'Product image URL': '',",
                "'Scrape method': 'blocked',\n    'Product image URL': '',",
            )

    # Rewire scrape path
    data["connections"]["Needs scrape"] = {
        "main": [
            [{"node": "Route scrape method", "type": "main", "index": 0}],
            [{"node": "Active product row", "type": "main", "index": 0}],
        ]
    }
    data["connections"]["Route scrape method"] = {
        "main": [[{"node": "Use browser?", "type": "main", "index": 0}]]
    }
    data["connections"]["Use browser?"] = {
        "main": [
            [{"node": "Browserless fetch page", "type": "main", "index": 0}],
            [{"node": "Fetch product page", "type": "main", "index": 0}],
        ]
    }
    data["connections"]["Browserless fetch page"] = {
        "main": [[{"node": "Wrap browser HTML", "type": "main", "index": 0}]]
    }
    data["connections"]["Wrap browser HTML"] = {
        "main": [[{"node": "Prepare page for scrape", "type": "main", "index": 0}]]
    }
    data["connections"]["Fetch product page"] = {
        "main": [[{"node": "Normalize HTTP page", "type": "main", "index": 0}]]
    }
    data["connections"]["Normalize HTTP page"] = {
        "main": [[{"node": "Prepare page for scrape", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Phase 4 Browserless routing patched into", path)


if __name__ == "__main__":
    main()
