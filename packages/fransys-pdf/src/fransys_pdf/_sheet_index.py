"""The SHEET_INDEX page: Sheet, Title and Page of every sheet (PAGES-INDEX, SI3 to SI5).

The Page cell is Typst's physical page at the sheet's destination label (ruling 2026-10-14,
the frame's `physical_page`), never a Python page count: a list page that overflows moves every
later page.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import sheet_index_rows

from ._flow import flow_columns
from ._frame import field_cell, physical_page
from ._geometry import resolve_sheet_format
from ._sizes import RULE, sizes_of
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab import Document, PageKind

_COLUMNS = ("Sheet", "Title", "Page")
_SHARE_PCT = 40  # as the other list pages (pdf-0026, L1)
_GUTTER_PCT = 20


def sheet_index_page(model: Model, record: Document, kinds: tuple[PageKind, ...]) -> str:
    """The two-column index table, `""` for fewer than two sheets (empty-list rule)."""
    rows = sheet_index_rows(model, record, kinds)
    if not rows:
        return ""
    sheet, sizes = resolve_sheet_format(model, record, kinds), sizes_of(model, record)
    cells = ["table.header(" + ", ".join(f"strong(text({literal(c)}))" for c in _COLUMNS) + ")"]
    for row in rows:
        page = f"context text(str({physical_page(f'locate(<{row.destination}>)')}))"
        title = field_cell(sheet, sizes, "page_title", row.title, shorter=row.shorter)[2]
        cells.extend((f"text({literal(row.sheet)})", f"text({literal(title)})", page))
    table = f"#table(columns: (auto, 1fr, auto), stroke: {RULE}, " + ", ".join(cells) + ")"
    return flow_columns([table], share_pct=_SHARE_PCT, gutter_pct=_GUTTER_PCT)
