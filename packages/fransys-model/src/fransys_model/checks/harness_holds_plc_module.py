"""Validator: a marked harness must not hold a PLC module; a rack is `d.rack` (model-0178)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.children import parent_item
from fransys_model.derive.facts.item_predicates import is_plc_module
from fransys_model.derive.facts.units import marked_harnesses
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
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
        finding(
            HARNESS_HOLDS_PLC_MODULE,
            Severity.ERROR,
            (item.id, parent),
            f"{ref(item)} is a PLC module under the harness "
            f"{ref(items(model)[parent])}: build the rack with d.rack, not d.harness",
        )
        for item in items(model).values()
        if (parent := parent_item(model, item.id)) in marked and is_plc_module(model, item)
    ]
    return ordered(found)
