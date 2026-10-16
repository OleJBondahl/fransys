"""The items a document's lists leave out because its drawings omit their harness (pdf-0043).

A location document draws no harness (ruling W-CABINET), so the harness items are not listed.
"""

from fransys_model.derive.facts.units import is_harness
from fransys_model.vocab.tables import items as items_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit
lazy from fransys_model.vocab.document import Document

from .indexes import build_indexes
from .lookups import descendants

__all__ = ["undrawn_items"]


def undrawn_items(
    model: Model, document: Document, unit: Id[Unit] | None, drawn: tuple[Id[Item], ...]
) -> tuple[Id[Item], ...]:
    """The harness items a location document does not draw, with all they own, sorted.

    Only a location document has any: a unit or item document draws its own harnesses.
    """
    if unit is not None or document.item is not None or document.location is None:
        return ()
    children = build_indexes(model).children_by_item
    found: set[Id[Item]] = set()
    for item in items_table(model):
        if item not in drawn and is_harness(model, item):
            found.update((item, *descendants(children, item)))
    return tuple(sorted(found))
