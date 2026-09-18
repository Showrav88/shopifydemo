#!/usr/bin/env node
/** Quick unit tests for scrape extractors — run: node scripts/test-scrape-extractors.js */
const SCRAPE = require('./n8n-scrape-extractors.js');

let passed = 0;
let failed = 0;

function assert(cond, msg) {
  if (cond) { passed++; return; }
  failed++;
  console.error('FAIL:', msg);
}

// ── isDirectImageUrl ──
assert(SCRAPE.isDirectImageUrl('https://images.lululemon.com/is/image/lululemon/abc123'), 'Lululemon Scene7');
assert(SCRAPE.isDirectImageUrl('https://cdn.shopify.com/s/files/1/000/1/products/jean.jpg'), 'Shopify CDN');
assert(!SCRAPE.isDirectImageUrl('https://shop.lululemon.com/p/tank'), 'page URL rejected');

// ── splitVariantTitle ──
const mate = SCRAPE.splitVariantTitle('NORI / XS');
assert(mate.color === 'NORI' && mate.size === 'XS', 'MATE color/size split');

const everlane = SCRAPE.splitVariantTitle('Dark Indigo / 26 / 27.5"');
assert(everlane.color === 'Dark Indigo' && everlane.size === '26', 'Everlane color/waist');
assert(everlane.length.includes('27.5'), 'Everlane length');

// ── parseShopifyVariants ──
const shopifySample = {
  product: {
    options: [
      { name: 'Color', values: ['Dark Indigo', 'Black'] },
      { name: 'Length', values: ['27.5" Inseam', '29.5" Inseam'] },
      { name: 'Size', values: ['26', '27', '28'] },
    ],
    variants: [
      { option1: 'Dark Indigo', option2: '27.5" Inseam', option3: '26', title: 'Dark Indigo / 27.5" Inseam / 26', price: '119', sku: 'E1' },
      { option1: 'Black', option2: '29.5" Inseam', option3: '28', title: 'Black / 29.5" Inseam / 28', price: '119', sku: 'E2' },
    ],
  },
};
const parsed = SCRAPE.parseShopifyVariants(shopifySample);
assert(parsed.colors.includes('Dark Indigo'), 'colors from options');
assert(parsed.lengths.some((l) => l.includes('27.5')), 'lengths from options');
assert(parsed.sizes.includes('26'), 'sizes from options');
assert(parsed.variants[0].color === 'Dark Indigo', 'variant color mapped');

// ── srcset in HTML ──
const html = `
  <picture>
    <source srcset="https://images.lululemon.com/is/image/lululemon/abc?wid=400 400w, https://images.lululemon.com/is/image/lululemon/abc?wid=1200 1200w">
    <img src="https://images.lululemon.com/is/image/lululemon/abc?wid=200">
  </picture>`;
const imgs = SCRAPE.extractProductImages(html, 'https://shop.lululemon.com');
assert(imgs.length > 0 && imgs[0].includes('lululemon'), 'srcset images extracted');

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
