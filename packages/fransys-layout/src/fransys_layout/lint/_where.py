"""Where a geometric finding stands: the page and frame cell, in derive's one position text."""

from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import frame_column, frame_row, position_text

if TYPE_CHECKING:
    from fransys_layout.stages import SheetFormat


def where(
    sheet: SheetFormat, here: tuple[int, int], x: int, y: int, *, several_sets: bool = False
) -> str:
    """`p<page>:<cell>` of the point `x`, `y` on page `here` (drawing set, page number).

    A design with more than one drawing set names the set too (`p<set>.<page>:<cell>`).
    """
    drawing_set, page = here
    column = frame_column(sheet.content_width, sheet.frame_columns, x)
    row = frame_row(sheet.content_height, sheet.frame_rows, y)
    return position_text(page, column, row, (), drawing_set if several_sets else None)
