"""Validator: supply names and potentials are model-wide (decision model-0075)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.supply_sources import (
    declarations_by_name,
    supplies_by_potential,
    supply_differences,
)
from fransys_model.kernel import Finding, Severity

if TYPE_CHECKING:
    from fransys_model.kernel import Model

SUPPLY_DIFFERS: Final[str] = "SUPPLY_DIFFERS"
POTENTIAL_IN_TWO_SUPPLIES: Final[str] = "POTENTIAL_IN_TWO_SUPPLIES"


def _detail(details: dict[str, str]) -> str:
    if len(details) == 1:
        ((field, text),) = details.items()
        return f"{field}: {text}"
    listed = "; ".join(f"{field} {text}" for field, text in details.items())
    fields = list(details)
    return f"{', '.join(fields[:-1])} and {fields[-1]}: {listed}"


def _supply_differs(model: Model) -> list[Finding]:
    by_name = declarations_by_name(model)
    return [
        finding(
            SUPPLY_DIFFERS,
            Severity.ERROR,
            sorted(supply.id for supply in by_name[name]),
            f"supplies named {name!r} differ in {_detail(details)}",
        )
        for name, details in supply_differences(model).items()
    ]


def _potential_in_two_supplies(model: Model) -> list[Finding]:
    found = []
    for potential, members in supplies_by_potential(model).items():
        names = sorted({supply.name for supply in members})
        if len(names) <= 1:
            continue
        message = (
            f"potential {potential!r} is a rail of more than one supply: "
            f"{', '.join(map(repr, names))}"
        )
        subjects = sorted(supply.id for supply in members)
        found.append(finding(POTENTIAL_IN_TWO_SUPPLIES, Severity.ERROR, subjects, message))
    return found


def check_supplies(model: Model) -> tuple[Finding, ...]:
    """Check that a supply name means one supply and a potential belongs to one supply.

    `SUPPLY_DIFFERS`, `POTENTIAL_IN_TWO_SUPPLIES`: `ERROR`. Declarations agreeing in `current`,
    `earthing` and `rails` are one supply; a potential in two supplies is reported once.
    """
    return ordered([*_supply_differs(model), *_potential_in_two_supplies(model)])
