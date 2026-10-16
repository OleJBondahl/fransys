"""Document and revision rows: what an output reads of an authored document (model-0305).

An output holds no `Document` or `Revision` record (M10): it reads these rows, in the model's
own order, and passes `DocumentRow.id` to the derive functions that take a document.
"""

from fransys_model.kernel import Id, Model, value
from fransys_model.vocab import Document, DocumentPreset, UnitRelease
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item
from fransys_model.vocab.tables import documents

from .revisions import revision_history

__all__ = ["DocumentRow", "RevisionRow", "document_row", "document_rows", "revision_rows"]


@value
class DocumentRow:
    """The fields of one `Document` an output reads.

    `location` and `item` are the subject's ids (the `SYSTEM` preset has neither), `cover` and
    `notes` the Markdown texts (`notes` is `None` when dropped) and `logo` the title block's SVG.
    """

    id: Id[Document]
    preset: DocumentPreset
    location: Id[AspectNode] | None
    item: Id[Item] | None
    cover: str
    notes: str | None
    logo: str | None


@value
class RevisionRow:
    """One revision-history entry, as the revision table prints it."""

    version: int
    revision: int
    date: str
    text: str
    created: str
    checked: str
    approved: str


def _row(record: Document) -> DocumentRow:
    return DocumentRow(
        id=record.id,
        preset=record.preset,
        location=record.location,
        item=record.item,
        cover=record.cover,
        notes=record.notes,
        logo=record.logo,
    )


def document_rows(model: Model) -> tuple[DocumentRow, ...]:
    """One row per document, in `documents(model)` order."""
    return tuple(_row(record) for record in documents(model).values())


def document_row(model: Model, document: Id[Document]) -> DocumentRow:
    """The row of `document`; raises `KeyError` when the id names no document of `model`."""
    return _row(documents(model)[document])


def revision_rows(model: Model, release: Id[UnitRelease] | None = None) -> tuple[RevisionRow, ...]:
    """`revision_history` as rows: date order, then version and revision order."""
    return tuple(
        RevisionRow(
            version=e.version,
            revision=e.revision,
            date=e.date,
            text=e.text,
            created=e.created,
            checked=e.checked,
            approved=e.approved,
        )
        for e in revision_history(model, release)
    )
