"""The diagram placer's frame (BD5): boxes, line ends, channels, sheets and cuts from the facts.

`build_frame` is pure and deterministic; None means the diagram cannot be placed on its sheet.
"""

from dataclasses import dataclass
lazy from collections.abc import Callable, Mapping, Sequence

from fransys_layout.engines.diagram.arrange import (
    Joint,
    box_width,
    heights,
    orient,
    place_ends,
    raw_ends,
    stack,
)
from fransys_layout.engines.diagram.channels import build_pairs, to_channel, to_cut
from fransys_layout.engines.diagram.columns import assign_columns
from fransys_layout.engines.diagram.frame_values import (
    Frame,
    FrameBox,
    FrameColumn,
    FrameSheet,
)
from fransys_layout.engines.diagram.order import order_columns
from fransys_layout.engines.diagram.sheets import split_sheets
from fransys_layout.geometry import Facing
lazy from fransys_layout.engines.diagram.channels import Pair
lazy from fransys_layout.engines.diagram.frame_values import FrameEnd
lazy from fransys_layout.engines.diagram.values import DiagramFacts, Ident


@dataclass(frozen=True, slots=True)
class Stacked:
    """The columns of a diagram with their joints, box heights and y, and each side's ends."""

    columns: tuple[tuple[Ident, ...], ...]
    joints: tuple[Joint, ...]
    height: Mapping[Ident, int]
    y: Mapping[Ident, int]
    ends: Mapping[tuple[Ident, Facing], tuple[FrameEnd, ...]]


def _stacked(facts: DiagramFacts) -> Stacked | None:
    """Columns, orientation, sizes, stacking and ends (rules 1 to 5), or None if too tall."""
    ids = tuple(b.box for b in facts.boxes)
    joined = [(line.a, line.b) for line in facts.lines]
    columns = order_columns(assign_columns(ids, joined), joined, {b: i for i, b in enumerate(ids)})
    joints = orient(facts, {b: c for c, col in enumerate(columns) for b in col})
    raw = raw_ends(joints)
    height = heights(facts, raw)
    y = stack(columns, height, facts.height)
    if y is None:
        return None
    ends = place_ends(raw, y, facts.text_height)
    return Stacked(columns=columns, joints=joints, height=height, y=y, ends=ends)


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
    pairs = build_pairs(facts, stacked.columns, stacked.joints, stacked.ends)
    by_box = {b.box: b for b in facts.boxes}
    widths = [max(box_width(by_box[b]) for b in col) for col in stacked.columns]
    split = None if pairs is None else split_sheets(widths, pairs, facts.width)
    if pairs is None or split is None:
        return None
    return _sheets(split, pairs, lambda c, x: _column(c, x, widths[c], facts, stacked))
