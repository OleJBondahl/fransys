"""The one home of a declared net that crosses a unit boundary (BOARD-NETS-FINDING, layout-0322).

A declared `Net` joins pins; its ports in items declared in two or more units cross a boundary,
which only a conductor or a mate may do. A net that a conductor or mate already joins into one
physical net is realised and no crossing; the PE net is never one.
"""

from fransys_model.derive.facts.closure import net_of
from fransys_model.derive.facts.net_facts import is_earth_net
from fransys_model.derive.facts.unit_index import unit_index
from fransys_model.derive.facts.units import declared_unit
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import functions, items, nets, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Net
lazy from fransys_model.vocab.core import Function, Port


def _unrealised(model: Model, net: Net) -> bool:
    """Whether the net's ports fall into more than one physical net (not the PE net)."""
    return len({net_of(model, p) for p in net.ports}) > 1 and not is_earth_net(model, net.id)


@digest_cached(DIGEST_CACHE_SIZE)
def net_crossings(model: Model) -> frozendict[Id[Net], tuple[Id[Port], ...]]:
    """Each unrealised declared net with ports in two or more declared units -> the ports to name.

    Those are its ports on a unit's boundary function, else all its ports; a net inside one unit
    or joined by conductors into one physical net is no key.
    """
    all_ports, all_functions, all_items = ports(model), functions(model), items(model)
    boundary = {f for found in unit_index(model).boundary_of.values() for f in found}
    found: dict[Id[Net], tuple[Id[Port], ...]] = {}
    for net in nets(model).values():
        units = {
            declared_unit(all_items[all_functions[all_ports[p].function].item]) for p in net.ports
        }
        if len(units) > 1 and _unrealised(model, net):
            on_boundary = tuple(p for p in net.ports if all_ports[p].function in boundary)
            found[net.id] = on_boundary or net.ports
    return frozendict(found)


def crossing_functions(model: Model) -> frozenset[Id[Function]]:
    """The functions that carry a port of a net that crosses a unit boundary."""
    all_ports = ports(model)
    return frozenset(all_ports[p].function for held in net_crossings(model).values() for p in held)
