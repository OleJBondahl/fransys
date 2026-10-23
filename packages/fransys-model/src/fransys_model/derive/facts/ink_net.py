"""The one home of the net a port's drawn ink carries (BOARD-NETS-FINDING A7)."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import nets
lazy from fransys_model.vocab.core import Port

from .closure import PhysicalNet, net_of, port_groups


@digest_cached(DIGEST_CACHE_SIZE)
def _ink_nets(model: Model) -> frozendict[Id[Port], PhysicalNet]:
    """Each pin of a declared net of two or more pins, to the net joining those pins' nets."""
    groups = [
        [q for p in net.ports for q in (net_of(model, p) or PhysicalNet(ports=(p,))).ports]
        for net in nets(model).values()
        if len(net.ports) > 1
    ]
    return frozendict({port: group for group in port_groups(groups) for port in group.ports})


def ink_net(model: Model, port: Id[Port]) -> PhysicalNet | None:
    """The net `port`'s ink carries: its physical net, joined with its declared net's pins.

    A net with no conductor is one singleton per pin; the declared net still makes them one net.
    """
    return _ink_nets(model).get(port) or net_of(model, port)
