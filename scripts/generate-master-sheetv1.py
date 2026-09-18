#!/usr/bin/env python3
"""Generate Master_Sheetv1 products tab CSV with lookup formulas on every row."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-master-sheetv1.csv"
LEGACY = ROOT / "sheet-products.csv"
LOOKUP_TAB = "LookupTables"
ROWS = 200

HEADER = [
    "Product URL", "Force browser", "Suggested Vendor", "Suggested Category",
    "Suggested Collection", "Suggested Variant profile", "Vendor", "Product category",
    "Variant profile", "Collection", "Shopify Category", "Title", "Description",
    "Product image URL", "Competitor price", "Competitor currency", "Sizes", "Colors",
    "Scraped variants", "Price", "SKU", "Inventory quantity", "Approve",
    "Prompt Title", "Prompt Description", "Prompt Tags", "Prompt SEO title",
    "Prompt SEO description", "Prompt Image alt", "Prompt Category", "Status", "Tags",
    "SEO title", "SEO description", "Image alt text", "Scrape Status", "Scrape method",
    "Source Product URL", "QA Status", "AI Score", "Overlap %", "QA Issues",
    "URL handle", "Generated Image URL", "Shopify Image URL", "Shopify Product URL",
]

SAMPLE_URLS = [
    "https://shop.mango.com/us/en/p/men/shirts/linen/regular-fit-100-linen-shirt/37031400/51/00",
    "https://www.everlane.com/products/womens-cheeky-straight-jean",
]


def vendor_formula(row: int) -> str:
    r = row
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP_TAB}!$K$2:$K$500,'
        f'({LOOKUP_TAB}!$A$2:$A$500="vendor_map")*({LOOKUP_TAB}!$L$2:$L$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP_TAB}!$L$2:$L$500,LOWER($A{r})))),1),""))'
    )


def category_formula(row: int) -> str:
    r = row
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP_TAB}!$F$2:$F$500,'
        f'({LOOKUP_TAB}!$A$2:$A$500="product_type_map")*({LOOKUP_TAB}!$B$2:$B$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP_TAB}!$B$2:$B$500,LOWER($A{r}&" "&$L{r}&" "&$M{r})))),1),""))'
    )


def collection_formula(row: int) -> str:
    r = row
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP_TAB}!$H$2:$H$500,'
        f'({LOOKUP_TAB}!$A$2:$A$500="collection_map")*({LOOKUP_TAB}!$B$2:$B$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP_TAB}!$B$2:$B$500,LOWER($A{r}&" "&$L{r}&" "&$M{r})))),1),""))'
    )


def variant_profile_formula(row: int) -> str:
    r = row
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({LOOKUP_TAB}!$G$2:$G$500,'
        f'({LOOKUP_TAB}!$A$2:$A$500="product_type_map")*({LOOKUP_TAB}!$B$2:$B$500<>"")*'
        f'ISNUMBER(SEARCH({LOOKUP_TAB}!$B$2:$B$500,LOWER($A{r}&" "&$L{r}&" "&$M{r})))),1),""))'
    )


def build_row(sheet_row: int, url: str = "") -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[2] = vendor_formula(sheet_row)
    row[3] = category_formula(sheet_row)
    row[4] = collection_formula(sheet_row)
    row[5] = variant_profile_formula(sheet_row)
    return row


def main():
    rows = [HEADER]
    for i in range(2, ROWS + 2):
        url = SAMPLE_URLS[i - 2] if i - 2 < len(SAMPLE_URLS) else ""
        rows.append(build_row(i, url))

    for path in (OUT, LEGACY):
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        print(f"Wrote {len(rows) - 1} data rows to {path}")


if __name__ == "__main__":
    main()
