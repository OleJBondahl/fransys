"""CONNECTION_DRAWN_TWICE and MARKER_UNPAIRED over the drawn netlist (DRAWN-NETLIST, el-0052).

A page whose wires close a loop through two ports or more draws a connection twice. A marker that
pairs with another (not an off stub) needs that marker drawn on some page.
"""

from typing import TYPE_CHECKING

from fransys_model.layout import StarKind

from .drawn_finding import drawn_finding
from .drawn_graph import Union
from .drawn_netlist import is_marker

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

    from .drawn_netlist import Netlist, PagePart

__all__ = ["loop_findings", "unpaired_findings"]

_MIN_PORTS = 2


def _loops(part: PagePart) -> tuple[Union, dict[object, bool]]:
    """The page's pieces, and those whose edges close a loop with whether a bundle runs through."""
    union, closing = Union(), []
    for edge in part.graph.edges:
        a, b = tuple(edge)
        if union.find(a) == union.find(b):
            closing.append(a)
        else:
            union.join(a, b)
    bundled = {
        union.find(next(iter(edge)))
        for edge, ws in part.graph.edges.items()
        if any(part.drawing.wires[i].lanes > 1 for i in ws)
    }
    return union, {union.find(a): union.find(a) in bundled for a in closing}


def loop_findings(net: Netlist) -> tuple[Finding, ...]:
    """CONNECTION_DRAWN_TWICE per page piece that closes a loop and holds two ports or more."""
    found = []
    for page, part in net.pages.items():
        union, loops = _loops(part)
        for root, bundled in loops.items():
            held = [p for p, at in part.ports.items() if union.find(at) == root]
            if len(held) >= _MIN_PORTS and not bundled:
                ids = [net.ids[p] for p in held[:_MIN_PORTS]]
                found.append(
                    drawn_finding("CONNECTION_DRAWN_TWICE", (page, *ids), "a loop of wires")
                )
    return tuple(found)


def unpaired_findings(net: Netlist) -> tuple[Finding, ...]:
    """MARKER_UNPAIRED per drawn marker whose partner marker is drawn on no page."""
    found = []
    for page, part in net.pages.items():
        for symbol in part.drawing.symbols:
            record = net.records.get(symbol.id.rpartition(":")[2]) if is_marker(symbol) else None
            if (
                record
                and record.star is not StarKind.OFF
                and record.partner.value not in net.markers
            ):
                found.append(
                    drawn_finding("MARKER_UNPAIRED", (page,), f"marker at {symbol.x}, {symbol.y}")
                )
    return tuple(found)
