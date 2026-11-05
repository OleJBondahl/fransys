"""Fact 5 (PLACEMENT-ENGINE 2.1): the pins that stand a power symbol, with no wire to the rail."""

from fransys_model.derive.connected_ports import boundary_rail_wires
from fransys_model.derive.facts.closure import physical_nets
from fransys_model.derive.facts.conductor_facts import conductor_ends
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab import Port, PowerKind

from .lookups import item_of_port
from .power import is_rail_terminal, port_power_kind

__all__ = ["stands"]


@digest_cached(DIGEST_CACHE_SIZE)
def stands(model: Model) -> frozendict[Id[Port], PowerKind]:
    """Each port of a rail net, mapped to the net's `PowerKind`; a wire or a signal is absent.

    Built on `power.port_power_kind`, the one rail rule, so a two-port net is never a stand. A port
    of a rail terminal is absent: the terminal is not drawn (POWER-NET). So is a port that ends a
    boundary rail wire: the wire is drawn to the terminal's replica, not also to a symbol (G08-POWER).
    """
    wired = frozenset(p for w in boundary_rail_wires(model) for p in conductor_ends(model, w))
    kinds: dict[Id[Port], PowerKind] = {}
    for physical in physical_nets(model):
        for port in physical.ports:
            kind = port_power_kind(model, port)
            if kind is not PowerKind.NONE and port not in wired and not is_rail_terminal(model, item_of_port(model, port)):
                kinds[port] = kind
    return frozendict(kinds)
