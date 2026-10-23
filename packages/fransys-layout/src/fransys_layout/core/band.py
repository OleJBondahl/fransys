"""One home for a trunk's band: the lane lines a `lanes`-wide trunk draws (layout-0312).

Lane 0 sits on the trunk line; lane k is `k * step` beside it, on one side. The axis (+x for a
vertical run, +y for a horizontal one) belongs to the caller. Plain values in, plain values out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

BAND_SIDES = ("E", "S")


def lane_offset(lane: int, step: int) -> int:
    """The offset of lane `lane` from the trunk line: lane * step."""
    return lane * step


def lane_offsets(lanes: int, step: int) -> tuple[int, ...]:
    """The offset of each lane line from the trunk line: 0, step, ..., (lanes - 1) * step."""
    return tuple(lane_offset(k, step) for k in range(lanes))


def band_extent(lanes: int, step: int) -> tuple[int, int]:
    """The near and far offsets of the band: the first and the last lane line."""
    offsets = lane_offsets(lanes, step)
    return offsets[0], offsets[-1]


def level_offset(lanes: int, level: int, step: int) -> int:
    """The offset of the line `level` steps past the `lanes` band lines: level 0 is just past."""
    return lane_offset(lanes + level, step)


def trunk_room(lanes: int, step: int) -> tuple[int, int]:
    """The G a row holds above and below a trunk line: one step above, the band and a step below."""
    return step, level_offset(lanes, 0, step)


def centred_span(lanes: int, step: int) -> int:
    """The estimate of a band drawn both ways round the trunk line: twice its depth."""
    return 2 * level_offset(lanes, 0, step)


def on_band_side(side: str) -> bool:
    """True for the sides the band grows towards (E and S: +x and +y), the caller's axis aside."""
    return side in BAND_SIDES


def lane_rows(ends: Sequence[tuple[int, int] | None]) -> tuple[int, ...]:
    """The band row of each lane: lane j's own, unless its leg column is lane j+1's driver column.

    Then lane j+1 stands on the driver side (nearer row) of lane j, so no drop of the shared
    column passes the other's row (layout-0389, R505). A run of such lanes takes its rows reversed.
    """
    rows = list(range(len(ends)))
    j = 0
    while j < len(ends):
        k = j
        while _shares(ends, k):
            k += 1
        rows[j : k + 1] = range(k, j - 1, -1)
        j = k + 1
    return tuple(rows)


def _shares(ends: Sequence[tuple[int, int] | None], j: int) -> bool:
    """Lane j runs rightwards and ends on the column lane j + 1 starts from."""
    if j + 1 >= len(ends):
        return False
    here, after = ends[j], ends[j + 1]
    return here is not None and after is not None and here[0] < here[1] == after[0]
