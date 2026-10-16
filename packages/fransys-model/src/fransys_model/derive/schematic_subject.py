"""Whether a document's subject has schematic drawings: a location or a unit, not an item."""

from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

__all__ = ["has_schematic_subject"]


def has_schematic_subject(model: Model, document: Id[Document]) -> bool:
    """True for a location or unit document; an item or SYSTEM document draws no schematic.

    `document` is the document's id.
    """
    record = documents(model)[document]
    return record.location is not None or record.unit is not None or record.unit_name is not None
