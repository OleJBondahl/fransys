"""Validator: a function's rated voltage against the voltage across it (decision model-0079).

Codes: `RATING_VOLTAGE_BELOW_CIRCUIT`.
"""

import dataclasses
from fractions import Fraction
from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab import voltage
from fransys_model.vocab.closure import port_rails, rail_pairs
from fransys_model.vocab.enums import Current, Earthing, NetClass
from fransys_model.vocab.rating_readers import function_ratings
from fransys_model.vocab.tables import (
    functions,
    items,
    nets,
    ports,
    supply_of_potential,
    supply_systems,
    units,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Item, Port

RATING_VOLTAGE_BELOW_CIRCUIT: Final[str] = "RATING_VOLTAGE_BELOW_CIRCUIT"


@dataclasses.dataclass(frozen=True, slots=True)
class _Stand:
    """A voltage that stands on a function: across two rails, or one rail to earth."""

    volt: voltage.Volt
    rails: tuple[voltage.RailV, ...]


def _earth_potentials(model: Model) -> frozenset[str]:
    """The potentials that are earth: those a net of class `PE` carries (decision model-0085).

    The one place of the rule. Such a rail stands at 0 V to earth in every supply, IT included,
    whatever values a supply lists for it.
    """
    return frozenset(
        net.potential
        for net in nets(model).values()
        if net.net_class is NetClass.PE and net.potential is not None
    )


def _rails_by_potential(model: Model) -> dict[str, voltage.RailV]:
    """Each potential's rail, taken from its supply with the smallest `(name, id)`.

    Equal-content declarations repeat rails and a potential in two supplies is an error, so the
    choice must not depend on record order. An earth rail is at 0 V with no phase.
    """
    earth_rails = _earth_potentials(model)
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
) -> list[_Stand]:
    """The candidate voltages of a function, `at_ports` being the rails each port reaches.

    `pairs` are the rails that can stand across the function at once, `(low, high)` by name.
    Only with no pair at all does the voltage to earth of each reached rail stand.
    """
    if pairs:
        return [_Stand(voltage.pair(a, b), (a, b)) for a, b in pairs]
    reached = {rail.name: rail for rails in at_ports for rail in rails}
    return [_Stand(rail.earth, (rail,)) for rail in reached.values()]


def _message(function: Function, item: Item, limit: Decimal, stand: _Stand, source: str) -> str:
    """Name the function, its rating and its source, the rails and V, and say when IT applied."""
    first = stand.rails[0]
    kind = "AC" if first.ac else "DC"
    where = f"function {function.name!r} of item {'/'.join(item.key)}"
    text = f"{where} is rated {limit:f} V {kind} ({source}), but "
    volt = voltage.show(stand.volt)
    if len(stand.rails) == 1:
        text += f"rail {first.name!r} is at {volt} V to earth"
        return text + (f" (IT supply {first.supply!r})" if first.it else "")
    second = stand.rails[1]
    text += f"rails {first.name!r} and {second.name!r} stand across it at {volt} V"
    if voltage.common_reference(first, second):
        return text
    if first.it or second.it:
        return text + " (IT: no common reference, the sum of their voltages to earth)"
    return text + " (two AC supplies, no fixed phase: the sum of their voltages to earth)"


def _finding(
    function: Function, item: Item, limit: Decimal, stands: list[_Stand], source: str
) -> Finding | None:
    rating = Fraction(limit)
    firing = [s for s in stands if voltage.exceeds(s.volt, rating)]
    if not firing:
        return None
    firing.sort(key=lambda s: tuple(rail.name for rail in s.rails))
    worst = max(firing, key=lambda s: voltage.magnitude(s.volt))  # first maximum: smallest names
    return Finding(
        code=RATING_VOLTAGE_BELOW_CIRCUIT,
        severity=Severity.ERROR,
        subjects=(function.id,),
        message=_message(function, item, limit, worst, source),
    )


def check_ratings(model: Model) -> tuple[Finding, ...]:
    """Check that no function is rated for less voltage than stands across it.

    `RATING_VOLTAGE_BELOW_CIRCUIT` (`ERROR`), one per function, current kind and rating source,
    when V is strictly above the rating. V: highest voltage that can stand at once, else to earth.
    """
    lookup = _rails_by_potential(model)
    if not lookup:
        return ()
    ports_of: dict[Id[Function], list[Id[Port]]] = {}
    for port in ports(model).values():
        ports_of.setdefault(port.function, []).append(port.id)
    item_of = items(model)
    unit_of = units(model)
    found: list[Finding] = []
    for function in functions(model).values():
        sources = function_ratings(model, function.id)
        if not sources:
            continue
        reached = [port_rails(model, port) for port in ports_of.get(function.id, ())]
        standing = sorted(rail_pairs(model, function.id))
        for source in sources:
            label = (
                "part or template rating"
                if source.unit is None
                else f"boundary rating of unit {key_text(unit_of[source.unit])}"
            )
            for ac, limit in (
                (True, source.rating.voltage_ac_v),
                (False, source.rating.voltage_dc_v),
            ):
                at_ports = [
                    [lookup[name] for name in names if name in lookup and lookup[name].ac is ac]
                    for names in reached
                ]
                at_ports = [rails for rails in at_ports if rails]
                if limit is None or not at_ports:
                    continue
                pairs = [
                    (lookup[low], lookup[high])
                    for low, high in standing
                    if low in lookup and high in lookup and lookup[low].ac is lookup[high].ac is ac
                ]
                stands = _stands(at_ports, pairs)
                finding = _finding(function, item_of[function.item], limit, stands, label)
                if finding is not None:
                    found.append(finding)
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
