"""Lanes, the order half: the stage column and the (lane, stage) cell of every box (O4, LO3 to LO5).

West stubs stand in the first column, east stubs after the last stage. The stages run over the
power lines from the boxes the west stubs join. A cell stacks strip-joined boxes by the first
terminal they join (LO5), then the rest in reader order.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Collection, Sequence
lazy from collections.abc import Set as AbstractSet

from fransys_layout.engines.overview.lanes.flow import neighbours, stack, stages

if TYPE_CHECKING:
    from fransys_layout.engines.overview.read.values import BoxSpec, Ident, ViewFacts


@dataclass(frozen=True, slots=True)
class Plan:
    """Each box's lane and stage, the boxes of each cell, the counts, the lines run west of a stage.

    `west` holds the lines whose same-stage run stands in the gap before the stage, not after it.
    """

    lane: dict[Ident, int]
    stage: dict[Ident, int]
    cells: dict[tuple[int, int], list[Ident]]
    lanes: int
    stages: int
    west: frozenset[int] = frozenset()

    def runs_west(self, line: int, stage: int) -> bool:
        """Whether a same-stage `line` at `stage` runs in the gap before it (the first has none)."""
        return line in self.west and stage > 0


def _reader_order(facts: ViewFacts) -> list[BoxSpec]:
    """The boxes in reader order, by the rank the reader gave each."""
    return [b for _, b in sorted(zip(facts.rank, facts.boxes, strict=True), key=lambda t: t[0])]


def _hosts(facts: ViewFacts, stubs: Collection[Ident], inner: Collection[Ident]) -> set[Ident]:
    """The inner boxes a line leaves from to a box of `stubs`."""
    return {
        end
        for ln in facts.lines
        for stub, end in ((ln.a, ln.b), (ln.b, ln.a))
        if stub in stubs and end in inner
    }


def _sources(
    inner: Sequence[Ident],
    pairs: Sequence[tuple[Ident, Ident]],
    west: AbstractSet[Ident],
    east: AbstractSet[Ident],
) -> list[Ident]:
    """The boxes the west stubs join, else the busiest box no east stub joins (first on a tie)."""
    joined = [b for b in inner if b in west]
    near = neighbours(inner, pairs)
    free = [b for b in inner if b not in east]
    return joined or ([max(free, key=lambda b: len(set(near[b])))] if free else [])


def _stages(
    facts: ViewFacts, inner: Sequence[Ident], west_stubs: AbstractSet[Ident]
) -> dict[Ident, int]:
    """The stage of every box: inner boxes by LO3, west stubs at 0, east stubs after the last."""
    inside = set(inner)
    stubs = {b.box for b in facts.boxes} - inside
    pairs = [(ln.a, ln.b) for ln in facts.lines if ln.a in inside and ln.b in inside]
    flow = [
        p
        for p, power in zip(((ln.a, ln.b) for ln in facts.lines), facts.power, strict=True)
        if power
    ]
    west = _hosts(facts, west_stubs, inside)
    east = _hosts(facts, stubs - west_stubs, inside)
    shift = 1 if west_stubs else 0
    found = {
        b: s + shift
        for b, s in stages(inner, flow, pairs, _sources(inner, pairs, west, east), east).items()
    }
    last = max(found.values(), default=0) + 1
    return {**found, **{s: 0 if s in west_stubs else last for s in stubs}}


def make_plan(facts: ViewFacts) -> Plan:
    """The plan of a lanes view: lanes from `facts.lanes`, west stubs from `facts.west`."""
    lane = {b.box: facts.lanes[n] for n, b in enumerate(facts.boxes)}
    stubs = {b.box for b in facts.boxes if b.key.at is not None}
    west = {b.box for b, w in zip(facts.boxes, facts.west, strict=True) if w}
    order = _reader_order(facts)
    stage = _stages(facts, [b.box for b in order if b.box not in stubs], west)
    join = {b.box: j if j >= 0 else math.inf for b, j in zip(facts.boxes, facts.join, strict=True)}
    cells = stack([b.box for b in order], {b: (lane[b], stage[b]) for b in lane}, join)
    inner = frozenset(i for i, ln in enumerate(facts.lines) if not {ln.a, ln.b} & stubs)
    return Plan(
        west=inner,
        lane=lane,
        stage=stage,
        cells=cells,
        lanes=max(lane.values(), default=0) + 1,
        stages=max(stage.values(), default=0) + 1,
    )
