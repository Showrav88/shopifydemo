/**
 * Phase 3: Shopify product organization — taxonomy category + collections.
 */

const ORG = {};

// Override via sheet column "Shopify Category" (full GID). Auto-map is best-effort.
ORG.TAXONOMY_GIDS = {
  shirt: 'gid://shopify/TaxonomyCategory/aa-1-13-8',
  shirts: 'gid://shopify/TaxonomyCategory/aa-1-13-8',
  tshirt: 'gid://shopify/TaxonomyCategory/aa-1-13-7',
  't-shirt': 'gid://shopify/TaxonomyCategory/aa-1-13-7',
  dress: 'gid://shopify/TaxonomyCategory/aa-1-13-1',
  dresses: 'gid://shopify/TaxonomyCategory/aa-1-13-1',
  jean: 'gid://shopify/TaxonomyCategory/aa-1-13-4',
  jeans: 'gid://shopify/TaxonomyCategory/aa-1-13-4',
  trouser: 'gid://shopify/TaxonomyCategory/aa-1-13-11',
  pant: 'gid://shopify/TaxonomyCategory/aa-1-13-11',
  jacket: 'gid://shopify/TaxonomyCategory/aa-1-13-3',
  coat: 'gid://shopify/TaxonomyCategory/aa-1-13-2',
  shoe: 'gid://shopify/TaxonomyCategory/aa-1-13-9',
  shoes: 'gid://shopify/TaxonomyCategory/aa-1-13-9',
  sneaker: 'gid://shopify/TaxonomyCategory/aa-1-13-9',
  bag: 'gid://shopify/TaxonomyCategory/aa-1-5-3',
  accessory: 'gid://shopify/TaxonomyCategory/aa-1-1',
};

ORG.slugify = function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
};

ORG.resolveTaxonomyGid = function resolveTaxonomyGid(row, listing) {
  const explicit = String(row['Shopify Category'] || row.shopify_category_gid || '').trim();
  if (explicit.startsWith('gid://shopify/TaxonomyCategory/')) return explicit;

  const hay = [
    row['Product category'],
    row['Suggested Category'],
    row.validated_category,
    listing?.collection,
    listing?.tags,
  ].join(' ').toLowerCase();

  for (const [key, gid] of Object.entries(ORG.TAXONOMY_GIDS)) {
    if (hay.includes(key)) return gid;
  }
  return '';
};

ORG.resolveCollectionHandle = function resolveCollectionHandle(row, listing) {
  const explicit = String(
    row.Collection || row['Suggested Collection'] || row.collection_handle || ''
  ).trim();
  if (explicit) return ORG.slugify(explicit);

  const path = String(
    listing?.collection || row['Product category'] || row['Suggested Category'] || ''
  ).trim();
  if (!path) return '';

  const parts = path.split(/>|\/|,/).map((p) => p.trim()).filter(Boolean);
  if (parts.length >= 2) {
    return ORG.slugify(`${parts[0]}-${parts[parts.length - 1]}`);
  }
  return ORG.slugify(parts[0] || path);
};

ORG.enrichProduct = function enrichProduct(product, row, listing) {
  const categoryGid = ORG.resolveTaxonomyGid(row, listing);
  if (categoryGid) product.category = categoryGid;

  const collectionHandle = ORG.resolveCollectionHandle(row, listing);
  if (collectionHandle) {
    const tag = `collection:${collectionHandle}`;
    const existing = String(product.tags || '');
    product.tags = existing ? `${existing}, ${tag}` : tag;
  }

  return {
    category_gid: categoryGid,
    collection_handle: ORG.resolveCollectionHandle(row, listing),
  };
};

if (typeof module !== 'undefined') module.exports = ORG;
