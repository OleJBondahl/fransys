"""Lanes, sizes and rows: the box sizes, the lane bands, the corridors between them (O4)."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.diagram.arrange import RawEnd, box_height, box_width
from fransys_layout.engines.diagram.sizes import PAGE_PAD, ROW_GAP, TRACK_PITCH
from fransys_layout.geometry import Facing, snap_up
from fransys_layout.stages.corridor import corridor_height, corridor_y, plan_corridors

if TYPE_CHECKING:
    from fransys_layout.engines.overview.lanes.plan import Plan
    from fransys_layout.engines.overview.read.values import Ident, ViewFacts
    from fransys_layout.stages.corridor import CorridorPlan


def side_of(stage: Mapping[Ident, int], me: Ident, far: Ident) -> Facing:
    """West towards an earlier stage, east towards a later one and for the same stage."""
    return Facing.W if stage[far] < stage[me] else Facing.E


def raw_ends(facts: ViewFacts, stage: Mapping[Ident, int]) -> tuple[RawEnd, ...]:
    """Both ends of every line, in line order."""
    out = []
    for i, ln in enumerate(facts.diagram.lines):
        out.append(RawEnd(i, ln.a, ln.b, side_of(stage, ln.a, ln.b), ln.tab_a))
        out.append(RawEnd(i, ln.b, ln.a, side_of(stage, ln.b, ln.a), ln.tab_b))
    return tuple(out)


def box_sizes(facts: ViewFacts, raw: tuple[RawEnd, ...]) -> dict[Ident, tuple[int, int]]:
    """Each box's width and height; the height fits the busier of its two sides."""
    count = Counter((e.box, e.side) for e in raw)
    return {
        b.box: (
            box_width(b),
            box_height(
                b, max(count[b.box, Facing.E], count[b.box, Facing.W]), facts.diagram.text_height
            ),
        )
        for b in facts.diagram.boxes
    }


def corridors(facts: ViewFacts, plan: Plan) -> CorridorPlan:
    """The corridor of each line across two or more stages (a line index is its key)."""
    lines = [
        (i, plan.lane[ln.a], plan.lane[ln.b], plan.stage[ln.a], plan.stage[ln.b])
        for i, ln in enumerate(facts.diagram.lines)
    ]
    return plan_corridors(lines, plan.lanes)


@dataclass(frozen=True, slots=True)
class Rows:
    """The y of every box, of every corridor track and of every lane's text."""

    box_y: dict[Ident, int]
    track_y: dict[int, int]
    head_y: dict[int, int]


def head_rise(facts: ViewFacts, plan: Plan) -> list[int]:
    """The room each lane keeps above its boxes for its text (none in the no-group lane)."""
    rise = facts.diagram.text_height + ROW_GAP
    return [rise if n < len(facts.heads) else 0 for n in range(plan.lanes)]


def _bands(
    plan: Plan, stack: Mapping[tuple[int, int], int], found: CorridorPlan, rise: Sequence[int]
) -> tuple[list[int], ...]:
    """Band heights and the tops of the corridors and bands, from the top: a corridor, a band."""
    band = [
        rise[n] + max((v for (lane, _), v in stack.items() if lane == n), default=0)
        for n in range(plan.lanes)
    ]
    floor = [ROW_GAP if 0 < c < plan.lanes else 0 for c in range(plan.lanes + 1)]
    chigh = [corridor_height(found.load[c], TRACK_PITCH, floor[c]) for c in range(plan.lanes + 1)]
    ctop: list[int] = []
    btop: list[int] = []
    y = PAGE_PAD
    for c in range(plan.lanes + 1):
        ctop.append(y)
        y += chigh[c]
        if c < plan.lanes:
            btop.append(y)
            y += band[c]
    return band, chigh, ctop, btop


def rows(plan: Plan, high: Mapping[Ident, int], found: CorridorPlan, rise: Sequence[int]) -> Rows:
    """Bands from the top, a corridor above each and one below the last; boxes centred in a band.

    A lane with a text keeps its first line free of boxes (`rise`).
    """
    stack = {k: sum(high[b] for b in m) + ROW_GAP * (len(m) - 1) for k, m in plan.cells.items()}
    band, chigh, ctop, btop = _bands(plan, stack, found, rise)
    box_y = {}
    for (lane, stage), members in plan.cells.items():
        free = band[lane] - rise[lane] - stack[lane, stage]
        cursor = btop[lane] + rise[lane] + snap_up(free // 2)
        for b in members:
            box_y[b] = cursor
            cursor += high[b] + ROW_GAP
    track_y = {
        i: corridor_y(ctop[c], chigh[c], found.load[c], found.rank[i], TRACK_PITCH)
        for i, c in found.corridor.items()
    }
    return Rows(box_y=box_y, track_y=track_y, head_y=dict(enumerate(btop)))
