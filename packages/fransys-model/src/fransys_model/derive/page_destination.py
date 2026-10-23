"""The label of a drawing page's PDF named destination, one fact in one place (OVERVIEW O21).

It is `position_text`'s set-and-page form. The set is counted among its own unit's sets, never
the design-wide number, so a unit's PDF reads nothing above it (layout-0177) and nesting moves
no label. A block diagram sheet's label is `b<n>` (PAGES-INDEX); no label repeats in one PDF.
"""

from fransys_model.layout import DiagramSheet, Page
lazy from fransys_model.kernel import Model

from .house_settings import reference_text_of
from .page_reference_text import page_reference_text
from .set_rank import set_rank
from .sheet_forms import diagram_text, set_page_text

__all__ = ["page_destination", "sheet_text", "sheet_title_text"]


def page_destination(model: Model, sheet: Page | DiagramSheet) -> str:
    """`p<k>.<page>`: the destination label of a page, `k` its set's rank; `b<n>` for a diagram."""
    if isinstance(sheet, DiagramSheet):
        return diagram_text(sheet).lower()
    return page_reference_text(model, sheet)


def sheet_text(model: Model, sheet: Page | DiagramSheet) -> str:
    """The sheet number a sheet prints: `3`, `2.3` in a set past its unit's first, `B1`.

    The destination label and a reference keep the set-and-page form `p1.3` (`set_page_text`).
    """
    if isinstance(sheet, DiagramSheet):
        return diagram_text(sheet)
    rank = set_rank(model, sheet)
    if rank == 1:
        return str(sheet.number)
    return set_page_text(reference_text_of(model), rank, sheet.number)


def sheet_title_text(model: Model, sheet: Page | DiagramSheet, title: str) -> str:
    """`Sheet 3: Pump 1`: a sheet's outline entry text; with no title, `Sheet 3`."""
    number = f"Sheet {sheet_text(model, sheet)}"
    return f"{number}: {title}" if title else number
