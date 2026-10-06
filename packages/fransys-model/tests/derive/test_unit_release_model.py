"""Tests for `derive.unit_release`, the one reader of a unit's release facts (schema spec SC2)."""

import pytest

from fransys_model.derive import unit_release
from fransys_model.kernel import Draft, Id, Model, Origin, SchemaError, freeze, make_id
from fransys_model.vocab.core import Unit, UnitRelease

_ORIGIN = Origin(file="test_unit_release_model.py", line=1, note="fixture")
_RELEASE_KEY = ("unit_release", "demo-io-board", "2", "3")
_RELEASE = make_id(UnitRelease, _RELEASE_KEY)
_UNIT = make_id(Unit, ("board",))


def _model() -> Model:
    draft = Draft()
    release = UnitRelease(
        id=_RELEASE,
        key=_RELEASE_KEY,
        name="demo-io-board",
        version=2,
        revision=3,
        interface="7",
        title="Relay interface board",
        number="SKX-RIB-2",
    )
    unit = Unit(id=_UNIT, key=("board",), release=_RELEASE, parent=None)
    draft.extend([release, unit], origin=_ORIGIN)
    return freeze(draft)


def test_each_release_fact_is_read_from_its_own_field() -> None:
    """Six different values: a mixed-up field makes exactly one assertion fail."""
    release = unit_release(_model(), _UNIT)
    assert release.name == "demo-io-board"
    assert release.version == 2
    assert release.revision == 3
    assert release.interface == "7"
    assert release.title == "Relay interface board"
    assert release.number == "SKX-RIB-2"


def test_the_reader_returns_the_release_record_the_unit_points_at() -> None:
    """SC2: the reader is a view of the table, not a copy: the record itself, by `Unit.release`."""
    release = unit_release(_model(), _UNIT)
    assert isinstance(release, UnitRelease)
    assert release.id == _RELEASE


def test_a_bad_unit_id_raises() -> None:
    """An id the model holds no `Unit` for is refused with `SchemaError`, kind `unit`."""
    other: Id[Unit] = make_id(Unit, ("nothing",))
    with pytest.raises(SchemaError) as raised:
        unit_release(_model(), other)
    assert raised.value.kind == "unit"
