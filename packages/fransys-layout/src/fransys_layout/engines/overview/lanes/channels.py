"""Lanes, the channels: the room right of each stage column and the tracks in it (O4).

A line between neighbouring stages runs in the channel between them. A line across two or more
stages runs in its channel to its corridor track, along the corridor, then down its last channel.
A line within one stage takes a track after the planned ones, right of its column, or left of it
when the plan runs it west.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.overview.lanes.arrange import place_ends
from fransys_layout.engines.overview.lanes.plan_channel import plan_channel
from fransys_layout.engines.overview.sizes import TRACK_PITCH, label_room, tab_reach
from fransys_layout.geometry import PAGE_PAD, WIRING_GRID, Facing

if TYPE_CHECKING:
    from fransys_layout.engines.overview.lanes.arrange import RawEnd
    from fransys_layout.engines.overview.lanes.frame_values import FrameEnd
    from fransys_layout.engines.overview.lanes.plan import Plan
    from fransys_layout.engines.overview.read.values import Ident, ViewFacts

type Run = tuple[int, int, int, int, int]  # line, part, left y, right y, track


@dataclass(frozen=True, slots=True)
class Channel:
    """One channel: its runs, the same-stage lines, the track count, the left room and width."""

    runs: tuple[Run, ...]
    same: tuple[int, ...]
    count: int
    lead: int
    width: int


def _stagger(
    by: Mapping[tuple[int, Ident], FrameEnd], stage: Mapping[Ident, int]
) -> dict[tuple[int, Ident], FrameEnd]:
    """Move a west end down by grid steps off the y of an east end of the stage before it."""
    east = {(stage[box], e.y) for (_, box), e in by.items() if e.side is Facing.E}
    taken: dict[Ident, set[int]] = {}
    out = dict(by)
    for (line, box), e in sorted(by.items(), key=lambda kv: (kv[1].y, kv[0][0])):
        if e.side is not Facing.W:
            continue
        used, y = taken.setdefault(box, set()), e.y
        while (stage[box] - 1, y) in east or y in used:
            y += WIRING_GRID
        used.add(y)
        out[line, box] = replace(e, y=y)
    return out


def end_ys(
    raw: tuple[RawEnd, ...],
    box_y: Mapping[Ident, int],
    high: Mapping[Ident, int],
    facts: ViewFacts,
    stage: Mapping[Ident, int],
) -> dict[tuple[int, Ident], FrameEnd]:
    """The end of each (line, box), spaced down its box edge by the diagram's rule."""
    placed = place_ends(raw, box_y, high, facts.diagram.text_height)
    return _stagger({(e.line, box): e for (box, _), group in placed.items() for e in group}, stage)


def _planned(nets: Sequence[tuple[int, int, int]]) -> tuple[tuple[Run, ...], int]:
    """The runs of `nets` and their track count; one track a net when the planner finds none."""
    plan = plan_channel(nets, spans=True) if nets else None
    if plan is None:
        return tuple((k, 0, a, b, i + 1) for i, (k, a, b) in enumerate(sorted(nets))), len(nets)
    runs = zip(plan.nets, plan.tracks, strict=True)
    return tuple((n.core, n.part, n.top, n.bottom, t) for n, t in runs), plan.count


def stage_nets(
    facts: ViewFacts,
    plan: Plan,
    by: Mapping[tuple[int, Ident], FrameEnd],
    track_y: Mapping[int, int],
) -> tuple[dict[int, list[tuple[int, int, int]]], dict[int, list[int]]]:
    """Per stage: the nets (line, left y, right y) of its channel and its same-stage lines."""
    nets: dict[int, list[tuple[int, int, int]]] = {s: [] for s in range(plan.stages)}
    same: dict[int, list[int]] = {s: [] for s in range(plan.stages)}
    for i, ln in enumerate(facts.diagram.lines):
        u, v = sorted((ln.a, ln.b), key=lambda b: (plan.stage[b], b != ln.a))
        su, sv = plan.stage[u], plan.stage[v]
        if su == sv:
            same[su - 1 if plan.runs_west(i, su) else su].append(i)
        elif i in track_y:
            nets[su].append((i, by[i, u].y, track_y[i]))
            nets[sv - 1].append((i, track_y[i], by[i, v].y))
        else:
            nets[su].append((i, by[i, u].y, by[i, v].y))
    return nets, same


def reaches(raw: tuple[RawEnd, ...], stage: Mapping[Ident, int]) -> dict[tuple[int, Facing], int]:
    """The widest tab reach per (stage, side)."""
    out: dict[tuple[int, Facing], int] = {}
    for e in raw:
        if e.tab is not None:
            key = (stage[e.box], e.side)
            out[key] = max(out.get(key, 0), tab_reach(e.tab))
    return out


def channels(
    facts: ViewFacts,
    plan: Plan,
    by: Mapping[tuple[int, Ident], FrameEnd],
    reach: Mapping[tuple[int, Facing], int],
    track_y: Mapping[int, int],
) -> list[Channel]:
    """The channel right of each stage column."""
    nets, same = stage_nets(facts, plan, by, track_y)
    label = [ln.label_width for ln in facts.diagram.lines]
    out = []
    for s in range(plan.stages):
        runs, count = _planned(nets[s])
        used = [r[0] for r in runs] + same[s]
        lab = label_room(max((label[i] for i in used), default=0))
        lead = reach.get((s, Facing.E), 0) + lab
        tail = lab + reach.get((s + 1, Facing.W), 0) if s + 1 < plan.stages else 0
        tracks = (count + len(same[s]) + 1) * TRACK_PITCH
        width = lead + tracks + tail if used else 2 * PAGE_PAD
        out.append(Channel(runs=runs, same=tuple(same[s]), count=count, lead=lead, width=width))
    return out
