"""The drawing sets a document prints, one fact in one place (decision model-0201).

A location subject prints the one set at that location with no unit of its own, since a nested
unit's set can share the node (model-0041). A unit subject prints that unit's sets. Layout orders
sets unit-then-location (layout-0045), so sorting by `number` gives "in location order" (U3).
"""

from fransys_model.layout import DrawingSet, layout_of
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.document import Document

from .document_unit import document_unit

__all__ = ["document_drawing_sets", "printed_drawing_sets"]


def document_drawing_sets(model: Model, document: Id[Document]) -> tuple[DrawingSet, ...]:
    """The drawing sets of `document` by `number`: a location's top-level set, a unit's sets.

    `document` is the document's id.
    """
    record = documents(model)[document]
    all_sets = layout_of(model, DrawingSet).values()
    if record.location is not None:
        matching = [s for s in all_sets if s.location == record.location and s.unit is None]
    elif (unit := document_unit(model, document)) is not None:
        matching = [s for s in all_sets if s.unit == unit]
    else:
        matching = []
    return tuple(sorted(matching, key=lambda found: found.number))


def printed_drawing_sets(model: Model) -> tuple[DrawingSet, ...]:
    """The sets some document of `model` prints, by `number`; none that no document prints."""
    printed = {
        s.id: s for doc in documents(model).values() for s in document_drawing_sets(model, doc.id)
    }
    return tuple(sorted(printed.values(), key=lambda found: found.number))
