"""Source declarations of a supply name, and the pins they put it on.

A name may be declared by a container and again by a unit inside it; only the outermost
declarations are the source. The one reader of that rule.
"""

from enum import Enum
from typing import TYPE_CHECKING, Final

from fransys_kernel import decimal_text
from fransys_model.derive.facts.units import declared_unit, unit_encloses
from fransys_model.vocab.tables import supply_systems

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Port
    from fransys_model.vocab.supply_system import SupplySystem

_COMPARED: Final = ("current", "earthing")
_FAULT_FIELDS: Final = ("fault_current_a", "fault_time_constant_ms")


def _encloses(model: Model, outer: SupplySystem, inner: SupplySystem) -> bool:
    """Whether `outer` sits in a unit strictly above `inner`'s; no unit encloses every unit."""
    return unit_encloses(model, declared_unit(outer), declared_unit(inner))


def declarations_by_name(model: Model) -> dict[str, tuple[SupplySystem, ...]]:
    """Every declaration of each supply name, in id order."""
    by_name: dict[str, list[SupplySystem]] = {}
    for supply in sorted(supply_systems(model).values(), key=lambda s: s.id):
        by_name.setdefault(supply.name, []).append(supply)
    return {name: tuple(found) for name, found in by_name.items()}


def supplies_by_potential(model: Model) -> dict[str, tuple[SupplySystem, ...]]:
    """The supplies that have a rail at each potential, in id order."""
    by_potential: dict[str, list[SupplySystem]] = {}
    for supply in sorted(supply_systems(model).values(), key=lambda s: s.id):
        for potential in supply.rails:
            by_potential.setdefault(potential, []).append(supply)
    return {potential: tuple(found) for potential, found in by_potential.items()}


def source_declarations(model: Model) -> dict[str, tuple[SupplySystem, ...]]:
    """The source declarations of each supply name, in id order.

    A source has no other declaration of its name in a unit strictly above its own; no unit is
    above every unit. Two declarations in one unit, or in sibling units, both count.
    """
    return {
        name: tuple(d for d in found if not any(_encloses(model, o, d) for o in found))
        for name, found in declarations_by_name(model).items()
    }


def supply_pins(model: Model) -> dict[str, frozenset[Id[Port]]]:
    """The ports a supply name's source declarations put it on, by name."""
    return {
        name: frozenset(pin for supply in sources for pin in supply.pins)
        for name, sources in source_declarations(model).items()
    }


def _rails_detail(members: Sequence[SupplySystem]) -> str | None:
    """Which potentials differ or are missing among the declarations; `None` when they agree."""
    potentials = sorted({potential for supply in members for potential in supply.rails})
    notes = []
    for potential in potentials:
        seen = [supply.rails.get(potential) for supply in members]
        if None in seen:
            notes.append(f"{potential} is missing in some")
        elif any(rail != seen[0] for rail in seen):
            notes.append(f"{potential} differs")
    return ", ".join(notes) if notes else None


def _field_text(supply: SupplySystem, field: str) -> str:
    """A compared field as text: an enum's value, a decimal's text, `"None"` when unset."""
    value = getattr(supply, field)
    if isinstance(value, Enum):
        return str(value.value)
    return "None" if value is None else decimal_text(value)


def _differing(members: Sequence[SupplySystem], fields: Iterable[str]) -> dict[str, str]:
    """The compared `fields` whose values differ among `members`, each with its values as text."""
    details: dict[str, str] = {}
    for field in fields:
        values = sorted({_field_text(supply, field) for supply in members})
        if len(values) > 1:
            details[field] = ", ".join(map(repr, values))
    return details


def _differences(
    members: Sequence[SupplySystem], sources: Sequence[SupplySystem]
) -> dict[str, str]:
    """The compared fields, the fault fields of the `sources` and the rails that differ."""
    details = _differing(members, _COMPARED)
    details.update(_differing(sources, _FAULT_FIELDS))
    rails = _rails_detail(members)
    if rails is not None:
        details["rails"] = rails
    return details


def supply_differences(model: Model) -> dict[str, dict[str, str]]:
    """Each supply name whose declarations disagree, with the differing fields as text."""
    sources = source_declarations(model)
    found = {
        name: _differences(members, sources[name])
        for name, members in declarations_by_name(model).items()
    }
    return {name: details for name, details in found.items() if details}
