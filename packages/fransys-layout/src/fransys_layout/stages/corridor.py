"""Corridors between bands of boxes: which corridor a long line uses and its track in it.

Integers only. A line across two or more columns runs in a corridor, never through a box.
Widest lines choose first, each the least loaded corridor it may use.
"""

from dataclasses import dataclass
lazy from collections.abc import Sequence

from fransys_layout.geometry import snap_up

LONG = 2  # columns a line spans before it needs a corridor
Line = tuple[int, int, int, int, int]  # key, band_a, band_b, col_a, col_b


@dataclass(frozen=True, slots=True)
class CorridorPlan:
    """Per line key: its corridor (0 above the first band .. bands below the last) and its rank."""

    corridor: dict[int, int]
    rank: dict[int, int]
    load: tuple[int, ...]


def _candidates(band_a: int, band_b: int) -> range:
    lo, hi = min(band_a, band_b), max(band_a, band_b)
    return range(lo, lo + 2) if lo == hi else range(lo + 1, hi + 1)


def _pick(line: Line, load: Sequence[int]) -> int:
    """The least loaded corridor; a tie goes to the lower index (below, in one band)."""
    _, band_a, band_b, _, _ = line
    sign = -1 if band_a == band_b else 1
    return min(_candidates(band_a, band_b), key=lambda c: (load[c], sign * c))


def plan_corridors(lines: Sequence[Line], bands: int) -> CorridorPlan:
    """The corridor and track rank of each line (key, band_a, band_b, col_a, col_b) of 2+ columns.

    Ranks in a corridor are unique, sorted by left column, then right column descending, then key.
    """
    long = sorted((ln for ln in lines if abs(ln[3] - ln[4]) >= LONG), key=_order)
    load = [0] * (bands + 1)
    corridor: dict[int, int] = {}
    for line in long:
        corridor[line[0]] = c = _pick(line, load)
        load[c] += 1
    seen = [0] * (bands + 1)
    rank: dict[int, int] = {}
    for line in sorted(long, key=_track_order):
        c = corridor[line[0]]
        rank[line[0]], seen[c] = seen[c], seen[c] + 1
    return CorridorPlan(corridor=corridor, rank=rank, load=tuple(load))


def _order(line: Line) -> tuple[int, int]:
    return -abs(line[3] - line[4]), line[0]


def _track_order(line: Line) -> tuple[int, int, int]:
    return min(line[3], line[4]), -max(line[3], line[4]), line[0]


def corridor_height(load: int, pitch: int, floor: int = 0) -> int:
    """The height of a corridor of `load` tracks: one pitch more than the tracks, 0 when empty."""
    return max((load + 1) * pitch if load else 0, floor)


def corridor_y(top: int, height: int, load: int, rank: int, pitch: int) -> int:
    """The y of track `rank`, the `load` tracks centred in the corridor, the first on the grid."""
    return top + snap_up((height - (load - 1) * pitch) // 2) + rank * pitch
