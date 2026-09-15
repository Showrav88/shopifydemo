/**
 * Phase 2: Shopify multi-variant builder for n8n Code nodes.
 * One sheet row → one product with Size/Color (etc.) options from scrape.
 */

const VARIANTS = {};

// ─── Profiles: how to name Shopify options per product family ───────────────

VARIANTS.PROFILES = {
  clothing_alpha: { option1: 'Size', option2: 'Color', sizePattern: 'alpha' },
  clothing_numeric: { option1: 'Waist', option2: 'Length', sizePattern: 'numeric' },
  footwear_uk: { option1: 'UK Size', option2: 'Color', sizePattern: 'numeric' },
  one_size: { option1: null, option2: 'Color', sizePattern: 'one' },
  color_only: { option1: null, option2: 'Color', sizePattern: 'one' },
  generic: { option1: 'Size', option2: 'Color', sizePattern: 'any' },
};

VARIANTS.detectProfile = function detectProfile(category, explicitProfile) {
  const p = String(explicitProfile || '').trim().toLowerCase();
  if (p && VARIANTS.PROFILES[p]) return p;

  const c = String(category || '').toLowerCase();
  if (/shoe|sneaker|boot|footwear|sandal|trainer/.test(c)) return 'footwear_uk';
  if (/jean|trouser|pant|chino/.test(c)) return 'clothing_numeric';
  if (/bag|belt|wallet|scarf|hat|cap|accessory|jewel|watch|sock/.test(c)) return 'one_size';
  if (/dress|shirt|tee|t-shirt|top|jacket|coat|hoodie|sweat|kurta|saree|blouse/.test(c)) return 'clothing_alpha';
  return 'generic';
};

VARIANTS.parseList = function parseList(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val.map((x) => String(x).trim()).filter(Boolean);
  return String(val).split(/[,;|/]+/).map((x) => x.trim()).filter(Boolean);
};

