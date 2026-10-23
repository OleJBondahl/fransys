"""CONNECTION_NOT_DRAWN over the drawn netlist: every port of a net lies in one drawn piece.

Pieces join through wires and dots, a bundle trunk, a reference pair and a link group. A net with a
port off the document needs only each of its drawn ports reached, by a wire or a stub (R412).
"""

from typing import TYPE_CHECKING

from fransys_model.derive import connected_ports, physical_nets

from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Port

    from .drawn_netlist import Netlist

__all__ = ["not_drawn_findings"]

_NAMED = 4
_MIN_PORTS = 2


def _verdict(
    net: Netlist, placed: list[Id[Port]], *, off: bool
) -> tuple[list[Id[Port]], int] | None:
    """The unreached ports and the piece count of a net's drawn ports; None when it is drawn."""
    lost = [p for p in placed if not net.reached(p.value)]
    pieces = {net.root(p.value): p for p in placed if net.reached(p.value)}
    if lost or (len(pieces) > 1 and not off):
        return lost, len(pieces)
    return None


def not_drawn_findings(model: Model, net: Netlist, cut: Collection[str]) -> tuple[Finding, ...]:
    """One WARNING per physical net whose drawn ports are not all joined, as R412 counts joins.

    A net with a port in `cut` (a NET_CUT_BY_SET subject) is drawn in several sets: skipped (R414).
    A net whose ports all stand on one symbol is joined by that symbol (a drawn bridge): skipped.
    """
    keep = {p.value for p in connected_ports(model)}
    found = []
    for physical in physical_nets(model):
        ports = [p for p in physical.ports if p.value in keep]
        placed = [p for p in ports if p.value in net.placed]
        if len(ports) < _MIN_PORTS or not placed or any(p.value in cut for p in physical.ports):
            continue
        if len({net.owner.get(p.value) for p in ports}) == 1:
            continue
        if verdict := _verdict(net, placed, off=len(placed) < len(ports)):
            lost, pieces = verdict
            found.append(
                drawn_finding(
                    "CONNECTION_NOT_DRAWN",
                    (*lost, *placed)[:_NAMED],
                    f"{len(lost)} of {len(placed)} drawn port(s) not reached; {pieces} piece(s)",
                )
            )
    return tuple(found)
