#!/usr/bin/env python3
"""Patch Prepare page for scrape + Apply scraped data + Active product row + Photoroom for image extraction."""
import json
from pathlib import Path

PREPARE_JS = r"""const row = $('Validate sheet row').first().json;
const http = $input.first().json;
const productUrl = row.source_product_url || row['Product URL'] || '';
let body = http.data ?? http.body ?? '';

if (typeof body !== 'string') {
  try { body = JSON.stringify(body); } catch { body = String(body); }
}

function extractJsonLd(html) {
  const out = [];
  const re = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    try { out.push(JSON.parse(m[1])); } catch { /* skip */ }
  }
  return out;
}

function meta(html, prop) {
  const re = new RegExp(`<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`, 'i');
  const m = html.match(re);
  if (m) return m[1];
  const re2 = new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["']${prop}["']`, 'i');
  const m2 = html.match(re2);
  return m2 ? m2[1] : '';
}

function isDirectImageUrl(url) {
  const u = String(url || '').trim().replace(/&amp;/g, '&');
  if (!u.startsWith('http')) return false;
  if (/\.html(?:\?|$|#)/i.test(u)) return false;
  if (/\.(jpe?g|png|webp|gif|avif)(\?|$|#)/i.test(u)) return true;
  if (/\/catalog\/product\//i.test(u)) return true;
  if (/\/wp-content\/uploads\//i.test(u)) return true;
  if (/\/media\/catalog\/product\//i.test(u)) return true;
  return false;
}

function addImage(candidates, seen, url) {
  if (!url || typeof url !== 'string') return;
  const u = url.trim().replace(/&amp;/g, '&');
  if (!isDirectImageUrl(u) || seen.has(u)) return;
  seen.add(u);
  candidates.push(u);
}

function imageRank(url) {
  if (/\/catalog\/product\//i.test(url) || /\/media\/catalog\/product\//i.test(url)) return 0;
  if (/\/wp-content\/uploads\//i.test(url)) return 1;
  if (/\/catalog\/category\//i.test(url)) return 9;
  return 5;
}

function extractProductImages(html) {
  const candidates = [];
  const seen = new Set();

  for (const prop of ['og:image', 'twitter:image', 'og:image:url']) {
    addImage(candidates, seen, meta(html, prop));
  }

  for (const block of extractJsonLd(html)) {
    const items = Array.isArray(block) ? block : [block];
    for (const item of items) {
      if (!item || typeof item !== 'object') continue;
      const img = item.image;
      if (typeof img === 'string') addImage(candidates, seen, img);
      else if (img && typeof img === 'object' && img.url) addImage(candidates, seen, img.url);
      else if (Array.isArray(img)) {
        for (const x of img) {
          if (typeof x === 'string') addImage(candidates, seen, x);
          else if (x && x.url) addImage(candidates, seen, x.url);
        }
      }
    }
  }

  const patterns = [
    /https?:\/\/[^"'\\s<>]+?\/catalog\/product\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
    /https?:\/\/[^"'\\s<>]+?\/media\/catalog\/product\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
    /https?:\/\/[^"'\\s<>]+?\/wp-content\/uploads\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
  ];
  for (const re of patterns) {
    for (const m of html.matchAll(re)) addImage(candidates, seen, m[0]);
  }

  const nextMatch = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i);
  if (nextMatch) {
    try {
      const nextJson = JSON.parse(nextMatch[1]);
      const blob = JSON.stringify(nextJson);
      for (const m of blob.matchAll(/https?:\\\/\\\/[^"\\]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"\\]*)?/gi)) {
        addImage(candidates, seen, m[0].replace(/\\\//g, '/'));
      }
      for (const m of blob.matchAll(/https?:\/\/[^"\\]+?\/(?:catalog|media)\/product\/[^"\\]+?\.(?:jpe?g|png|webp|gif)[^"\\]*/gi)) {
        addImage(candidates, seen, m[0]);
      }
    } catch { /* skip */ }
  }

  for (const m of html.matchAll(/<img[^>]+src=["']([^"']+)["']/gi)) {
    addImage(candidates, seen, m[1]);
  }

  candidates.sort((a, b) => imageRank(a) - imageRank(b));
  return candidates;
}

const jsonLd = extractJsonLd(body);
const candidateImages = extractProductImages(body);
const ogImage = meta(body, 'og:image') || meta(body, 'twitter:image') || candidateImages[0] || '';

const snippet = {
  product_url: productUrl,
  run_id: row._run_id,
  json_ld: jsonLd.slice(0, 3),
  og_title: meta(body, 'og:title'),
  og_description: meta(body, 'og:description'),
  og_image: ogImage,
  candidate_images: candidateImages.slice(0, 10),
  html_excerpt: body.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/\s+/g, ' ').slice(0, 12000),
};

return [{ json: { ...row, scrape_context: snippet } }];"""

