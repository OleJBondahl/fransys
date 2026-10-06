"""Validator: a part-less top-level item must be able to take a designation (model-0134)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.membership import is_harness
from fransys_model.vocab.numbering_codes import item_class_code, terminal_class_codes
from fransys_model.vocab.own_designation import has_own_designation
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Item

STRIP_WITHOUT_TAG: Final[str] = "STRIP_WITHOUT_TAG"


def _why(model: Model, item: Item) -> str:
    codes = terminal_class_codes(model, item.id)
    if not codes:
        return "it has no terminals to take a class code from"
    if len(codes) > 1:
        return f"its terminals' parts disagree on the class code ({', '.join(sorted(codes))})"
    return "its terminals' part has no class code"


def check_strip_without_tag(model: Model) -> tuple[Finding, ...]:
    """Check every part-less top-level item has a tag or a numbering class code (model-0134)."""
    found = [
        Finding(
            code=STRIP_WITHOUT_TAG,
            severity=Severity.ERROR,
            subjects=(item.id,),
            message=(
                f"{key_text(item)} has no part, no tag and no class code to number from: "
                f"{_why(model, item)}; give it a part, a tag, or terminals of one class code"
            ),
        )
        for item in items(model).values()
        if item.part is None
        and item.parent is None
        and not is_harness(model, item.id)
        and not has_own_designation(model, item)
        and not item_class_code(model, item.id)
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
