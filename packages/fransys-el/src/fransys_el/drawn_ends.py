"""INK_WITHOUT_CONDUCTOR: every wire the drawing joins between ports is a conductor of the model (CONDUCTOR-INK, CP-S2c-2).

Per page, a piece is a run (two port points) or a cluster (three or more joined by dots). A run stands for a conductor between
the classes of its two ends; a cluster, for conductors that join its classes into one set. A class is the ports one symbol node
joins (`Netlist.joins`) or a part's own join (`derive.port_joins`). A piece that holds a bundle lane foot or touches a power
symbol is joined by the arrow or the potential: its ports need only be one net. A marker off a port point joins its piece to
another piece, never the ports of one piece to each other: the conductors among the piece's own classes and those the marker
reaches must join them.
The expected pairs are `far_pins`.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.derive import far_pins, port_designation, port_joins

from .drawn_finding import drawn_finding
from .drawn_graph import Union
from .drawn_netlist import is_marker

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import Page

    from .drawn_netlist import Netlist, PagePart

__all__ = ["ink_without_conductor"]

XY = tuple[int, int]
_RUN = 2  # terminals of a run; a cluster holds more
type _Pairs = set[frozenset[object]]


def _pairs(model: Model, net: Netlist, classes: Union) -> _Pairs:
    """The class pair of each conductor of the model: the ink may join these and no other classes."""
    return {frozenset((classes.find(near.value), classes.find(far.value))) for near, far in far_pins(model, net.ids.values())}


def _run_stands(ends: list[set[object]], pairs: _Pairs) -> bool:
    """True when one conductor, or one symbol node, joins a class of the run's first end to a class of its second."""
    first, second = ends
    return any(a == b or frozenset((a, b)) in pairs for a in first for b in second)


def _stands(ends: list[set[object]], pairs: _Pairs, *, read: bool, reach: set[object]) -> bool:
    """A run needs a conductor; a cluster, conductors among its classes and those a marker reaches; a piece another rule reads, one net."""
    if len(ends) == _RUN and not read and not reach:
        return _run_stands(ends, pairs)
    held = set().union(*ends)
    tree = Union()
    for pair in pairs:
        if read or pair <= held | reach:
            tree.join(*pair)
    return len({tree.find(c) for c in held}) == 1


def _pieces(part: PagePart, terminal: set[XY]) -> list[tuple[set[XY], set[XY]]]:
    """Each piece's terminals and nodes: a wire between two terminals, or the points of a cluster joined away from every terminal."""
    edges = [tuple(edge) for edge in part.graph.edges]
    free = Union()
    for a, b in edges:
        if a not in terminal and b not in terminal:
            free.join(a, b)
    ends: dict[object, set[XY]] = defaultdict(set)
    nodes: dict[object, set[XY]] = defaultdict(set)
    for a, b in edges:
        loose = next((p for p in (a, b) if p not in terminal), None)
        key = frozenset((a, b)) if loose is None else free.find(loose)
        ends[key] |= {p for p in (a, b) if p in terminal}
        nodes[key] |= {a, b}
    return [(ends[key], nodes[key]) for key in nodes]


def _marks(net: Netlist, page: Id[Page], by_point: dict[XY, list[str]]) -> set[XY]:
    """The points of markers off a port point (a marker on a port point joins no piece)."""
    return {(s.x, s.y) for s in net.pages[page].drawing.symbols if is_marker(s)} - by_point.keys()


def _finding(model: Model, net: Netlist, page: Id[Page], ports: list[str]) -> Finding:
    """The finding for the ports a piece of ink joins with no conductor."""
    names = ", ".join(port_designation(model, net.ids[port]) for port in ports)
    return drawn_finding("INK_WITHOUT_CONDUCTOR", (page, *(net.ids[port] for port in ports)), f"the wires join {names} where no conductor runs")


def _page_pieces(net: Netlist, page: Id[Page], classes: Union, pairs: _Pairs, by_root: dict[object, set[object]]) -> list[list[str]]:
    """The ports of each piece of one page whose joined classes no conductor joins."""
    part = net.pages[page]
    by_point: dict[XY, list[str]] = defaultdict(list)
    for port, at in part.ports.items():
        by_point[at].append(port)
    marks = _marks(net, page, by_point)
    read = set(part.powers.values()) | {at for where, at in (*net.lanes.joined, *net.lanes.bare) if where == page}
    found = []
    for terminals, nodes in _pieces(part, set(by_point)):
        if len(terminals) < _RUN:
            continue
        ends = [{classes.find(port) for port in by_point[at]} for at in terminals]
        reach = set().union(*(by_root[net.union.find((page, at))] for at in nodes & marks))
        if not _stands(ends, pairs, read=bool(nodes & read), reach=reach):
            found.append([port for port, at in part.ports.items() if at in terminals])
    return found


def ink_without_conductor(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """One INK_WITHOUT_CONDUCTOR per drawn run or cluster that joins classes no conductor of the model joins (CONDUCTOR-INK)."""
    classes = Union()
    for a, b in (*net.joins, *port_joins(model)):  # a part's own joins (`joins =`) are one pin, as a symbol node is
        classes.join(a.value, b.value)
    pairs = _pairs(model, net, classes)
    by_root: dict[object, set[object]] = defaultdict(set)
    for port, places in net.placed.items():
        for place in places:
            by_root[net.union.find(place)].add(classes.find(port))
    return tuple(_finding(model, net, page, ports) for page in net.pages for ports in _page_pieces(net, page, classes, pairs, by_root))
