"""RAIL_IDENTITY_SHARED over the drawn power symbols (READ-RAILS, R3 second half, R1955).

Two unbonded nets that print one rail identity in one cabinet are one drawn piece the model keeps apart. The identity is the
cabinet's flagged rail, or with none flagged the cabinet plus the printed potential. A missing flag alone raises nothing.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from electrical_symbols import power_symbol_key
from fransys_model.derive import unit_label

from .drawn_finding import drawn_finding
from .drawn_power import symbol_classes

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab import Port

    from .drawn_netlist import Netlist
    from .drawn_power import RailClass

__all__ = ["rail_findings"]

_GROUND = power_symbol_key("ground")
_FUSE = "no unique protective device lies between them to name the second: put a fuse or breaker between them"
_BOND = "bond the nets, or declare each supply in its own unit so each prints its declaring unit's tag"


def rail_findings(net: Netlist, model: Model) -> tuple[Finding, ...]:
    """RAIL_IDENTITY_SHARED per identity (class in one cabinet) that two unbonded nets print; the message names its remedy."""
    nets: dict[RailClass, dict[str, Id[Port]]] = defaultdict(dict)
    for port, joined, inked in symbol_classes(net, model):
        if inked:
            nets[joined].setdefault(net.net(port), net.ids[port])
    return tuple(
        drawn_finding(
            "RAIL_IDENTITY_SHARED",
            tuple(held.values()),
            f"{unit_label(model, joined[0])} prints one rail identity for {len(held)} unbonded nets: {_BOND if joined[1] == _GROUND else _FUSE}",
        )
        for joined, held in nets.items()
        if len(held) > 1
    )
