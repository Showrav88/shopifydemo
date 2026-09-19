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

// ── Mango / Next.js color-size payload ──
const mangoNextData = {
  props: {
    pageProps: {
      product: {
        name: 'Regular-fit 100% linen shirt',
        price: 69.99,
        currency: 'USD',
        colors: [
          {
            id: '51',
            label: 'Ecru',
            price: 69.99,
            images: [{ url: 'https://media.mango.com/is/image/punto/37031400-51-002' }],
            sizes: [
              { id: '19', label: 'S', available: true },
              { id: '20', label: 'M', available: true },
              { id: '21', label: 'L', available: false },
            ],
          },
          {
            id: '99',
            label: 'Black',
            images: [{ url: 'https://media.mango.com/is/image/punto/37031400-99-002' }],
            sizes: [{ id: '19', label: 'S', available: true }],
          },
        ],
      },
    },
  },
};
const mangoHtml = `<html><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(mangoNextData)}</script></html>`;
const mangoStructured = SCRAPE.buildStructuredProduct(mangoHtml, 'https://shop.mango.com/us/en/p/shirt/37031400');
assert(mangoStructured.colors?.includes('Ecru'), 'Mango colors from __NEXT_DATA__');
assert(mangoStructured.sizes?.includes('M'), 'Mango sizes from __NEXT_DATA__');
assert(mangoStructured.variants?.length >= 4, 'Mango variant matrix');
assert(SCRAPE.isDirectImageUrl('https://media.mango.com/is/image/punto/37031400-51-002'), 'Mango CDN image');

// ── fetch strategy routing ──
assert(SCRAPE.pickFetchStrategy('https://www.everlane.com/products/jean') === 'shopify_json', 'Everlane → shopify_json');
assert(SCRAPE.pickFetchStrategy('https://www.macys.com/shop/product/foo') === 'browser', 'Macys → browser');
assert(SCRAPE.pickFetchStrategy('https://shop.mango.com/us/en/p/men/shirts/linen/shirt/37031400/51/00') === 'browser', 'Mango → browser');
assert(SCRAPE.isForceBrowser({ 'Force browser': 'YES' }), 'Force browser YES');
assert(SCRAPE.pickFetchStrategy('https://everlane.com/products/jean', { forceBrowser: true }) === 'browser', 'Force overrides shopify');
assert(SCRAPE.pickFetchStrategy('https://www.aarong.com/shirt.html') === 'http', 'Aarong → http');
assert(SCRAPE.pickFetchStrategy('https://shop.lululemon.com/p/mens-shirt/_/prod123') === 'browser', 'Lululemon → browser');
assert(SCRAPE.pickFetchStrategy('https://www.calvinklein.us/en/mens-shirts/product') === 'browser', 'Calvin Klein → browser');
assert(SCRAPE.pickFetchStrategy('https://www.ralphlauren.com/men-clothing-shirts/product') === 'browser', 'Ralph Lauren → browser');
assert(SCRAPE.pickFetchStrategy('https://www.skims.com/products/fits-everybody-tank') === 'shopify_json', 'Skims → shopify_json');
assert(SCRAPE.pickFetchStrategy('https://www.tecovas.com/products/the-earl') === 'shopify_json', 'Tecovas → shopify_json');
assert(SCRAPE.pickFetchStrategy('https://www.fashionnova.com/products/basic-tee') === 'shopify_json', 'Fashion Nova → shopify_json');
assert(SCRAPE.pickFetchStrategy('https://usa.tommy.com/en/men/shirts/product') === 'browser', 'Tommy usa.tommy.com → browser');
assert(SCRAPE.isBotBlocked('<html>Checking your browser before accessing</html>'), 'bot block detected');
assert(SCRAPE.needsBrowserRetry({}, '<html>Checking your browser</html>', 'https://x.com'), 'retry on bot block');
assert(!SCRAPE.needsBrowserRetry({ title: 'Shirt', image_url: 'https://cdn.shopify.com/s/files/1/000/1/products/x.jpg', competitor_price: '50', _sources: { title: 'shopify_json' } }, '', 'https://everlane.com/p'), 'shopify_json ok → no retry');

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
