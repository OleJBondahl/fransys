"""Runs keyed by their track (layout-0133): the one index the label placer and the diagram lint read.

A lookup reads by grid row or column, never scans the runs. The index over-selects; a caller keeps its exact test.
"""

lazy from collections.abc import Iterable

from fransys_layout.geometry import WIRING_GRID as G
from fransys_layout.geometry import Box
lazy from fransys_layout.routing.space import Run


class TrackIndex[T]:
    """Entries `(run, item)` by the grid row of a horizontal run or the grid column of a vertical one (a point sits in both)."""

    def __init__(self, entries: Iterable[tuple[Run, T]]) -> None:
        self.entries = tuple(entries)
        self._by: dict[tuple[bool, int], list[tuple[Run, T]]] = {}
        for e in self.entries:
            if e[0].y == e[0].to_y:
                self._by.setdefault((True, e[0].y // G), []).append(e)
            if e[0].x == e[0].to_x:
                self._by.setdefault((False, e[0].x // G), []).append(e)

    def near(self, box: Box) -> list[tuple[Run, T]]:
        """The entries on a row or column the closed `box` reaches."""
        spans = ((True, box.y, box.height), (False, box.x, box.width))
        return [e for horizontal, at, size in spans for k in range(at // G, (at + size) // G + 1) for e in self._by.get((horizontal, k), ())]
