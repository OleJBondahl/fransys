"""The WARNING for a laid-out drawing set that no document prints (R316).

No document, no layout (owner 2026-09-26): a set no document covers is named, never silent.
"""

from fransys_model.kernel import Finding, Model, Severity
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.codes import fix_text
from fransys_model.vocab.tables import items

from .designation import printed_designation
from .document_sets import set_unit
from .drawing_text import unit_label
from .facts.unit_index import item_unit
from .lookups import item_location
from .order import in_designation_order
from .printed_sets import printed_drawing_sets

__all__ = ["check_unprinted_sets"]

UNPRINTED_SET = "UNPRINTED_SET"


def _items_of(model: Model, drawing_set: DrawingSet) -> str:
    """The designations of the items drawn in `drawing_set`, in designation order."""
    held = [
        item.id
        for item in items(model).values()
        if item_unit(model, item.id) == set_unit(drawing_set)
        and item_location(model, item.id) == drawing_set.location
    ]
    names = [printed_designation(model, item) for item in in_designation_order(model, held)]
    return ", ".join(names)


def _subject(model: Model, drawing_set: DrawingSet) -> str:
    """The unit's name or the location's label a document for the set would name."""
    if (unit := set_unit(drawing_set)) is not None:
        return unit_label(model, unit)
    return "its location"


def check_unprinted_sets(model: Model) -> tuple[Finding, ...]:
    """One WARNING per drawing set with a page that no document prints, naming its items."""
    drawn = {page.drawing_set for page in layout_of(model, Page).values()}
    printed = {s.id for s in printed_drawing_sets(model)}
    return tuple(
        Finding(
            code=UNPRINTED_SET,
            severity=Severity.WARNING,
            subjects=(),
            message=(
                f"drawing set {s.number} has pages that no document prints; its items: "
                f"{_items_of(model, s)}. Add a document for {_subject(model, s)}, or nest it."
            ),
            fix=fix_text(UNPRINTED_SET),
        )
        for s in layout_of(model, DrawingSet).values()
        if s.id in drawn and s.id not in printed
    )
