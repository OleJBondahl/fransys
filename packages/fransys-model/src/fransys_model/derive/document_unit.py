"""The one reader of a `Document`'s subject unit, by id or by release name (spec UN1, UN2)."""

from fransys_model.vocab.unit_by_name import units_named
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit
lazy from fransys_model.vocab.document import Document


def document_unit(model: Model, document: Document) -> Id[Unit] | None:
    """The unit `document` is about: `document.unit` when set, else its resolved `unit_name`.

    `document.unit` wins when set. Else, for a `unit_name`, the one id `units_named` finds;
    `None` for zero or several matches (silently: a pure reader, never a validator) and `None`
    when the document has neither field set. Never re-derives the match: `vocab.unit_by_name`
    is its only home.

    Example: `document_unit(model, Document(unit_name="relay-board", ...))` returns the id of
    the one `Unit` instance of a release named `"relay-board"`, or `None` if that name matches
    zero or several units.
    """
    if document.unit is not None:
        return document.unit
    if document.unit_name is None:
        return None
    matches = units_named(model, document.unit_name)
    return matches[0] if len(matches) == 1 else None
