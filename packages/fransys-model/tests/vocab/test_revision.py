"""Tests for `Revision`, the unit's or the project's history entry (units spec U4)."""

from typing import Any

from fransys_model.kernel import Draft, Origin, dumps, freeze, loads, make_id
from fransys_model.vocab.core import Unit, UnitRelease
from fransys_model.vocab.revision import Revision
from fransys_model.vocab.tables import revisions

_ORIGIN = Origin(file="test_revision.py", line=1, note="fixture")
_RELEASE_KEY = ("unit_release", "board", "1", "2")
_RELEASE = make_id(UnitRelease, _RELEASE_KEY)


def _unit() -> tuple[UnitRelease, Unit]:
    """The release `board` revision 2 and one instance of it."""
    release = UnitRelease(
        id=_RELEASE, key=_RELEASE_KEY, name="board", version=1, revision=2, interface="1"
    )
    unit = Unit(id=make_id(Unit, ("board",)), key=("board",), release=release.id, parent=None)
    return release, unit


def _revision(key: str, **fields: Any) -> Revision:
    base: dict[str, Any] = {
        "id": make_id(Revision, (key,)),
        "key": (key, "revision", "1"),
        "release": None,
        "version": 1,
        "revision": 1,
        "date": "2026-09-23",
        "text": "First release",
        "created": "OJB",
    }
    return Revision(**{**base, **fields})


def test_a_project_revision_with_every_field_set_round_trips() -> None:
    """`release=None`, `checked` and `approved` both set: comes back equal."""
    revision = _revision("r1", checked="KN", approved="OJB")
    draft = Draft()
    draft.add(revision, origin=_ORIGIN)
    model = freeze(draft)
    text = dumps(model)
    assert loads(text) == model
    assert revisions(loads(text))[revision.id] == revision


def test_a_release_revision_with_default_checked_and_approved_round_trips() -> None:
    """`checked=""`, `approved=""` at their defaults, `release` set: comes back equal."""
    revision = _revision("r2", release=_RELEASE, revision=2, text="Second release")
    draft = Draft()
    draft.extend((*_unit(), revision), origin=_ORIGIN)
    model = freeze(draft)
    text = dumps(model)
    assert loads(text) == model
    assert revision.checked == ""
    assert revision.approved == ""
    assert revisions(loads(text))[revision.id] == revision


def test_revisions_returns_exactly_the_records_added() -> None:
    """`revisions(model)` reaches every `Revision`, no more, no fewer (count asserted first)."""
    r1 = _revision("r1")
    r2 = _revision("r2", release=_RELEASE, revision=2, text="Second release")
    draft = Draft()
    draft.extend((*_unit(), r1, r2), origin=_ORIGIN)
    model = freeze(draft)
    table = revisions(model)
    assert len(table) == 2
    assert set(table) == {r1.id, r2.id}
