"""Stage 6 counts of one page: the scorer's counters, collinear overlaps and gap demand.

Crossings, bends, excess, length and detour come from `score_wiring` (one rule, one home).
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .outputs import Counts, Demand
from .score_wiring import MIN_POINTS, crossings_on_page, shape

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Gap, Wire


def counts(wires: Sequence[Wire]) -> Counts:
    """The five counts of one page's wires, through the scorer's `shape` and `crossings_on_page`."""
    shapes = [shape(w.points) for w in wires if len(w.points) >= MIN_POINTS]
    return Counts(
        crossings=crossings_on_page(wires),
        bends=sum(s[0] for s in shapes),
        excess=sum(s[1] for s in shapes),
        length=sum(s[2] for s in shapes),
        detour=sum(s[2] - s[3] for s in shapes),
    )


def _runs(wires: Sequence[Wire]) -> dict[tuple[bool, int], list[tuple[int, int, str]]]:
    """Every run keyed by (horizontal, line coordinate), as (low, high, net)."""
    lines: dict[tuple[bool, int], list[tuple[int, int, str]]] = defaultdict(list)
    for w in wires:
        for (x0, y0), (x1, y1) in pairwise(w.points):
            if y0 == y1 and x0 != x1:
                lines[(True, y0)].append((min(x0, x1), max(x0, x1), w.net))
            elif x0 == x1 and y0 != y1:
                lines[(False, x0)].append((min(y0, y1), max(y0, y1), w.net))
    return lines


def collinear(wires: Sequence[Wire]) -> int:
    """Pairs of runs of different nets on one line that share more than a point.

    The crossing count cannot see them: it counts only perpendicular meetings.
    """
    return sum(
        1
        for row in _runs(wires).values()
        for i, a in enumerate(row)
        for b in row[i + 1 :]
        if a[2] != b[2] and max(a[0], b[0]) < min(a[1], b[1])
    )


def _in_gap(gap: Gap, x: int, top: int, bottom: int) -> bool:
    """X is strictly inside the gap and, when its row band is set, the run meets the band."""
    if not gap.x0 < x < gap.x1:
        return False
    return gap.y0 is None or gap.y1 is None or (top <= gap.y1 and bottom >= gap.y0)


def demand(wires: Sequence[Wire], gaps: Sequence[Gap]) -> tuple[Demand, ...]:
    """Tracks each gap needs: the distinct x of the vertical runs inside it."""
    verticals = [
        (a[0], min(a[1], b[1]), max(a[1], b[1]))
        for w in wires
        for a, b in pairwise(w.points)
        if a[0] == b[0] and a[1] != b[1]
    ]
    return tuple(
        Demand(g.id, len({x for x, top, bottom in verticals if _in_gap(g, x, top, bottom)}))
        for g in gaps
    )
