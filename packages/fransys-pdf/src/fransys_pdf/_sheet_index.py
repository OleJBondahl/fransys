"""The SHEET_INDEX page: Sheet, Title and Page of every sheet (PAGES-INDEX, SI3 to SI5).

The Page cell is Typst's physical page at the sheet's destination label (ruling 2026-10-14,
the background's `physical_page`), never a Python page count: a list page that overflows moves every
later page. Every cell links to the sheet's page (NV1), invisibly.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import SheetKey, sheet_index_rows
from fransys_model.vocab import PageKind

from ._background import physical_page, sheet_of
from ._flow import flow_columns
from ._sizes import rule_of
from ._typst import literal

if TYPE_CHECKING:
    from ._doc import Doc


def sheet_index_page(doc: Doc, headers: tuple[str, str, str], *, share_pct: float, gutter_pct: float) -> str:
    """The two-column index table, `""` for fewer than two sheets (empty-list rule)."""
    model, record, pages, _, sheets, diagrams, _ = doc
    rows = sheet_index_rows(model, record.id, pages, diagrams)
    if not rows:
        return ""
    titles = sheet_of(sheets, SheetKey(record.id, PageKind.SHEET_INDEX, 0)).index_titles
    cells = ["table.header(" + ", ".join(f"strong(text({literal(c)}))" for c in headers) + ")"]
    for row, title in zip(rows, titles, strict=True):
        page = f"context text(str({physical_page(f'locate(<{row.destination}>)')}))"
        shown = (f"text({literal(row.sheet)})", f"text({literal(title)})", page)
        cells.extend(f"link(<{row.destination}>, {cell})" for cell in shown)
    table = f"#table(columns: (auto, 1fr, auto), stroke: {rule_of(model)}, " + ", ".join(cells) + ")"
    return flow_columns([table], share_pct=share_pct, gutter_pct=gutter_pct)
