"""The diagram frame's channels: the room between two adjacent columns, tracks and cuts.

A pair is column `c` and `c + 1` (None after the last). Its channel is drawn when both share a
sheet; when a sheet ends between them it is a cut, and the pair's `trail` and `lead` zones apply.
"""

from dataclasses import dataclass, replace
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.overview.lanes.frame_values import FrameChannel, FrameCut, FrameTrack
from fransys_layout.engines.overview.lanes.plan_channel import plan_channel
from fransys_layout.engines.overview.sizes import (
    MARKER_W,
    TRACK_PITCH,
    label_room,
    tab_reach,
)
from fransys_layout.geometry import PAGE_PAD, Facing
lazy from fransys_layout.engines.overview.lanes.arrange import Joint
lazy from fransys_layout.engines.overview.lanes.frame_values import FrameEnd
lazy from fransys_layout.engines.overview.sheet_values import DiagramFacts, Ident

type Ends = Mapping[tuple[Ident, Facing], Sequence[FrameEnd]]


@dataclass(frozen=True, slots=True)
class Pair:
    """Columns `left` and `left + 1`: lines between, same-column lines of `left`, the rooms."""

    left: int
    right: int | None
    lines: tuple[int, ...]
    same: tuple[int, ...]
    same_tracks: tuple[int, ...]
    tab_l: int
    tab_r: int
    label: int
    cut_label: int
    tracks: tuple[FrameTrack, ...]
    count: int
    same_first: bool = False

    @property
    def width(self) -> int:
        """The channel's width (rule 6): two page pads when nothing is routed in it."""
        if not self.lines and not self.same:
            return 2 * PAGE_PAD
        last = max([self.count + max(self.same_tracks, default=0), *(t.track for t in self.tracks)])
        tracks = (last + 1) * TRACK_PITCH
        return self.tab_l + self.label + tracks + (self.label + self.tab_r if self.right else 0)

    @property
    def trail(self) -> int:
        """The room right of the left column: its channel's width, or a cut's stub zone."""
        if self.right is None:
            return self.width
        if not self.lines and not self.same:
            return PAGE_PAD
        return self.tab_l + self.label + max(self.same_tracks, default=0) * TRACK_PITCH + MARKER_W

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
        [(j.line, line_y[j.line, j.left], line_y[j.line, j.right]) for j in between],
        spans=True,
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
    share: bool
    nest: bool = False


def _span(line_y: Mapping[tuple[int, Ident], int], j: Joint) -> tuple[int, int]:
    """The y span of a same-column line, top first."""
    a, b = line_y[j.line, j.left], line_y[j.line, j.right]
    return (min(a, b), max(a, b))


def _nested_tracks(spans: Sequence[tuple[int, int]], *, share: bool) -> tuple[int, ...]:
    """Tracks by span length, shortest first, so a span lies outside every span it contains.

    Without `share` each span has its own track. With it a span takes the lowest track outside
    what it contains and free of every overlapping span already placed.
    """
    order = sorted(range(len(spans)), key=lambda k: (spans[k][1] - spans[k][0], spans[k]))
    found = [0] * len(spans)
    for n, k in enumerate(order):
        a, b = spans[k]
        before = order[:n]
        inside = [found[o] for o in before if a <= spans[o][0] and spans[o][1] <= b]
        busy = {found[o] for o in before if spans[o][0] <= b and a <= spans[o][1]}
        track = n + 1 if not share else max(inside, default=0) + 1
        while share and track in busy:
            track += 1
        found[k] = track
    return tuple(found)


def same_tracks(
    spans: Sequence[tuple[int, int]], *, share: bool, nest: bool = False
) -> tuple[int, ...]:
    """Each span's track, 1 nearest the column: its own, or with `share` the fewest that fit.

    Spans that overlap (or touch) never share a track; greedy by start is optimal for intervals.
    With `nest` a span outside another's track holds the outer track (`_nested_tracks`).
    """
    if nest:
        return _nested_tracks(spans, share=share)
    if not share:
        return tuple(range(1, len(spans) + 1))
    free: list[int] = []  # the end of the last span on each track
    found = [0] * len(spans)
    for k in sorted(range(len(spans)), key=lambda k: spans[k]):
        track = next((t for t, end in enumerate(free) if end < spans[k][0]), len(free))
        free[track : track + 1] = [spans[k][1]]
        found[k] = track + 1
    return tuple(found)


