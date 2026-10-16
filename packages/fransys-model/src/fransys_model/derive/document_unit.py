"""The one reader of a `Document`'s subject unit, by id or by release name."""

from fransys_model.derive.facts.unit_names import units_named
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit
lazy from fransys_model.vocab.document import Document


def document_unit(model: Model, document_id: Id[Document]) -> Id[Unit] | None:
    """The unit of the document `document_id`: its `unit` when set, else its resolved `unit_name`.

    The document's `unit` wins when set. Else, for a `unit_name`, the one id `units_named` finds;
    `None` for zero or several matches (silently: a pure reader, never a validator) and `None`
    when the document has neither field set. Never re-derives the match: `derive.facts.unit_names`
    is its only home.

    Example: `document_unit(model, document_id)` for a `Document(unit_name="relay-board", ...)`
    returns the id of the one `Unit` instance of a release named `"relay-board"`, or `None` if
    that name matches zero or several units.
    """
    return record_unit(model, documents(model)[document_id])


def record_unit(model: Model, document: Document) -> Id[Unit] | None:
    """`document_unit` for a record the caller already holds."""
    if document.unit is not None:
        return document.unit
    if document.unit_name is None:
        return None
    matches = units_named(model, document.unit_name)
    return matches[0] if len(matches) == 1 else None
