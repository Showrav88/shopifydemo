# Ashik Bhai's Shopify UK Store — Team Kickoff Presentation

**Project:** UK Men's & Women's Fashion E-commerce (Internal Test Store)  
**Date:** September 2026  
**Presenter:** Showrav Karmakar  
**Audience:** Product & Engineering Team  
**Status:** Planning → Build

> **Open the presentation:** Double-click [presentation.html](./presentation.html) — one file, no install needed.

---

## Slide 1 — Title

# Build a UK Fashion Shopify Store
### Men's & Women's Clothing + Accessories
**Internal product testing environment — no physical store**

---

## Slide 2 — Why Analysis First (Client, Location, Customer)

Before building in Shopify, we must complete **Phase 0 analysis**. This is what makes the UI look professional and work on mobile, laptop, and every screen size.

### Client analysis
- Business goals (internal product testing)
- Brand personality and tone
- Budget and timeline
- Success criteria and decision makers

### Location analysis
- UK market — GBP, VAT, shipping zones, consumer law
- No physical store (online only)
- UK payment methods (Visa, Apple Pay, Klarna)
- Seasonal fashion trends

### Customer analysis
- UK shoppers aged 22–45
- Men's and women's fashion buyers
- Mobile-first browsing (70%+ traffic)
- Expect fast checkout, clear sizing, trust signals

### Analysis → UI decisions

| Analysis input | UI output in Shopify |
|----------------|---------------------|
| UK fashion customer | Clean neutrals + one bold accent colour |
| Mobile-first shopper | Dawn theme, large tap targets, stacked sections |
| Men + Women catalog | Split navigation: Men / Women / Accessories |
| UK trust expectations | Shipping policy, 14-day returns, GDPR privacy in footer |
| Mid-range pricing (£15–£80) | Professional photography, not discount-store layout |

### Responsive testing matrix

| Device | Browser | Test |
|--------|---------|------|
| iPhone | Safari | Homepage, cart, checkout |
| Android | Chrome | Collections, product page |
| iPad | Safari | Navigation, filters |
| MacBook | Chrome | Full store walkthrough |
| Windows | Edge/Chrome | Checkout, account |

**Rule:** Design and test on mobile first. Log results in Excel Sheet 4.

---

## Slide 3 — Ashik Bhai's Plan (Call Summary)

### What we agreed on the call

| Decision | Detail |
|----------|--------|
| **Platform** | Shopify (hosted, fast to launch, no server management) |
| **Market** | United Kingdom only |
| **Catalog** | Men's clothing, women's clothing, accessories |
| **Physical store** | None — online only, ships UK-wide |
| **Purpose** | Internal sandbox to test products we are building |
| **Theme** | Free Shopify theme (Dawn or Craft recommended) |
| **Design goal** | Look professional and polished — not a rough prototype |
| **Timeline approach** | Phase 1: store shell + brand → Phase 2: test products → Phase 3: integrate with our product testing workflows |

### Success criteria
- Store looks like a real UK fashion brand
- Team can place test orders end-to-end
- All pages, policies, and checkout flows work on mobile
- Reusable prompts and docs so we rebuild faster next time

---

## Slide 3 — Why Shopify for This Project

| Benefit | Why it matters for us |
|---------|----------------------|
| **Fast setup** | Live store in days, not weeks |
| **No infrastructure** | No servers, SSL, or hosting to manage |
| **Built-in checkout** | PCI-compliant payments out of the box |
| **Free themes** | Professional look without design agency cost |
| **App ecosystem** | Add features (reviews, size guides, analytics) when needed |
| **UK-native** | GBP, UK VAT, Royal Mail integrations, Shopify Payments UK |
| **AI tools included** | Sidekick assistant, Magic for product descriptions |
| **Password protection** | Keep store private during internal testing |

---

## Slide 4 — Current Shopify UK Pricing (September 2026)

