"""Whether a document's subject has schematic drawings: a location, a unit or the design root, not an item."""

from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

__all__ = ["has_schematic_subject"]


def has_schematic_subject(model: Model, document: Id[Document]) -> bool:
    """True for a location, unit or root (subject-less) document; an item document draws no schematic.

    `document` is the document's id.
    """
    record = documents(model)[document]
    return record.item is None
