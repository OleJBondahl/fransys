"""Validator: a wire's two ends must not sit under plugs of two harnesses (model-0171)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.harness_wires import wire_harnesses
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import conductors

if TYPE_CHECKING:
    from fransys_model.kernel import Model

WIRE_ON_TWO_HARNESSES: Final[str] = "WIRE_ON_TWO_HARNESSES"


def check_wire_on_two_harnesses(model: Model) -> tuple[Finding, ...]:
    """One `ERROR` per WIRE conductor whose ends sit under two different harnesses."""
    found = []
    for conductor in conductors(model):
        pair = wire_harnesses(model, conductor)
        if len(pair) > 1:
            names = " and ".join(ref(harness) for harness in pair)
            message = f"a wire joins plugs of two harnesses, {names}: a wire has one harness"
            found.append(finding(WIRE_ON_TWO_HARNESSES, Severity.ERROR, (conductor,), message))
    return ordered(found)
