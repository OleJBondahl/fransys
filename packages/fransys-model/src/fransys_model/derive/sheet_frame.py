"""A sheet's frame in mm: the border, the four reference strips and the title-block band.

The values render passes to the sheet symbols; the symbols themselves are data
(`electrical_symbols`, `symbols/sheet-*.toml` and `title-block*.toml`).
"""

lazy from fransys_model.layout import SheetFormat

from .frame_labels import frame_labels
from .rows_sheet_pages import FrameStrip, SheetFrame

__all__ = ["sheet_frame"]


def _strips(sheet: SheetFormat) -> tuple[FrameStrip, ...]:
    """Top and bottom strips one cell per frame column; left and right one per frame row."""
    x0, y0 = sheet.content_x_mm, sheet.content_y_mm
    labels = frame_labels(sheet.frame_columns, sheet.frame_rows)
    column = sheet.content_width_mm / sheet.frame_columns
    row = sheet.content_height_mm / sheet.frame_rows
    return (
        FrameStrip("top", x0, 0, column, y0, "x", labels.columns),
        FrameStrip("bottom", x0, sheet.height_mm - y0, column, y0, "x", labels.columns),
        FrameStrip("left", 0, y0, x0, row, "y", labels.rows),
        FrameStrip("right", sheet.width_mm - x0, y0, x0, row, "y", labels.rows),
    )


def sheet_frame(sheet: SheetFormat) -> SheetFrame:
    """The frame of `sheet`: the border keeps the content box's margin on every side.

    The band is the border's bottom part under the content box; the square logo cell ends it.
    """
    x0, y0 = sheet.content_x_mm, sheet.content_y_mm
    width, height = sheet.width_mm - 2 * x0, sheet.height_mm - 2 * y0
    band = height - sheet.content_height_mm
    return SheetFrame(
        border=(x0, y0, width, height),
        strips=_strips(sheet),
        band=band,
        band_top=y0 + sheet.content_height_mm,
        title_width=width - band,
        logo_x=x0 + width - band,
    )
