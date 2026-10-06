"""The `unit_release` kind and the version and revision rule (schema spec SC2, FD4).

A version or a revision below 1 is refused when a `UnitRelease`, `Project` or `Revision` is
made, through one helper (`release_version.refuse_below_one`). Invented data only.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

import pytest

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Origin,
    SchemaError,
    freeze,
    key_text,
    make_id,
)
from fransys_model.vocab import (
    Project,
    Revision,
    Unit,
    UnitRelease,
    revisions,
    unit_releases,
)
from fransys_model.vocab.release_version import refuse_below_one

if TYPE_CHECKING:
    from collections.abc import Callable

_ORIGIN = Origin(file="test_unit_release_record.py", line=1, note="fixture")


def _release(version: int = 1, revision: int = 1, **fields: Any) -> UnitRelease:
    key = ("unit_release", "demo-io-board", str(version), str(revision))
    return UnitRelease(
        id=make_id(UnitRelease, key),
        key=key,
        name="demo-io-board",
        version=version,
        revision=revision,
        interface="1",
        **fields,
    )


def _project(version: int = 1, revision: int = 1) -> Project:
    return Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title="Invented pump station",
        number="P-0001",
        customer="Invented Customer AS",
        revision=revision,
        author="N. N.",
        version=version,
    )


def _revision(version: int = 1, revision: int = 1) -> Revision:
    key = ("revision", str(version), str(revision))
    return Revision(
        id=make_id(Revision, key),
        key=key,
        release=None,
        version=version,
        revision=revision,
        date="2026-09-26",
        text="First issue",
        created="XX",
    )


# The kind each maker's record is registered under, which the refusal names.
_MAKERS: dict[str, Callable[..., Any]] = {
    "unit_release": _release,
    "project": _project,
    "revision": _revision,
}


@pytest.mark.parametrize("value", [0, -1])
@pytest.mark.parametrize("field", ["version", "revision"])
@pytest.mark.parametrize("kind", list(_MAKERS))
def test_a_number_below_one_is_refused_when_the_record_is_made(
    kind: str, field: str, value: int
) -> None:
    """Can fail: without the `__post_init__` call, the record is made and no error is raised."""
    with pytest.raises(SchemaError) as raised:
        _MAKERS[kind](**{field: value})
    assert raised.value.kind == kind
    assert raised.value.record_id is not None
    assert raised.value.record_id.kind == kind
    assert f"{field} {value}" in str(raised.value)


@pytest.mark.parametrize("value", [1, 2])
@pytest.mark.parametrize("field", ["version", "revision"])
@pytest.mark.parametrize("kind", list(_MAKERS))
def test_one_and_two_are_accepted(kind: str, field: str, value: int) -> None:
    """The refusal is at 1, not above it: 1 and 2 make a record that keeps its number."""
    assert getattr(_MAKERS[kind](**{field: value}), field) == value


@pytest.mark.parametrize("field", ["version", "revision"])
def test_replace_runs_the_same_refusal(field: str) -> None:
    """A valid record changed to 0 is refused too (`replace` calls `__init__` again)."""
    with pytest.raises(SchemaError):
        dataclasses.replace(_release(2, 2), **{field: 0})


@pytest.mark.parametrize("field", ["version", "revision"])
@pytest.mark.parametrize("wrong", [True, "1", None, 1.5])
def test_a_wrong_type_is_left_for_freeze_to_report(field: str, wrong: Any) -> None:
    """Only an `int` below 1 is refused at make time; `bool` and other types are not."""
    refuse_below_one("unit_release", make_id(UnitRelease, ("x",)), "a release", field, wrong)


@pytest.mark.parametrize("field", ["version", "revision"])
@pytest.mark.parametrize("kind", list(_MAKERS))
def test_freeze_reports_a_str_number(kind: str, field: str) -> None:
    """The record accepts a `str` at make time (type-tolerant); `freeze()` refuses it."""
    record = _MAKERS[kind](**{field: "1"})
    draft = Draft()
    draft.add(record, origin=_ORIGIN)
    with pytest.raises(FreezeError):
        freeze(draft)


def test_a_refusal_without_an_id_leaves_record_id_empty() -> None:
    """`record_id` is kept only when it is an `Id`, as `SupplySystem` does."""
    not_an_id: Any = "not an id"
    with pytest.raises(SchemaError) as raised:
        refuse_below_one("unit_release", not_an_id, "a release", "revision", 0)
    assert raised.value.record_id is None


def test_the_release_key_text_writes_version_and_revision_as_decimal_text() -> None:
    """SC2: key `("unit_release", name, str(version), str(revision))`; `key_text` joins with `/`."""
    assert key_text(_release(3, 1)) == "unit_release/demo-io-board/3/1"


def test_a_release_and_its_instances_freeze_and_resolve() -> None:
    """Two instances point at one release; the table holds one record, the field resolves."""
    release = _release(2, title="Relay interface board", number="SKX-RIB-2")
    units = [
        Unit(id=make_id(Unit, (name,)), key=(name,), release=release.id, parent=None)
        for name in ("board-1", "board-2")
    ]
    draft = Draft()
    draft.extend([release, *units], origin=_ORIGIN)
    draft.extend([release], origin=_ORIGIN)  # the same record again is kept once
    model = freeze(draft)
    assert list(unit_releases(model)) == [release.id]
    assert unit_releases(model)[release.id].number == "SKX-RIB-2"


def test_a_unit_pointing_at_no_release_fails_freeze() -> None:
    """`Unit.release` is a required reference: a dangling one is a freeze error."""
    unit = Unit(
        id=make_id(Unit, ("board",)),
        key=("board",),
        release=make_id(UnitRelease, ("nothing",)),
        parent=None,
    )
    draft = Draft()
    draft.add(unit, origin=_ORIGIN)
    with pytest.raises(FreezeError):
        freeze(draft)


def test_a_revision_of_a_release_keeps_its_version() -> None:
    """`Revision.release` names a release; `version` is stored beside `revision`."""
    release = _release(2)
    entry = Revision(
        id=make_id(Revision, ("entry",)),
        key=("entry",),
        release=release.id,
        version=2,
        revision=1,
        date="2026-09-26",
        text="First release",
        created="XX",
    )
    draft = Draft()
    draft.extend([release, entry], origin=_ORIGIN)
    model = freeze(draft)
    assert revisions(model)[entry.id].version == 2
    assert revisions(model)[entry.id].release == release.id
