# Store Setup Guide — UK Men's & Women's Fashion (Internal Test Store)

## Goal

Build a professional-looking UK Shopify store for men's and women's clothing and accessories using a **free theme**. The store is for **internal product testing** — no physical location, UK market only.

---

## Phase 1 — Account & Basics (Day 1)

### 1. Create Shopify Account
- Go to [shopify.com/uk](https://www.shopify.com/uk)
- Start free trial (3 days, then promotional pricing available)
- Store name: use output from [01-brand-domain-prompt.md](./01-brand-domain-prompt.md)

### 2. Store Settings
| Setting | Value |
|---------|-------|
| Store address country | United Kingdom |
| Currency | GBP (£) |
| Time zone | Europe/London (GMT/BST) |
| Store contact email | Team shared inbox |
| Legal business name | [YOUR COMPANY NAME] |
| Physical location | None — online only |

**Path:** Settings → Store details

### 3. Markets & Shipping
- **Primary market:** United Kingdom
- **Shipping zones:** UK only (England, Scotland, Wales, Northern Ireland)
- **Rates:** Flat rate for testing (e.g. £3.95 standard, free over £50)
- Disable international shipping for now

**Path:** Settings → Markets → Shipping and delivery

### 4. Taxes
- Enable **UK VAT** collection if selling B2C
- For internal testing with no real sales, document VAT settings but use test mode

**Path:** Settings → Taxes and duties

---

## Phase 2 — Brand & Theme (Day 1–2)

### 5. Brand Identity
Run these prompts in order:
1. [01-brand-domain-prompt.md](./01-brand-domain-prompt.md) → pick domain
2. [02-logo-prompt.md](./02-logo-prompt.md) → create logo
3. [03-colour-scheme-prompt.md](./03-colour-scheme-prompt.md) → apply colours in theme editor
4. [04-hero-banner-prompt.md](./04-hero-banner-prompt.md) → set homepage hero

Upload logo: **Settings → Brand → Logo**

### 6. Install Free Theme
1. Online Store → Themes → **Explore free themes**
2. Install **Dawn** (recommended) or **Craft**
3. Click **Customize** and apply colour scheme from step 5

### 7. Navigation Structure
```
Home
├── Men
│   ├── Tops
│   ├── Bottoms
│   ├── Outerwear
│   └── Accessories
├── Women
│   ├── Tops
│   ├── Dresses
│   ├── Bottoms
│   └── Accessories
├── New In
├── Sale
└── About
```

**Path:** Online Store → Navigation

---

## Phase 3 — Content & Products (Day 2–3)

### 8. Store Pages
Run [06-store-pages-prompt.md](./06-store-pages-prompt.md) to generate:
- About Us
- Privacy Policy (UK GDPR)
- Terms of Service (UK law)
- Shipping Policy
- Returns & Refunds Policy

Add pages: **Online Store → Pages**

### 9. Footer
Run [05-footer-prompt.md](./05-footer-prompt.md) for footer text.

**Path:** Online Store → Themes → Customize → Footer

### 10. Test Products (minimum 10)
Add a mix for realistic testing:

| Category | Example products | Variants to test |
|----------|-----------------|------------------|
| Men's | Cotton tee, chinos, hoodie | Size S–XL, 2 colours |
| Women's | Blouse, midi dress, cardigan | Size 6–16, 2 colours |
| Accessories | Belt, scarf, cap | One size / colour |

For each product include:
- Title, description, price (£)
- 2–4 images (use Shopify free image library or placeholders)
- Variants (size, colour)
- SKU and inventory (set to 100 for testing)
- Collection assignment (Men / Women / Accessories)

### 11. Collections
Create automated collections:
- **Men** → product type contains "Men"
- **Women** → product type contains "Women"
- **Accessories** → product type contains "Accessories"
- **New In** → tag equals "new-in"
- **Sale** → compare-at price is set

---

## Phase 4 — Payments & Launch (Day 3)

### 12. Payments
- Enable **Shopify Payments** (UK)
- For internal testing: use **Bogus Gateway** or test mode — no real charges
- Enable Apple Pay / Google Pay for checkout testing

**Path:** Settings → Payments

### 13. Checkout Settings
- Customer accounts: optional (recommended for testing login flows)
- Email notifications: enable order confirmation, shipping update
- Abandoned checkout: enable (test email flow)

**Path:** Settings → Checkout

### 14. Domain
- Use free `yourstore.myshopify.com` for internal testing
- Buy `.co.uk` or `.com` later if needed: [domains.shopify.com](https://domains.shopify.com/)

### 15. Go Live (Internal)
- Remove password protection when team is ready
- Or keep password on and share password with team only
- Add store URL to Jira project board (see presentation doc)

---

## Phase 5 — Ongoing Testing Checklist

Use this checklist each sprint when testing new product features:

- [ ] Add new test product with all variant combinations
- [ ] Test add-to-cart from collection page and product page
- [ ] Test checkout with UK address (test card: 4242 4242 4242 4242)
- [ ] Test discount code application
- [ ] Test return/refund flow (create test order → refund)
- [ ] Test on mobile (iOS Safari + Android Chrome)
- [ ] Test email notifications (order confirm, shipping)
- [ ] Screenshot any bugs → attach to Jira ticket
- [ ] Log test results in Excel tracker (see presentation doc)

---

## Useful Links

| Resource | URL |
|----------|-----|
| Shopify UK pricing | https://www.shopify.com/uk/pricing |
| Shopify Help Center | https://help.shopify.com/en |
| Free themes | https://themes.shopify.com/themes?price=free |
| Shopify Payments UK | https://www.shopify.com/uk/payments |
| Collaborator accounts | https://help.shopify.com/en/manual/your-account/staff-accounts/security/collaborator-accounts |
| UK GDPR guidance | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/ |
