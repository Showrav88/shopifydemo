#!/usr/bin/env python3
"""Generate sheet-products.csv — LookupTables + VariantLibrary + PromptLibrary formulas."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sheet-products.csv"
LOOKUP = "LookupTables"
VARIANTS = "VariantLibrary"
PROMPTS = "PromptLibrary"
ROWS = 50

HEADER = [
    "Product URL",
    "Force browser",
    "Vendor",
    "Product category",
    "Variant profile",
    "Variant preset ID",
    "Option 1 name",
    "Option 1 values",
    "Option 2 name",
    "Option 2 values",
    "Option 3 name",
    "Option 3 values",
    "Collection",
    "Title",
    "Description",
    "Product image URL",
    "Competitor price",
    "Competitor currency",
    "Sizes",
    "Colors",
    "Lengths",
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
]

PROMPT_COLS = {
    "Prompt Title": "C",
    "Prompt Description": "D",
    "Prompt Tags": "E",
    "Prompt SEO title": "F",
    "Prompt SEO description": "G",
    "Prompt Image alt": "H",
    "Prompt Category": "I",
}

# Product sheet columns (1-based): E=profile, F=preset ID, G-L=options, Y=prompt ID
PROMPT_ID_COL = "Y"

GENDER_FILTER = (
    'IF(REGEXMATCH(LOWER($A{r}),"/men/|/hombre/"),{L}!$E$2:$E$500="men",'
    'IF(REGEXMATCH(LOWER($A{r}),"/women/|/mujer/|womens"),{L}!$E$2:$E$500="women",'
    'IF(REGEXMATCH(LOWER($A{r}),"/kids/|/boys/|/girls/|/children/"),{L}!$E$2:$E$500="kids",1)))'
)

SEARCH_TEXT = 'LOWER($A{r}&" "&$N{r}&" "&$O{r})'


def resolved_preset(r: int) -> str:
    return (
        f'IF($F{r}<>"",$F{r},IFERROR(INDEX(FILTER({VARIANTS}!$A$2:$A$500,'
        f'{VARIANTS}!$B$2:$B$500=$E{r}),1),"uk-shirts"))'
    )


def variant_field(r: int, lib_col: str) -> str:
    key = resolved_preset(r)
    return (
        f'=IF($A{r}="","",IFERROR(INDEX(FILTER({VARIANTS}!{lib_col}$2:{lib_col}$500,'
        f'{VARIANTS}!$A$2:$A$500={key}),1),""))'
    )


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
        f'{PROMPTS}!$A$2:$A$500=IF(${PROMPT_ID_COL}{r}="","default",${PROMPT_ID_COL}{r})),1),""))'
    )


def sizes_display_formula(r: int) -> str:
    """Show option1 values when option1 is a size field (scrape may overwrite)."""
    return (
        f'=IF($A{r}="","",IF(OR($G{r}="Size",$G{r}="Waist",$G{r}="UK Size",$G{r}="US Size"),$H{r},""))'
    )


def colors_display_formula(r: int) -> str:
    return (
        f'=IF($A{r}="","",IF($I{r}="Color",$J{r},IF($K{r}="Color",$L{r},IF($G{r}="Color",$H{r},""))))'
    )


def lengths_display_formula(r: int) -> str:
    return f'=IF($A{r}="","",IF($I{r}="Length",$J{r},IF($K{r}="Length",$L{r},"")))'


def build_row(sheet_row: int, url: str = "", preset_id: str = "", prompt_id: str = "") -> list:
    row = [""] * len(HEADER)
    row[0] = url
    row[2] = vendor_formula(sheet_row)
    row[3] = priority_lookup(sheet_row, "product_type_map", "F")
    row[4] = priority_lookup(sheet_row, "product_type_map", "G")
    row[5] = preset_id
    row[6] = variant_field(sheet_row, "C")
    row[7] = variant_field(sheet_row, "D")
    row[8] = variant_field(sheet_row, "E")
    row[9] = variant_field(sheet_row, "F")
    row[10] = variant_field(sheet_row, "G")
    row[11] = variant_field(sheet_row, "H")
    row[12] = priority_lookup(sheet_row, "collection_map", "H")
    row[HEADER.index("Sizes")] = sizes_display_formula(sheet_row)
    row[HEADER.index("Colors")] = colors_display_formula(sheet_row)
    row[HEADER.index("Lengths")] = lengths_display_formula(sheet_row)
    row[HEADER.index("Prompt ID")] = prompt_id
    for col_name, lib_col in PROMPT_COLS.items():
        row[HEADER.index(col_name)] = prompt_formula(sheet_row, lib_col)
    return row


def main():
    rows = [HEADER]
    mango = "https://shop.mango.com/us/en/p/men/shirts/linen/regular-fit-100-linen-shirt/37031400/51/00"
    rows.append(build_row(2, mango, preset_id="", prompt_id="mango-linen-qa90"))
    for i in range(3, ROWS + 2):
        rows.append(build_row(i))

    with OUT.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {OUT} — VariantLibrary drives options; user sets Variant preset ID only")


if __name__ == "__main__":
    main()
