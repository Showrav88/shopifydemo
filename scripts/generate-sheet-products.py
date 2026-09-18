#!/usr/bin/env python3
"""Generate sheet-products.csv — one products tab, lookup formulas in real columns."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-products.csv"
LOOKUP = "LookupTables"
ROWS = 100

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
    "Status",
    "URL handle",
    "Generated Image URL",
    "Shopify Image URL",
    "Shopify Product URL",
]


def vendor_formula(r: int) -> str:
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP}!$K$2:$K$500,'
        f'({LOOKUP}!$A$2:$A$500="vendor_map")*({LOOKUP}!$L$2:$L$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP}!$L$2:$L$500,LOWER($A{r})))),1),""))'
    )


def category_formula(r: int) -> str:
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP}!$F$2:$F$500,'
        f'({LOOKUP}!$A$2:$A$500="product_type_map")*({LOOKUP}!$B$2:$B$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP}!$B$2:$B$500,LOWER($A{r}&" "&$G{r}&" "&$H{r})))),1),""))'
    )


def variant_formula(r: int) -> str:
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP}!$G$2:$G$500,'
        f'({LOOKUP}!$A$2:$A$500="product_type_map")*({LOOKUP}!$B$2:$B$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP}!$B$2:$B$500,LOWER($A{r}&" "&$G{r}&" "&$H{r})))),1),""))'
    )


def collection_formula(r: int) -> str:
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP}!$H$2:$H$500,'
        f'({LOOKUP}!$A$2:$A$500="collection_map")*({LOOKUP}!$B$2:$B$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP}!$B$2:$B$500,LOWER($A{r}&" "&$G{r}&" "&$H{r})))),1),""))'
    )


def build_row(sheet_row: int, url: str = "") -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[2] = vendor_formula(sheet_row)
    row[3] = category_formula(sheet_row)
    row[4] = variant_formula(sheet_row)
    row[5] = collection_formula(sheet_row)
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
