#!/usr/bin/env node
/**
 * Tests for scripts/n8n-shopify-variants.js
 */
const VARIANTS = require('./n8n-shopify-variants.js');

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// VariantLibrary option config — UK shirts 6 sizes × 10 colors
const ukShirtRow = {
  'Option 1 name': 'Size',
  'Option 1 values': 'XS,S,M,L,XL,XXL',
  'Option 2 name': 'Color',
  'Option 2 values': 'Black,Navy,White,Grey,Beige,Red,Olive,Tan,Blue,Burgundy',
  'Scraped variants': '',
};
const ukBuilt = VARIANTS.buildVariantRows(ukShirtRow);
assert(ukBuilt.source === 'library', 'library source');
assert(ukBuilt.rows.length === 60, `uk-shirts 6×10 = 60 (got ${ukBuilt.rows.length})`);

// UK jeans — 3-option cartesian
const ukJeansRow = {
  'Option 1 name': 'Waist',
  'Option 1 values': '30,32,34',
  'Option 2 name': 'Length',
  'Option 2 values': '30,32',
  'Option 3 name': 'Color',
  'Option 3 values': 'Black,Indigo',
  'Scraped variants': '',
};
const jeansBuilt = VARIANTS.buildVariantRows(ukJeansRow);
assert(jeansBuilt.rows.length === 12, `jeans 3×2×2 = 12 (got ${jeansBuilt.rows.length})`);

// US shoes — custom option names Shopify accepts
const usShoesRow = {
  'Option 1 name': 'US Size',
  'Option 1 values': '8,9,10',
  'Option 2 name': 'Color',
  'Option 2 values': 'Black,White',
  'Scraped variants': '',
};
const shoesBuilt = VARIANTS.buildVariantRows(usShoesRow);
assert(shoesBuilt.rows.length === 6, `us-shoes 3×2 = 6 (got ${shoesBuilt.rows.length})`);

// Scraped variants beat library
const scrapedRow = {
  'Option 1 name': 'Size',
  'Option 1 values': 'XS,S,M,L,XL,XXL',
  'Option 2 name': 'Color',
  'Option 2 values': 'Black,Navy,White,Grey,Beige,Red,Olive,Tan,Blue,Burgundy',
  'Scraped variants': JSON.stringify([
    { size: 'M', color: 'Navy' },
    { size: 'L', color: 'White' },
  ]),
};
const scrapedBuilt = VARIANTS.buildVariantRows(scrapedRow);
assert(scrapedBuilt.source === 'scraped', 'scraped wins');
assert(scrapedBuilt.rows.length === 2, 'uses scraped only');

// Full Shopify payload with dynamic option names
const listing = { title: 'Test Shirt', description_html: '<p>x</p>', tags: 'shirt', collection: 'mens-shirts' };
const payload = VARIANTS.buildShopifyPayload(
  {
    ...ukShirtRow,
    'Product category': 'Men > Shirts > Casual',
    'Variant preset ID': 'uk-shirts',
    Price: '49.99',
    'Inventory quantity': 60,
    SKU: 'SHRT-001',
    Vendor: 'Mango',
  },
  listing,
);
assert(payload.multi_variant === true, 'multi variant');
assert(payload.used_library === true, 'from library');
assert(payload.shopify_payload.product.options[0].name === 'Size', 'dynamic option1 name');
assert(payload.shopify_payload.product.options[1].name === 'Color', 'dynamic option2 name');
assert(payload.variant_count === 60, '60 variants');

console.log('All shopify-variants tests passed');