> Source: [shopify.com/uk/pricing](https://www.shopify.com/uk/pricing) — verify before purchase as prices change.

### Main Plans

| Plan | Monthly (pay yearly) | Monthly (pay monthly) | Staff Accounts | Card Rate (Shopify Payments) | Best For |
|------|---------------------|----------------------|----------------|------------------------------|----------|
| **Basic** | **£19/mo** | £25/mo | Owner only* | 2.0% + 25p | Solo setup, internal test store |
| **Grow** | **£49/mo** | £65/mo | **5 staff** | 1.7% + 25p | Small team needing admin access |
| **Advanced** | **£259/mo** | £344/mo | **15 staff** | 1.5% + 25p | High volume, custom reports |
| **Plus** | **from £1,800/mo** | from £1,800/mo | **Unlimited** | from 1.3% + 25p | Enterprise, custom checkout |

\* Basic includes the store owner login. Additional staff seats require Grow or above. **Collaborator accounts** (see Slide 6) are available on all plans and do not count toward staff limits.

### Add-ons

| Add-on | Price | When needed |
|--------|-------|-------------|
| **POS Pro** | +£69/mo per location | Physical retail (not needed for us) |
| **Domain (.co.uk)** | ~£10–15/year | When we want a custom URL |
| **Apps** | Free–£50+/mo each | Size guides, reviews, analytics |

### Trial & Promotions
- **3-day free trial** — no credit card required to start
- Promotional offer often available: **£1/month for first 3 months** after trial
- Annual billing saves ~25% vs monthly

### Official Links

| Resource | URL |
|----------|-----|
| UK Pricing | https://www.shopify.com/uk/pricing |
| Plan comparison | https://www.shopify.com/uk/pricing#plan-comparison |
| Start free trial | https://www.shopify.com/uk/free-trial |
| Shopify Payments UK | https://www.shopify.com/uk/payments |
| Free themes | https://themes.shopify.com/themes?price=free |
| Help Center | https://help.shopify.com/en |
| Collaborator accounts | https://help.shopify.com/en/manual/your-account/staff-accounts/security/collaborator-accounts |

---

## Slide 5 — Which Plan Should We Pick?

### Recommendation for this project: **Basic (£19/mo annual)**

| Factor | Why Basic works |
|--------|----------------|
| Internal testing only | No real sales volume — transaction fees irrelevant |
| 1–2 people setting up | Owner account is enough for initial build |
| Free theme | Full theme customisation included |
| Unlimited products | Add as many test SKUs as needed |
| Shopify Payments test mode | Test checkout without real charges |

### When to upgrade to Grow (£49/mo)

Upgrade when **3+ team members** need direct admin access (not via collaborators):

- Marketing person managing collections and campaigns
- Developer customising theme code
- QA tester managing orders and refunds
- Operations person handling inventory

**Break-even math:** Grow costs £30/mo more than Basic. At ~£10k/mo in real sales, the lower card rate (1.7% vs 2.0%) saves ~£30/mo — but this is irrelevant for internal testing.

---

## Slide 6 — How Developers & Team Members Work Together

### Three ways to give people access

| Method | Who | Counts toward staff limit? | Available on |
|--------|-----|--------------------------|--------------|
| **Store owner** | Person who created the store | N/A (always 1 owner) | All plans |
| **Staff accounts** | Team members with role-based permissions | Yes — 0 on Basic, 5 on Grow, 15 on Advanced | Grow+ for additional seats |
| **Collaborator accounts** | Developers/agencies with Shopify Partner accounts | **No — free, unlimited** | All plans |

### Collaborator accounts — key for our dev team

- Any developer with a **free Shopify Partner account** can request access
- Store owner approves via a **collaborator request code**
- Collaborators get granular permissions (themes, products, settings, etc.)
- **Do not count** toward staff account limits on any plan
- Ideal for: theme developers, agency partners, freelancers

**Setup:**
1. Developer creates free account at [partners.shopify.com](https://partners.shopify.com/)
2. Developer requests store access with the collaborator code
3. Store owner approves in **Settings → Users and permissions**

### Recommended access model for our project

| Person | Access method | Permissions |
|--------|--------------|-------------|
| Ashik Bhai / Project lead | Store owner | Full |
| Developer 1 (theme) | Collaborator | Themes, Online Store |
| Developer 2 (products/API) | Collaborator | Products, Settings |
| QA tester | Staff (Grow) or Collaborator | Orders, Products (view) |
| Designer | Collaborator | Themes, Files |

**Bottom line:** We can run the entire project on **Basic + Collaborator accounts** without upgrading — unless we need 3+ non-developer staff with daily admin access.

---

## Slide 7 — Pros & Cons: Shopify Plan Comparison

### Basic (£19/mo) — Pros
- Lowest cost for a full online store
- Unlimited products, collections, pages
- Free themes + full theme editor
- Shopify Payments + test mode
- Collaborator access for developers (free)
- Password protection for internal use
- Sidekick AI assistant included
- 10 inventory locations
- 24/7 live chat support

### Basic (£19/mo) — Cons
- **No additional staff accounts** — only store owner login
- Basic reports only (no professional/cohort reports)
- Higher card rates if we ever process real sales (2.0% + 25p)
- 2% third-party payment gateway fee (if not using Shopify Payments)
- Limited checkout customisation
- No Shopify Flow automation
- API rate limits: standard

### Grow (£49/mo) — Pros
- **5 staff accounts** with role-based permissions
- Professional reports (cohort, retention, behaviour)
- Lower card rates (1.7% + 25p)
- Shopify Flow automation (abandoned cart, tagging, etc.)
- 1% third-party gateway fee (vs 2% on Basic)
- Better for teams where non-devs need daily admin access

### Grow (£49/mo) — Cons
- £30/mo more than Basic — hard to justify for test-only store
- Still limited checkout customisation
- Standard API rate limits
- May be overkill if only developers touch the store

### Advanced (£259/mo) — Pros
- 15 staff accounts
- Custom reports and report builder
- Lowest card rates (1.5% + 25p)
- Live third-party shipping rates at checkout
- Up to 2× API rate limits on select APIs
- Enhanced live chat support

### Advanced (£259/mo) — Cons
- **£259/mo is excessive** for an internal test store
- Only justified at £20k+/mo real sales volume
- Not needed for our current scope

### Plus (from £1,800/mo) — Pros
- Unlimited staff with custom roles
- Fully customisable checkout
- Up to 9 free expansion stores
- Up to 10× API rate limits
- Dedicated launch manager
- B2B wholesale catalogs

### Plus (from £1,800/mo) — Cons
- Enterprise pricing — completely out of scope
- 3-year contract typical
- Massive overkill for internal testing

---

## Slide 8 — Pros & Cons: Shopify vs Alternatives (Before We Start)

### Why Shopify (Pros)

| Pro | Detail |
|-----|--------|
| Speed to market | Store live in 1–3 days with free theme |
| No DevOps | Hosting, SSL, CDN, security handled by Shopify |
| Checkout trust | Shopify Checkout converts ~15% better than average |
| UK compliance | GDPR tools, UK VAT, Consumer Rights Act templates |
| Mobile-first themes | Dawn theme scores 90+ on Lighthouse |
| Ecosystem | 8,000+ apps for any feature we might need later |
| Documentation | Excellent help center and community |
| Test mode | Bogus gateway + Shopify Payments test transactions |
| Version control | Theme code exportable to GitHub (with Shopify GitHub integration) |

### Shopify Considerations (Cons)

| Con | Detail | Mitigation |
|-----|--------|------------|
| Monthly cost | £19–£49/mo even with no sales | Acceptable for test infra; cancel when done |
| Transaction fees | 2.0% + 25p per sale on Basic | Use test mode; no real transactions |
| Theme limitations | Free themes have fixed section layouts | Customise within theme editor; upgrade to paid theme (£$180–350) only if needed |
| App costs add up | Useful apps are £5–50/mo each | Start with zero apps; add only when blocked |
| Vendor lock-in | Migrating off Shopify later is painful | Acceptable — this is a test store, not permanent infra |
| Liquid templating | Theme code uses Shopify's Liquid, not React | Developers learn Liquid (similar to Jinja/Twig) |
| No direct DB access | Can't query product DB with SQL | Use Shopify Admin API / Storefront API |
| Basic plan staff limit | Only owner login on Basic | Use Collaborator accounts for devs |
| Custom domain cost | ~£10–15/year for .co.uk | Use free .myshopify.com for testing |
| Email limitations | Shopify Email free tier is basic | Use Mailchimp/Klaviyo later if needed |

### Things to Decide Before Building

| Question | Our answer | Notes |
|----------|-----------|-------|
| Custom domain now or later? | **Later** | Use `.myshopify.com` for testing |
| Real payments or test only? | **Test only** | Bogus gateway / Shopify Payments test mode |
| Who owns the store account? | **Ashik Bhai** | Store owner; others get collaborator access |
| Which plan? | **Basic (£19/mo)** | Upgrade to Grow only if 3+ staff need daily access |
| Which theme? | **Dawn (free)** | Switch to Craft if we want editorial look |
| International shipping? | **No** | UK only |
| VAT registered? | **TBD** | Enable VAT collection if selling B2C publicly later |
| Product data source? | **Manual entry** | 10–20 test products; CSV import if scaling |
| Analytics? | **Shopify Analytics (built-in)** | Add Google Analytics 4 later if needed |

---

## Slide 9 — Team Workflow: Jira + Excel

### Why we track in both Jira and Excel

| Tool | Purpose |
|------|---------|
| **Jira** | Sprint tasks, bugs, blockers, dev assignments |
| **Excel / Google Sheets** | Store config reference, credentials, design decisions, test results log |

Jira drives **what to do**. Excel captures **what we decided** — so anyone can pick up the project later without digging through tickets.

---

### Jira Project Structure

**Project key:** `SHOP`  
**Board type:** Kanban (To Do → In Progress → Review → Done)

#### Epics

| Epic ID | Title | Description |
|---------|-------|-------------|
| SHOP-E1 | Store Setup | Account, settings, theme, brand |
| SHOP-E2 | Content & Pages | About, policies, footer, navigation |
| SHOP-E3 | Product Catalog | Test products, collections, variants |
| SHOP-E4 | Checkout & Payments | Payment setup, test orders, refunds |
| SHOP-E5 | QA & Launch | Mobile testing, bug fixes, go-live |

#### Sample Tickets

| Ticket | Epic | Assignee | Priority |
|--------|------|----------|----------|
| SHOP-001 | E1 | Ashik | High — Create Shopify account (UK, GBP) |
| SHOP-002 | E1 | Dev 1 | High — Install Dawn theme |
| SHOP-003 | E1 | Designer | High — Brand name + logo (use build kit prompts) |
| SHOP-004 | E1 | Designer | Medium — Apply colour scheme in theme editor |
| SHOP-005 | E2 | Dev 1 | Medium — Create navigation (Men/Women/Accessories) |
| SHOP-006 | E2 | Dev 2 | Medium — Generate and publish store pages (UK legal) |
| SHOP-007 | E3 | Dev 2 | High — Add 10 test products with variants |
| SHOP-008 | E3 | Dev 2 | Medium — Create collections (Men, Women, Accessories) |
| SHOP-009 | E4 | Dev 1 | High — Enable Shopify Payments test mode |
| SHOP-010 | E4 | QA | High — Place test order end-to-end |
| SHOP-011 | E5 | QA | High — Mobile testing (iOS + Android) |
| SHOP-012 | E5 | Dev 1 | Medium — Fix bugs from QA |
| SHOP-013 | E5 | Ashik | Low — Share store URL with product team |

#### Jira Ticket Template

```
Title: [SHOP-XXX] Short description
Epic: SHOP-E1 Store Setup
Assignee: @name
Priority: High / Medium / Low

Description:
What needs to be done and why.

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Screenshot attached
- [ ] Excel tracker updated

Links:
- Build kit file: shopify-uk-build-kit/XX-file.md
- Shopify admin path: Online Store → Themes → ...
```

---

### Excel Tracker Structure

**File name:** `SHOP-UK-Store-Tracker.xlsx`  
**Location:** Shared team drive (link in Jira project description)

#### Sheet 1 — Store Config

| Field | Value | Updated by | Date |
|-------|-------|------------|------|
| Store name | | | |
| Store URL | | | |
| Shopify plan | Basic £19/mo | | |
| Theme | Dawn | | |
| Primary colour | #______ | | |
| Currency | GBP | | |
| Market | UK only | | |
| Store owner | Ashik Bhai | | |
| Collaborator code | (private — do not share publicly) | | |
| Password (if protected) | | | |

#### Sheet 2 — Brand Assets

| Asset | Status | File/link | Owner | Date |
|-------|--------|-----------|-------|------|
| Brand name | | | | |
| Domain | | | | |
| Logo (PNG) | | | | |
| Favicon | | | | |
| Hero banner | | | | |
| Colour scheme | | | | |

#### Sheet 3 — Products

| SKU | Title | Category | Gender | Price (£) | Sizes | Colours | Status | Notes |
|-----|-------|----------|--------|-----------|-------|---------|--------|-------|
| M-TEE-001 | Classic Cotton Tee | Tops | Men | 24.99 | S,M,L,XL | White,Navy | Draft | |
| W-DRS-001 | Midi Wrap Dress | Dresses | Women | 49.99 | 8,10,12,14 | Black,Floral | Draft | |

#### Sheet 4 — Test Results Log

| Date | Tester | Test case | Device | Pass/Fail | Screenshot | Jira ticket |
|------|--------|-----------|--------|-----------|------------|-------------|
| | | Add to cart | iPhone 15 | | | SHOP-011 |
| | | Checkout (test card) | Desktop Chrome | | | SHOP-010 |
| | | Returns page loads | Android | | | |

#### Sheet 5 — Decisions Log

| Date | Decision | Rationale | Decided by |
|------|----------|-----------|------------|
| Sep 2026 | Use Shopify Basic plan | Internal test only; collaborators for devs | Ashik Bhai |
| Sep 2026 | Dawn free theme | Fast, mobile-first, clean fashion look | Team |
| Sep 2026 | UK only, no physical store | Scope per Ashik Bhai call | Ashik Bhai |
| Sep 2026 | Jira for tasks, Excel for config | Faster onboarding for future team members | Team |

---

### Team Rituals

| Ritual | When | What |
|--------|------|------|
| **Kickoff** | Day 1 | Ashik Bhai walks through this presentation |
| **Daily stand-up** | 15 min | Jira board review — blockers only |
| **Build session** | Day 1–3 | Follow build kit prompts in order |
| **QA pass** | Day 3–4 | QA runs test cases, logs in Excel, files Jira bugs |
| **Demo** | Day 5 | Show store to product team, collect feedback |
| **Retro** | Day 5 | What worked, update build kit for next time |

---

## Slide 10 — Build Phases & Timeline

```
Week 1 — Foundation
├── Day 1: Account + settings + theme install
├── Day 2: Brand (name, logo, colours, hero)
└── Day 3: Pages + navigation + footer

Week 1 — Catalog
├── Day 3: Add 10 test products
├── Day 4: Collections + checkout setup
└── Day 5: QA + demo + retro

Week 2+ — Product Testing
├── Integrate with our product testing workflows
├── Add/remove test products as needed
└── Iterate on theme and UX based on feedback
```

---

## Slide 11 — Build Kit Reference

All prompts and guides are in the repo:

```
shopify-uk-build-kit/
├── README.md                    ← Start here
├── 00-store-setup-guide.md      ← Step-by-step checklist
├── 01-brand-domain-prompt.md    ← Brand name AI prompt
├── 02-logo-prompt.md            ← Logo AI prompt
├── 03-colour-scheme-prompt.md   ← Theme colours AI prompt
├── 04-hero-banner-prompt.md     ← Homepage hero AI prompt
├── 05-footer-prompt.md          ← Footer text AI prompt
└── 06-store-pages-prompt.md     ← Legal pages AI prompt (UK)
```

**Rule:** Always use the build kit prompts — do not freestyle. This keeps output consistent and saves time on the next project.

---

## Slide 12 — Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Wrong Shopify plan chosen | Low — £30/mo wasted | Medium | Start Basic; upgrade only when needed |
| Store looks unprofessional | High — undermines testing | Medium | Use Dawn theme + build kit prompts |
| Team members locked out | Medium — slows dev | Low | Use Collaborator accounts on Basic |
| Legal pages incomplete | Medium — if store goes public | Low | Use UK-specific prompts; solicitor review before public launch |
| Test products look fake | Medium — unrealistic testing | Medium | Use real product photos and detailed descriptions |
| Credentials lost | High — lose store access | Low | Document in Excel; store owner = Ashik Bhai |
| Scope creep (apps, custom dev) | Medium — delays launch | High | Stick to free theme + zero apps for Phase 1 |

---

## Slide 13 — Action Items (Next Steps)

| # | Action | Owner | Due |
|---|--------|-------|-----|
| 1 | Create Shopify account (UK, GBP, Basic plan) | Ashik Bhai | Day 1 |
| 2 | Set up Jira project `SHOP` with epics and tickets | Ashik Bhai | Day 1 |
| 3 | Create Excel tracker and share with team | Ashik Bhai | Day 1 |
| 4 | Run brand/domain prompt → pick name | Designer | Day 1 |
| 5 | Install Dawn theme + apply brand | Dev 1 | Day 2 |
| 6 | Generate and publish UK legal pages | Dev 2 | Day 2 |
| 7 | Add 10 test products | Dev 2 | Day 3 |
| 8 | Enable test payments + place test order | Dev 1 + QA | Day 4 |
| 9 | Mobile QA pass | QA | Day 4 |
| 10 | Demo to product team | Ashik Bhai | Day 5 |

---

## Slide 14 — Q&A

### Common questions

**Q: Can we use Basic and still have 3 developers working?**  
A: Yes. Developers use **Collaborator accounts** (free, unlimited, don't count toward staff limits). Only upgrade to Grow if non-developer team members need daily admin login.

**Q: Do we need a custom domain?**  
A: Not for internal testing. Use `yourstore.myshopify.com`. Buy `.co.uk` later if the store goes public.

**Q: Will we be charged for test orders?**  
A: No, if using Shopify Payments test mode or Bogus Gateway. No real money moves.

**Q: What if we outgrow Shopify?**  
A: This is a test store. If we need a production e-commerce platform later, we evaluate separately. Shopify is the fastest path to a realistic test environment now.

**Q: Who pays the Shopify bill?**  
A: [TBD — company card / Ashik Bhai's account → expense]

---

## Appendix A — Shopify Test Card Numbers

| Card | Number | Use |
|------|--------|-----|
| Visa (success) | 4242 4242 4242 4242 | Test successful payment |
| Visa (decline) | 4000 0000 0000 0002 | Test declined payment |
| Mastercard | 5555 5555 5555 4444 | Test successful payment |

- Expiry: any future date
- CVV: any 3 digits
- Postcode: any valid UK postcode (e.g. SW1A 1AA)

---

## Appendix B — Free Theme Comparison

| Theme | Style | Mobile score | Best for |
|-------|-------|-------------|----------|
| **Dawn** | Minimal, clean | 90+ | Our project — default choice |
| **Craft** | Editorial, storytelling | 85+ | If we want magazine-style layout |
| **Sense** | Bold, visual | 85+ | Seasonal campaigns |
| **Refresh** | Product-focused | 88+ | Large catalogs |

Install: Online Store → Themes → Explore free themes

---

## Appendix C — Useful Links (Bookmark These)

| Resource | URL |
|----------|-----|
| Shopify UK | https://www.shopify.com/uk |
| UK Pricing | https://www.shopify.com/uk/pricing |
| Free trial | https://www.shopify.com/uk/free-trial |
| Free themes | https://themes.shopify.com/themes?price=free |
| Shopify Payments UK | https://www.shopify.com/uk/payments |
| Partner program (for devs) | https://www.shopify.com/uk/partners |
| Collaborator accounts guide | https://help.shopify.com/en/manual/your-account/staff-accounts/security/collaborator-accounts |
| UK policy generator | https://www.shopify.com/uk/tools/policy-generator |
| Shopify Help Center | https://help.shopify.com/en |
| Shopify Community | https://community.shopify.com/ |
| UK GDPR (ICO) | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/ |
| Consumer Rights Act 2015 | https://www.gov.uk/government/publications/cancelling-goods-or-services-guide-for-consumers |

---

*End of presentation. Build kit files: `shopify-uk-build-kit/`*
