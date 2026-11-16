"""Validator: a document's `unit_name` resolves to one unit (spec unit-subject-by-name)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.system_document import is_system_document
from fransys_model.derive.facts.unit_names import unit_name_unresolved, units_named
from fransys_model.vocab.codes import finding
from fransys_model.vocab.tables import documents, projects
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Model

DOCUMENT_UNIT_UNRESOLVED: Final[str] = "DOCUMENT_UNIT_UNRESOLVED"
SYSTEM_DOCUMENT_NO_PROJECT: Final[str] = "SYSTEM_DOCUMENT_NO_PROJECT"


def check_documents(model: Model) -> tuple[Finding, ...]:
    """Check every `Document.unit_name` resolves to one unit.

    Zero or several `units_named` ids: `DOCUMENT_UNIT_UNRESOLVED` (`ERROR`), subject the document; a `SYSTEM` document
    with no `Project` is `SYSTEM_DOCUMENT_NO_PROJECT`. Findings sorted by `(code, subjects, message)`.
    """
    found = []
    for document in documents(model).values():
        if document.unit_name is None:
            continue
        matches = units_named(model, document.unit_name)
        if len(matches) == 1:
            continue
        message = unit_name_unresolved(model, document.unit_name)
        found.append(finding(DOCUMENT_UNIT_UNRESOLVED, (document.id,), message))
    return ordered([*found, *_system_without_project(model)])


def _system_without_project(model: Model) -> list[Finding]:
    """One `SYSTEM_DOCUMENT_NO_PROJECT` per `SYSTEM` document while the model holds no `Project`."""
    if projects(model):
        return []
    message = "A SYSTEM document names the project title, and this design declares no Project."
    return [finding(SYSTEM_DOCUMENT_NO_PROJECT, (doc.id,), message) for doc in documents(model).values() if is_system_document(model, doc.id)]
