"""The strict point graph of one page's wires, read from geometry alone (DRAWN-NETLIST, el-0052).

Two wires join at a shared end point, where an end meets another wire's interior on a junction
dot, and along a collinear overlap. A crossing
or a T with no dot does not join; such a T is listed. Three or more ink directions meeting at a wire end
or vertex with no dot and no pin tip, a dot on a crossing, and a wire over a pin tip are listed too.
Pure: reads integer points; no model, no Drawing.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from collections.abc import Set as AbstractSet

__all__ = ("PageGraph", "page_graph")

XY = tuple[int, int]
Seg = tuple[XY, XY]
Dir = tuple[int, int]
Findings = tuple[tuple[XY, ...], tuple[XY, ...], tuple[tuple[XY, int], ...]]
TEE_DIRECTIONS = 3  # a T has three ink directions
CROSS_DIRECTIONS = 4  # a crossing has four


@dataclass(frozen=True)
class PageGraph:
    """Edges between consecutive cut points, with the wires along each, and the dotless T's.

    A tee is (point, wire ending there, wire passing through). A joint is a point where two port
    points coincide: one node, with no edge. A bare joint is a wire end or vertex where three or more ink
    directions meet with no dot and no pin tip; a dot crossing is a dot where two wires cross through
    each other's interiors; an over-tip is (pin tip, wire) for a wire whose interior passes a pin tip with no dot.
    """

    edges: dict[frozenset[XY], frozenset[int]]
    tees: tuple[tuple[XY, int, int], ...]
    joints: frozenset[XY] = frozenset()
    bare_joints: tuple[XY, ...] = ()
    dot_crossings: tuple[XY, ...] = ()
    over_tips: tuple[tuple[XY, int], ...] = ()


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


def _dir(seg: Seg) -> Dir:
    """The unit step from the first end of `seg` to the second."""
    (x1, y1), (x2, y2) = seg
    return ((x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1))


def _ink(segs: Sequence[tuple[Seg, int]]) -> dict[XY, set[Dir]]:
    """The directions of ink leaving each wire end or vertex."""
    ink: dict[XY, set[Dir]] = defaultdict(set)
    for (a, b), _ in segs:
        ink[a].add(_dir((a, b)))
        ink[b].add(_dir((b, a)))
    return ink


def _both(passes: Sequence[tuple[Dir, int]]) -> set[Dir]:
    """Both directions of every pass: the ink a wire's interior gives its point."""
    return {d for (x, y), _ in passes for d in ((x, y), (-x, -y))}


def _ink_findings(ink: Mapping[XY, AbstractSet[Dir]], over: Mapping[XY, Sequence[tuple[Dir, int]]], page: _Page) -> Findings:
    """The bare joints, the dot crossings and the wires over a pin tip (as `PageGraph` lists them)."""
    dots, tips = set(page.dots), set(page.anchors)
    bare = tuple(p for p, d in ink.items() if p not in dots | tips and len(d | _both(over.get(p, []))) >= TEE_DIRECTIONS)
    crossing = tuple(p for p, hit in over.items() if p in dots and p not in ink and len(_both(hit)) >= CROSS_DIRECTIONS)
    return bare, crossing, tuple(dict.fromkeys((p, j) for p, hit in over.items() if p in tips and p not in dots for _, j in hit))


def _scan(
    item: tuple[Seg, int], line: Sequence[tuple[Seg, int]], page: _Page, watch: Collection[XY]
) -> tuple[list[tuple[XY, XY]], list[tuple[XY, int, int]], list[XY]]:
    """One segment's runs, its dotless T's and the watched points it passes over."""
    cuts, found = _cuts(item, line, page)
    tees = [(pt, j, item[1]) for pt, j in found if not any(k == j and (pt in seg or _inside(pt, seg)) for seg, k in line)]
    return _runs(cuts), tees, [p for p in watch if _inside(p, item[0])]


def _wire_ends(wires: Sequence[Sequence[XY]]) -> dict[XY, set[int]]:
    """The wires that end at each point."""
    ends: dict[XY, set[int]] = defaultdict(set)
    for i, points in enumerate(wires):
        ends[points[0]].add(i)
        ends[points[-1]].add(i)
    return ends


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
    page, ink = _Page(_wire_ends(wires), dots, anchors), _ink(segs)
    watch = {*ink, *dots, *anchors}
    edges: dict[frozenset[XY], set[int]] = defaultdict(set)
    tees: list[tuple[XY, int, int]] = []
    over: dict[XY, list[tuple[Dir, int]]] = defaultdict(list)
    for item in segs:
        runs, found, hit = _scan(item, by_line[_line(item[0])], page, watch)
        tees.extend(found)
        for run in runs:
            edges[frozenset(run)].add(item[1])
        for p in hit:
            over[p].append((_dir(item[0]), item[1]))
    bare, crossing, tips = _ink_findings(ink, over, page)
    joints = frozenset(p for p, n in Counter(anchors).items() if n > 1)
    return PageGraph({e: frozenset(w) for e, w in edges.items()}, tuple(dict.fromkeys(tees)), joints, bare, crossing, tips)
