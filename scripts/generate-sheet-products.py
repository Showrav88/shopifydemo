#!/usr/bin/env python3
"""Generate sheet-products.csv — manual Vendor cols + Suggested* lookup formulas at end."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-products.csv"
LOOKUP = "LookupTables"
PROMPTS = "PromptLibrary"
ROWS = 50

# Manual columns C–F stay EMPTY in CSV — you type here to override lookup.
# Suggested* columns at the end are formulas (hide those columns in Sheets).
SUGGESTED = [
    "Suggested Vendor",
    "Suggested Product category",
    "Suggested Variant profile",
    "Suggested Collection",
]

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
    "Prompt ID",
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
    *SUGGESTED,
]

PROMPT_LIB_COLS = {
    "Prompt Title": "C",
    "Prompt Description": "D",
    "Prompt Tags": "E",
    "Prompt SEO title": "F",
    "Prompt SEO description": "G",
    "Prompt Image alt": "H",
    "Prompt Category": "I",
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


def prompt_formula(r: int, lib_col: str) -> str:
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({PROMPTS}!{lib_col}$2:{lib_col}$500,'
        f'{PROMPTS}!$A$2:$A$500=IF($R{r}="","default",$R{r})),1),""))'
    )


def build_row(sheet_row: int, url: str = "", prompt_id: str = "") -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[17] = prompt_id
    for col_name, lib_col in PROMPT_LIB_COLS.items():
        row[HEADER.index(col_name)] = prompt_formula(sheet_row, lib_col)
    base = len(HEADER) - len(SUGGESTED)
    row[base] = vendor_formula(sheet_row)
    row[base + 1] = priority_lookup(sheet_row, "product_type_map", "F")
    row[base + 2] = priority_lookup(sheet_row, "product_type_map", "G")
    row[base + 3] = priority_lookup(sheet_row, "collection_map", "H")
    return row


def main():
    rows = [HEADER]
    mango = "https://shop.mango.com/us/en/p/men/shirts/linen/regular-fit-100-linen-shirt/37031400/51/00"
    rows.append(build_row(2, mango, prompt_id="mango-linen-qa90"))
    for i in range(3, ROWS + 2):
        rows.append(build_row(i))

    with OUT.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {OUT} — C–F manual (blank); Suggested* formulas at end")


if __name__ == "__main__":
    main()
