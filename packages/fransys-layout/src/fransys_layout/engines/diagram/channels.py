"""The diagram frame's channels (BD5): the room between two adjacent columns, tracks and cuts.

A pair is column `c` and `c + 1` (None after the last). Its channel is drawn when both share a
sheet; when a sheet ends between them it is a cut, and the pair's `trail` and `lead` zones apply.
"""

from dataclasses import dataclass
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.diagram.frame_values import FrameChannel, FrameCut, FrameTrack
from fransys_layout.engines.diagram.sizes import (
    MARKER_W,
    PAGE_PAD,
    TRACK_PITCH,
    label_room,
    tab_reach,
)
from fransys_layout.geometry import Facing
from fransys_layout.stages.channel import plan_channel
lazy from fransys_layout.engines.diagram.arrange import Joint
lazy from fransys_layout.engines.diagram.frame_values import FrameEnd
lazy from fransys_layout.engines.diagram.values import DiagramFacts, Ident

type Ends = Mapping[tuple[Ident, Facing], Sequence[FrameEnd]]


@dataclass(frozen=True, slots=True)
class Pair:
    """Columns `left` and `left + 1`: lines between, same-column lines of `left`, the rooms."""

    left: int
    right: int | None
    lines: tuple[int, ...]
    same: tuple[int, ...]
    tab_l: int
    tab_r: int
    label: int
    cut_label: int
    tracks: tuple[FrameTrack, ...]
    count: int

    @property
    def width(self) -> int:
        """The channel's width (rule 6): two page pads when nothing is routed in it."""
        if not self.lines and not self.same:
            return 2 * PAGE_PAD
        tracks = (self.count + len(self.same) + 1) * TRACK_PITCH
        return self.tab_l + self.label + tracks + (self.label + self.tab_r if self.right else 0)

    @property
    def trail(self) -> int:
        """The room right of the left column: its channel's width, or a cut's stub zone."""
        if self.right is None:
            return self.width
        if not self.lines and not self.same:
            return PAGE_PAD
        return self.tab_l + self.label + len(self.same) * TRACK_PITCH + MARKER_W

    @property
    def lead(self) -> int:
        """The room right of a sheet's start before the right column when this pair is cut."""
        return self.tab_r + self.cut_label + MARKER_W if self.lines else PAGE_PAD


def tab_room(boxes: Sequence[Ident], ends: Ends, side: Facing) -> int:
    """The widest tab reach on `side` of any of `boxes`, 0 when none has a tab."""
    reach = (tab_reach(e.tab) for b in boxes for e in ends.get((b, side), ()) if e.tab is not None)
    return max(reach, default=0)


def _tracks(
    between: Sequence[Joint], line_y: Mapping[tuple[int, Ident], int]
) -> tuple[tuple[FrameTrack, ...], int] | None:
    """The plan of the lines between two columns as tracks and their count, or None."""
    plan = plan_channel(
        [(j.line, line_y[j.line, j.left], line_y[j.line, j.right]) for j in between]
    )
    if plan is None:
        return None
    runs = tuple(
        FrameTrack(line=n.core, part=n.part, left_y=n.top, right_y=n.bottom, track=t)
        for n, t in zip(plan.nets, plan.tracks, strict=True)
    )
    return runs, plan.count


@dataclass(frozen=True, slots=True)
class Context:
    """What every pair reads: columns, joints, ends, each end's y by (line, box), label widths."""

    columns: Sequence[Sequence[Ident]]
    joints: Sequence[Joint]
    ends: Ends
    line_y: Mapping[tuple[int, Ident], int]
    labels: Sequence[int]


def _pair(c: int, ctx: Context) -> Pair | None:
    """The pair of column `c` and the next, or None when its channel cannot be planned."""
    columns = ctx.columns
    where = {b: i for i, col in enumerate(columns) for b in col}
    between = [j for j in ctx.joints if not j.same and where[j.left] == c]
    same = [j for j in ctx.joints if j.same and where[j.left] == c]
    planned = _tracks(between, ctx.line_y)
    if planned is None:
        return None
    right = c + 1 if c + 1 < len(columns) else None
    tab_r = tab_room(columns[c + 1], ctx.ends, Facing.W) if right is not None else 0
    wide = max((ctx.labels[j.line] for j in between), default=0)
    widest = max((ctx.labels[j.line] for j in (*between, *same)), default=0)
    return Pair(
        left=c,
        right=right,
        lines=tuple(j.line for j in between),
        same=tuple(j.line for j in same),
        tab_l=tab_room(columns[c], ctx.ends, Facing.E),
        tab_r=tab_r,
        label=label_room(widest),
        cut_label=label_room(wide),
        tracks=planned[0],
        count=planned[1],
    )


def build_pairs(
    facts: DiagramFacts,
    columns: Sequence[Sequence[Ident]],
    joints: Sequence[Joint],
    ends: Ends,
) -> tuple[Pair, ...] | None:
    """Every pair, left to right, or None when any channel cannot be planned."""
    line_y = {(e.line, box): e.y for (box, _), found in ends.items() for e in found}
    labels = [line.label_width for line in facts.lines]
    ctx = Context(columns=columns, joints=joints, ends=ends, line_y=line_y, labels=labels)
    pairs = [_pair(c, ctx) for c in range(len(columns))]
    return None if None in pairs else tuple(p for p in pairs if p is not None)


def to_channel(pair: Pair, start: int) -> FrameChannel:
    """The pair's channel, starting at `start`, the left column's right edge."""
    return FrameChannel(
        left=pair.left,
        right=pair.right,
        start=start,
        tab_l=pair.tab_l,
        tab_r=pair.tab_r,
        label=pair.label,
        lines=pair.lines,
        same=pair.same,
        tracks=pair.tracks,
        count=pair.count,
        width=pair.width,
    )


def to_cut(pair: Pair, left_sheet: int) -> FrameCut:
    """The pair as a cut between `left_sheet` and the next sheet."""
    return FrameCut(
        left=pair.left,
        right=pair.left + 1,
        left_sheet=left_sheet,
        lines=pair.lines,
        same=pair.same,
        tab_l=pair.tab_l,
        tab_r=pair.tab_r,
        label=pair.label,
        left_zone=pair.trail,
    )
