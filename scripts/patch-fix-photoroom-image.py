#!/usr/bin/env python3
"""Fix empty Product image URL reaching Photoroom — deeper scrape fallbacks + re-scrape trigger."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "ShopifyProductAdd.V2.json"

IS_DIRECT_FN = """
function isDirectImageUrl(url) {
  const u = String(url || '').trim().replace(/&amp;/g, '&');
  if (!u.startsWith('http')) return false;
  if (/\\.html(?:\\?|$|#)/i.test(u)) return false;
  if (/\\.(jpe?g|png|webp|gif|avif)(\\?|$|#)/i.test(u)) return true;
  if (/\\/catalog\\/product\\//i.test(u)) return true;
  if (/\\/wp-content\\/uploads\\//i.test(u)) return true;
  if (/\\/media\\/catalog\\/product\\//i.test(u)) return true;
  return false;
}
"""

PICK_IMAGE_BLOCK = """
function pickImageUrl(merged) {
  const tryOne = (u) => (isDirectImageUrl(u) ? String(u).trim().replace(/&amp;/g, '&') : '');
  const tryList = (arr) => {
    for (const u of arr || []) {
      const ok = tryOne(u);
      if (ok) return ok;
    }
    return '';
  };

  let img = tryList([merged.validated_image_url, merged['Product image URL'], merged.image_url]);
  if (img) return img;

  try {
    const scraped = $('Apply scraped data').first().json;
    img = tryList([scraped?.validated_image_url, scraped?.['Product image URL'], scraped?.image_url]);
    if (img) return img;
    if (scraped && typeof scraped === 'object') merged = { ...merged, ...scraped };
  } catch { /* scrape branch did not run this execution */ }

  const ctx = { ...(merged.scrape_context || {}) };
  try {
    const prep = $('Prepare page for scrape').first().json;
    if (prep?.scrape_context) Object.assign(ctx, prep.scrape_context);
  } catch { /* prepare did not run */ }

  const structured = ctx.structured || {};
  return tryList([
    structured.image_url,
    ctx.og_image,
    ...(structured.candidate_images || []),
    ...(ctx.candidate_images || []),
  ]);
}
"""

ACTIVE_OLD = """try {
  const scraped = $('Apply scraped data').first().json;
  if (scraped?.validated_sku) merged = { ...merged, ...scraped };
} catch { /* scrape branch did not run */ }

if (!isDirectImageUrl(merged.validated_image_url)) {
  merged.validated_image_url = isDirectImageUrl(merged['Product image URL']) ? merged['Product image URL'] : '';
}
if (!merged['Product image URL'] && isDirectImageUrl(merged.validated_image_url)) {
  merged['Product image URL'] = merged.validated_image_url;
}"""

ACTIVE_NEW = """try {
  const scraped = $('Apply scraped data').first().json;
  if (scraped && typeof scraped === 'object') merged = { ...merged, ...scraped };
} catch { /* scrape branch did not run */ }

const resolvedImage = pickImageUrl(merged);
if (resolvedImage) {
  merged.validated_image_url = resolvedImage;
  merged['Product image URL'] = resolvedImage;
} else {
  merged.validated_image_url = '';
  if (!isDirectImageUrl(merged['Product image URL'])) merged['Product image URL'] = '';
}"""

VALIDATE_NEEDS_OLD = """  const imageUrl = String(row['Product image URL'] || '').trim();
  const title = String(row['Title'] || '').trim();
  if (!imageUrl || !title) return true;"""

VALIDATE_NEEDS_NEW = """  const imageUrl = String(row['Product image URL'] || row.validated_image_url || '').trim();
  const title = String(row['Title'] || '').trim();
  if (!isDirectImageUrl(imageUrl) || !title) return true;"""

PHOTOROOM_EXPR = (
    "={{ (() => { const row = $('Active product row').first().json; "
    "const u = row['Product image URL'] || row.validated_image_url || ''; "
    "if (!u || /\\.html(\\?|$|#)/i.test(u)) { "
    "const src = row['Product URL'] || row.source_product_url || 'this product'; "
    "throw new Error('No product image URL for ' + src + '. Clear Scrape Status cell and re-trigger, or paste a direct .jpg URL in Product image URL column.'); "
    "} return u; })() }}"
)


def main():
    data = json.loads(WORKFLOW.read_text())

    for node in data["nodes"]:
        name = node.get("name", "")
        p = node.get("parameters", {})

        if name == "Validate sheet row":
            code = p["jsCode"]
            if "function isDirectImageUrl" not in code:
                code = code.replace(
                    "function getProductUrl(row)",
                    IS_DIRECT_FN + "\nfunction getProductUrl(row)",
                )
            code = code.replace(VALIDATE_NEEDS_OLD, VALIDATE_NEEDS_NEW)
            p["jsCode"] = code

        elif name == "Active product row":
            code = p["jsCode"]
            if "function pickImageUrl" not in code:
                code = code.replace(
                    "function isDirectImageUrl(url)",
                    "function isDirectImageUrl(url)",
                    1,
                )
                code = code.replace(
                    "\nconst v = $('Validate sheet row').first().json;",
                    PICK_IMAGE_BLOCK + "\nconst v = $('Validate sheet row').first().json;",
                )
            code = code.replace(ACTIVE_OLD, ACTIVE_NEW)
            p["jsCode"] = code

        elif name == "Remove background Photoroom":
            for q in p.get("queryParameters", {}).get("parameters", []):
                if q.get("name") == "imageUrl":
                    q["value"] = PHOTOROOM_EXPR

    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched Photoroom image URL resolution into", WORKFLOW)


if __name__ == "__main__":
    main()
