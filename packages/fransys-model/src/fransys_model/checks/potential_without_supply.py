"""Validator: a net potential that no supply declares gives no rank and no power symbol."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.potential_without_supply import (
    declared_rails,
    potentials_without_supply,
)
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import nets

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model

POTENTIAL_WITHOUT_SUPPLY: Final[str] = "POTENTIAL_WITHOUT_SUPPLY"


def check_potential_without_supply(model: Model) -> tuple[Finding, ...]:
    """Warn once per net whose `potential` is no supply's rail and no earth rail (model-0085)."""
    named = ", ".join(declared_rails(model)) or "none"
    found = []
    for net_id, potential in potentials_without_supply(model):
        origin = model.origins[net_id]
        message = (
            f"net {ref(nets(model)[net_id])} ({origin.file}:{origin.line}) carries potential "
            f"{potential!r}, which no supply declares (declared: {named}): it gets no rank and "
            "no power symbol"
        )
        found.append(finding(POTENTIAL_WITHOUT_SUPPLY, (net_id,), message))
    return ordered(found)
