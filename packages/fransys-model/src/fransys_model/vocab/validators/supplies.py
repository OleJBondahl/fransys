"""Validator: supply names and potentials are model-wide (decision model-0075)."""

from enum import Enum
from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.kernel.encode import decimal_text
from fransys_model.vocab.supply_sources import source_declarations
from fransys_model.vocab.tables import supply_systems

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.supply_system import SupplySystem

SUPPLY_DIFFERS: Final[str] = "SUPPLY_DIFFERS"
POTENTIAL_IN_TWO_SUPPLIES: Final[str] = "POTENTIAL_IN_TWO_SUPPLIES"
_COMPARED: Final = ("current", "earthing")
_FAULT_FIELDS: Final = ("fault_current_a", "fault_time_constant_ms")


def _finding(code: str, severity: Severity, subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(code=code, severity=severity, subjects=tuple(subjects), message=message)


def _rails_detail(members: list[SupplySystem]) -> str | None:
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


def _differing(members: list[SupplySystem], fields: Iterable[str]) -> dict[str, str]:
    """The compared `fields` whose values differ among `members`, each with its values as text."""
    details: dict[str, str] = {}
    for field in fields:
        values = sorted({_field_text(supply, field) for supply in members})
        if len(values) > 1:
            details[field] = ", ".join(map(repr, values))
    return details


def _supply_differs(model: Model) -> list[Finding]:
    by_name: dict[str, list[SupplySystem]] = {}
    for supply in supply_systems(model).values():
        by_name.setdefault(supply.name, []).append(supply)
    sources = source_declarations(model)
    found = []
    for name, members in by_name.items():
        details = _differing(members, _COMPARED)
        details.update(_differing(list(sources[name]), _FAULT_FIELDS))
        rails = _rails_detail(members)
        if rails is not None:
            details["rails"] = rails
        if not details:
            continue
        if len(details) == 1:
            ((field, text),) = details.items()
            detail = f"{field}: {text}"
        else:
            listed = "; ".join(f"{field} {text}" for field, text in details.items())
            fields = list(details)
            detail = f"{', '.join(fields[:-1])} and {fields[-1]}: {listed}"
        message = f"supplies named {name!r} differ in {detail}"
        subjects = sorted(supply.id for supply in members)
        found.append(_finding(SUPPLY_DIFFERS, Severity.ERROR, subjects, message))
    return found


def _potential_in_two_supplies(supplies: Iterable[SupplySystem]) -> list[Finding]:
    by_potential: dict[str, list[SupplySystem]] = {}
    for supply in supplies:
        for potential in supply.rails:
            by_potential.setdefault(potential, []).append(supply)
    found = []
    for potential, members in by_potential.items():
        names = sorted({supply.name for supply in members})
        if len(names) <= 1:
            continue
        message = (
            f"potential {potential!r} is a rail of more than one supply: "
            f"{', '.join(map(repr, names))}"
        )
        subjects = sorted(supply.id for supply in members)
        found.append(_finding(POTENTIAL_IN_TWO_SUPPLIES, Severity.ERROR, subjects, message))
    return found


def check_supplies(model: Model) -> tuple[Finding, ...]:
    """Check that a supply name means one supply and a potential belongs to one supply.

    `SUPPLY_DIFFERS`, `POTENTIAL_IN_TWO_SUPPLIES`: `ERROR`. Declarations agreeing in `current`,
    `earthing` and `rails` are one supply; a potential in two supplies is reported once.
    """
    supplies = tuple(supply_systems(model).values())
    found = [*_supply_differs(model), *_potential_in_two_supplies(supplies)]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
