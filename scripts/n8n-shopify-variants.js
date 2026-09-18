/**
 * Phase 2: Shopify multi-variant builder for n8n Code nodes.
 * One sheet row → one product with Size/Color (etc.) options from scrape.
 */

const VARIANTS = {};

// ─── Profiles: how to name Shopify options per product family ───────────────

VARIANTS.PROFILES = {
  clothing_alpha: { option1: 'Size', option2: 'Color', option3: null, sizePattern: 'alpha' },
  clothing_numeric: { option1: 'Waist', option2: 'Length', option3: 'Color', sizePattern: 'numeric' },
  footwear_uk: { option1: 'UK Size', option2: 'Color', option3: null, sizePattern: 'numeric' },
  one_size: { option1: null, option2: 'Color', option3: null, sizePattern: 'one' },
  color_only: { option1: null, option2: 'Color', option3: null, sizePattern: 'one' },
  generic: { option1: 'Size', option2: 'Color', option3: null, sizePattern: 'any' },
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

VARIANTS.splitCombinedVariant = function splitCombinedVariant(sizeStr) {
  const raw = VARIANTS.norm(sizeStr);
  if (!raw.includes('/')) return { size: raw, color: '', length: '' };
  const parts = raw.split(/\s*\/\s*/).map((x) => x.trim()).filter(Boolean);
  let size = '';
  let color = '';
  let length = '';
  for (const p of parts) {
    if (/\d+(?:\.\d+)?\s*(?:"|''|inch|\bin\b|inseam)/i.test(p) || /^\d+(?:\.\d+)?"$/.test(p)) {
      length = p;
    } else if (/^(xx?s|xx?l|[0-5]x|xs|s|m|l|xl|xxl|xxxl|one\s*size)$/i.test(p)) {
      size = p;
    } else if (/^\d{2,3}$/.test(p) && Number(p) >= 20 && Number(p) <= 54) {
      size = p;
    } else if (/[a-z]/i.test(p)) {
      color = color ? `${color} / ${p}` : p;
    }
  }
  return { size: size || parts[parts.length - 1] || raw, color, length };
};

VARIANTS.parseScrapedVariants = function parseScrapedVariants(row) {
  const raw = row['Scraped variants'] || row.scraped_variants || '';
  if (!raw) return [];
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (!Array.isArray(parsed)) return [];
    return parsed.map((v) => {
      const sizeRaw = VARIANTS.norm(v.size || v.option1 || v.title || '');
      const hasSlash = sizeRaw.includes('/') && !v.color && !v.length;
      const split = hasSlash ? VARIANTS.splitCombinedVariant(sizeRaw) : null;
      return {
        ...v,
        size: split ? split.size : sizeRaw,
        color: VARIANTS.norm(v.color || v.option2 || (split && split.color) || ''),
        length: VARIANTS.norm(v.length || v.option3 || (split && split.length) || ''),
      };
    });
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
      let size = VARIANTS.norm(v.size || v.option1 || '');
      let color = VARIANTS.norm(v.color || v.option2 || '');
      let length = VARIANTS.norm(v.length || v.option3 || '');
      if (!size && !color && v.title) {
        const split = VARIANTS.splitCombinedVariant(v.title);
        size = split.size;
        color = split.color;
        length = split.length || length;
      }
      const price = v.price ?? v.competitor_price ?? '';
      const sku = VARIANTS.norm(v.sku || '');
      const qty = v.inventory ?? v.inventory_quantity ?? v.stock ?? null;
      if (!size && !color && !length) continue;
      rows.push({ size, color, length, price, sku, qty });
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

VARIANTS.resolvePrice = function resolvePrice(row) {
  const sheet = row['Price'] ?? row['Variant Price'] ?? row.validated_price;
  if (sheet !== null && sheet !== undefined && String(sheet).trim() !== '') {
    const n = Number(String(sheet).replace(/[^0-9.]/g, ''));
    if (!Number.isNaN(n) && n > 0) return n.toFixed(2);
  }
  const comp = row['Competitor price'] ?? row.competitor_price;
  if (comp !== null && comp !== undefined && String(comp).trim() !== '') {
    const n = Number(String(comp).replace(/[^0-9.]/g, ''));
    if (!Number.isNaN(n) && n > 0) return n.toFixed(2);
  }
  return '0.00';
};

VARIANTS.resolveInventory = function resolveInventory(row) {
  const sheetInv = row['Inventory quantity'] ?? row.validated_inventory ?? row['Variant Inventory Qty'];
  if (sheetInv !== '' && sheetInv !== null && sheetInv !== undefined) {
    const n = Number(sheetInv);
    if (!Number.isNaN(n) && n > 0) return n;
  }
  return 10;
};

VARIANTS.buildShopifyPayload = function buildShopifyPayload(row, listing) {
  const category = row.validated_category || row['Product category'] || row['Suggested Category'] || listing.collection || '';
  const profileKey = VARIANTS.detectProfile(
    category,
    row['Variant profile'] || row['Suggested Variant profile'] || row.variant_profile
  );
  const { profile, rows } = VARIANTS.buildVariantRows(row, profileKey);

  const sellPrice = VARIANTS.resolvePrice(row);
  const totalInv = VARIANTS.resolveInventory(row);

  const baseSku = row.validated_sku || row.SKU || row.processing_sku || '';
  const vendor = row.Vendor || row.validated_vendor || row['Suggested Vendor'] || '';
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
            price: sellPrice,
            sku: baseSku,
            inventory_management: 'shopify',
            inventory_quantity: 0,
          }],
        },
      },
      inventory_updates: [{
        sku: baseSku,
        inventory_quantity: totalInv,
      }],
    };
  }

  // ── Multi-variant ──
  const option1Name = profile.option1;
  const option2Name = profile.option2;
  const option3Name = profile.option3;
  const option1Values = new Set();
  const option2Values = new Set();
  const option3Values = new Set();
  const shopifyVariants = [];
  const inventoryUpdates = [];

  const perVariantInv = rows.length > 0 && totalInv > 0
    ? Math.max(1, Math.floor(totalInv / rows.length))
    : 0;

  rows.forEach((r, i) => {
    const sizeVal = r.size || (profile.sizePattern === 'one' ? 'One Size' : `Option ${i + 1}`);
    const lengthVal = r.length || '';
    const colorVal = r.color || '';

    let opt1;
    let opt2;
    let opt3;

    if (profileKey === 'clothing_numeric') {
      opt1 = option1Name ? sizeVal : undefined;
      opt2 = option2Name && lengthVal ? lengthVal : undefined;
      opt3 = option3Name && colorVal ? colorVal : undefined;
    } else {
      opt1 = option1Name ? sizeVal : (colorVal || 'Default');
      opt2 = option1Name && option2Name && colorVal ? colorVal : undefined;
      opt3 = undefined;
    }

    if (opt1 && option1Name) option1Values.add(opt1);
    if (opt2 && option2Name) option2Values.add(opt2);
    if (opt3 && option3Name) option3Values.add(opt3);

    const variant = {
      price: sellPrice,
      sku: r.sku || VARIANTS.variantSku(baseSku, sizeVal, colorVal || lengthVal, i),
      inventory_management: 'shopify',
      inventory_quantity: 0,
    };

    if (opt1 && option1Name) variant.option1 = opt1;
    if (opt2 && option2Name) variant.option2 = opt2;
    if (opt3 && option3Name) variant.option3 = opt3;

    shopifyVariants.push(variant);

    const vInv = r.qty !== null && r.qty !== undefined && r.qty !== ''
      ? Number(r.qty)
      : perVariantInv;

    inventoryUpdates.push({
      sku: variant.sku,
      option1: variant.option1,
      option2: variant.option2,
      option3: variant.option3,
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
    if (option3Name && option3Values.size > 0) {
      product.options.push({ name: option3Name, values: [...option3Values] });
    }
  }

  return {
    multi_variant: shopifyVariants.length > 1,
    variant_count: shopifyVariants.length,
    variant_profile: profileKey,
    shopify_payload: { product },
    inventory_updates: inventoryUpdates,
  };
};

if (typeof module !== 'undefined') module.exports = VARIANTS;
