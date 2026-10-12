"""Where a geometric finding stands: the frame cell of its page; the last pass names the page."""

from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import frame_column, frame_row, position_text

if TYPE_CHECKING:
    from fransys_layout.stages import SheetFormat


def where(sheet: SheetFormat, here: tuple[int, int], x: int, y: int) -> str:
    """The frame cell of the point `x`, `y` on page `here` (drawing set, page number): `3F`.

    The page and its set come after the message, from derive's `position_text` in the last pass.
    """
    column = frame_column(sheet.content_width, sheet.frame_columns, x)
    row = frame_row(sheet.content_height, sheet.frame_rows, y)
    return position_text(here[1], column, row, (), own_page=here[1])
