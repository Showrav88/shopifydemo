/**
 * Production scrape extractors for n8n Code nodes.
 * Pattern used by e-commerce automation teams:
 *   Tier 1: APIs + Schema.org JSON-LD (highest trust)
 *   Tier 2: OpenGraph / meta product tags
 *   Tier 3: Platform payloads (__NEXT_DATA__, Shopify embed, WooCommerce)
 *   Tier 4: HTML heuristics (images, price patterns)
 *   Tier 5: AI enrichment — gaps only (lowest cost, runs in separate node)
 *
 * Injected into Prepare page for scrape + Apply scraped data via patch script.
 */

/* global module */
const SCRAPE_EXTRACTORS = {};

// ─── helpers ───────────────────────────────────────────────────────────────

SCRAPE_EXTRACTORS.isDirectImageUrl = function isDirectImageUrl(url) {
  const u = String(url || '').trim().replace(/&amp;/g, '&');
  if (!u.startsWith('http')) return false;
  if (/\.html(?:\?|$|#)/i.test(u)) return false;
  if (/\.(jpe?g|png|webp|gif|avif)(\?|$|#)/i.test(u)) return true;
  if (/\/catalog\/product\//i.test(u)) return true;
  if (/\/wp-content\/uploads\//i.test(u)) return true;
  if (/\/media\/catalog\/product\//i.test(u)) return true;
  if (/\/cdn\/shop\//i.test(u)) return true;
  return false;
};

SCRAPE_EXTRACTORS.absolutizeUrl = function absolutizeUrl(url, base) {
  const u = String(url || '').trim().replace(/&amp;/g, '&');
  if (!u) return '';
  if (u.startsWith('http')) return u;
  if (u.startsWith('//')) return `https:${u}`;
  try {
    return new URL(u, base).href;
  } catch {
    return u;
  }
};

SCRAPE_EXTRACTORS.cleanText = function cleanText(t) {
  return String(t || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
};

SCRAPE_EXTRACTORS.meta = function meta(html, prop) {
  const re1 = new RegExp(`<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`, 'i');
  const m1 = html.match(re1);
  if (m1) return m1[1];
  const re2 = new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["']${prop}["']`, 'i');
  const m2 = html.match(re2);
  return m2 ? m2[1] : '';
};

SCRAPE_EXTRACTORS.extractJsonLd = function extractJsonLd(html) {
  const out = [];
  const re = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    try {
      out.push(JSON.parse(m[1]));
    } catch { /* skip */ }
  }
  return out;
};

SCRAPE_EXTRACTORS.flattenJsonLd = function flattenJsonLd(blocks) {
  const items = [];
  for (const block of blocks) {
    if (!block) continue;
    if (Array.isArray(block)) items.push(...block);
    else if (block['@graph']) items.push(...(Array.isArray(block['@graph']) ? block['@graph'] : [block['@graph']]));
    else items.push(block);
  }
  return items;
};

SCRAPE_EXTRACTORS.isProductType = function isProductType(t) {
  const type = String(t || '').toLowerCase();
  return type.includes('product');
};

SCRAPE_EXTRACTORS.pickImageFromSchema = function pickImageFromSchema(image, baseUrl) {
  if (!image) return '';
  if (typeof image === 'string') return SCRAPE_EXTRACTORS.absolutizeUrl(image, baseUrl);
  if (Array.isArray(image)) {
    for (const x of image) {
      const u = SCRAPE_EXTRACTORS.pickImageFromSchema(x, baseUrl);
      if (u) return u;
    }
    return '';
  }
  if (typeof image === 'object') {
    return SCRAPE_EXTRACTORS.absolutizeUrl(image.url || image.contentUrl || image['@id'] || '', baseUrl);
  }
  return '';
};

SCRAPE_EXTRACTORS.parsePriceOffer = function parsePriceOffer(offers) {
  if (!offers) return { price: '', currency: '' };
  const list = Array.isArray(offers) ? offers : [offers];
  for (const o of list) {
    if (!o || typeof o !== 'object') continue;
    const price = o.price ?? o.lowPrice ?? o.highPrice ?? '';
    const currency = o.priceCurrency || '';
    if (price !== '' && price !== null) return { price: String(price), currency };
  }
  return { price: '', currency: '' };
};

// ─── Tier 1: JSON-LD Product ───────────────────────────────────────────────

SCRAPE_EXTRACTORS.extractSchemaOrgProduct = function extractSchemaOrgProduct(html, baseUrl) {
  const blocks = SCRAPE_EXTRACTORS.flattenJsonLd(SCRAPE_EXTRACTORS.extractJsonLd(html));
  for (const item of blocks) {
    if (!item || typeof item !== 'object') continue;
    const types = item['@type'];
    const typeList = Array.isArray(types) ? types : [types];
    if (!typeList.some(SCRAPE_EXTRACTORS.isProductType)) continue;

    const { price, currency } = SCRAPE_EXTRACTORS.parsePriceOffer(item.offers);
    const brand = typeof item.brand === 'object' ? item.brand.name : item.brand;

    return {
      source: 'json_ld',
      confidence: 0.95,
      title: SCRAPE_EXTRACTORS.cleanText(item.name || ''),
      description: SCRAPE_EXTRACTORS.cleanText(item.description || ''),
      image_url: SCRAPE_EXTRACTORS.pickImageFromSchema(item.image, baseUrl),
      competitor_price: price,
      competitor_currency: currency,
      vendor: SCRAPE_EXTRACTORS.cleanText(brand || ''),
      product_category: SCRAPE_EXTRACTORS.cleanText(item.category || ''),
      sku: String(item.sku || item.mpn || '').trim(),
    };
  }
  return null;
};

// ─── Tier 2: OpenGraph + meta product ──────────────────────────────────────

SCRAPE_EXTRACTORS.extractOpenGraph = function extractOpenGraph(html, baseUrl) {
  const title = SCRAPE_EXTRACTORS.meta(html, 'og:title') || SCRAPE_EXTRACTORS.meta(html, 'twitter:title');
  const description = SCRAPE_EXTRACTORS.meta(html, 'og:description') || SCRAPE_EXTRACTORS.meta(html, 'description');
  const image = SCRAPE_EXTRACTORS.meta(html, 'og:image') || SCRAPE_EXTRACTORS.meta(html, 'twitter:image');
  const price = SCRAPE_EXTRACTORS.meta(html, 'product:price:amount') || SCRAPE_EXTRACTORS.meta(html, 'og:price:amount');
  const currency = SCRAPE_EXTRACTORS.meta(html, 'product:price:currency') || SCRAPE_EXTRACTORS.meta(html, 'og:price:currency');

  if (!title && !image && !description) return null;

  return {
    source: 'open_graph',
    confidence: 0.85,
    title: SCRAPE_EXTRACTORS.cleanText(title),
    description: SCRAPE_EXTRACTORS.cleanText(description),
    image_url: SCRAPE_EXTRACTORS.absolutizeUrl(image, baseUrl),
    competitor_price: price ? String(price) : '',
    competitor_currency: currency || '',
    vendor: SCRAPE_EXTRACTORS.cleanText(SCRAPE_EXTRACTORS.meta(html, 'og:site_name')),
    product_category: '',
    sku: '',
  };
};

// ─── Tier 3: Platform payloads ─────────────────────────────────────────────

SCRAPE_EXTRACTORS.extractHtmlTitle = function extractHtmlTitle(html) {
  const m = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  if (!m) return '';
  let t = SCRAPE_EXTRACTORS.cleanText(m[1]);
  t = t.replace(/\s*[|\-–]\s*Aarong.*$/i, '');
  t = t.replace(/\.html$/i, '');
  t = t.replace(/[-_]/g, ' ');
  if (/^[a-z0-9\s-]+\.html$/i.test(t) || t.length < 4) return '';
  return t.trim();
};

SCRAPE_EXTRACTORS.extractNextData = function extractNextData(html, baseUrl) {
  const m = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i);
  if (!m) return null;
  try {
    const data = JSON.parse(m[1]);
    const blob = JSON.stringify(data);
    const titlePatterns = [
      /"name"\s*:\s*"([^"\\]{3,200})"/,
      /"title"\s*:\s*"([^"\\]{3,200})"/,
      /"product_name"\s*:\s*"([^"\\]{3,200})"/,
    ];
    let title = '';
    for (const re of titlePatterns) {
      const tm = blob.match(re);
      if (tm && !/\.html$/i.test(tm[1]) && tm[1].length > 3) {
        title = SCRAPE_EXTRACTORS.cleanText(tm[1]);
        break;
      }
    }
    const images = [];
    for (const im of blob.matchAll(/https?:\\\/\\\/[^"\\]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"\\]*)?/gi)) {
      images.push(im[0].replace(/\\\//g, '/'));
    }
    for (const im of blob.matchAll(/https?:\/\/[^"\\]+?\/(?:catalog|media)\/product\/[^"\\]+?\.(?:jpe?g|png|webp|gif)[^"\\]*/gi)) {
      images.push(im[0]);
    }
    const priceM = blob.match(/"price"\s*:\s*"?([0-9]+(?:\.[0-9]{1,2})?)"?/);
    if (!title && images.length === 0) return null;
    return {
      source: 'next_data',
      confidence: 0.8,
      title,
      description: '',
      image_url: images[0] || '',
      competitor_price: priceM ? priceM[1] : '',
      competitor_currency: '',
      vendor: '',
      product_category: '',
      sku: '',
      candidate_images: [...new Set(images)].slice(0, 10),
    };
  } catch {
    return null;
  }
};

SCRAPE_EXTRACTORS.normalizeShopifyProduct = function normalizeShopifyProduct(json, baseUrl) {
  const p = json?.product;
  if (!p) return null;
  const v = p.variants?.[0] || {};
  const img = p.images?.[0]?.src || p.image?.src || '';
  return {
    source: 'shopify_json',
    confidence: 0.98,
    title: SCRAPE_EXTRACTORS.cleanText(p.title || ''),
    description: SCRAPE_EXTRACTORS.cleanText(p.body_html || ''),
    image_url: SCRAPE_EXTRACTORS.absolutizeUrl(img, baseUrl),
    competitor_price: v.price ? String(v.price) : '',
    competitor_currency: '',
    vendor: SCRAPE_EXTRACTORS.cleanText(p.vendor || ''),
    product_category: SCRAPE_EXTRACTORS.cleanText(p.product_type || ''),
    sku: String(v.sku || '').trim(),
    sizes: (p.variants || []).map((x) => x.title).filter(Boolean),
    variants: (p.variants || []).map((x) => ({
      size: x.title,
      sku: x.sku,
      price: x.price,
    })),
  };
};

SCRAPE_EXTRACTORS.shopifyJsonUrl = function shopifyJsonUrl(productUrl) {
  const u = String(productUrl || '').trim();
  if (!u) return '';
  if (u.includes('.json')) return u.split('?')[0];
  if (/\/products\/[^/?#]+/.test(u)) return `${u.replace(/\/$/, '').split('?')[0]}.json`;
  return '';
};

// ─── Tier 4: Images + price heuristics ─────────────────────────────────────

SCRAPE_EXTRACTORS.extractProductImages = function extractProductImages(html, baseUrl) {
  const candidates = [];
  const seen = new Set();

  function add(url) {
    const u = SCRAPE_EXTRACTORS.absolutizeUrl(url, baseUrl);
    if (!SCRAPE_EXTRACTORS.isDirectImageUrl(u) || seen.has(u)) return;
    seen.add(u);
    candidates.push(u);
  }

  function rank(url) {
    if (/\/catalog\/product\//i.test(url) || /\/media\/catalog\/product\//i.test(url)) return 0;
    if (/\/cdn\/shop\//i.test(url)) return 1;
    if (/\/wp-content\/uploads\//i.test(url)) return 2;
    if (/\/catalog\/category\//i.test(url)) return 9;
    return 5;
  }

  for (const prop of ['og:image', 'twitter:image', 'og:image:url']) {
    add(SCRAPE_EXTRACTORS.meta(html, prop));
  }

  for (const block of SCRAPE_EXTRACTORS.flattenJsonLd(SCRAPE_EXTRACTORS.extractJsonLd(html))) {
    if (!block || typeof block !== 'object') continue;
    add(SCRAPE_EXTRACTORS.pickImageFromSchema(block.image, baseUrl));
  }

  const patterns = [
    /https?:\/\/[^"'\\s<>]+?\/catalog\/product\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
    /https?:\/\/[^"'\\s<>]+?\/media\/catalog\/product\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
    /https?:\/\/[^"'\\s<>]+?\/wp-content\/uploads\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
    /https?:\/\/[^"'\\s<>]+?\/cdn\/shop\/[^"'\\s<>]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"'\\s<>]*)?/gi,
  ];
  for (const re of patterns) {
    for (const m of html.matchAll(re)) add(m[0]);
  }

  const next = SCRAPE_EXTRACTORS.extractNextData(html, baseUrl);
  if (next?.candidate_images) {
    for (const u of next.candidate_images) add(u);
  }

  for (const m of html.matchAll(/<img[^>]+src=["']([^"']+)["']/gi)) add(m[1]);
  for (const m of html.matchAll(/<img[^>]+data-src=["']([^"']+)["']/gi)) add(m[1]);

  candidates.sort((a, b) => rank(a) - rank(b));
  return candidates;
};

SCRAPE_EXTRACTORS.extractPriceHeuristic = function extractPriceHeuristic(html) {
  const currencyPatterns = [
    { re: /(?:৳|BDT)\s*([0-9][0-9,]{2,}(?:\.[0-9]{1,2})?)/, currency: 'BDT' },
    { re: /([0-9][0-9,]{2,}(?:\.[0-9]{1,2})?)\s*(?:৳|BDT)/, currency: 'BDT' },
    { re: /(?:£|GBP)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)/, currency: 'GBP' },
    { re: /(?:\$|USD)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)/, currency: 'USD' },
  ];
  for (const { re, currency } of currencyPatterns) {
    const m = html.match(re);
    if (m) {
      const price = m[1].replace(/,/g, '');
      if (Number(price) >= 50) return { price, currency };
    }
  }
  return { price: '', currency: '' };
};

// ─── Merge tiers (production priority stack) ───────────────────────────────

SCRAPE_EXTRACTORS.FIELD_ORDER = [
  'shopify_json',
  'json_ld',
  'open_graph',
  'next_data',
  'heuristic',
];

SCRAPE_EXTRACTORS.mergeExtractions = function mergeExtractions(layers, baseUrl) {
  const byField = {};
  const sources = {};

  function set(field, value, source) {
    if (value === '' || value === null || value === undefined) return;
    if (byField[field] !== undefined && byField[field] !== '') return;
    byField[field] = value;
    sources[field] = source;
  }

  const sorted = [...layers].filter(Boolean).sort(
    (a, b) => SCRAPE_EXTRACTORS.FIELD_ORDER.indexOf(a.source) - SCRAPE_EXTRACTORS.FIELD_ORDER.indexOf(b.source)
  );

  for (const layer of sorted) {
    const src = layer.source;
    set('title', layer.title, src);
    set('description', layer.description, src);
    set('image_url', layer.image_url, src);
    set('competitor_price', layer.competitor_price, src);
    set('competitor_currency', layer.competitor_currency, src);
    set('vendor', layer.vendor, src);
    set('product_category', layer.product_category, src);
    set('sku', layer.sku, src);
    if (layer.sizes?.length) set('sizes', layer.sizes, src);
    if (layer.variants?.length) set('variants', layer.variants, src);
    if (layer.candidate_images?.length && !byField.candidate_images) {
      byField.candidate_images = layer.candidate_images;
      sources.candidate_images = src;
    }
  }

  return { ...byField, _sources: sources, _confidence: sorted[0]?.confidence || 0 };
};

SCRAPE_EXTRACTORS.buildStructuredProduct = function buildStructuredProduct(html, baseUrl, shopifyLayer) {
  const candidateImages = SCRAPE_EXTRACTORS.extractProductImages(html, baseUrl);
  const priceHint = SCRAPE_EXTRACTORS.extractPriceHeuristic(html);
  const heuristic = {
    source: 'heuristic',
    confidence: 0.5,
    title: SCRAPE_EXTRACTORS.extractHtmlTitle(html),
    description: '',
    image_url: candidateImages[0] || '',
    competitor_price: priceHint.price,
    competitor_currency: priceHint.currency,
    vendor: '',
    product_category: '',
    sku: '',
    candidate_images: candidateImages,
  };

  const structured = SCRAPE_EXTRACTORS.mergeExtractions([
    shopifyLayer,
    SCRAPE_EXTRACTORS.extractSchemaOrgProduct(html, baseUrl),
    SCRAPE_EXTRACTORS.extractOpenGraph(html, baseUrl),
    SCRAPE_EXTRACTORS.extractNextData(html, baseUrl),
    heuristic,
  ], baseUrl);

  if (!structured.candidate_images) structured.candidate_images = candidateImages.slice(0, 10);
  if (!structured.image_url && candidateImages[0]) {
    structured.image_url = candidateImages[0];
    structured._sources.image_url = 'candidate_images';
  }

  return structured;
};

SCRAPE_EXTRACTORS.pickImageUrl = function pickImageUrl(scraped, row) {
  const ctx = row.scrape_context || {};
  const structured = ctx.structured || {};
  const candidates = [
    structured.image_url,
    scraped?.image_url,
    scraped?.product_image_url,
    ctx.og_image,
    ...(structured.candidate_images || ctx.candidate_images || []),
    row.validated_image_url,
    row['Product image URL'],
  ];
  for (const c of candidates) {
    if (SCRAPE_EXTRACTORS.isDirectImageUrl(c)) return String(c).trim().replace(/&amp;/g, '&');
  }
  return '';
};

SCRAPE_EXTRACTORS.mergeField = function mergeField(structured, ai, key, aiAlts = []) {
  const s = structured?.[key];
  if (s !== undefined && s !== null && String(s).trim() !== '') return s;
  for (const alt of aiAlts) {
    const v = ai?.[alt];
    if (v !== undefined && v !== null && String(v).trim() !== '') return v;
  }
  const v = ai?.[key];
  return v !== undefined && v !== null ? v : '';
};

if (typeof module !== 'undefined') module.exports = SCRAPE_EXTRACTORS;
