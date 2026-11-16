"""The one reader of whether a document is the SYSTEM document."""

from fransys_model.vocab import DocumentPreset
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document


def is_system_document(model: Model, document: Id[Document]) -> bool:
    """Whether the document, by id, has the `SYSTEM` preset (the one home of that question)."""
    return documents(model)[document].preset is DocumentPreset.SYSTEM
