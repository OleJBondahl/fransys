"""Tests for `validators.revisions` (units spec U4, schema spec SC2, SC5)."""

import re

import pytest

from fransys_model.kernel import (
    Draft,
    Finding,
    Id,
    Model,
    Origin,
    Record,
    Severity,
    freeze,
    make_id,
)
from fransys_model.vocab.core import Unit, UnitRelease
from fransys_model.vocab.project import Project
from fransys_model.vocab.revision import Revision
from fransys_model.vocab.tables import projects, revisions, unit_releases, units
from fransys_model.vocab.validators.revisions import (
    REVISION_CURRENT_MISSING,
    REVISION_DATE_FORMAT,
    REVISION_INITIALS_MISSING,
    check_revisions,
)


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    origin = Origin(file="test_validator_revision.py", line=1, note="fixture")
    draft.extend(records, origin=origin)
    return freeze(draft)


def _release(*, name: str = "board", version: int = 1, revision: int = 1) -> UnitRelease:
    key = ("unit_release", name, str(version), str(revision))
    return UnitRelease(
        id=make_id(UnitRelease, key),
        key=key,
        name=name,
        version=version,
        revision=revision,
        interface="1",
    )


def _instance(key: str, release: UnitRelease) -> Unit:
    """One instance of `release`, told apart by its key."""
    return Unit(id=make_id(Unit, (key,)), key=(key,), release=release.id, parent=None)


def _project(*, revision: int = 1) -> Project:
    return Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title="Invented pump station",
        number="P-0001",
        customer="Invented Customer AS",
        revision=revision,
        author="N. N.",
    )


def _revision(  # noqa: PLR0913 -- one keyword per Revision field the tests vary, kept explicit
    key: str,
    *,
    release: Id[UnitRelease] | None = None,
    version: int = 1,
    revision: int = 1,
    date: str = "2026-09-23",
    created: str = "OJB",
) -> Revision:
    return Revision(
        id=make_id(Revision, (key,)),
        key=(key, "revision", str(revision)),
        release=release,
        version=version,
        revision=revision,
        date=date,
        text="First release",
        created=created,
    )


def _missing(model: Model) -> list[Finding]:
    return [f for f in check_revisions(model) if f.code == REVISION_CURRENT_MISSING]


def test_release_revision_with_no_matching_entry_yields_revision_current_missing() -> None:
    """A release whose revision has no `Revision(release=..., revision=...)` entry is `ERROR`."""
    release = _release(revision=1)
    model = _freeze((release, _instance("board", release)))
    # examined: the release is in the model and carries no Revision entry at all
    assert unit_releases(model)[release.id].revision == 1
    assert len(revisions(model)) == 0
    matches = _missing(model)
    assert len(matches) == 1
    assert matches[0].severity is Severity.ERROR
    assert matches[0].subjects == (release.id,)


def test_release_revision_current_missing_text_says_what_to_add_in_model_terms() -> None:
    """G4: the release text names the release, its current revision and what the entry needs."""
    release = _release(revision=1)
    model = _freeze((release, _instance("board", release)))
    expected = (
        "unit 'board': its current revision 1.1 has no Revision entry: "
        "add one with its date, text and author initials"
    )
    assert [f.message for f in _missing(model)] == [expected]


def test_a_missing_current_revision_message_names_no_authoring_call() -> None:
    """SC5: the text is in model terms: "Revision entry" and what to add, no `.revision(` call."""
    release = _release(revision=1)
    model = _freeze((release, _instance("board", release), _project(revision=2)))
    matches = _missing(model)
    assert len(matches) == 2
    for finding in matches:
        assert "Revision entry" in finding.message
        assert "date, text and author initials" in finding.message
        assert "revision(" not in finding.message
        assert not re.search(r"\b[ds]\.", finding.message)


