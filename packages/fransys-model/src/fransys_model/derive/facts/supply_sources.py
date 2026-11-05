"""The declarations of a supply name and of a potential, and where they disagree."""

from enum import Enum
from typing import TYPE_CHECKING

from fransys_kernel import decimal_text
from fransys_model.vocab.tables import supply_systems

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_model.kernel import Model
    from fransys_model.vocab.supply_system import SupplySystem


def declarations_by_name(model: Model) -> dict[str, tuple[SupplySystem, ...]]:
    """Every declaration of each supply name, in id order."""
    by_name: dict[str, list[SupplySystem]] = {}
    for supply in supply_systems(model).values():
        by_name.setdefault(supply.name, []).append(supply)
    return {name: tuple(found) for name, found in by_name.items()}


def supplies_by_potential(model: Model) -> dict[str, tuple[SupplySystem, ...]]:
    """The supplies that have a rail at each potential, in id order."""
    by_potential: dict[str, list[SupplySystem]] = {}
    for supply in supply_systems(model).values():
        for potential in supply.rails:
            by_potential.setdefault(potential, []).append(supply)
    return {potential: tuple(found) for potential, found in by_potential.items()}


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


def _differences(members: Sequence[SupplySystem]) -> dict[str, str]:
    """The current and the rails that differ among `members`."""
    details = _differing(members, ("current",))
    rails = _rails_detail(members)
    if rails is not None:
        details["rails"] = rails
    return details


def supply_differences(model: Model) -> dict[str, dict[str, str]]:
    """Each supply name whose declarations disagree, with the differing fields as text."""
    found = {name: _differences(members) for name, members in declarations_by_name(model).items()}
    return {name: details for name, details in found.items() if details}
