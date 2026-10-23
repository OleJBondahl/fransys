"""Validator: revision history entries."""

import re
from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import finding, ordered
from fransys_model.derive.facts.house_settings import revision_form_of
from fransys_model.derive.facts.revision_label import revision_label
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import projects, revisions, unit_releases

if TYPE_CHECKING:
    from fransys_model.kernel import Model

REVISION_CURRENT_MISSING: Final[str] = "REVISION_CURRENT_MISSING"
REVISION_DATE_FORMAT: Final[str] = "REVISION_DATE_FORMAT"
REVISION_INITIALS_MISSING: Final[str] = "REVISION_INITIALS_MISSING"

_DATE_LETTERS: Final = {"YYYY": "[0-9]{4}", "MM": "[0-9]{2}", "DD": "[0-9]{2}"}
_ADD_ENTRY: Final[str] = "add one with its date, text and author initials"


def _date_regex(pattern: str) -> re.Pattern[str]:
    """The regex of a date pattern: `YYYY`, `MM` and `DD` are digit groups, the rest literal."""
    parts = re.split("(YYYY|MM|DD)", pattern)
    return re.compile("".join(_DATE_LETTERS.get(p) or re.escape(p) for p in parts))


def _current_missing(model: Model) -> list[Finding]:
    current = {
        (entry.release, entry.version, entry.revision) for entry in revisions(model).values()
    }
    form = revision_form_of(model)
    found = []
    # One finding per unit release record: its instances share it and its history.
    # Subject: the release's id.
    for release in unit_releases(model).values():
        if (release.id, release.version, release.revision) in current:
            continue
        message = f"{ref(release)}: its current revision has no Revision entry: {_ADD_ENTRY}"
        found.append(finding(REVISION_CURRENT_MISSING, Severity.ERROR, (release.id,), message))
    for project in projects(model).values():
        if (None, project.version, project.revision) not in current:
            text = revision_label(form, project.version, project.revision)
            message = f"project's current revision {text} has no Revision entry: {_ADD_ENTRY}"
            found.append(finding(REVISION_CURRENT_MISSING, Severity.ERROR, (project.id,), message))
    return found


def _date_format(model: Model) -> list[Finding]:
    form = revision_form_of(model)
    date_re = _date_regex(form.date_format)
    found = []
    for entry in revisions(model).values():
        if not date_re.fullmatch(entry.date):
            text = revision_label(form, entry.version, entry.revision)
            message = f"revision {text}'s date {entry.date!r} is not {form.date_format}"
            found.append(finding(REVISION_DATE_FORMAT, Severity.ERROR, (entry.id,), message))
    return found


def _initials_missing(model: Model) -> list[Finding]:
    form = revision_form_of(model)
    if not form.initials_required:
        return []
    found = []
    for entry in revisions(model).values():
        if entry.created == "":
            text = revision_label(form, entry.version, entry.revision)
            message = f"revision {text} has no created initials"
            found.append(finding(REVISION_INITIALS_MISSING, Severity.ERROR, (entry.id,), message))
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
    return ordered(found)
