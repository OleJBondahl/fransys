"""One index of boxes by the wiring-grid cells they meet (layout-0133).

A lookup reads by cell key, never scans the entries. A closed box that meets a closed segment
shares a point with it, so it shares a cell: the cells over-select, and a caller keeps its
exact test.
"""

from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID, Box

if TYPE_CHECKING:
    from collections.abc import Iterable

type _Cell = tuple[int, int]


def _cells(x: int, y: int, to_x: int, to_y: int) -> Iterable[_Cell]:
    """The wiring-grid cells of the closed corner pair, in any corner order."""
    low_x, high_x = sorted((x, to_x))
    low_y, high_y = sorted((y, to_y))
    return (
        (column, row)
        for column in range(low_x // WIRING_GRID, high_x // WIRING_GRID + 1)
        for row in range(low_y // WIRING_GRID, high_y // WIRING_GRID + 1)
    )


class CellIndex[T]:
    """Items keyed by the wiring-grid cells their closed boxes meet; `meeting` reads by key."""

    __slots__ = ("_items", "_ranks")

    def __init__(self, entries: Iterable[tuple[Box, T]]) -> None:
        self._items: list[T] = []
        self._ranks: dict[_Cell, list[int]] = {}
        for box, item in entries:
            rank = len(self._items)
            self._items.append(item)
            for cell in _cells(box.x, box.y, box.x + box.width, box.y + box.height):
                self._ranks.setdefault(cell, []).append(rank)

    def meeting(self, x: int, y: int, to_x: int, to_y: int) -> tuple[T, ...]:
        """The items stored under a cell of the corner pair's range, once each, in entry order."""
        found: set[int] = set()
        for cell in _cells(x, y, to_x, to_y):
            found.update(self._ranks.get(cell, ()))
        return tuple(self._items[rank] for rank in sorted(found))