def test_a_project_with_a_current_revision_and_no_entry_yields_one_error() -> None:
    """SC5 (a): the project's own `(None, revision)` entry is missing: one ERROR on the project."""
    project = _project(revision=1)
    model = _freeze((project,))
    assert len(revisions(model)) == 0
    matches = _missing(model)
    assert len(matches) == 1
    assert matches[0].severity is Severity.ERROR
    assert matches[0].subjects == (project.id,)


@pytest.mark.parametrize("count", [2, 3])
def test_instances_of_one_release_with_no_entry_yield_one_finding_on_the_release(
    count: int,
) -> None:
    """SC5 (c): the finding is per release record, not per instance; its subject is the release."""
    release = _release()
    instances = tuple(_instance(key, release) for key in ("a", "b", "c")[:count])
    model = _freeze((release, *instances))
    assert len(units(model)) == count
    assert len(unit_releases(model)) == 1
    matches = _missing(model)
    assert len(matches) == 1
    assert matches[0].severity is Severity.ERROR
    assert matches[0].subjects == (release.id,)
    assert all(unit.id not in matches[0].subjects for unit in instances)


def test_two_different_releases_with_no_entries_yield_two_findings() -> None:
    """SC5 (d): a different name, a different revision or a different version is its own release."""
    board = _release(name="relay-board", revision=1)
    other_revision = _release(name="relay-board", revision=2)
    other_version = _release(name="relay-board", version=2, revision=1)
    other_name = _release(name="io-board", revision=1)
    for pair in ((board, other_revision), (board, other_name), (board, other_version)):
        model = _freeze(tuple(_instance(f"i{n}", release) for n, release in enumerate(pair)) + pair)
        assert {f.subjects for f in _missing(model)} == {(r.id,) for r in pair}


def test_a_model_with_no_project_yields_no_project_finding() -> None:
    """SC5 (e): with no `Project` record there is no project revision to be missing."""
    release = _release()
    model = _freeze((release, _instance("a", release)))
    assert len(projects(model)) == 0
    # examined: the release's own finding is there, so the empty-project result is not a blank check
    assert [f.subjects for f in _missing(model)] == [(release.id,)]
    assert not _missing(_freeze(()))


def test_a_release_with_its_entry_yields_no_finding_whatever_its_instances() -> None:
    """SC5 (f): one entry of the release covers it; its instances carry no entry of their own."""
    release = _release()
    instances = tuple(_instance(key, release) for key in ("a", "b", "c"))
    entry = _revision("r1", release=release.id, revision=1)
    model = _freeze((release, *instances, entry))
    # examined: the entry names the release, and no instance holds an entry
    assert revisions(model)[entry.id].release == release.id
    assert not _missing(model)
    # a same-name release at another revision is still its own release, still missing
    later = _release(revision=2)
    model = _freeze((release, *instances, entry, later, _instance("d", later)))
    assert [f.subjects for f in _missing(model)] == [(later.id,)]


def test_a_release_whose_entry_is_of_another_revision_is_still_missing() -> None:
    """SC5 (f), twin: the entry must match the release's revision, not just its release."""
    release = _release(revision=2)
    entry = _revision("r1", release=release.id, revision=1)
    matches = _missing(_freeze((release, _instance("a", release), entry)))
    assert [f.subjects for f in matches] == [(release.id,)]


def test_a_release_whose_entry_is_of_another_version_is_still_missing() -> None:
    """FD4: the entry is matched by `(version, revision)`; version 2 does not cover version 1."""
    release = _release(version=1, revision=1)
    entry = _revision("r1", release=release.id, version=2, revision=1)
    matches = _missing(_freeze((release, _instance("a", release), entry)))
    assert [f.subjects for f in matches] == [(release.id,)]
    covering = _revision("r2", release=release.id, version=1, revision=1)
    assert not _missing(_freeze((release, _instance("a", release), entry, covering)))


def test_project_revision_current_missing_text_says_what_to_add_in_model_terms() -> None:
    """G4: the project variant has the same shape, in model terms."""
    project = _project(revision=2)
    model = _freeze((project,))
    expected = (
        "project's current revision 1.2 has no Revision entry: "
        "add one with its date, text and author initials"
    )
    assert [f.message for f in _missing(model)] == [expected]


