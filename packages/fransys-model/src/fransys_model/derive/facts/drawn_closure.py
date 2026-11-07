"""The drawn closure: the groups and nets a drawing joins, from `drawn_conductors` (model-0435).

Above `power` in the import order: which conductors a drawing leaves out can depend on a net's kind.
"""

from fransys_model.derive.facts.closure import PhysicalNet, joined_nets, required_groups
from fransys_model.derive.facts.conductor_facts import drawn_conductors
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import item_of_port
from fransys_model.derive.power import is_rail_terminal
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import conductors
lazy from fransys_model.vocab.core import Port

__all__ = ["drawn_groups", "drawn_net_of", "drawn_physical_nets"]


def _all_rail(model: Model, group: tuple[Id[Port], ...]) -> bool:
    """Whether every port of `group` is on a rail terminal, which draws no symbol: the rail's power symbol stands for its pins."""
    return all(is_rail_terminal(model, item_of_port(model, p)) for p in group)


@digest_cached(DIGEST_CACHE_SIZE)
def drawn_groups(model: Model) -> tuple[tuple[Id[Port], ...], ...]:
    """`required_groups` less what a drawing draws no wire for: what a drawing must join.

    Left out: each conductor `drawn_conductors` omits (a bridge, in the terminal table), each group no drawn conductor
    ends in (a mate or a join inside a part), each group wholly on rail terminals (the power symbol stands for them).
    """
    groups, wires, drawn = required_groups(model), tuple(conductors(model)), drawn_conductors(model)
    by_port = build_indexes(model).conductors_by_port
    kept = (*(g for g, c in zip(groups, wires, strict=False) if c in drawn), *groups[len(wires) :])
    return tuple(g for g in kept if any(c in drawn for p in g for c in by_port.get(p, ())) and not _all_rail(model, g))


@digest_cached(DIGEST_CACHE_SIZE)
def drawn_physical_nets(model: Model) -> tuple[PhysicalNet, ...]:
    """The nets a drawing joins: `physical_nets` built from `drawn_groups`, so a bridge joins nothing."""
    return joined_nets(model, drawn_groups(model))


@digest_cached(DIGEST_CACHE_SIZE)
def _drawn_by_port(model: Model) -> frozendict[Id[Port], PhysicalNet]:
    return frozendict({port: net for net in drawn_physical_nets(model) for port in net.ports})


def drawn_net_of(model: Model, port: Id[Port]) -> PhysicalNet | None:
    """The drawn net containing `port` (`net_of` less the bridges), or `None` for a port in no drawn net.

    A bridge joins two nets in `net_of` and none here, so a net a model bundle names by one of its ports
    is this net, not the electrical net `net_of` returns.
    """
    return _drawn_by_port(model).get(port)
