"""The facts a document's title block prints: title, number, customer, revision, date, author.

One home for the Author cell and its siblings (CL6, decision layout-0230); pdf reads them.
"""

from fransys_model.derive.document_unit import document_unit
from fransys_model.derive.facts.house_settings import revision_form_of
from fransys_model.derive.facts.revision_label import revision_label
from fransys_model.derive.revisions import current_revision
from fransys_model.derive.unit_release import unit_release
from fransys_model.vocab.tables import projects
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.document import Document

__all__ = ["document_facts", "project_facts"]


def project_facts(model: Model) -> tuple[str, str, str, str, str, str]:
    """(title, number, customer, revision, revision_date, author); all empty with no `Project`."""
    table = projects(model)
    if not table:
        return ("", "", "", "", "", "")
    record = next(iter(table.values()))
    current = current_revision(model)
    form = revision_form_of(model)
    return (
        record.title,
        record.number,
        record.customer,
        revision_label(form, record.version, record.revision),
        "" if current is None else current.date,
        record.author,
    )


def document_facts(model: Model, document: Id[Document]) -> tuple[str, str, str, str, str, str]:
    """`project_facts`, or for a unit document the unit release's own, customer empty.

    A unit document's author is the `created` of the unit's current revision.

    `document` is the document's id.
    """
    unit = document_unit(model, document)
    if unit is None:
        return project_facts(model)
    release = unit_release(model, unit)
    matching = current_revision(model, release.id)
    revision_date, author = ("", "") if matching is None else (matching.date, matching.created)
    return (
        release.title,
        release.number,
        "",
        revision_label(revision_form_of(model), release.version, release.revision),
        revision_date,
        author,
    )
