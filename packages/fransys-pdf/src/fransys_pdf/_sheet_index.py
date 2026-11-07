"""The SHEET_INDEX page: Title and Page of every sheet (PAGES-INDEX, SI3 to SI5).

The Page cell is `derive.pdf_page`, the one page fact (model-0436): the index follows the drawings,
so no list page can move one. Every cell links to the sheet's page (NV1), invisibly.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import SheetKey, sheet_index_rows
from fransys_model.vocab import PageKind

from ._background import sheet_of
from ._flow import flow_columns
from ._sizes import rule_of
from ._typst import literal

if TYPE_CHECKING:
    from ._doc import Doc


def sheet_index_page(doc: Doc, headers: tuple[str, str], *, share_pct: float, gutter_pct: float) -> str:
    """The two-column index table, `""` for fewer than two sheets (empty-list rule)."""
    model, record, pages, _, sheets, diagrams, _ = doc
    rows = sheet_index_rows(model, record.id, pages, diagrams)
    if not rows:
        return ""
    titles = sheet_of(sheets, SheetKey(record.id, PageKind.SHEET_INDEX, 0)).index_titles
    cells = ["table.header(" + ", ".join(f"strong(text({literal(c)}))" for c in headers) + ")"]
    for row, title in zip(rows, titles, strict=True):
        shown = (f"text({literal(title)})", f"text({literal(str(row.page))})")
        cells.extend(f"link(<{row.destination}>, {cell})" for cell in shown)
    table = f"#table(columns: (1fr, auto), stroke: {rule_of(model)}, " + ", ".join(cells) + ")"
    return flow_columns([table], share_pct=share_pct, gutter_pct=gutter_pct)
