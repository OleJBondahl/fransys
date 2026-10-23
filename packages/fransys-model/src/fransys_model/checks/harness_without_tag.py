"""Validator: a structural harness must carry its own designation (decision model-0107)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.item_predicates import has_own_designation
from fransys_model.derive.facts.units import is_harness
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

HARNESS_WITHOUT_TAG: Final[str] = "HARNESS_WITHOUT_TAG"


def check_harness_without_tag(model: Model) -> tuple[Finding, ...]:
    """Check every harness has its own designation, so a label read never raises.

    A harness (`is_harness`: marked, or with a `cable` child) with no own designation is an
    `ERROR`, so `build` never lets `_ancestor_label` raise a bare `SchemaError`.
    """
    found = [
        finding(
            HARNESS_WITHOUT_TAG,
            Severity.ERROR,
            (item.id,),
            f"{ref(item)} reads as a harness (a marked harness or a cable child), "
            "but has no designation: give it a tag: d.harness(tag=...), or tag= on the item",
        )
        for item in items(model).values()
        if is_harness(model, item.id) and not has_own_designation(model, item)
    ]
    return ordered(found)
