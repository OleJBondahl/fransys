"""DRAWING_SHORTS_NETS, MISSING_JUNCTION_DOT and ROUTE_WRONG_PORT over the drawn netlist.

A piece of the drawings that holds ports of two physical nets is a short, unless a bundle trunk
carries it. A wire that ends on another wire with no dot is a short when the two hold different
nets, else a missing dot. A one-lane wire ends on ports of two nets: a wrong port.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Port

    from .drawn_netlist import Netlist

__all__ = ["short_findings", "wrong_port_findings"]

XY = tuple[int, int]


def _piece_nets(model: Model, net: Netlist) -> dict[object, dict[str, Id[Port]]]:
    """For each piece, its reached ports' nets, each with one port of it."""
    found: dict[object, dict[str, Id[Port]]] = defaultdict(dict)
    for port in net.placed:
        if net.reached(port):
            found[net.root(port)].setdefault(net.net(model, port), net.ids[port])
    return found


def _wire_roots(net: Netlist) -> tuple[dict[tuple[Id[Page], int], object], dict[object, bool]]:
    """The piece of each (page, wire index), and the pieces a bundle trunk runs through."""
    roots: dict[tuple[Id[Page], int], object] = {}
    trunks: dict[object, bool] = {}
    for page, part in net.pages.items():
        for edge, wires in part.graph.edges.items():
            root = net.union.find((page, next(iter(edge))))
            for i in wires:
                roots.setdefault((page, i), root)
                if part.drawing.wires[i].lanes > 1:
                    trunks[root] = True
    return roots, trunks


def _tee_finding(
    page: Id[Page], at: XY, here: dict[str, Id[Port]], there: dict[str, Id[Port]]
) -> Finding:
    nets = {**here, **there}
    where = f"a wire ends on another at {at} with no junction dot"
    if len(nets) > 1:
        return drawn_finding("DRAWING_SHORTS_NETS", (page, *nets.values()), where)
    return drawn_finding("MISSING_JUNCTION_DOT", (page,), where)


def short_findings(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """DRAWING_SHORTS_NETS per piece with two nets; each dotless T is a short or a missing dot."""
    nets = _piece_nets(model, net)
    roots, trunks = _wire_roots(net)
    found = [
        drawn_finding("DRAWING_SHORTS_NETS", tuple(held.values()), f"{len(held)} nets in one piece")
        for root, held in nets.items()
        if len(held) > 1 and root not in trunks
    ]
    for page, part in net.pages.items():
        for at, ending, through in part.graph.tees:
            here = nets.get(roots.get((page, ending)), {})
            there = nets.get(roots.get((page, through)), {})
            found.append(_tee_finding(page, at, here, there))
    return tuple(found)


def _ends_at(part_ports: dict[str, XY], at: XY) -> list[str]:
    return [port for port, point in part_ports.items() if point == at]


def wrong_port_findings(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """ROUTE_WRONG_PORT per one-lane wire whose two ends stand on ports of different nets."""
    found = []
    for part in net.pages.values():
        for wire in part.drawing.wires:
            if wire.lanes > 1:
                continue
            first = {net.net(model, p): p for p in _ends_at(part.ports, wire.points[0])}
            last = {net.net(model, p): p for p in _ends_at(part.ports, wire.points[-1])}
            if first and last and not first.keys() & last.keys():
                ids = [net.ids[next(iter(m.values()))] for m in (first, last)]
                found.append(
                    drawn_finding("ROUTE_WRONG_PORT", ids, f"a wire joins ports of {len(ids)} nets")
                )
    return tuple(found)
