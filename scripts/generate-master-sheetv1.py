#!/usr/bin/env python3
"""Generate Master_Sheetv1 products tab CSV with MAP lookup formulas (row 2 only)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-master-sheetv1.csv"
LEGACY = ROOT / "sheet-products.csv"
MASTER_EXPORT = ROOT / "Master_Sheetv1 - Products.csv"
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

# MAP formulas live ONLY in row 2 — they auto-fill the whole column when you paste URLs.
# Deleting a product row no longer removes formulas (clear column A instead).
FORMULA_ROW = {
    2: (
        '=MAP(A2:A,LAMBDA(a,IF(a="","",IFERROR(INDEX(FILTER('
        f'{LOOKUP_TAB}!$K$2:$K$500,({LOOKUP_TAB}!$A$2:$A$500="vendor_map")*'
        f'({LOOKUP_TAB}!$L$2:$L$500<>"")*ISNUMBER(SEARCH({LOOKUP_TAB}!$L$2:$L$500,LOWER(a)))),1),""))))'
    ),
    3: (
        '=MAP(A2:A,L2:L,M2:M,LAMBDA(a,l,m,IF(a="","",IFERROR(INDEX(FILTER('
        f'{LOOKUP_TAB}!$F$2:$F$500,({LOOKUP_TAB}!$A$2:$A$500="product_type_map")*'
        f'({LOOKUP_TAB}!$B$2:$B$500<>"")*ISNUMBER(SEARCH({LOOKUP_TAB}!$B$2:$B$500,LOWER(a&" "&l&" "&m)))),1),""))))'
    ),
    4: (
        '=MAP(A2:A,L2:L,M2:M,LAMBDA(a,l,m,IF(a="","",IFERROR(INDEX(FILTER('
        f'{LOOKUP_TAB}!$H$2:$H$500,({LOOKUP_TAB}!$A$2:$A$500="collection_map")*'
        f'({LOOKUP_TAB}!$B$2:$B$500<>"")*ISNUMBER(SEARCH({LOOKUP_TAB}!$B$2:$B$500,LOWER(a&" "&l&" "&m)))),1),""))))'
    ),
    5: (
        '=MAP(A2:A,L2:L,M2:M,LAMBDA(a,l,m,IF(a="","",IFERROR(INDEX(FILTER('
        f'{LOOKUP_TAB}!$G$2:$G$500,({LOOKUP_TAB}!$A$2:$A$500="product_type_map")*'
        f'({LOOKUP_TAB}!$B$2:$B$500<>"")*ISNUMBER(SEARCH({LOOKUP_TAB}!$B$2:$B$500,LOWER(a&" "&l&" "&m)))),1),""))))'
    ),
}


def build_row(sheet_row: int, url: str = "") -> list:
    row = [""] * len(HEADER)
    row[0] = url
    if sheet_row == 2:
        row[2] = FORMULA_ROW[2]
        row[3] = FORMULA_ROW[3]
        row[4] = FORMULA_ROW[4]
        row[5] = FORMULA_ROW[5]
    return row


def main():
    rows = [HEADER]
    for i in range(2, ROWS + 2):
        url = SAMPLE_URLS[i - 2] if i - 2 < len(SAMPLE_URLS) else ""
        rows.append(build_row(i, url))

    for path in (OUT, LEGACY, MASTER_EXPORT):
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        print(f"Wrote {len(rows) - 1} data rows to {path}")


if __name__ == "__main__":
    main()
