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


def build_row(sheet_row: int, url: str = "", include_prompts: bool = False) -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[2] = vendor_formula(sheet_row)
    row[3] = priority_lookup(sheet_row, "product_type_map", "F")
    row[4] = priority_lookup(sheet_row, "product_type_map", "G")
    row[5] = priority_lookup(sheet_row, "collection_map", "H")
    if include_prompts:
        for col_name, text in DEFAULT_PROMPTS.items():
            row[HEADER.index(col_name)] = text
    return row


def main():
    rows = [HEADER]
    mango = "https://shop.mango.com/us/en/p/men/shirts/linen/regular-fit-100-linen-shirt/37031400/51/00"
    rows.append(build_row(2, mango, include_prompts=True))
    for i in range(3, ROWS + 2):
        rows.append(build_row(i))

    with OUT.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {OUT} — row 2 = Mango URL + prompt instructions, rows 3+ empty")


if __name__ == "__main__":
    main()
