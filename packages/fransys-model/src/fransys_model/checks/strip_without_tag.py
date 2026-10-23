"""Validator: a part-less top-level item must be able to take a designation (model-0134)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.item_predicates import terminal_class_codes
from fransys_model.derive.facts.strip_without_tag import strips_without_tag
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item

STRIP_WITHOUT_TAG: Final[str] = "STRIP_WITHOUT_TAG"


def _why(model: Model, item: Id[Item]) -> str:
    codes = terminal_class_codes(model, item)
    if not codes:
        return "it has no terminals to take a class code from"
    if len(codes) > 1:
        return f"its terminals' parts disagree on the class code ({', '.join(sorted(codes))})"
    return "its terminals' part has no class code"


def check_strip_without_tag(model: Model) -> tuple[Finding, ...]:
    """Check every part-less top-level item has a tag or a numbering class code (model-0134)."""
    found = [
        finding(
            STRIP_WITHOUT_TAG,
            Severity.ERROR,
            (strip,),
            f"{ref(items(model)[strip])} has no part, no tag and no class code to number from: "
            f"{_why(model, strip)}; give it a part, a tag, or terminals of one class code",
        )
        for strip in strips_without_tag(model)
    ]
    return ordered(found)
