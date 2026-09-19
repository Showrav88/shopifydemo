/**
 * Shopify multi-variant builder — driven by VariantLibrary sheet (any option combo).
 * Priority: scraped variants → manual Sizes/Colors → Option 1/2/3 columns → single variant.
 */

const VARIANTS = {};

VARIANTS.detectProfile = function detectProfile(category, explicitProfile) {
  const p = String(explicitProfile || '').trim().toLowerCase();
  if (p) return p;
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
        option1: VARIANTS.norm(v.option1 || (split ? split.size : sizeRaw)),
        option2: VARIANTS.norm(v.option2 || v.color || (split && split.color) || ''),
        option3: VARIANTS.norm(v.option3 || v.length || (split && split.length) || ''),
      };
    });
  } catch {
    return [];
  }
};

/** Read Shopify option config from VariantLibrary columns on the product row. */
VARIANTS.parseOptionConfig = function parseOptionConfig(row) {
  const options = [];
  for (let i = 1; i <= 3; i++) {
    const name = VARIANTS.norm(row[`Option ${i} name`]);
    const values = VARIANTS.parseList(row[`Option ${i} values`]);
    if (name && values.length > 0) options.push({ name, values });
  }
  return options;
};

/** Legacy Sizes / Colors / Lengths columns merged into named options when Option columns empty. */
VARIANTS.legacyOptionConfig = function legacyOptionConfig(row) {
  const sizes = VARIANTS.parseList(row.Sizes);
  const colors = VARIANTS.parseList(row.Colors);
  const lengths = VARIANTS.parseList(row.Lengths);
  const profile = VARIANTS.norm(row['Variant profile'] || row.variant_profile).toLowerCase();
  const options = [];

  if (sizes.length > 0) {
    const sizeName = /numeric|jean|pant|trouser/.test(profile) ? 'Waist'
      : /footwear|shoe/.test(profile) ? 'UK Size' : 'Size';
    options.push({ name: sizeName, values: sizes });
  }
  if (lengths.length > 0) {
    options.push({ name: 'Length', values: lengths });
  }
  if (colors.length > 0) {
    options.push({ name: 'Color', values: colors });
  }
  return options;
};

VARIANTS.cartesian = function cartesian(options) {
  if (!options.length) return [];
  let combos = options[0].values.map((v) => [v]);
  for (let i = 1; i < options.length; i++) {
    const next = [];
    for (const combo of combos) {
      for (const val of options[i].values) {
        next.push([...combo, val]);
      }
    }
    combos = next;
  }
  return combos;
};

VARIANTS.buildRowsFromOptions = function buildRowsFromOptions(options) {
  const combos = VARIANTS.cartesian(options);
  return combos.map((vals) => ({
    options: options.map((opt, i) => ({ name: opt.name, value: vals[i] || '' })),
    option1: vals[0] || '',
    option2: vals[1] || '',
    option3: vals[2] || '',
    price: '',
    sku: '',
    qty: null,
  }));
};

VARIANTS.buildVariantRows = function buildVariantRows(row) {
  const scraped = VARIANTS.parseScrapedVariants(row);
  const rows = [];

  if (scraped.length > 0) {
    for (const v of scraped) {
      const o1 = VARIANTS.norm(v.option1 || v.size || '');
      const o2 = VARIANTS.norm(v.option2 || v.color || '');
      const o3 = VARIANTS.norm(v.option3 || v.length || '');
      if (!o1 && !o2 && !o3) continue;
      rows.push({
        options: [
          o1 ? { name: 'Option 1', value: o1 } : null,
          o2 ? { name: 'Option 2', value: o2 } : null,
          o3 ? { name: 'Option 3', value: o3 } : null,
        ].filter(Boolean),
        option1: o1,
        option2: o2,
        option3: o3,
        price: v.price ?? v.competitor_price ?? '',
        sku: VARIANTS.norm(v.sku || ''),
        qty: v.inventory ?? v.inventory_quantity ?? v.stock ?? null,
      });
    }
    return { rows, used_library: false, source: 'scraped' };
  }

  let optionConfig = VARIANTS.parseOptionConfig(row);
  if (optionConfig.length === 0) {
    optionConfig = VARIANTS.legacyOptionConfig(row);
  }
  if (optionConfig.length > 0) {
    return {
      rows: VARIANTS.buildRowsFromOptions(optionConfig),
      used_library: true,
      source: 'library',
      optionConfig,
    };
  }

  return { rows: [], used_library: false, source: 'none' };
};

VARIANTS.variantSku = function variantSku(baseSku, parts, index) {
  const base = VARIANTS.norm(baseSku) || 'SKU';
  const slugParts = [base];
  for (const p of parts) {
    if (p && p !== 'One Size') slugParts.push(VARIANTS.slugPart(p));
  }
  if (slugParts.length === 1) slugParts.push(`V${index + 1}`);
  return slugParts.join('-').slice(0, 50);
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
  const profileKey = VARIANTS.detectProfile(
    row.validated_category || row['Product category'] || '',
    row['Variant profile'] || row.variant_profile,
  );
  const { rows, used_library, optionConfig, source } = VARIANTS.buildVariantRows(row);

  const sellPrice = VARIANTS.resolvePrice(row);
  const totalInv = VARIANTS.resolveInventory(row);
  const baseSku = row.validated_sku || row.SKU || row.processing_sku || '';
  const vendor = row.Vendor || row.validated_vendor || '';
  const productType = row.validated_category || row['Product category'] || listing.collection || '';

  if (rows.length === 0) {
    return {
      multi_variant: false,
      variant_count: 1,
      variant_profile: profileKey,
      variant_source: source,
      used_library: false,
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
      inventory_updates: [{ sku: baseSku, inventory_quantity: totalInv }],
    };
  }

  const config = optionConfig && optionConfig.length
    ? optionConfig
    : rows[0].options.map((o, i) => ({ name: o.name || `Option ${i + 1}`, values: [] }));

  const optionNames = config.length
    ? config.map((o) => o.name)
    : ['Option 1', 'Option 2', 'Option 3'].filter((_, i) => rows.some((r) => {
      const v = [r.option1, r.option2, r.option3][i];
      return Boolean(v);
    }));

  const valueSets = optionNames.map(() => new Set());
  const shopifyVariants = [];
  const inventoryUpdates = [];
  const perVariantInv = rows.length > 0 && totalInv > 0
    ? Math.max(1, Math.floor(totalInv / rows.length))
    : 0;

  rows.forEach((r, i) => {
    const vals = [r.option1, r.option2, r.option3];
    const variant = {
      price: sellPrice,
      sku: r.sku || VARIANTS.variantSku(baseSku, vals.filter(Boolean), i),
      inventory_management: 'shopify',
      inventory_quantity: 0,
    };

    optionNames.forEach((name, idx) => {
      const val = vals[idx];
      if (val) {
        valueSets[idx].add(val);
        variant[`option${idx + 1}`] = val;
      }
    });

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

  const shopifyOptions = optionNames
    .map((name, idx) => ({ name, values: [...valueSets[idx]] }))
    .filter((o) => o.values.length > 0);

  if (shopifyOptions.length > 0) {
    product.options = shopifyOptions;
  }

  return {
    multi_variant: shopifyVariants.length > 1,
    variant_count: shopifyVariants.length,
    variant_profile: profileKey,
    variant_preset: row['Variant preset ID'] || row.variant_preset_id || '',
    variant_source: source,
    used_library: Boolean(used_library),
    shopify_payload: { product },
    inventory_updates: inventoryUpdates,
  };
};

if (typeof module !== 'undefined') module.exports = VARIANTS;
