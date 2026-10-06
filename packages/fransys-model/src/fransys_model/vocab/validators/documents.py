"""Validator: a document's `unit_name` resolves to one unit (spec unit-subject-by-name UN3)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.tables import documents
from fransys_model.vocab.unit_by_name import unit_name_unresolved, units_named

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model

DOCUMENT_UNIT_UNRESOLVED: Final[str] = "DOCUMENT_UNIT_UNRESOLVED"


def _finding(subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(
        code=DOCUMENT_UNIT_UNRESOLVED,
        severity=Severity.ERROR,
        subjects=tuple(subjects),
        message=message,
    )


def check_documents(model: Model) -> tuple[Finding, ...]:
    """Check every `Document.unit_name` resolves to one unit.

    Zero or several `units_named` ids: `DOCUMENT_UNIT_UNRESOLVED` (`ERROR`), subject the document.
    Only `unit_name` documents are checked; findings sorted by `(code, subjects, message)`.
    """
    found = []
    for document in documents(model).values():
        if document.unit_name is None:
            continue
        matches = units_named(model, document.unit_name)
        if len(matches) == 1:
            continue
        message = unit_name_unresolved(model, document.unit_name)
        found.append(_finding((document.id,), message))
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
