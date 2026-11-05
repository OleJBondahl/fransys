"""The page frame's reference-grid cell of a point, read through symdef (SY4, R893): no arithmetic here."""

from dataclasses import replace
from typing import TYPE_CHECKING

from symdef import GridPoint, floor_divisions, reference_cell

from fransys_model.derive.drawing_text import row_letter

if TYPE_CHECKING:
    from fransys_model.layout import SheetFormat

    from .shape import SymbolLibrary

__all__ = ("frame_cell", "frame_extent")


def frame_extent(library: SymbolLibrary, sheet: SheetFormat) -> tuple[int, int]:
    """The `(width, height)` of `sheet`'s content box in whole grid divisions, rounded down."""
    grid = replace(library.grid, module_mm=float(sheet.module_mm))
    return floor_divisions(grid, float(sheet.content_width_mm)), floor_divisions(grid, float(sheet.content_height_mm))


def frame_cell(library: SymbolLibrary, sheet: SheetFormat, x: int, y: int) -> tuple[int, str]:
    """The `(column from 1, row letter from A)` of the frame cell holding the point `x`, `y` on `sheet`."""
    columns = tuple(str(number) for number, _ in enumerate(range(sheet.frame_columns), start=1))  # labels from 1, no sum
    rows = tuple(row_letter(index) for index in range(sheet.frame_rows))
    column, row = reference_cell(columns, rows, *frame_extent(library, sheet), GridPoint(x, y))
    return int(column), row
