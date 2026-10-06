"""Tests for `derive.current_revision` (schema spec SC4, units spec U4)."""

from typing import Any

import pytest

from fransys_model.derive import current_revision
from fransys_model.kernel import Draft, Id, Model, Origin, Record, SchemaError, freeze, make_id
from fransys_model.vocab.core import Unit, UnitRelease
from fransys_model.vocab.project import Project
from fransys_model.vocab.revision import Revision

_ORIGIN = Origin(file="test_current_revision_model.py", line=1, note="fixture")
_UNIT = make_id(Unit, ("board",))


def _model(*records: Record) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _release(revision: int = 1) -> UnitRelease:
    key = ("unit_release", "board", "1", str(revision))
    return UnitRelease(
        id=make_id(UnitRelease, key),
        key=key,
        name="board",
        version=1,
        revision=revision,
        interface="1",
    )


def _unit(revision: int = 1) -> tuple[UnitRelease, Unit]:
    release = _release(revision)
    return release, Unit(id=_UNIT, key=("board",), release=release.id, parent=None)


def _project(revision: int = 1) -> Project:
    return Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title="Invented pump station",
        number="P-0001",
        customer="Invented Customer AS",
        revision=revision,
        author="N. N.",
    )


def _revision(key: str, **fields: Any) -> Revision:
    base: dict[str, Any] = {
        "id": make_id(Revision, (key,)),
        "key": (key, "revision"),
        "release": None,
        "version": 1,
        "revision": 1,
        "date": "2026-01-01",
        "text": "",
        "created": "OJB",
    }
    return Revision(**{**base, **fields})


def test_the_project_current_entry_is_returned() -> None:
    """The entry whose `revision` equals `Project.revision` and whose `release` is `None`."""
    current = _revision("current", revision=2, date="2026-02-01")
    older = _revision("older", revision=1, date="2026-01-01")
    unit_entry = _revision("unit", release=_release(2).id, revision=2, date="2026-02-02")
    model = _model(_project(2), *_unit(2), current, older, unit_entry)
    assert current_revision(model) == current
    assert current_revision(model, None) == current


def test_the_current_entry_is_not_the_latest_one() -> None:
    """Current, not latest: an entry with a later date but another revision is not returned."""
    current = _revision("current", revision=1, date="2026-01-01")
    later = _revision("later", revision=2, date="2026-06-01")
    model = _model(_project(1), current, later)
    result = current_revision(model)
    assert result == current
    assert result != later


def test_no_project_gives_none() -> None:
    """A model without a `Project` has no current revision to miss, whatever entries it holds."""
    model = _model(_revision("r1"))
    assert current_revision(model) is None


def test_a_project_revision_with_no_entry_gives_none() -> None:
    """The project's revision is 2, and only 1 has an entry."""
    model = _model(_project(2), _revision("r1", revision=1))
    assert current_revision(model) is None


def test_a_releases_current_entry_is_returned() -> None:
    """The entry with `release=<id>` and `revision == UnitRelease.revision`, not the project's."""
    release = _release(2)
    current = _revision("current", release=release.id, revision=2, date="2026-02-01")
    older = _revision("older", release=release.id, revision=1, date="2026-01-01")
    later = _revision("later", release=release.id, revision=3, date="2026-03-01")
    project_entry = _revision("project", release=None, revision=2, date="2026-02-09")
    model = _model(_project(2), *_unit(2), current, older, later, project_entry)
    assert current_revision(model, release.id) == current


def test_a_release_whose_current_revision_has_no_entry_gives_none() -> None:
    """The release is at 3; only 1 and 2 have entries. The project's 3 is not its."""
    release = _release(3)
    project_entry = _revision("project", release=None, revision=3)
    model = _model(
        _project(3),
        *_unit(3),
        _revision("one", release=release.id, revision=1),
        _revision("two", release=release.id, revision=2),
        project_entry,
    )
    assert current_revision(model, None) == project_entry
    assert current_revision(model, release.id) is None


def test_an_unknown_release_raises_schema_error() -> None:
    """A release id the model does not hold is a caller error, not `None`."""
    other: Id[UnitRelease] = make_id(UnitRelease, ("ghost",))
    release = _release()
    model = _model(_project(), *_unit(), _revision("r1", release=release.id))
    with pytest.raises(SchemaError):
        current_revision(model, other)
