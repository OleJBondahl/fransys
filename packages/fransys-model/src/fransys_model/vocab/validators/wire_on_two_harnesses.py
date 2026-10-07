"""Validator: a wire's two ends must not sit under plugs of two harnesses (HA2, model-0171)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.tables import conductors, items
from fransys_model.vocab.wire_harness import wire_harnesses

if TYPE_CHECKING:
    from fransys_model.kernel import Model

WIRE_ON_TWO_HARNESSES: Final[str] = "WIRE_ON_TWO_HARNESSES"


def check_wire_on_two_harnesses(model: Model) -> tuple[Finding, ...]:
    """One `ERROR` per WIRE conductor whose ends sit under two different harnesses."""
    found = []
    for conductor in conductors(model):
        pair = wire_harnesses(model, conductor)
        if len(pair) > 1:
            names = " and ".join(key_text(items(model)[harness]) for harness in pair)
            found.append(
                Finding(
                    code=WIRE_ON_TWO_HARNESSES,
                    severity=Severity.ERROR,
                    subjects=(conductor,),
                    message=f"a wire joins plugs of two harnesses, {names}: a wire has one harness",
                )
            )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
