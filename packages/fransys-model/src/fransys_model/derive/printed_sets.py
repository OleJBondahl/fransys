"""The drawing sets a document prints, one fact in one place (decision model-0201, model-0360).

Each set is printed by exactly one document: `document_scope` holds the sets of each (R331, R361).
A place document prints that place's top-level set; a unit document prints its unit's sets, the
sets of its undocumented nested units and the top-level sets of the items its strips feed. Layout
orders sets unit-then-location (layout-0045), so sorting by `number` gives "in location order".
"""

from fransys_model.layout import DrawingSet, layout_of
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.document import Document

from .document_scope import document_scope

__all__ = ["document_drawing_sets", "printed_drawing_sets"]


def document_drawing_sets(model: Model, document: Id[Document]) -> tuple[DrawingSet, ...]:
    """The drawing sets `document` prints, by `number`: `document_scope`'s `drawing_sets`.

    `document` is the document's id.
    """
    held = set(document_scope(model, document).drawing_sets)
    found = [s for s in layout_of(model, DrawingSet).values() if s.id in held]
    return tuple(sorted(found, key=lambda s: s.number))


def printed_drawing_sets(model: Model) -> tuple[DrawingSet, ...]:
    """The sets some document of `model` prints, by `number`; none that no document prints."""
    printed = {
        s.id: s for doc in documents(model).values() for s in document_drawing_sets(model, doc.id)
    }
    return tuple(sorted(printed.values(), key=lambda found: found.number))
