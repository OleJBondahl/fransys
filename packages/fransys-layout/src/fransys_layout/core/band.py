"""One home for a trunk's band: the lane lines a `lanes`-wide trunk draws (layout-0312).

Lane 0 sits on the trunk line; lane k is `k * step` beside it, on one side. The axis (+x for a
vertical run, +y for a horizontal one) belongs to the caller. Plain values in, plain values out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import marker_box_at, marker_drawn_box_at
from .sides import step_out

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Trunk
    from .values import Box, Options, Orientation, PinRef, Side


def lane_offset(lane: int, step: int) -> int:
    """The offset of lane `lane` from the trunk line: lane * step."""
    return lane * step


def level_offset(lanes: int, level: int, step: int) -> int:
    """The offset of the line `level` steps past the `lanes` band lines: level 0 is just past."""
    return lane_offset(lanes + level, step)


def arrow_hang(lanes: int, step: int, arrow: int) -> int:
    """The y a lane-end arrow's `arrow` room reaches past the `lanes`-wide band, 0 when it stays inside (R1719)."""
    return max(0, lane_offset(lanes - 1, step) + arrow - level_offset(lanes, 0, step))


def trunk_room(lanes: int, step: int, leg: int = 0) -> tuple[int, int]:
    """The G a row holds above and below a trunk line: one step above; the band and the `leg` depth of its markers below.

    The one formula: the solver's edges, the trunk's `room` and the round-one estimate all read it.
    """
    return step, level_offset(lanes, 0, step) + leg


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


def lane_line(t: Trunk, pole: int, lanes: int, step: int) -> tuple[int, int, int, tuple[bool, bool]]:
    """(x0, x1, y, stood) of the line a pole's arrow stands on: the trunk's, or its own lane's when the fan has `lanes` > 1.

    `stood` says whether the (left, right) end stood. One home: the marker stage stands the arrow on it and a leg stand clears it.
    """
    stood = t.stood[pole] if t.stood else (True, True)
    if lanes == 1:
        return t.x0, t.x1, t.y, stood
    x0, x1 = t.lane_ends[pole] or (t.x0, t.x1)
    return x0, x1, t.y + lane_offset(lane_rows(t.lane_ends)[pole], step), stood


def abut(options: Options, side: Side, x: int, y: int, key: tuple[PinRef, str]) -> tuple[int, int, Orientation]:
    """The origin and turn of the marker whose box has its near edge at (x, y) on `side`; the box turns to face it."""
    turned = options.marker_facing[side]  # the symbol at R0 points east; this turn points its box along the pin's side
    box = marker_box_at(0, 0, options, turned, key)  # the box about an origin of (0, 0)
    depth = {"E": -box.x, "W": box.x + box.w, "S": -box.y, "N": box.y + box.h}[side]
    return (*step_out(side, x, y, depth), turned)


def arrow_box(options: Options, side: Side, x: int, y: int, key: tuple[PinRef, str]) -> Box:
    """The drawn box of the arrow whose near edge is at (x, y) on `side`: the one box the placement walk and the marker stand test (layout-0524)."""
    ox, oy, turned = abut(options, side, x, y, key)
    return marker_drawn_box_at(ox, oy, options, turned, key)
