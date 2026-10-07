"""The diagram frame's boxes (BD5): lines oriented, boxes sized and stacked, ends ordered.

A line leaves the left box's east edge and enters the right box's west edge; a same-column line
leaves both east edges. Ends sit `attach_pitch` apart, ordered by the far box's top then line.
"""

from collections import Counter
from dataclasses import dataclass
lazy from collections.abc import Mapping

from fransys_layout.engines.diagram.frame_values import FrameEnd
from fransys_layout.engines.diagram.sizes import (
    PAGE_PAD,
    ROW_GAP,
    TEXT_LEAD,
    TEXT_PAD,
    attach_pitch,
)
from fransys_layout.geometry import Facing, snap_up
lazy from fransys_layout.engines.diagram.values import BoxFacts, DiagramFacts, Ident


@dataclass(frozen=True, slots=True)
class Joint:
    """Line `line` with its `left` and `right` boxes (a, b when same column) and their tabs."""

    line: int
    left: Ident
    right: Ident
    left_tab: int | None
    right_tab: int | None
    same: bool


@dataclass(frozen=True, slots=True)
class RawEnd:
    """One end before it has a y: its line, box, the far box, the side and the tab text width."""

    line: int
    box: Ident
    far: Ident
    side: Facing
    tab: int | None


def orient(facts: DiagramFacts, column_of: Mapping[Ident, int]) -> tuple[Joint, ...]:
    """Each line as a joint: the box in the lower column is left, ties a."""
    joints = []
    for i, line in enumerate(facts.lines):
        flip = column_of[line.b] < column_of[line.a]
        a, b, ta, tb = line.a, line.b, line.tab_a, line.tab_b
        left, right, lt, rt = (b, a, tb, ta) if flip else (a, b, ta, tb)
        same = column_of[a] == column_of[b]
        joints.append(Joint(line=i, left=left, right=right, left_tab=lt, right_tab=rt, same=same))
    return tuple(joints)


def raw_ends(joints: tuple[Joint, ...]) -> tuple[RawEnd, ...]:
    """Both ends of every joint, in line order."""
    ends = []
    for j in joints:
        right_side = Facing.E if j.same else Facing.W
        ends.append(RawEnd(line=j.line, box=j.left, far=j.right, side=Facing.E, tab=j.left_tab))
        ends.append(RawEnd(line=j.line, box=j.right, far=j.left, side=right_side, tab=j.right_tab))
    return tuple(ends)


def box_width(box: BoxFacts) -> int:
    """The box's own width on the grid: its widest text and the padding either side."""
    return snap_up(max(box.text_widths, default=0) + 2 * TEXT_PAD)


def box_height(box: BoxFacts, ends: int, text_height: int) -> int:
    """The height that fits the texts and `ends` ends (plus one pitch) on its busier side."""
    n = len(box.text_widths)
    text = n * text_height + max(n - 1, 0) * TEXT_LEAD + 2 * TEXT_PAD
    return snap_up(max(text, (ends + 1) * attach_pitch(text_height)))


def heights(facts: DiagramFacts, ends: tuple[RawEnd, ...]) -> dict[Ident, int]:
    """Each box's height from the busier of its two sides."""
    count = Counter((e.box, e.side) for e in ends)
    return {
        b.box: box_height(b, max(count[b.box, Facing.E], count[b.box, Facing.W]), facts.text_height)
        for b in facts.boxes
    }


def stack(
    columns: tuple[tuple[Ident, ...], ...], height: Mapping[Ident, int], sheet_height: int
) -> dict[Ident, int] | None:
    """Each box's y, columns centred on the tallest; None when the tallest does not fit."""
    totals = [sum(height[b] for b in col) + ROW_GAP * (len(col) - 1) for col in columns]
    tallest = max(totals, default=0)
    if tallest + 2 * PAGE_PAD > sheet_height:
        return None
    y: dict[Ident, int] = {}
    for col, total in zip(columns, totals, strict=True):
        cursor = PAGE_PAD + snap_up((tallest - total) // 2)
        for box in col:
            y[box] = cursor
            cursor += height[box] + ROW_GAP
    return y


def place_ends(
    ends: tuple[RawEnd, ...], y: Mapping[Ident, int], text_height: int
) -> dict[tuple[Ident, Facing], tuple[FrameEnd, ...]]:
    """The ends of each box side, ordered by the far box's top then line, with their y."""
    groups: dict[tuple[Ident, Facing], list[RawEnd]] = {}
    for e in ends:
        groups.setdefault((e.box, e.side), []).append(e)
    pitch = attach_pitch(text_height)
    return {
        (box, side): tuple(
            FrameEnd(line=e.line, side=side, y=y[box] + pitch * (k + 1), tab=e.tab)
            for k, e in enumerate(sorted(group, key=lambda e: (y[e.far], e.line)))
        )
        for (box, side), group in groups.items()
    }
