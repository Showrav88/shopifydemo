#!/usr/bin/env python3
"""Generate sheet-products.csv — lookup formulas + AI prompt instruction columns."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-products.csv"
LOOKUP = "LookupTables"
ROWS = 50

HEADER = [
    "Product URL",
    "Force browser",
    "Vendor",
    "Product category",
    "Variant profile",
    "Collection",
    "Title",
    "Description",
    "Product image URL",
    "Competitor price",
    "Competitor currency",
    "Sizes",
    "Colors",
    "Scraped variants",
    "Price",
    "SKU",
    "Inventory quantity",
    "Prompt Title",
    "Prompt Description",
    "Prompt Tags",
    "Prompt SEO title",
    "Prompt SEO description",
    "Prompt Image alt",
    "Prompt Category",
    "Status",
    "Tags",
    "SEO title",
    "SEO description",
    "Image alt text",
    "Scrape Status",
    "Scrape method",
    "Source Product URL",
    "QA Status",
    "AI Score",
    "Overlap %",
    "QA Issues",
    "URL handle",
    "Generated Image URL",
    "Shopify Image URL",
    "Shopify Product URL",
]

DEFAULT_PROMPTS = {
    "Prompt Title": (
        "Write a completely NEW original title. Same product facts but different words. "
        "Never copy competitor phrasing. Max 70 chars UK fashion."
    ),
    "Prompt Description": (
        "Rewrite in your own words — new sentences only. Keep factual specs (material, fit, colour). "
        "Do NOT copy competitor text (copyright). HTML <p> tags."
    ),
    "Prompt Tags": "Original search tags only — not copied from source. Max 10 UK fashion keywords.",
    "Prompt SEO title": "Original Google title, max 60 chars. Paraphrase — do not copy source.",
    "Prompt SEO description": "Original meta description, max 160 chars. New wording, same facts.",
    "Prompt Image alt": "Original alt text describing what you see in the image.",
    "Prompt Category": "UK fashion category path e.g. Men > Shirts > Casual",
}

# Tuned for Mango linen shirt — targets QA score >= 90 (overlap checks must pass).
MANGO_LINEN_QA90_PROMPTS = {
    "Prompt Title": (
        "UK men's fashion title, max 65 chars. Completely new wording — zero copied phrases. "
        "Facts: linen shirt, men's, casual. DO NOT use verbatim: regular-fit, regular fit, "
        "100% linen, band collar, long sleeve. Prefer: lightweight linen, relaxed fit, "
        "mandarin collar, breathable summer shirt. Mention colour only if in image analysis."
    ),
    "Prompt Description": (
        "Two or three HTML <p> paragraphs. UK spelling. Men's linen shirt — same facts, "
        "brand-new sentences. FORBIDDEN exact phrases from source: regular fit, band collar, "
        "buttoned cuffs, front button closure, 100% linen fabric. Paraphrase: e.g. relaxed "
        "silhouette, stand collar, barrel cuffs, button-through front, woven linen. "
        "No sentence may share 4+ consecutive words with the scraped description. "
        "Sell breathability and warm-weather wear."
    ),
    "Prompt Tags": (
        "8 original UK tags. No competitor brand names. Ideas: men's shirt, linen weave, "
        "summer layering, smart casual, breathable, lightweight, warm weather, wardrobe staple. "
        "Do not copy tag list from source page."
    ),
    "Prompt SEO title": (
        "Unique Google title under 58 chars. Different structure from product page title. "
        "No copy of 'regular fit' or '100% linen shirt'. Benefit-led or style-led wording."
    ),
    "Prompt SEO description": (
        "Meta description max 155 chars. Fresh wording only. Highlight comfort, linen fabric, "
        "versatile styling. No phrase duplicated from Mango listing."
    ),
    "Prompt Image alt": (
        "Accessibility alt for men's linen shirt in image: colour, collar type, sleeve length. "
        "Original words — not copied from page title."
    ),
    "Prompt Category": "Men > Shirts > Linen",
}

GENDER_FILTER = (
    'IF(REGEXMATCH(LOWER($A{r}),"/men/|/hombre/"),{L}!$E$2:$E$500="men",'
    'IF(REGEXMATCH(LOWER($A{r}),"/women/|/mujer/|womens"),{L}!$E$2:$E$500="women",'
    'IF(REGEXMATCH(LOWER($A{r}),"/kids/|/boys/|/girls/|/children/"),{L}!$E$2:$E$500="kids",1)))'
)

SEARCH_TEXT = 'LOWER($A{r}&" "&$G{r}&" "&$H{r})'


def _base_match(r: int, table_type: str, value_col: str) -> str:
    g = GENDER_FILTER.format(r=r, L=LOOKUP)
    return (
        f'( {LOOKUP}!$A$2:$A$500="{table_type}" )*'
        f'( {LOOKUP}!$B$2:$B$500<>"" )*'
        f'( {LOOKUP}!{value_col}$2:{value_col}$500<>"" )*'
        f'ISNUMBER(SEARCH({LOOKUP}!$B$2:$B$500,{SEARCH_TEXT.format(r=r)}))*'
        f'{g}'
    )


def priority_lookup(r: int, table_type: str, value_col: str) -> str:
    cond = _base_match(r, table_type, value_col)
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(SORT(FILTER({{'
        f'{LOOKUP}!{value_col}$2:{value_col}$500,{LOOKUP}!$D$2:$D$500}},'
        f'{cond}),2,TRUE),1,1),""))'
    )


def vendor_formula(r: int) -> str:
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP}!$K$2:$K$500,'
        f'({LOOKUP}!$A$2:$A$500="vendor_map")*({LOOKUP}!$L$2:$L$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP}!$L$2:$L$500,LOWER($A{r})))),1),""))'
    )


def build_row(sheet_row: int, url: str = "", prompts: dict | None = None) -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[2] = vendor_formula(sheet_row)
    row[3] = priority_lookup(sheet_row, "product_type_map", "F")
    row[4] = priority_lookup(sheet_row, "product_type_map", "G")
    row[5] = priority_lookup(sheet_row, "collection_map", "H")
    if prompts:
        for col_name, text in prompts.items():
            row[HEADER.index(col_name)] = text
    return row


def main():
    rows = [HEADER]
    mango = "https://shop.mango.com/us/en/p/men/shirts/linen/regular-fit-100-linen-shirt/37031400/51/00"
    rows.append(build_row(2, mango, prompts=MANGO_LINEN_QA90_PROMPTS))
    for i in range(3, ROWS + 2):
        rows.append(build_row(i))

    with OUT.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {OUT} — row 2 = Mango URL + prompt instructions, rows 3+ empty")


if __name__ == "__main__":
    main()
