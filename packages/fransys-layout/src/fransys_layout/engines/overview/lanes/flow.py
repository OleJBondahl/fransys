"""Lanes, the general half: the stage search and the cell stacking on plain values (LO3, LO5, LO6).

The keys are anything hashable. The rules that pick the sources, the flow pairs and the last
boxes are the overview's conventions, and the caller passes them in.
"""

from collections import deque
from typing import TYPE_CHECKING
lazy from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison

    type Cell = tuple[int, int]


def neighbours[K: Hashable](boxes: Iterable[K], pairs: Iterable[tuple[K, K]]) -> dict[K, list[K]]:
    """Each box's neighbours over `pairs`, a pair with equal ends left out."""
    near: dict[K, list[K]] = {b: [] for b in boxes}
    for a, b in pairs:
        if a != b and a in near and b in near:
            near[a].append(b)
            near[b].append(a)
    return near


def _depths[K: Hashable](near: Mapping[K, Sequence[K]], sources: Iterable[K]) -> dict[K, int]:
    """Breadth-first depth from `sources` (depth 0); a box nothing reaches is absent."""
    depth = dict.fromkeys((s for s in sources if s in near), 0)
    queue = deque(depth)
    while queue:
        box = queue.popleft()
        for other in near[box]:
            if other not in depth:
                depth[other] = depth[box] + 1
                queue.append(other)
    return depth


def _relaxed[K: Hashable](near: Mapping[K, Sequence[K]], depth: Mapping[K, int]) -> dict[K, int]:
    """`depth`, plus the shortest depth from a staged box for every box `depth` lacks."""
    found = dict(depth)
    changed = True
    while changed:
        changed = False
        for box, others in near.items():
            via = [found[o] + 1 for o in others if o in found]
            if box not in depth and via and min(via) < found.get(box, min(via) + 1):
                found[box] = min(via)
                changed = True
    return found


def stages[K: Hashable](
    boxes: Sequence[K],
    flow: Iterable[tuple[K, K]],
    lines: Iterable[tuple[K, K]],
    sources: Collection[K],
    last: Collection[K],
) -> dict[K, int]:
    """The stage of every box, counted from 0 over the stages that are used.

    Depth is breadth-first over `flow` from `sources`; a missed box takes it over all `lines`.
    The `last` boxes, a source too, take the deepest stage; a box nothing reaches takes depth 1.
    """
    reached = _relaxed(neighbours(boxes, lines), _depths(neighbours(boxes, flow), sources))
    deepest = max(reached.values(), default=0)
    raw = {**reached, **dict.fromkeys(last, deepest)}
    rank = {
        d: n for n, d in enumerate(sorted({*raw.values(), *(1 for b in boxes if b not in raw)}))
    }
    return {b: rank[raw.get(b, 1)] for b in boxes}


def stack[K: Hashable](
    order: Iterable[K], cell_of: Mapping[K, Cell], key: Mapping[K, SupportsRichComparison]
) -> dict[Cell, list[K]]:
    """The boxes of each cell, sorted by `key`; boxes with equal keys keep the order of `order`."""
    cells: dict[Cell, list[K]] = {}
    for box in sorted(order, key=key.__getitem__):
        cells.setdefault(cell_of[box], []).append(box)
    return cells