VARIANTS.parseScrapedVariants = function parseScrapedVariants(row) {
  const raw = row['Scraped variants'] || row.scraped_variants || '';
  if (!raw) return [];
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

VARIANTS.norm = function norm(v) {
  return String(v || '').trim();
};

VARIANTS.slugPart = function slugPart(v) {
  return String(v || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 12) || 'VAR';
};

VARIANTS.buildVariantRows = function buildVariantRows(row, profileKey) {
  const profile = VARIANTS.PROFILES[profileKey] || VARIANTS.PROFILES.generic;
  const scraped = VARIANTS.parseScrapedVariants(row);
  const sizes = VARIANTS.parseList(row.Sizes);
  const colors = VARIANTS.parseList(row.Colors);
  const rows = [];

  if (scraped.length > 0) {
    for (const v of scraped) {
      const size = VARIANTS.norm(v.size || v.option1 || v.title || '');
      const color = VARIANTS.norm(v.color || v.option2 || '');
      const price = v.price ?? v.competitor_price ?? '';
      const sku = VARIANTS.norm(v.sku || '');
      const qty = v.inventory ?? v.inventory_quantity ?? v.stock ?? null;
      if (!size && !color) continue;
      rows.push({ size, color, price, sku, qty });
    }
  }

  if (rows.length === 0 && sizes.length > 0) {
    const colorList = colors.length > 0 ? colors : [''];
    for (const size of sizes) {
      for (const color of colorList) {
        rows.push({ size, color, price: '', sku: '', qty: null });
      }
    }
  }

  if (rows.length === 0 && colors.length > 0) {
    for (const color of colors) {
      rows.push({ size: profile.sizePattern === 'one' ? 'One Size' : '', color, price: '', sku: '', qty: null });
    }
  }

  return { profile, rows };
};

VARIANTS.variantSku = function variantSku(baseSku, size, color, index) {
  const base = VARIANTS.norm(baseSku) || 'SKU';
  const parts = [base];
  if (size && size !== 'One Size') parts.push(VARIANTS.slugPart(size));
  if (color) parts.push(VARIANTS.slugPart(color));
  if (parts.length === 1) parts.push(`V${index + 1}`);
  return parts.join('-').slice(0, 50);
};

VARIANTS.buildShopifyPayload = function buildShopifyPayload(row, listing) {
  const category = row.validated_category || row['Product category'] || listing.collection || '';
  const profileKey = VARIANTS.detectProfile(category, row['Variant profile'] || row.variant_profile);
  const { profile, rows } = VARIANTS.buildVariantRows(row, profileKey);

  const sheetPrice = row['Price'] ?? row.validated_price;
  const defaultPrice = sheetPrice === '' || sheetPrice === null || sheetPrice === undefined
    ? '0.00'
    : String(sheetPrice);

  const sheetInv = row['Inventory quantity'] ?? row.validated_inventory;
  const totalInv = sheetInv === '' || sheetInv === null || sheetInv === undefined
    ? 0
    : Number(sheetInv);

  const baseSku = row.validated_sku || row.SKU || row.processing_sku || '';
  const vendor = row.Vendor || row.validated_vendor || '';
  const productType = category || listing.collection || '';

  // ── Single variant fallback (no scrape sizes) ──
  if (rows.length === 0) {
    return {
      multi_variant: false,
      variant_count: 1,
      variant_profile: profileKey,
      shopify_payload: {
        product: {
          title: listing.title,
          body_html: listing.description_html,
          vendor,
          product_type: productType,
          tags: listing.tags,
          status: 'draft',
          variants: [{
            price: '0.00',
            sku: baseSku,
            inventory_management: 'shopify',
            inventory_quantity: 0,
          }],
        },
      },
      price_updates: [{
        sku: baseSku,
        price: defaultPrice,
        inventory_quantity: totalInv,
      }],
    };
  }

  // ── Multi-variant ──
  const option1Name = profile.option1;
  const option2Name = profile.option2;
  const option1Values = new Set();
  const option2Values = new Set();
  const shopifyVariants = [];
  const priceUpdates = [];

  const perVariantInv = rows.length > 0 && totalInv > 0
    ? Math.max(1, Math.floor(totalInv / rows.length))
    : 0;

  rows.forEach((r, i) => {
    const sizeVal = r.size || (profile.sizePattern === 'one' ? 'One Size' : `Option ${i + 1}`);
    const colorVal = r.color || '';
    const opt1 = option1Name ? sizeVal : (colorVal || 'Default');
    const opt2 = option1Name && option2Name && colorVal ? colorVal : undefined;

    if (option1Name) option1Values.add(opt1);
    if (opt2 && option2Name) option2Values.add(opt2);

    const variant = {
      price: '0.00',
      sku: r.sku || VARIANTS.variantSku(baseSku, sizeVal, colorVal, i),
      inventory_management: 'shopify',
      inventory_quantity: 0,
    };

    if (option1Name) variant.option1 = opt1;
    if (opt2 && option2Name) variant.option2 = opt2;

    shopifyVariants.push(variant);

    const vPrice = r.price !== '' && r.price !== null && r.price !== undefined
      ? String(r.price)
      : defaultPrice;
    const vInv = r.qty !== null && r.qty !== undefined && r.qty !== ''
      ? Number(r.qty)
      : perVariantInv;

    priceUpdates.push({
      sku: variant.sku,
      option1: variant.option1,
      option2: variant.option2,
      price: vPrice,
      inventory_quantity: vInv,
    });
  });

  const product = {
    title: listing.title,
    body_html: listing.description_html,
    vendor,
    product_type: productType,
    tags: listing.tags,
    status: 'draft',
    variants: shopifyVariants,
  };

  if (option1Name && option1Values.size > 0) {
    product.options = [];
    product.options.push({ name: option1Name, values: [...option1Values] });
    if (option2Name && option2Values.size > 0) {
      product.options.push({ name: option2Name, values: [...option2Values] });
    }
  }

  return {
    multi_variant: shopifyVariants.length > 1,
    variant_count: shopifyVariants.length,
    variant_profile: profileKey,
    shopify_payload: { product },
    price_updates: priceUpdates,
  };
};

if (typeof module !== 'undefined') module.exports = VARIANTS;
