"""The rails a function reaches and the voltage across it: one home for what the checks share.

The two rating validators (`RATING_VOLTAGE_BELOW_CIRCUIT`, `RATING_CURRENT_BELOW_BRANCH`) and the
RATINGS-3 fault and draw checks all read the same rails, kinds, supplies and stands from here.
"""

import dataclasses
from fractions import Fraction
from typing import TYPE_CHECKING

from fransys_model.vocab import voltage
from fransys_model.vocab.closure import port_rails, rail_pairs
from fransys_model.vocab.enums import Current, Earthing, NetClass
from fransys_model.vocab.tables import nets, ports, supply_of_potential, supply_systems

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port


@dataclasses.dataclass(frozen=True, slots=True)
class Stand:
    """A voltage that stands on a function: across two rails, or one rail to earth."""

    volt: voltage.Volt
    rails: tuple[voltage.RailV, ...]


def earth_potentials(model: Model) -> frozenset[str]:
    """The potentials that are earth: those a net of class `PE` carries (decision model-0085).

    The one place of the rule. Such a rail stands at 0 V to earth in every supply, IT included,
    whatever values a supply lists for it.
    """
    return frozenset(
        net.potential
        for net in nets(model).values()
        if net.net_class is NetClass.PE and net.potential is not None
    )


def rails_by_potential(model: Model) -> dict[str, voltage.RailV]:
    """Each potential's rail, taken from its supply with the smallest `(name, id)`.

    Equal-content declarations repeat rails and a potential in two supplies is an error, so the
    choice must not depend on record order. An earth rail is at 0 V with no phase.
    """
    earth_rails = earth_potentials(model)
    found: dict[str, voltage.RailV] = {}
    for supply in sorted(supply_systems(model).values(), key=lambda s: (s.name, s.id)):
        ac = supply.current is Current.AC
        it = supply.earthing is Earthing.IT
        points = {
            name: (Fraction(0), None) if name in earth_rails else (Fraction(rail.max_v), rail.phase)
            for name, rail in supply.rails.items()
        }
        live = tuple(point for name, point in points.items() if name not in earth_rails)
        shared = voltage.it_earth(live, ac=ac) if it else None
        for name in sorted(points):
            if supply_of_potential(model, name) is not supply:
                continue
            max_v, phase = points[name]
            earth = (
                shared
                if shared is not None and name not in earth_rails
                else voltage.exact(abs(max_v))
            )
            found[name] = voltage.RailV(name, supply.name, it, ac, max_v, phase, earth)
    return found


def _stands(
    at_ports: Sequence[Sequence[voltage.RailV]],
    pairs: Sequence[tuple[voltage.RailV, voltage.RailV]],
) -> list[Stand]:
    """The candidate voltages of a function, `at_ports` being the rails each port reaches.

    `pairs` are the rails that can stand across the function at once, `(low, high)` by name.
    Only with no pair at all does the voltage to earth of each reached rail stand.
    """
    if pairs:
        return [Stand(voltage.pair(a, b), (a, b)) for a, b in pairs]
    reached = {rail.name: rail for rails in at_ports for rail in rails}
    return [Stand(rail.earth, (rail,)) for rail in reached.values()]


def ports_by_function(model: Model) -> dict[Id[Function], list[Id[Port]]]:
    """The ports of each function that has any."""
    ports_of: dict[Id[Function], list[Id[Port]]] = {}
    for port in ports(model).values():
        ports_of.setdefault(port.function, []).append(port.id)
    return ports_of


@dataclasses.dataclass(frozen=True, slots=True)
class RailReach:
    """What a function's ports reach: the rails by potential, per port, and the pairs across it."""

    lookup: Mapping[str, voltage.RailV]
    reached: Sequence[frozenset[str]]
    standing: Sequence[tuple[str, str]]

    def stands(self, *, ac: bool) -> list[Stand] | None:
        """The stands of current kind `ac`, or `None` when no port reaches a rail of that kind."""
        lookup = self.lookup
        at_ports = [
            [lookup[name] for name in names if name in lookup and lookup[name].ac is ac]
            for names in self.reached
        ]
        at_ports = [rails for rails in at_ports if rails]
        if not at_ports:
            return None
        pairs = [
            (lookup[low], lookup[high])
            for low, high in self.standing
            if low in lookup and high in lookup and lookup[low].ac is lookup[high].ac is ac
        ]
        return _stands(at_ports, pairs)


def reach_of(
    model: Model,
    function: Id[Function],
    lookup: Mapping[str, voltage.RailV],
    ports_of: Mapping[Id[Function], Sequence[Id[Port]]],
) -> RailReach:
    """The `RailReach` of `function`, built the one way every check builds it."""
    reached = [port_rails(model, port) for port in ports_of.get(function, ())]
    return RailReach(lookup, reached, sorted(rail_pairs(model, function)))


def worst_stand(stands: Sequence[Stand]) -> Stand:
    """The stand of largest magnitude; of equal ones, the first by rail names (the one rule)."""
    ordered = sorted(stands, key=lambda s: tuple(rail.name for rail in s.rails))
    return max(ordered, key=lambda s: voltage.magnitude(s.volt))


def voltage_across(reach: RailReach, *, ac: bool) -> Stand | None:
    """The worst stand of kind `ac` (`worst_stand`), or `None` when no rail of that kind."""
    stands = reach.stands(ac=ac)
    return worst_stand(stands) if stands else None


def reached_kinds(model: Model) -> dict[Id[Function], set[Current]]:
    """The current kinds of the rails the ports of each function carry."""
    lookup = rails_by_potential(model)
    reached: dict[Id[Function], set[Current]] = {}
    for port in ports(model).values():
        kinds = reached.setdefault(port.function, set())
        for name in port_rails(model, port.id):
            if name in lookup:
                kinds.add(Current.AC if lookup[name].ac else Current.DC)
    return reached


def reached_supplies(model: Model) -> dict[Id[Function], set[str]]:
    """The names of the supply systems whose rails the ports of each function carry."""
    lookup = rails_by_potential(model)
    reached: dict[Id[Function], set[str]] = {}
    for port in ports(model).values():
        names = reached.setdefault(port.function, set())
        names.update(lookup[name].supply for name in port_rails(model, port.id) if name in lookup)
    return reached
