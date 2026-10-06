"""The potentials one physical net carries: the one read, shared by a validator and `power_kind`."""

from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached

from .closure import net_of
from .enums import NetClass
from .tables import nets

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

    from .closure import PhysicalNet
    from .connectivity import Net
    from .core import Port


@digest_cached(DIGEST_CACHE_SIZE)
def _carried(model: Model) -> frozendict[Id[Port], frozendict[str, tuple[Id[Net], ...]]]:
    """Each physical net's potentials with their declared nets, the net keyed by its first port."""
    found: dict[Id[Port], dict[str, set[Id[Net]]]] = {}
    for net in nets(model).values():
        if net.potential is None:
            continue
        for port in net.ports:
            physical = net_of(model, port)
            if physical is not None:
                by_name = found.setdefault(physical.ports[0], {})
                by_name.setdefault(net.potential, set()).add(net.id)
    return frozendict(
        {
            first: frozendict({name: tuple(sorted(ids)) for name, ids in by_name.items()})
            for first, by_name in found.items()
        }
    )


def physical_potentials(
    model: Model, physical: PhysicalNet
) -> frozendict[str, tuple[Id[Net], ...]]:
    """The potentials the declared nets on `physical` carry, each with its net ids; cached."""
    return frozendict(_carried(model).get(physical.ports[0], {}))


def pe_firsts(model: Model) -> frozenset[Id[Port]]:
    """The first port of each physical net holding a port of a `NetClass.PE` net."""
    physical = (
        net_of(model, port)
        for net in nets(model).values()
        if net.net_class is NetClass.PE
        for port in net.ports
    )
    return frozenset(net.ports[0] for net in physical if net is not None)
