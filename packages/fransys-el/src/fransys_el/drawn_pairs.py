"""CONNECTION_DRAWN_TWICE, MARKER_UNPAIRED and DANGLING_WIRE_END over the drawn netlist (DRAWN-NETLIST, el-0052).

A page whose wires close a loop through two ports or more draws a connection twice. A marker that
pairs with another (not an off stub) needs that marker drawn on some page. A wire end meets a
symbol port, a dot, a marker, another wire or a lane end the netlist joins (el-0086).
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.layout import StarKind

from .drawn_finding import drawn_finding
from .drawn_graph import Union
from .drawn_netlist import is_marker, lane_chain

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Finding
    from fransys_model.layout import LinkMarker

    from .drawn_netlist import Netlist, PagePart

__all__ = ["dangling_findings", "loop_findings", "unpaired_findings"]

_MIN_PORTS = 2
XY = tuple[int, int]


def _loops(part: PagePart) -> tuple[Union, set[object]]:
    """The page's pieces, and those whose edges close a loop."""
    union, closing = Union(), []
    for edge in part.graph.edges:
        a, b = tuple(edge)
        if union.find(a) == union.find(b):
            closing.append(a)
        else:
            union.join(a, b)
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


def unpaired_findings(net: Netlist) -> tuple[Finding, ...]:
    """MARKER_UNPAIRED per drawn marker whose partner marker is drawn on no page."""
    found = []
    for page, part in net.pages.items():
        for symbol in part.drawing.symbols:
            record = net.records.get(symbol.id.rpartition(":")[2]) if is_marker(symbol) else None
            if record and record.star is not StarKind.OFF and record.partner.value not in net.markers:
                found.append(drawn_finding("MARKER_UNPAIRED", (page,), f"marker at {symbol.x}, {symbol.y}"))
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


def _stood_on(here: dict[int, set[tuple[int, int]]], wire: int) -> bool:
    """True when another wire leaves the node and none runs the way `wire` does: a collinear overlap past the end is no meeting."""
    return any(i != wire and not ways & here.get(wire, set()) for i, ways in here.items())


def _sign(a: XY, b: XY) -> tuple[int, int]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))


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


def _partner_nets(net: Netlist, record: LinkMarker) -> set[str] | None:
    """The nets of the lane chain the pair marker's partner ends, on the partner's page; None when the partner is not drawn."""
    node = net.markers.get(record.partner.value)
    if node is None:
        return None
    part = net.pages[node[0]]
    chain = lane_chain(part, node[1][1], net.pitch)
    return {w.net for w in part.drawing.wires if w.net and w.style == "trunk" and w.points[0][1] in chain}


def _arrows(net: Netlist, page: object, part: PagePart) -> list[tuple[XY, Callable[[object, str], bool]]]:
    """Each marker of the page that a trunk lane ends on: its point, and what a lane (its piece, its net) must hold to stand under it.

    An off stub: the lane's piece holds a port its pairs list. A pair marker: the lane's net runs in the partner's lane chain (R1667).
    """
    ends = {at for w in part.drawing.wires if w.net and w.style == "trunk" for at in (w.points[0], w.points[-1])}
    found = []
    for key, record in net.records.items():
        node = net.markers.get(key)
        if node is None or node[0] != page or node[1] not in ends:
            continue
        if record.star is StarKind.OFF:
            listed = {net.union.find((page, part.ports[x.port.value])) for x in record.pairs if x.port.value in part.ports}
            found.append((node[1], lambda piece, _net, listed=listed: piece in listed))
        else:
            nets = _partner_nets(net, record)
            found.append((node[1], lambda _piece, lane_net, nets=nets: nets is not None and lane_net in nets))
    return found


def _lane_met(net: Netlist, page: object, part: PagePart) -> set[XY]:
    """The ends of a bundle's lanes the marker's one arrow stands for (R1352, R1666, R1667).

    A trunk lane end is met when it lies in the lane chain of a lead lane that ends on a marker, within one pitch of the lead's end,
    and the arrow's condition holds: an off stub's pairs list a port the lane's piece holds; a pair marker's partner chain carries the lane's net.
    """
    found: set[XY] = set()
    lanes = [w for w in part.drawing.wires if w.net and w.style == "trunk"]
    for lead, holds in _arrows(net, page, part):
        chain = lane_chain(part, lead[1], net.pitch)
        for wire in lanes:
            first, last = wire.points[0], wire.points[-1]
            end = first if abs(first[0] - lead[0]) <= abs(last[0] - lead[0]) else last
            if wire.points[0][1] in chain and abs(end[0] - lead[0]) <= net.pitch and holds(net.union.find((page, wire.points[0])), wire.net):
                found.add(end)
    return found


def dangling_findings(net: Netlist) -> tuple[Finding, ...]:
    """DANGLING_WIRE_END per wire end that meets no port, dot, marker or wire; an overlap along a wire is met only where a dot lies on the run."""
    found = []
    for page, part in net.pages.items():
        met, leaving = _met(part) | _lane_met(net, page, part), _leaving(part)
        for i, wire in enumerate(part.drawing.wires):
            found.extend(
                drawn_finding("DANGLING_WIRE_END", (page,), f"wire end at {at[0]}, {at[1]}")
                for at in {wire.points[0], wire.points[-1]}
                if at not in met and not _stood_on(leaving.get(at, {}), i) and not _dotted_run(part, at, i, leaving.get(at, {}).get(i, set()))
            )
    return tuple(found)
