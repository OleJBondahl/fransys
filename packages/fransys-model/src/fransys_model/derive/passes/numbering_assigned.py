"""The assigned-designation half of the numbering pass: first free `code + n` per sibling group."""

from typing import TYPE_CHECKING

from fransys_model.derive.designation import (
    designating_ancestors,
    own_designation_or_none,
    takes_parents_designation,
)
from fransys_model.derive.passes.numbering_units import instance_tags_in
from fransys_model.kernel import Model, make_id
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.numbering_codes import item_class_code

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item


def _taken_texts(model: Model, siblings: list[Item], reserved: frozenset[str]) -> set[str]:
    taken = {
        text for item in siblings if (text := own_designation_or_none(model, item)) is not None
    } | reserved
    if siblings and not designating_ancestors(model, siblings[0].id):
        taken |= instance_tags_in(model, siblings[0].unit)  # UT3: one count with the instances
    return taken


def _first_free(code: str, taken: set[str]) -> str:
    counter = 1
    while f"{code}{counter}" in taken:
        counter += 1
    return f"{code}{counter}"


def _assigned_facet(item: Item, text: str) -> AssignedDesignationFacet:
    key = (*item.key, "assigned_designation")
    return AssignedDesignationFacet(
        id=make_id(AssignedDesignationFacet, key), key=key, subject=item.id, text=text
    )


def assigned_facets(
    model: Model,
    siblings: list[Item],
    reserved: frozenset[str],
) -> list[AssignedDesignationFacet]:
    """One `facet.assigned_designation` for each unnumbered sibling that can be numbered.

    Each takes the first `code + str(n)`, from n = 1, not already an exact string in the group.
    An item with an own text is skipped and its text taken; an accessory uses up no number.
    """
    taken = _taken_texts(model, siblings, reserved)
    numbered: list[AssignedDesignationFacet] = []
    for item in sorted(siblings, key=lambda item: (item.key, item.id)):
        if own_designation_or_none(model, item) is not None or takes_parents_designation(
            model, item.id
        ):
            continue
        code = item_class_code(model, item.id)
        if not code:
            continue
        candidate = _first_free(code, taken)
        taken.add(candidate)
        numbered.append(_assigned_facet(item, candidate))
    return numbered
