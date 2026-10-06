"""Validator: revision history entries (units spec U4)."""

import re
from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.revision_text import revision_text
from fransys_model.vocab.tables import projects, revisions, unit_releases

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model

REVISION_CURRENT_MISSING: Final[str] = "REVISION_CURRENT_MISSING"
REVISION_DATE_FORMAT: Final[str] = "REVISION_DATE_FORMAT"
REVISION_INITIALS_MISSING: Final[str] = "REVISION_INITIALS_MISSING"

_DATE_RE: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ADD_ENTRY: Final[str] = "add one with its date, text and author initials"


def _finding(code: str, severity: Severity, subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(code=code, severity=severity, subjects=tuple(subjects), message=message)


def _current_missing(model: Model) -> list[Finding]:
    current = {
        (entry.release, entry.version, entry.revision) for entry in revisions(model).values()
    }
    found = []
    # One finding per unit release record (SC2, SC5): its instances share it and its history.
    # Subject: the release's id.
    for release in unit_releases(model).values():
        if (release.id, release.version, release.revision) in current:
            continue
        text = revision_text(release.version, release.revision)
        message = (
            f"unit {release.name!r}: its current revision {text} has no Revision "
            f"entry: {_ADD_ENTRY}"
        )
        found.append(_finding(REVISION_CURRENT_MISSING, Severity.ERROR, (release.id,), message))
    for project in projects(model).values():
        if (None, project.version, project.revision) not in current:
            text = revision_text(project.version, project.revision)
            message = f"project's current revision {text} has no Revision entry: {_ADD_ENTRY}"
            found.append(_finding(REVISION_CURRENT_MISSING, Severity.ERROR, (project.id,), message))
    return found


def _date_format(model: Model) -> list[Finding]:
    found = []
    for entry in revisions(model).values():
        if not _DATE_RE.fullmatch(entry.date):
            message = f"revision {key_text(entry)}'s date {entry.date!r} is not YYYY-MM-DD"
            found.append(_finding(REVISION_DATE_FORMAT, Severity.ERROR, (entry.id,), message))
    return found


def _initials_missing(model: Model) -> list[Finding]:
    found = []
    for entry in revisions(model).values():
        if entry.created == "":
            message = f"revision {key_text(entry)} has no created initials"
            found.append(_finding(REVISION_INITIALS_MISSING, Severity.ERROR, (entry.id,), message))
    return found


def check_revisions(model: Model) -> tuple[Finding, ...]:
    """Check the revision history against `UnitRelease` and `Project` revisions.

    `REVISION_CURRENT_MISSING`, `REVISION_DATE_FORMAT`, `REVISION_INITIALS_MISSING`: all `ERROR`.
    A missing current revision: no title block date; sorted by `(code, subjects, message)`.
    """
    found = [
        *_current_missing(model),
        *_date_format(model),
        *_initials_missing(model),
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
