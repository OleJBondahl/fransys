"""Stage 6 counts of one page: the scorer's counters, collinear overlaps and gap demand.

Crossings, bends, excess and length come from `score_wiring` (one rule, one home).
"""

from typing import TYPE_CHECKING

from .occupancy import Occupancy
from .outputs import Counts, Demand
from .score_wiring import MIN_POINTS, crossings_on_page, shape

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .outputs import Gap, Wire

GRID = 8  # the marks' cell size; collinear and columns_used read exact runs, not cells


def counts(wires: Sequence[Wire], bundle_of: Mapping[str, str] | None = None) -> Counts:
    """The four counts of one page's wires, through the scorer's `shape` and `crossings_on_page`."""
    shapes = [shape(w.points) for w in wires if len(w.points) >= MIN_POINTS]
    return Counts(
        crossings=crossings_on_page(wires, bundle_of),
        bends=sum(s[0] for s in shapes),
        excess=sum(s[1] for s in shapes),
        length=sum(s[2] for s in shapes),
    )


def _marked(wires: Sequence[Wire]) -> Occupancy:
    """An occupancy holding the wires' marks: the one index `collinear` and `demand` read."""
    occ = Occupancy(0, 0, GRID)
    for w in wires:
        occ.mark_wire(w.net, w.points)
    return occ


def collinear(wires: Sequence[Wire]) -> int:
    """Pairs of runs of different nets on one line that share more than a point.

    The crossing count cannot see them: it counts only perpendicular meetings.
    """
    return _marked(wires).collinear()


def demand(wires: Sequence[Wire], gaps: Sequence[Gap]) -> tuple[Demand, ...]:
    """Tracks each gap needs: the nets with a vertical run inside it, never fewer than their distinct x."""
    occ = _marked(wires)
    return tuple(Demand(g.id, occ.columns_used(g)) for g in gaps)
