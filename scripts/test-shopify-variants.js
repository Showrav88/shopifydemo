#!/usr/bin/env node
/**
 * Tests for scripts/n8n-shopify-variants.js
 */
const VARIANTS = require('./n8n-shopify-variants.js');

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// Profile auto-detect — no separate variant lookup table
assert(VARIANTS.detectProfile('Men > Shirts > Linen', '') === 'clothing_alpha', 'shirt → clothing_alpha');
assert(VARIANTS.detectProfile('Men > Jeans', '') === 'clothing_numeric', 'jeans → clothing_numeric');
assert(VARIANTS.detectProfile('Women > Shoes > Boots', '') === 'footwear_uk', 'boots → footwear_uk');

// Default sizes when scrape missed
const shirtRow = { Sizes: '', Colors: 'Black, Navy', 'Scraped variants': '' };
const shirtBuilt = VARIANTS.buildVariantRows(shirtRow, 'clothing_alpha');
assert(shirtBuilt.used_defaults === true, 'used_defaults when no scrape sizes');
assert(shirtBuilt.rows.length === 12, `shirt defaults × 2 colors = 12 (got ${shirtBuilt.rows.length})`);

const pantsRow = { Sizes: '', Colors: 'Black', 'Scraped variants': '' };
const pantsBuilt = VARIANTS.buildVariantRows(pantsRow, 'clothing_numeric');
assert(pantsBuilt.rows.length === 10, `pants waist×length×color = 10 (got ${pantsBuilt.rows.length})`);

// Scraped sizes beat defaults
const scrapedRow = {
  Sizes: 'M, L',
  Colors: 'White',
  'Scraped variants': '',
};
const scrapedBuilt = VARIANTS.buildVariantRows(scrapedRow, 'clothing_alpha');
assert(scrapedBuilt.used_defaults === false, 'no defaults when sizes present');
assert(scrapedBuilt.rows.length === 2, 'uses sheet sizes');

// Colors from lookup formula column
const colorRow = { Colors: 'Black, Navy, White', 'Scraped variants': '' };
assert(VARIANTS.resolveColors(colorRow).length === 3, 'resolveColors from sheet');

// Full Shopify payload
const listing = { title: 'Test Shirt', description_html: '<p>x</p>', tags: 'shirt', collection: 'mens-shirts' };
const payload = VARIANTS.buildShopifyPayload(
  {
    'Product category': 'Men > Shirts > Casual',
    Colors: 'Black, Navy',
    Price: '49.99',
    'Inventory quantity': 20,
    SKU: 'SHRT-001',
    Vendor: 'Mango',
  },
  listing,
);
assert(payload.multi_variant === true, 'multi variant from defaults');
assert(payload.used_default_sizes === true, 'flags default sizes');
assert(payload.variant_count >= 10, 'many variants created');

console.log('All shopify-variants tests passed');
