"""The strict point graph of one page's wires, read from geometry alone (DRAWN-NETLIST, el-0052).

Two wires join at a shared end point, where an end meets another wire's interior on a junction
dot, and along a collinear overlap. A crossing
or a T with no dot does not join; such a T is listed.
Pure: reads integer points; no model, no Drawing.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

__all__ = ("PageGraph", "page_graph")

XY = tuple[int, int]
Seg = tuple[XY, XY]


@dataclass(frozen=True)
class PageGraph:
    """Edges between consecutive cut points, with the wires along each, and the dotless T's.

    A tee is (point, wire ending there, wire passing through). A joint is a point where two port
    points coincide: one node, with no edge.
    """

    edges: dict[frozenset[XY], frozenset[int]]
    tees: tuple[tuple[XY, int, int], ...]
    joints: frozenset[XY] = frozenset()


def _inside(pt: XY, seg: Seg) -> bool:
    """True when `pt` lies strictly between the ends of the rectilinear `seg`."""
    (x1, y1), (x2, y2) = seg
    x, y = pt
    if x1 == x2 == x:
        return min(y1, y2) < y < max(y1, y2)
    return y1 == y2 == y and min(x1, x2) < x < max(x1, x2)


def _segments(wires: Sequence[Sequence[XY]]) -> list[tuple[Seg, int]]:
    return [((a, b), i) for i, points in enumerate(wires) for a, b in pairwise(points) if a != b]


def _line(seg: Seg) -> tuple[str, int]:
    """The line a rectilinear segment lies on: ('h', y) or ('v', x); a diagonal gets none."""
    (x1, y1), (x2, y2) = seg
    return ("v", x1) if x1 == x2 else ("h", y1) if y1 == y2 else ("d", 0)


@dataclass(frozen=True)
class _Page:
    """What `_cuts` reads of one page: wire ends, junction dots, port points."""

    ends: dict[XY, set[int]]
    dots: Collection[XY]
    anchors: Collection[XY]


def _end_cuts(seg: Seg, own: int, page: _Page) -> tuple[set[XY], list[tuple[XY, int]]]:
    """The cuts other wires' ends make in `seg` on a junction dot, and the dotless T's."""
    cuts: set[XY] = set()
    tees: list[tuple[XY, int]] = []
    for pt, wires in page.ends.items():
        if not (hit := wires - {own}):
            continue
        if _inside(pt, seg) and pt in page.dots:
            cuts.add(pt)
        elif _inside(pt, seg):
            tees.extend((pt, j) for j in hit)
    return cuts, tees


def _cuts(seg: tuple[Seg, int], on_line: Sequence[tuple[Seg, int]], page: _Page) -> tuple[set[XY], list[tuple[XY, int]]]:
    """The points that cut `seg` and its dotless T's."""
    (a, b), own = seg
    cuts, tees = _end_cuts((a, b), own, page)
    cuts |= {a, b}
    for other, j in on_line:
        if j != own:
            cuts.update(p for p in other if _inside(p, (a, b)))
    cuts.update(p for p in page.anchors if p in page.dots and _inside(p, (a, b)))
    return cuts, tees


def _runs(cuts: Collection[XY]) -> list[tuple[XY, XY]]:
    """Each pair of cuts on one segment with no other cut strictly between them."""
    points = list(cuts)
    return [(p, q) for i, p in enumerate(points) for q in points[i + 1 :] if not any(_inside(r, (p, q)) for r in points)]


def page_graph(
    wires: Sequence[Sequence[XY]],
    dots: Collection[XY],
    anchors: Sequence[XY],
) -> PageGraph:
    """The edges of `wires` cut at dots, overlaps and ends; `anchors` are port points, one per port (a repeat is a joint)."""
    segs = _segments(wires)
    by_line = defaultdict(list)
    for item in segs:
        by_line[_line(item[0])].append(item)
    ends: dict[XY, set[int]] = defaultdict(set)
    for i, points in enumerate(wires):
        ends[points[0]].add(i)
        ends[points[-1]].add(i)
    page = _Page(ends, dots, anchors)
    edges: dict[frozenset[XY], set[int]] = defaultdict(set)
    tees: list[tuple[XY, int, int]] = []
    for item in segs:
        cuts, found = _cuts(item, by_line[_line(item[0])], page)
        line = by_line[_line(item[0])]
        tees.extend((pt, j, item[1]) for pt, j in found if not any(k == j and (pt in seg or _inside(pt, seg)) for seg, k in line))
        for a, b in _runs(cuts):
            edges[frozenset((a, b))].add(item[1])
    return PageGraph(
        {e: frozenset(w) for e, w in edges.items()}, tuple(dict.fromkeys(tees)), frozenset(p for p, n in Counter(anchors).items() if n > 1)
    )
