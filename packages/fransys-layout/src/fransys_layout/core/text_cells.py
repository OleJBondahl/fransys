"""Stage 8, the page grid: a point on the page named by its column and row, as "3C"."""

from __future__ import annotations

from typing import TYPE_CHECKING

LETTERS = 26

if TYPE_CHECKING:
    from .values import Size


def _index(v: int, extent: int, count: int) -> int:
    """The zero-based cell of `v` on an axis of `extent` cut into `count`; the far edge is last."""
    return min(v * count // extent, count - 1)


def cell_of(x: int, y: int, area: Size, cells: tuple[int, int]) -> str:
    """The cell of (x, y): the column number then the row letter, over the whole `area`.

    The grid is `cells` = (columns, rows). A point on a border between cells goes to the higher
    cell; a point on the right or bottom edge of the area goes to the last one.
    """
    columns, rows = cells
    if not (0 <= x <= area.w and 0 <= y <= area.h):
        msg = f"cell_of: ({x}, {y}) lies outside the {area.w} x {area.h} area"
        raise ValueError(msg)
    if not 1 <= rows <= LETTERS or columns < 1:
        msg = f"cell_of: the grid {cells} cannot be named"
        raise ValueError(msg)
    return f"{_index(x, area.w, columns) + 1}{chr(ord('A') + _index(y, area.h, rows))}"
