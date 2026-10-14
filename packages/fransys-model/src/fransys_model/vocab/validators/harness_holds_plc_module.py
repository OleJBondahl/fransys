"""Validator: a marked harness must not hold a PLC module; a rack is `d.rack` (model-0178)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.membership import marked_harnesses
from fransys_model.vocab.plc_module import is_plc_module
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

HARNESS_HOLDS_PLC_MODULE: Final[str] = "HARNESS_HOLDS_PLC_MODULE"


def check_harness_holds_plc_module(model: Model) -> tuple[Finding, ...]:
    """One `ERROR` per module of a PLC rack that sits under a marked harness.

    A marked harness prints its children through itself, so its modules would stop printing flat.
    """
    marked = marked_harnesses(model)
    found = [
        Finding(
            code=HARNESS_HOLDS_PLC_MODULE,
            severity=Severity.ERROR,
            subjects=(item.id, item.parent),
            message=(
                f"{ref(item)} is a PLC module under the harness "
                f"{ref(items(model)[item.parent])}: build the rack with d.rack, not d.harness"
            ),
        )
        for item in items(model).values()
        if item.parent in marked and is_plc_module(model, item)
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