APPLY_PATCH = r"""
function isDirectImageUrl(url) {
  const u = String(url || '').trim().replace(/&amp;/g, '&');
  if (!u.startsWith('http')) return false;
  if (/\.html(?:\?|$|#)/i.test(u)) return false;
  if (/\.(jpe?g|png|webp|gif|avif)(\?|$|#)/i.test(u)) return true;
  if (/\/catalog\/product\//i.test(u)) return true;
  if (/\/wp-content\/uploads\//i.test(u)) return true;
  if (/\/media\/catalog\/product\//i.test(u)) return true;
  return false;
}

function pickImageUrl(scraped, row) {
  const ctx = row.scrape_context || {};
  const candidates = [
    scraped.image_url,
    scraped.product_image_url,
    ctx.og_image,
    ...(ctx.candidate_images || []),
    row.validated_image_url,
    row['Product image URL'],
  ];
  for (const c of candidates) {
    if (isDirectImageUrl(c)) return String(c).trim().replace(/&amp;/g, '&');
  }
  return '';
}
"""

ACTIVE_PATCH = r"""
function isDirectImageUrl(url) {
  const u = String(url || '').trim().replace(/&amp;/g, '&');
  if (!u.startsWith('http')) return false;
  if (/\.html(?:\?|$|#)/i.test(u)) return false;
  if (/\.(jpe?g|png|webp|gif|avif)(\?|$|#)/i.test(u)) return true;
  if (/\/catalog\/product\//i.test(u)) return true;
  if (/\/wp-content\/uploads\//i.test(u)) return true;
  if (/\/media\/catalog\/product\//i.test(u)) return true;
  return false;
}
"""

AI_PROMPT_ADD = (
    "image_url MUST be a direct image file URL (.jpg/.png/.webp) from candidate_images or og_image — "
    "NEVER use the product page URL. Prefer the first catalog/product image."
)


def main():
    path = Path("ShopifyProductAdd.V2.json")
    data = json.loads(path.read_text())

    for node in data["nodes"]:
        name = node.get("name", "")
        if name == "Prepare page for scrape":
            node["parameters"]["jsCode"] = PREPARE_JS
        elif name == "Apply scraped data":
            code = node["parameters"]["jsCode"]
            if "function pickImageUrl" not in code:
                insert_at = code.find("const category = scraped.product_category")
                code = code[:insert_at] + APPLY_PATCH + "\n" + code[insert_at:]
            code = code.replace(
                "const imageUrl = scraped.image_url || scraped.product_image_url || row.validated_image_url;",
                "const imageUrl = pickImageUrl(scraped, row);",
            )
            node["parameters"]["jsCode"] = code
        elif name == "Active product row":
            code = node["parameters"]["jsCode"]
            if "function isDirectImageUrl" not in code:
                code = ACTIVE_PATCH + "\n" + code
            code = code.replace(
                "if (!merged.validated_image_url) {\n  merged.validated_image_url = merged['Product image URL'] || '';\n}",
                "if (!isDirectImageUrl(merged.validated_image_url)) {\n  merged.validated_image_url = isDirectImageUrl(merged['Product image URL']) ? merged['Product image URL'] : '';\n}\nif (!merged['Product image URL'] && isDirectImageUrl(merged.validated_image_url)) {\n  merged['Product image URL'] = merged.validated_image_url;\n}",
            )
            node["parameters"]["jsCode"] = code
        elif name == "Remove background Photoroom":
            params = node["parameters"]["queryParameters"]["parameters"]
            for p in params:
                if p.get("name") == "imageUrl":
                    p["value"] = (
                        "={{ (() => { const u = $json['Product image URL'] || $json.validated_image_url || ''; "
                        "if (!u || /\\.html(\\?|$|#)/i.test(u)) throw new Error('No product image URL — scrape missed image. "
                        "Re-run scrape or paste Product image URL manually.'); return u; })() }}"
                    )
        elif name == "AI scrape product":
            vals = node["parameters"]["responses"]["values"]
            if vals and AI_PROMPT_ADD not in vals[0]["content"]:
                vals[0]["content"] = vals[0]["content"].replace(
                    "Do NOT set our sell price or stock.",
                    "Do NOT set our sell price or stock.\n" + AI_PROMPT_ADD,
                )

    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Patched", path)


if __name__ == "__main__":
    main()
