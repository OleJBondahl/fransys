"""CONNECTION_DRAWN_TWICE and DANGLING_WIRE_END over the drawn netlist (DRAWN-NETLIST, el-0052).

A page whose wires close a loop through two ports or more draws a connection twice. A wire end meets a
symbol port, a dot, a marker, another wire or a lane end the netlist joins (el-0086).
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.kernel import UnionFind

from .drawn_finding import drawn_finding
from .drawn_netlist import is_marker

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

    from .drawn_netlist import Netlist, PagePart

__all__ = ["dangling_findings", "loop_findings"]

_MIN_PORTS = 2
XY = tuple[int, int]


def _loops(part: PagePart) -> tuple[UnionFind[XY], set[XY]]:
    """The page's pieces, and those whose edges close a loop."""
    union: UnionFind[XY] = UnionFind()
    closing: list[XY] = []
    for edge in part.graph.edges:
        a, b = tuple(edge)
        if union.find(a) == union.find(b):
            closing.append(a)
        else:
            union.union(a, b)
    return union, {union.find(a) for a in closing}


def loop_findings(net: Netlist) -> tuple[Finding, ...]:
    """CONNECTION_DRAWN_TWICE per page piece that closes a loop and holds two ports or more."""
    found = []
    for page, part in net.pages.items():
        union, loops = _loops(part)
        for root in loops:
            held = [p for p, at in part.ports.items() if union.find(at) == root]
            if len(held) >= _MIN_PORTS:
                ids = [net.ids[p] for p in held[:_MIN_PORTS]]
                found.append(drawn_finding("CONNECTION_DRAWN_TWICE", (page, *ids), "a loop of wires"))
    return tuple(found)


def _met(part: PagePart) -> set[XY]:
    """The points of one page a wire end may stand on: a symbol point, a dotless T."""
    found = set(part.anchors)
    found.update(at for at, _, _ in part.graph.tees)
    return found


def _leaving(part: PagePart) -> dict[XY, dict[int, set[tuple[int, int]]]]:
    """Per node, per wire, the ways (the sign of each axis towards the edge's other node) its edges leave the node in the page graph."""
    found: dict[XY, dict[int, set[tuple[int, int]]]] = defaultdict(lambda: defaultdict(set))
    for edge, ids in part.graph.edges.items():
        for at in edge:
            (x, y), *_ = edge - {at}
            found[at].update({i: found[at][i] | {_sign(at, (x, y))} for i in ids})
    return found


def _sign(a: XY, b: XY) -> tuple[int, int]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))


def _stands(part: PagePart) -> dict[XY, set[str]]:
    """The nets of the reference markers standing at each point of one page."""
    found: dict[XY, set[str]] = defaultdict(set)
    for s in part.drawing.symbols:
        if is_marker(s):
            found[(s.x, s.y)].add(s.net)
    return found


def _on_run(dot: XY, a: XY, b: XY) -> bool:
    """True when `dot` lies on the segment a-b, not at a."""
    (x, y), (ax, ay), (bx, by) = dot, a, b
    return dot != a and (bx - ax) * (y - ay) == (by - ay) * (x - ax) and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by)


def _dotted_run(part: PagePart, at: XY, wire: int, ways: set[tuple[int, int]]) -> bool:
    """True when a junction dot lies on a run from `at` that `wire` shares with another wire: the overlap is joined at the dot."""
    dots = [(s.x, s.y) for s in part.drawing.symbols if s.key == "junction-dot"]
    shared = [(edge, ids) for edge, ids in part.graph.edges.items() if wire in ids and len(ids) > 1]
    for way in ways:
        here = at
        while step := next((q for e, _ in shared for q in e - {here} if here in e and _sign(here, q) == way), None):
            if any(_on_run(d, here, step) for d in dots):
                return True
            here = step
    return False


def dangling_findings(net: Netlist) -> tuple[Finding, ...]:
    """DANGLING_WIRE_END per wire end that meets no port, dot, wire or marker of its own net, and per lane foot whose piece holds no port.

    An overlap along a wire is met only where a dot lies on the run.
    """
    found = []
    for page, part in net.pages.items():
        met, leaving, stands = _met(part) | {at for there, at in net.lanes.joined if there == page}, _leaving(part), _stands(part)
        for i, wire in enumerate(part.drawing.wires):
            found.extend(
                drawn_finding("DANGLING_WIRE_END", (page,), f"wire end at {at[0]}, {at[1]}")
                for at in {wire.points[0], wire.points[-1]}
                if (page, at) in net.lanes.bare
                or (
                    at not in met
                    and wire.net not in stands.get(at, ())
                    and not any(j != i and not ways & leaving.get(at, {}).get(i, set()) for j, ways in leaving.get(at, {}).items())
                    and not _dotted_run(part, at, i, leaving.get(at, {}).get(i, set()))
                )
            )
    return tuple(found)