def test_release_revision_with_a_matching_entry_yields_no_revision_current_missing() -> None:
    """Clean twin: the matching `Revision` entry is present."""
    release = _release(revision=1)
    entry = _revision("r1", release=release.id, revision=1)
    model = _freeze((release, _instance("board", release), entry))
    # examined: the entry that makes this clean is really in the model, matching the release
    assert revisions(model)[entry.id].release == release.id
    assert revisions(model)[entry.id].revision == unit_releases(model)[release.id].revision == 1
    assert not _missing(model)


def test_project_revision_with_only_a_releases_entry_still_yields_revision_current_missing() -> (
    None
):
    """Discriminates matching by `(release, revision)`, not by revision number alone.

    A `Revision(release=<the release>, revision=1)` does not satisfy the project's own
    `revision=1`: the project needs its own `release=None` entry.
    """
    release = _release(revision=1)
    project = _project(revision=1)
    entry = _revision("r1", release=release.id, revision=1)
    model = _freeze((release, _instance("board", release), project, entry))
    # examined: the only entry present belongs to the release, not the project
    assert revisions(model)[entry.id].release == release.id
    matches = _missing(model)
    assert len(matches) == 1
    assert project.id in matches[0].subjects
    assert release.id not in matches[0].subjects


def test_project_revision_with_its_own_entry_yields_no_revision_current_missing() -> None:
    """Clean twin: a second entry, `release=None`, matches the project's own revision."""
    release = _release(revision=1)
    project = _project(revision=1)
    release_entry = _revision("r1", release=release.id, revision=1)
    project_entry = _revision("r2", release=None, revision=1)
    model = _freeze((release, _instance("board", release), project, release_entry, project_entry))
    # examined: the project's own entry is present, with release=None and a matching revision
    assert revisions(model)[project_entry.id].release is None
    assert revisions(model)[project_entry.id].revision == projects(model)[project.id].revision
    assert not _missing(model)


@pytest.mark.parametrize("bad", ["23-09-2026", "2026-9-23", "2026-09-23\n"])
def test_a_badly_formed_date_yields_revision_date_format(bad: str) -> None:
    """A `Revision.date` that is not `YYYY-MM-DD` is `ERROR`; a trailing newline still fails."""
    entry = _revision("r1", date=bad)
    model = _freeze((entry,))
    assert revisions(model)[entry.id].date == bad
    findings = check_revisions(model)
    matches = [f for f in findings if f.code == REVISION_DATE_FORMAT]
    assert len(matches) == 1
    assert matches[0].severity is Severity.ERROR
    assert entry.id in matches[0].subjects


def test_revision_date_in_iso_form_yields_no_revision_date_format() -> None:
    """Clean twin: an ISO 8601 `date`."""
    entry = _revision("r1", date="2026-09-23")
    model = _freeze((entry,))
    assert revisions(model)[entry.id].date == "2026-09-23"
    findings = check_revisions(model)
    assert not [f for f in findings if f.code == REVISION_DATE_FORMAT]


def test_a_revision_with_no_created_initials_yields_revision_initials_missing() -> None:
    """A `Revision` with `created=""` is `ERROR`."""
    entry = _revision("r1", created="")
    model = _freeze((entry,))
    assert revisions(model)[entry.id].created == ""
    findings = check_revisions(model)
    matches = [f for f in findings if f.code == REVISION_INITIALS_MISSING]
    assert len(matches) == 1
    assert matches[0].severity is Severity.ERROR
    assert entry.id in matches[0].subjects


def test_a_revision_with_created_initials_yields_no_revision_initials_missing() -> None:
    """Clean twin: `created="OJB"`."""
    entry = _revision("r1", created="OJB")
    model = _freeze((entry,))
    assert revisions(model)[entry.id].created == "OJB"
    findings = check_revisions(model)
    assert not [f for f in findings if f.code == REVISION_INITIALS_MISSING]