def _after(tracks: Sequence[FrameTrack], skip: int) -> tuple[FrameTrack, ...]:
    """The tracks moved `skip` tracks outward, past the same-column lines' tracks."""
    return tuple(replace(t, track=t.track + skip) for t in tracks)


def _struck(r: FrameTrack, runs: Sequence[FrameTrack], ys: frozenset[int], first: int) -> bool:
    """Whether run `r`'s stretch into the next column lies along a line's stretch from the left.

    That is a same-column stub (it reaches past every track below `first`) or another line's
    left stretch at `r`'s end y that reaches past `r`'s track.
    """
    if r.track < first and r.right_y in ys:
        return True
    return any(o.line != r.line and o.left_y == r.right_y and o.track > r.track for o in runs)


def _apart(runs: Sequence[FrameTrack], ys: frozenset[int], first: int) -> tuple[FrameTrack, ...]:
    """The runs, each that a stretch from the left lies along moved to its own track from `first`.

    Moving it beyond the stretch's track makes the two meet only where they cross (LEGACY-B3 L12).
    """
    out, free = list(runs), first
    for _ in runs:
        hit = next((i for i, r in enumerate(out) if _struck(r, out, ys, first)), None)
        if hit is None:
            break
        r = out[hit]
        out[hit] = FrameTrack(
            line=r.line, part=r.part, left_y=r.left_y, right_y=r.right_y, track=free
        )
        free += 1
    return tuple(out)


def _plan(
    between: Sequence[Joint], same: Sequence[Joint], ctx: Context
) -> tuple[tuple[FrameTrack, ...], int, tuple[int, ...]] | None:
    """The between tracks, their count and the same-column tracks of a pair, or None."""
    planned = _tracks(between, ctx.line_y)
    if planned is None:
        return None
    runs, count = planned
    spans = [_span(ctx.line_y, j) for j in same]
    own = same_tracks(spans, share=ctx.share, nest=ctx.nest)
    if ctx.nest:
        runs = _after(runs, max(own, default=0))
    ys = frozenset(y for span in spans for y in span)
    return _apart(runs, ys, count + max(own, default=0) + 1), count, own


def _pair(c: int, ctx: Context) -> Pair | None:
    """The pair of column `c` and the next, or None when its channel cannot be planned."""
    columns = ctx.columns
    where = {b: i for i, col in enumerate(columns) for b in col}
    between = [j for j in ctx.joints if not j.same and where[j.left] == c]
    same = [j for j in ctx.joints if j.same and where[j.left] == c]
    planned = _plan(between, same, ctx)
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
        same_tracks=planned[2],
        tab_l=tab_room(columns[c], ctx.ends, Facing.E),
        tab_r=tab_r,
        label=label_room(widest),
        cut_label=label_room(wide),
        tracks=planned[0],
        count=planned[1],
        same_first=ctx.nest,
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
    ctx = Context(
        columns=columns,
        joints=joints,
        ends=ends,
        line_y=line_y,
        labels=labels,
        share=facts.share_tracks,
        nest=facts.nest_same,
    )
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
        same_tracks=pair.same_tracks,
        tracks=pair.tracks,
        count=pair.count,
        width=pair.width,
        same_first=pair.same_first,
    )


def to_cut(pair: Pair, left_sheet: int) -> FrameCut:
    """The pair as a cut between `left_sheet` and the next sheet."""
    return FrameCut(
        left=pair.left,
        right=pair.left + 1,
        left_sheet=left_sheet,
        lines=pair.lines,
        same=pair.same,
        same_tracks=pair.same_tracks,
        tab_l=pair.tab_l,
        tab_r=pair.tab_r,
        label=pair.label,
        left_zone=pair.trail,
    )
