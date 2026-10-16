"""The SHEET_INDEX page: Sheet, Title and Page of every sheet (PAGES-INDEX, SI3 to SI5).

The Page cell is Typst's physical page at the sheet's destination label (ruling 2026-10-14,
the background's `physical_page`), never a Python page count: a list page that overflows moves every
later page. Every cell links to the sheet's page (NV1), invisibly.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import SheetKey, field_printed, sheet_index_rows
from fransys_model.vocab import PageKind

from ._background import physical_page, sheet_of
from ._flow import GUTTER_PCT, SHARE_PCT, flow_columns
from ._sizes import RULE, sizes_of
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import DocumentRow, SheetBackground
    from fransys_model.kernel import Model

_COLUMNS = ("Sheet", "Title", "Page")


def sheet_index_page(
    model: Model,
    record: DocumentRow,
    kinds: tuple[PageKind, ...],
    sheets: Mapping[SheetKey, SheetBackground],
) -> str:
    """The two-column index table, `""` for fewer than two sheets (empty-list rule)."""
    rows = sheet_index_rows(model, record.id, kinds)
    if not rows:
        return ""
    sizes = sizes_of(model, record.id)
    room = sheet_of(sheets, SheetKey(record.id, PageKind.SHEET_INDEX, 0)).title_room_mm
    cells = ["table.header(" + ", ".join(f"strong(text({literal(c)}))" for c in _COLUMNS) + ")"]
    for row in rows:
        page = f"context text(str({physical_page(f'locate(<{row.destination}>)')}))"
        title = row.title
        if room is not None:
            title = field_printed(row.title, room_mm=room, size_mm=sizes.body, shorter=row.shorter)[
                2
            ]
        shown = (f"text({literal(row.sheet)})", f"text({literal(title)})", page)
        cells.extend(f"link(<{row.destination}>, {cell})" for cell in shown)
    table = f"#table(columns: (auto, 1fr, auto), stroke: {RULE}, " + ", ".join(cells) + ")"
    return flow_columns([table], share_pct=SHARE_PCT, gutter_pct=GUTTER_PCT)
