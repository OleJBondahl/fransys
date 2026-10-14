"""The printed forms of a sheet number, one fact in one place (PAGES-TITLES, SI3; PAGES-INDEX).

A sheet is a schematic `Page` or a `DiagramSheet`. `set_page_text` is the set-and-page form a
reference or a destination prints after its `p`; `sheet_counter_text` is the title block's
`n / N` cell, `B1 / 2` on a block diagram sheet (owner label B1).
"""

from fransys_model.layout import DiagramSheet, Page

__all__ = ["diagram_text", "set_page_text", "sheet_counter_text"]


def set_page_text(set_number: int, page_number: int) -> str:
    """`<set>.<page>`, `"2.3"`: a page named with its drawing set (a reference prints `p` first)."""
    return f"{set_number}.{page_number}"


def diagram_text(sheet: DiagramSheet) -> str:
    """`B<n>`: the number a block diagram sheet prints."""
    return f"B{sheet.number}"


def sheet_counter_text(sheet: Page | DiagramSheet, total: int) -> str:
    """`<number> / <total>`: the title block's sheet cell; `B1 / 2` for a block diagram sheet."""
    first = diagram_text(sheet) if isinstance(sheet, DiagramSheet) else str(sheet.number)
    return f"{first} / {total}"
