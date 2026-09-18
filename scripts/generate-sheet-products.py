#!/usr/bin/env python3
"""Generate sheet-products.csv — lookup formulas with priority sort + URL gender filter."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-products.csv"
LOOKUP = "LookupTables"
ROWS = 100

HEADER = [
    "Product URL", "Force browser", "Vendor", "Product category", "Variant profile",
    "Collection", "Title", "Description", "Product image URL", "Competitor price",
    "Competitor currency", "Sizes", "Colors", "Scraped variants", "Price", "SKU",
    "Inventory quantity", "Tags", "SEO title", "SEO description", "Image alt text",
    "Scrape Status", "Scrape method", "Source Product URL", "QA Status", "AI Score",
    "Overlap %", "QA Issues", "Status", "URL handle", "Generated Image URL",
    "Shopify Image URL", "Shopify Product URL",
]

# Lower priority number = wins. Gender from URL excludes wrong-gender rules.
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
    """Pick best match: lowest priority number, skip empty values."""
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


def build_row(sheet_row: int, url: str = "") -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[2] = vendor_formula(sheet_row)
    row[3] = priority_lookup(sheet_row, "product_type_map", "F")
    row[4] = priority_lookup(sheet_row, "product_type_map", "G")
    row[5] = priority_lookup(sheet_row, "collection_map", "H")
    return row


def main():
    rows = [HEADER]
    samples = [
        "https://shop.mango.com/us/en/p/men/shirts/linen/regular-fit-100-linen-shirt/37031400/51/00",
        "https://www.everlane.com/products/womens-cheeky-straight-jean",
    ]
    for i in range(2, ROWS + 2):
        url = samples[i - 2] if i - 2 < len(samples) else ""
        rows.append(build_row(i, url))

    with OUT.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {OUT} ({ROWS} data rows)")


if __name__ == "__main__":
    main()
