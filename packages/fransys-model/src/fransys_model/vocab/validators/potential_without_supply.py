"""Validator: a net potential that no supply declares gives no rank and no power symbol (V11)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.rail_reach import earth_potentials
from fransys_model.vocab.tables import nets, supply_of_potential, supply_systems

if TYPE_CHECKING:
    from fransys_model.kernel import Model

POTENTIAL_WITHOUT_SUPPLY: Final[str] = "POTENTIAL_WITHOUT_SUPPLY"


def check_potential_without_supply(model: Model) -> tuple[Finding, ...]:
    """Warn once per net whose `potential` is no supply's rail and no earth rail (model-0085)."""
    earth = earth_potentials(model)
    declared = sorted({name for s in supply_systems(model).values() for name in s.rails})
    named = ", ".join(declared) or "none"
    found = []
    for net in nets(model).values():
        potential = net.potential
        if potential is None or potential in earth or supply_of_potential(model, potential):
            continue
        origin = model.origins[net.id]
        message = (
            f"net {key_text(net)} ({origin.file}:{origin.line}) carries potential {potential!r}, "
            f"which no supply declares (declared: {named}): it gets no rank and no power symbol"
        )
        found.append(
            Finding(
                code=POTENTIAL_WITHOUT_SUPPLY,
                severity=Severity.WARNING,
                subjects=(net.id,),
                message=message,
            )
        )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
