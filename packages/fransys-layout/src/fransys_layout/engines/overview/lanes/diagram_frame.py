"""The diagram placer's frame: boxes, line ends, channels, sheets and cuts from the facts.

`build_frame` is pure and deterministic; None means the diagram cannot be placed on its sheet.
"""

from dataclasses import dataclass, replace
lazy from collections.abc import Callable, Mapping, Sequence

from fransys_layout.engines.overview.columns import assign_columns, column_columns
from fransys_layout.engines.overview.lanes.arrange import (
    Joint,
    box_width,
    heights,
    orient,
    place_ends,
    raw_ends,
    stack,
)
from fransys_layout.engines.overview.lanes.diagram_channels import build_pairs, to_channel, to_cut
from fransys_layout.engines.overview.lanes.frame_values import (
    Frame,
    FrameBox,
    FrameColumn,
    FrameSheet,
)
from fransys_layout.engines.overview.order import order_columns
from fransys_layout.engines.overview.sheets import split_sheets
from fransys_layout.engines.overview.sizes import ROW_GAP
from fransys_layout.geometry import PAGE_PAD, Facing
lazy from fransys_layout.engines.overview.lanes.arrange import RawEnd
lazy from fransys_layout.engines.overview.lanes.diagram_channels import Pair
lazy from fransys_layout.engines.overview.lanes.frame_values import FrameEnd
lazy from fransys_layout.engines.overview.sheet_values import DiagramFacts, Ident


@dataclass(frozen=True, slots=True)
class Stacked:
    """The columns of a diagram with their joints, box heights and y, and each side's ends."""

    columns: tuple[tuple[Ident, ...], ...]
    breaks: frozenset[int]
    joints: tuple[Joint, ...]
    height: Mapping[Ident, int]
    y: Mapping[Ident, int]
    ends: Mapping[tuple[Ident, Facing], tuple[FrameEnd, ...]]


def _oriented(facts: DiagramFacts, columns: tuple[tuple[Ident, ...], ...]) -> tuple[tuple[Joint, ...], tuple[RawEnd, ...], dict[Ident, int]]:
    joints = orient(facts, {b: c for c, col in enumerate(columns) for b in col})
    raw = raw_ends(joints)
    return joints, raw, heights(facts, raw)


def _fit(columns: tuple[tuple[Ident, ...], ...], height: Mapping[Ident, int], room: int) -> tuple[tuple[tuple[Ident, ...], ...], frozenset[int]]:
    """A column taller than `room` is cut between boxes; each rest starts a sheet. Returns the columns and those starts."""
    out: list[tuple[Ident, ...]] = []
    breaks: set[int] = set()
    for col in columns:
        piece: list[Ident] = []
        used = 0
        for box in col:
            if piece and used + ROW_GAP + height[box] > room:
                out.append(tuple(piece))
                breaks.add(len(out))
                piece, used = [], -ROW_GAP
            piece.append(box)
            used += ROW_GAP + height[box]
        out.append(tuple(piece))
    return tuple(out), frozenset(breaks)


def _columns_heights(
    facts: DiagramFacts,
) -> tuple[tuple[tuple[Ident, ...], ...], frozenset[int], tuple[Joint, ...], tuple[RawEnd, ...], dict[Ident, int]]:
    """The columns, the sheet-starting ones, joints, raw ends and box heights of a diagram (rules 1 to 4)."""
    ids = tuple(b.box for b in facts.boxes)
    joined = [(line.a, line.b) for line in facts.lines]
    stand = column_columns(ids, joined, facts.column, facts.left) if facts.column else assign_columns(ids, joined)
    columns = order_columns(stand, joined, {b: i for i, b in enumerate(ids)}, facts.column)
    cut, breaks = _fit(columns, _oriented(facts, columns)[2], facts.height - 2 * PAGE_PAD)
    return cut, breaks, *_oriented(facts, cut)


def _jumps(joints: Sequence[Joint], columns: Sequence[Sequence[Ident]], breaks: frozenset[int]) -> tuple[int, ...]:
    """The lines that skip a column across a sheet start: each ends in a reference marker on both sheets."""
    where = {b: c for c, col in enumerate(columns) for b in col}
    return tuple(j.line for j in joints if where[j.right] - where[j.left] > 1 and any(where[j.left] < f <= where[j.right] for f in breaks))


def _stacked(facts: DiagramFacts) -> Stacked | None:
    """Columns, orientation, sizes, stacking and ends (rules 1 to 5), or None if too tall."""
    columns, breaks, joints, raw, height = _columns_heights(facts)
    y = stack(columns, height, facts.height)
    if y is None:
        return None
    ends = place_ends(raw, y, height, facts.text_height, nest=facts.nest_same)
    return Stacked(columns=columns, breaks=breaks, joints=joints, height=height, y=y, ends=ends)


def _column(c: int, x: int, width: int, facts: DiagramFacts, stacked: Stacked) -> FrameColumn:
    """Column `c` at `x`: each box at its y with its east then west ends."""
    dashed = {b.box: b.dashed for b in facts.boxes}
    ends = stacked.ends
    boxes = tuple(
        FrameBox(
            box=b,
            dashed=dashed[b],
            x=x,
            y=stacked.y[b],
            width=width,
            height=stacked.height[b],
            ends=(*ends.get((b, Facing.E), ()), *ends.get((b, Facing.W), ())),
        )
        for b in stacked.columns[c]
    )
    return FrameColumn(index=c, x=x, width=width, boxes=boxes)


def _sheets(
    split: Sequence[Sequence[tuple[int, int]]],
    pairs: Sequence[Pair],
    column: Callable[[int, int], FrameColumn],
) -> Frame:
    """The sheets of `split` with the channels inside them and the cuts between them."""
    sheets, cuts = [], []
    for number, sheet in enumerate(split, start=1):
        cols = tuple(column(c, x) for c, x in sheet)
        channels = [to_channel(pairs[c.index], c.x + c.width) for c in cols[:-1]]
        end = cols[-1]
        if end.index == len(pairs) - 1:
            channels.append(to_channel(pairs[end.index], end.x + end.width))
        else:
            cuts.append(to_cut(pairs[end.index], number))
        sheets.append(FrameSheet(number=number, columns=cols, channels=tuple(channels)))
    return Frame(sheets=tuple(sheets), cuts=tuple(cuts))


def build_frame(facts: DiagramFacts) -> Frame | None:
    """The frame of one diagram, or None when it cannot be placed (too tall, too wide, no plan)."""
    stacked = _stacked(facts)
    if stacked is None:
        return None
    jumps = _jumps(stacked.joints, stacked.columns, stacked.breaks)
    pairs = build_pairs(facts, stacked.columns, stacked.joints, stacked.ends, jumps)
    by_box = {b.box: b for b in facts.boxes}
    widths = [max(box_width(by_box[b]) for b in col) for col in stacked.columns]
    split = None if pairs is None else split_sheets(widths, pairs, facts.width, stacked.breaks)
    if pairs is None or split is None:
        return None
    return replace(_sheets(split, pairs, lambda c, x: _column(c, x, widths[c], facts, stacked)), jumps=jumps)
