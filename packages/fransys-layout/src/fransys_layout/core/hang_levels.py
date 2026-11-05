"""The stagger of flags over one symbol's pins: one drawn box further out per overlapping flag (R362).

`text_markers.stagger` places the markers so; the fold counts it from the pins' turned offsets, so
the footprint holds the levels before any x is known (layout-0395 P4a).
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from . import intervals
from .geometry import overlaps, shift, union
from .hangings import KEEP_KIND
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Hashable, Sequence

    from .hangings import Hanging

FLAGS = frozenset(k for k, v in KEEP_KIND.items() if v == "marker" and k != "arrow")


def _raised(box: Box, step: int, level: int) -> Box:
    """The box and the stem to it, standing `level` steps further out from its pin."""
    far = Box(box.x, box.y + (level * step if box.y >= 0 else -level * step), box.w, box.h)
    return union(box, far)


def _side(h: Hanging) -> str | None:
    """Above the pin, below it, or None for a box that straddles it or is no flag."""
    return None if h.kind not in FLAGS else "up" if h.box_rel.y + h.box_rel.h <= 0 else "down" if h.box_rel.y >= 0 else None


def staggered(boxes: Sequence[Box], sides: Sequence[Hashable], keys: Sequence[int], along_x: Sequence[bool]) -> list[tuple[int, int]]:
    """Each box's (level, step): boxes on one side whose drawn boxes overlap or touch, through a chain, stand one step further out each.

    A group ranks by `keys` along the axis `along_x` names and steps by its longest extent across it; a None side joins none (MARKER-STAGGER).
    """
    grown = [Box(b.x - 1, b.y - 1, b.w + 2, b.h + 2) for b in boxes]  # a shared edge draws one line: touching counts
    spans = [(b.x, b.x + b.w) if ax else (b.y, b.y + b.h) for b, ax in zip(boxes, along_x, strict=True)]
    label, out = list(range(len(boxes))), [(0, 0)] * len(boxes)
    for i, j in itertools.combinations(range(len(boxes)), 2):
        if sides[i] is not None and sides[i] == sides[j] and overlaps(grown[i], boxes[j]):
            label = [label[i] if x == label[j] else x for x in label]
    for group in set(label):
        idx = [i for i, x in enumerate(label) if x == group]
        step = max(boxes[i].h if along_x[i] else boxes[i].w for i in idx)  # a level clears the longest drawn box
        for i, lv in zip(idx, intervals.ranked_levels([spans[i] for i in idx], [keys[i] for i in idx]), strict=True):
            out[i] = (lv, step)
    return out


def raised(items: Sequence[tuple[int, Hanging]]) -> list[Box]:
    """Each (pin x, hanging)'s box from its pin; a flag above or below is raised by its level."""
    got = staggered([shift(h.box_rel, x, 0) for x, h in items], [_side(h) for _, h in items], [x for x, _ in items], [True] * len(items))
    return [_raised(h.box_rel, step, lv) for (_, h), (lv, step) in zip(items, got, strict=True)]


def _below(boxes: Sequence[Box]) -> int:
    return max((b.y + b.h for b in boxes if b.y + b.h > 0), default=0)


def extra(items: Sequence[tuple[int, Hanging]]) -> int:
    """The G the stagger adds past the plain flag boxes below the pins: what `raised` puts on a footprint's foot."""
    flags = [(x, h) for x, h in items if h.kind in FLAGS]
    return _below(raised(flags)) - _below([h.box_rel for _, h in flags])
