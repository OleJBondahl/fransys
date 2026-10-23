"""The nets whose potential no supply declares and no earth rail carries (model-0085)."""

from fransys_model.derive.facts.net_facts import net_potential
from fransys_model.derive.facts.rail_reach import earth_potentials
from fransys_model.vocab.tables import nets, supply_of_potential, supply_systems
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Net


def potentials_without_supply(model: Model) -> tuple[tuple[Id[Net], str], ...]:
    """Each net, in net order, with its potential, when that is no supply's rail and no earth."""
    earth = earth_potentials(model)
    found = []
    for net in nets(model).values():
        potential = net_potential(model, net.id)
        if potential is None or potential in earth or supply_of_potential(model, potential):
            continue
        found.append((net.id, potential))
    return tuple(found)


def declared_rails(model: Model) -> tuple[str, ...]:
    """The rail potentials some supply declares, sorted."""
    return tuple(sorted({name for s in supply_systems(model).values() for name in s.rails}))
