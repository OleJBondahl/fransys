"""One home for a trunk's band: the lane lines a `lanes`-wide trunk draws (layout-0312).

Lane 0 sits on the trunk line; lane k is `k * step` beside it, on one side. The axis (+x for a
vertical run, +y for a horizontal one) belongs to the caller. Plain values in, plain values out.
"""

from __future__ import annotations

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
