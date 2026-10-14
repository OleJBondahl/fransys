"""Lanes, the order half: the stage column and the (lane, stage) cell of every box (O4).

Stubs stand in stage 0, west. Their host boxes come next and the rest by line distance from them;
with no stub the busiest box is the source. A cell stacks its boxes in the level's text order.
"""

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping, Sequence
lazy from collections.abc import Set as AbstractSet

if TYPE_CHECKING:
    from fransys_layout.engines.overview.read.values import Ident, ViewFacts


@dataclass(frozen=True, slots=True)
class Plan:
    """Each box's lane and stage, the boxes of each (lane, stage) cell, the counts."""

    lane: dict[Ident, int]
    stage: dict[Ident, int]
    cells: dict[tuple[int, int], list[Ident]]
    lanes: int
    stages: int


def _near(facts: ViewFacts, inner: AbstractSet[Ident]) -> dict[Ident, list[Ident]]:
    """Each inner box's inner neighbours over the level's lines."""
    near: dict[Ident, list[Ident]] = {b: [] for b in inner}
    for ln in facts.lines:
        if ln.a != ln.b and ln.a in inner and ln.b in inner:
            near[ln.a].append(ln.b)
            near[ln.b].append(ln.a)
    return near


def _hosts(facts: ViewFacts, stubs: AbstractSet[Ident]) -> set[Ident]:
    """The boxes a stub line leaves from."""
    return {
        end
        for ln in facts.lines
        for stub, end in ((ln.a, ln.b), (ln.b, ln.a))
        if stub in stubs and end not in stubs
    }


def _spread(
    depth: Mapping[Ident, int],
    near: Mapping[Ident, Sequence[Ident]],
    order: Mapping[Ident, int],
    sources: Sequence[Ident],
) -> dict[Ident, int]:
    """Breadth first from `sources` (depth 0): `depth` with the boxes not yet reached filled in."""
    queue = deque(s for s in sources if s not in depth)
    found = {**depth, **dict.fromkeys(queue, 0)}
    while queue:
        box = queue.popleft()
        for other in sorted(near[box], key=order.__getitem__):
            if other not in found:
                found[other] = found[box] + 1
                queue.append(other)
    return found


def stages(facts: ViewFacts) -> dict[Ident, int]:
    """The stage column of every box."""
    order = {b.box: n for n, b in enumerate(facts.boxes)}
    stubs = {b.box for b in facts.boxes if b.key.at is not None}
    inner = [b for b in order if b not in stubs]
    near = _near(facts, set(inner))
    hosts = sorted(_hosts(facts, stubs) & set(inner), key=order.__getitem__)
    depth = _spread({}, near, order, hosts)
    while len(depth) < len(inner):
        rest = [b for b in inner if b not in depth]
        depth = _spread(depth, near, order, [max(rest, key=lambda b: (len(near[b]), -order[b]))])
    shift = 1 if stubs else 0
    return {**{b: d + shift for b, d in depth.items()}, **dict.fromkeys(stubs, 0)}


SWEEPS = 4  # barycentre passes over the cells, alternating east and west


def _proxy(cells: Mapping[tuple[int, int], Sequence[Ident]]) -> dict[Ident, float]:
    """A box's place down the page: its lane, plus its share of the way down its cell."""
    return {b: lane + n / len(m) for (lane, _), m in cells.items() for n, b in enumerate(m)}


def _mean(place: Mapping[Ident, float], near: Mapping[Ident, Sequence[Ident]], box: Ident) -> float:
    """The mean place of `box`'s neighbours, its own place when it has none."""
    return sum(place[o] for o in near[box]) / len(near[box]) if near[box] else place[box]


def _sweep(
    cells: Mapping[tuple[int, int], Sequence[Ident]],
    near: Mapping[Ident, Sequence[Ident]],
    *,
    west: bool,
) -> dict[tuple[int, int], list[Ident]]:
    """Cells with each multi-box one re-sorted by the mean place of its boxes' neighbours."""
    place = _proxy(cells)
    found = {k: list(v) for k, v in cells.items()}
    for key in sorted(cells, key=lambda k: k[1], reverse=west):
        if len(found[key]) > 1:
            found[key].sort(key=lambda b: _mean(place, near, b))
            place.update(_proxy({key: found[key]}))
    return found


def make_plan(facts: ViewFacts) -> Plan:
    """The plan of a lanes view: `facts.lanes` gives each box's lane."""
    lane = {b.box: facts.lanes[n] for n, b in enumerate(facts.boxes)}
    stage = stages(facts)
    cells: dict[tuple[int, int], list[Ident]] = {}
    for b in facts.boxes:
        cells.setdefault((lane[b.box], stage[b.box]), []).append(b.box)
    near = _near(facts, set(lane))
    for n in range(SWEEPS):
        cells = _sweep(cells, near, west=bool(n % 2))
    return Plan(
        lane=lane,
        stage=stage,
        cells=cells,
        lanes=max(lane.values(), default=0) + 1,
        stages=max(stage.values(), default=0) + 1,
    )
