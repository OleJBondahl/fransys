"""Validator: a structural harness must carry its own designation (decision model-0107)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.membership import is_harness
from fransys_model.vocab.own_designation import has_own_designation
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

HARNESS_WITHOUT_TAG: Final[str] = "HARNESS_WITHOUT_TAG"


def check_harness_without_tag(model: Model) -> tuple[Finding, ...]:
    """Check every harness has its own designation, so a label read never raises.

    An item with a `cable` child (`is_harness`) and no own designation is an `ERROR`, reported
    here so `build` never lets `_ancestor_label` raise a bare `SchemaError`.
    """
    found = [
        Finding(
            code=HARNESS_WITHOUT_TAG,
            severity=Severity.ERROR,
            subjects=(item.id,),
            message=(
                f"{key_text(item)} has a cable child and reads as a harness, but has no "
                "designation: give it a tag: d.harness(tag=...), or tag= on the item"
            ),
        )
        for item in items(model).values()
        if is_harness(model, item.id) and not has_own_designation(model, item)
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
