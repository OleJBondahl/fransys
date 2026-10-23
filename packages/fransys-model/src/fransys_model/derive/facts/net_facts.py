"""The one home of `Net.net_class` and `Net.potential` (EL-2 rail nature, model-0294)."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.roles import NET_CLASS_ROLES
from fransys_model.vocab.tables import nets
lazy from fransys_model.vocab.connectivity import Net
lazy from fransys_model.vocab.core import Port
lazy from fransys_model.vocab.enums import NetClass


def net_class_of(model: Model, net: Id[Net]) -> NetClass:
    """The declared `NetClass` of `net`: the one reader of `Net.net_class`."""
    return nets(model)[net].net_class


def net_class_name(model: Model, net: Id[Net]) -> str:
    """The printed text of `net`'s class, as the baseline listing writes it."""
    return net_class_of(model, net).value


def is_earth_net(model: Model, net: Id[Net]) -> bool:
    """Whether `net` is a protective-earth net, read from its class's role row."""
    return NET_CLASS_ROLES[net_class_of(model, net)].earth


def net_potential(model: Model, net: Id[Net]) -> str | None:
    """The potential `net` declares, or `None`: the one reader of `Net.potential`."""
    return nets(model)[net].potential


@digest_cached(DIGEST_CACHE_SIZE)
def _declared(model: Model) -> frozendict[Id[Port], tuple[Id[Net], ...]]:
    found: dict[Id[Port], list[Id[Net]]] = {}
    for net in nets(model).values():
        for port in net.ports:
            found.setdefault(port, []).append(net.id)
    return frozendict({port: tuple(ids) for port, ids in found.items()})


def declared_nets_of(model: Model, port: Id[Port]) -> tuple[Id[Net], ...]:
    """The declared nets that list `port`, in net order; empty when none does."""
    return _declared(model).get(port, ())
