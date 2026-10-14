"""Lanes, the sheet: boxes at their stage columns and bands, lines through the channels (O4)."""

from dataclasses import dataclass
from itertools import accumulate
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.diagram.labels import label_lines
from fransys_layout.engines.diagram.route import tidy
from fransys_layout.engines.diagram.sizes import TRACK_PITCH, tab_reach
from fransys_layout.engines.diagram.values import (
    PlacedBox,
    PlacedSheet,
    PlacedTab,
    PlacedText,
)
from fransys_layout.geometry import PAGE_PAD, Box, Facing, Point
from fransys_layout.stages.corridor import LONG
lazy from fransys_layout.engines.overview.lanes.channels import Channel

if TYPE_CHECKING:
    from fransys_layout.engines.diagram.frame_values import FrameEnd
    from fransys_layout.engines.overview.lanes.plan import Plan
    from fransys_layout.engines.overview.read.values import Ident, ViewFacts


@dataclass(frozen=True, slots=True)
class Room:
    """Where things stand: the channels, the stage columns' x and width, box y and size."""

    chans: list[Channel]
    xs: list[int]
    wide: list[int]
    box_y: dict[Ident, int]
    size: dict[Ident, tuple[int, int]]


def column_xs(
    plan: Plan, width: Mapping[Ident, int], chans: Sequence[Channel]
) -> tuple[list[int], list[int]]:
    """The left x of each stage column and the width of each."""
    wide = [
        max((width[b] for b in plan.stage if plan.stage[b] == s), default=0)
        for s in range(plan.stages)
    ]
    starts = accumulate((w + c.width for w, c in zip(wide, chans, strict=True)), initial=PAGE_PAD)
    return list(starts)[:-1], wide


def touch(rect: Box, end: FrameEnd) -> Point:
    """Where a line meets its end: the box edge, or the outer edge of the end's tab."""
    reach = 0 if end.tab is None else tab_reach(end.tab)
    x = rect.x + rect.width + reach if end.side is Facing.E else rect.x - reach
    return Point(x=x, y=end.y)


def _middle(room: Room, s: int, line: int) -> list[Point]:
    """The points of a line's runs in channel `s`, a jogged core's halves in order."""
    out: list[Point] = []
    chan = room.chans[s]
    for _, _, top, bottom, track in sorted(
        (r for r in chan.runs if r[0] == line), key=lambda r: r[1]
    ):
        x = room.xs[s] + room.wide[s] + chan.lead + track * TRACK_PITCH
        out += [Point(x=x, y=top), Point(x=x, y=bottom)]
    return out


def line_points(
    i: int, plan: Plan, ends: tuple[Ident, Ident], touches: tuple[Point, Point], room: Room
) -> tuple[Point, ...]:
    """The points of line `i` from its lower-stage end `ends[0]` to the other."""
    (su, sv), (tu, tv) = (plan.stage[ends[0]], plan.stage[ends[1]]), touches
    if su == sv:
        s = su - 1 if plan.runs_west(i, su) else su
        c = room.chans[s]
        x = room.xs[s] + room.wide[s] + c.lead + (c.count + 1 + c.same.index(i)) * TRACK_PITCH
        return tidy((tu, Point(x=x, y=tu.y), Point(x=x, y=tv.y), tv))
    mid = _middle(room, su, i)
    if sv - su >= LONG:
        mid += _middle(room, sv - 1, i)
    return tidy((tu, *mid, tv))


def sheet(
    facts: ViewFacts,
    plan: Plan,
    by: Mapping[tuple[int, Ident], FrameEnd],
    room: Room,
    head_y: Mapping[int, int],
) -> PlacedSheet:
    """The placed sheet: every box with its tabs, every line with its label, every lane's text."""
    size, box_y = room.size, room.box_y
    rect = {
        b.box: Box(
            x=room.xs[plan.stage[b.box]],
            y=box_y[b.box],
            width=size[b.box][0],
            height=size[b.box][1],
        )
        for b in facts.diagram.boxes
    }
    tabs: dict[Ident, list[PlacedTab]] = {b: [] for b in rect}
    for (line, box), e in sorted(by.items(), key=lambda kv: (kv[1].y, kv[0][0])):
        if e.tab is not None:
            tabs[box].append(
                PlacedTab(
                    cable=facts.diagram.lines[line].cable, side=e.side, y=e.y, text_width=e.tab
                )
            )
    boxes = tuple(
        PlacedBox(
            box=b.box,
            dashed=b.dashed,
            x=r.x,
            y=r.y,
            width=r.width,
            height=r.height,
            tabs=tuple(tabs[b.box]),
        )
        for b in facts.diagram.boxes
        for r in (rect[b.box],)
    )
    routed = []
    for i, ln in enumerate(facts.diagram.lines):
        low, high = sorted((ln.a, ln.b), key=lambda b: (plan.stage[b], b != ln.a))
        pts = line_points(
            i,
            plan,
            (low, high),
            (touch(rect[low], by[i, low]), touch(rect[high], by[i, high])),
            room,
        )
        pts = pts if low == ln.a else pts[::-1]
        routed.append((ln, pts))
    lines = label_lines(routed, boxes, facts.diagram.text_height)
    heads = tuple(
        PlacedText(
            owner=h.owner, x=PAGE_PAD, y=head_y[n], width=h.width, height=facts.diagram.text_height
        )
        for n, h in enumerate(facts.heads)
    )
    return PlacedSheet(number=1, boxes=boxes, lines=tuple(lines), markers=(), texts=heads)
