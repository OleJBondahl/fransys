"""Connector boxes at a harness line's end: cells, size and parts (HL5)."""

from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, Point, snap_up, text_width
from fransys_model.kernel import Id, value

if TYPE_CHECKING:
    from collections.abc import Sequence

CELL_ROWS = 2  # a cell is two grids high
HALF = WIRING_GRID // 2  # a box pads its texts by half a grid on each side


@value
class BoxCell:
    """One pin cell of a placed box: the port it stands for and its rectangle."""

    port: Id[Any]
    box: Box


@value
class PlacedConnectorBox:
    """One connector box on one page: its rectangle, each text line's anchor and its cells."""

    function: Id[Any]
    drawing_set: int
    page: int
    box: Box
    texts: tuple[Point, ...]
    cells: tuple[BoxCell, ...]


def has_cells(*, plug: bool, black_box: bool, board: bool, wired: bool) -> bool:
    """HL5: a plug, a black-box interface and a board connector never; else only when wired."""
    return wired and not (plug or black_box or board)


def _text_block(count: int, text_height: int) -> int:
    """Height of `count` text lines one grid apart, padded by half a grid above and below."""
    return count * text_height + (count - 1) * WIRING_GRID + 2 * HALF if count else 0


def cell_width(marking: str, text_height: int) -> int:
    return max(text_width(marking, height=text_height) + WIRING_GRID, CELL_ROWS * WIRING_GRID)


def box_size(lines: Sequence[str], markings: Sequence[str], *, text_height: int) -> tuple[int, int]:
    """Width and height of a box with text `lines` and one cell per marking, snapped up."""
    widest = max((text_width(line, height=text_height) for line in lines), default=0)
    cells = sum(cell_width(marking, text_height) for marking in markings)
    row = CELL_ROWS * WIRING_GRID if markings else 0
    height = _text_block(len(lines), text_height) + row
    return snap_up(max(widest + 2 * HALF, cells)), snap_up(height)
