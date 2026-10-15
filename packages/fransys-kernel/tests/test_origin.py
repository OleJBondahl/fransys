"""Tests for `kernel.origin`, `describe` and the `OriginSource` lookups."""

from typing import Any

import pytest

from fransys_kernel import (
    AuthoringKey,
    Id,
    MergeConflict,
    ModelError,
    Origin,
    SchemaError,
    SchemaVersionError,
    ValueTypeError,
    describe,
)

_HOLDER = Id(kind="thing", value="a" * 32)
_MISSING = Id(kind="thing", value="b" * 32)
_PUMP = Origin(file="pumps.py", line=12, note="pump1")
_PUMP_KEY = ("aux", "pumps", "pump1")


class _Source:
    """An `OriginSource` that is not a `Model`: `describe` must rely on the protocol alone."""

    def __init__(
        self,
        origins: dict[Id[Any], Origin] | None = None,
        keys: dict[Id[Any], AuthoringKey] | None = None,
    ) -> None:
        self._origins = origins or {}
        self._keys = keys or {}

    def origin_of(self, target: Id[Any]) -> Origin | None:
        return self._origins.get(target)

    def key_of(self, target: Id[Any]) -> AuthoringKey | None:
        return self._keys.get(target)


def _holder_source() -> _Source:
    return _Source({_HOLDER: _PUMP}, {_HOLDER: _PUMP_KEY})


def test_describe_a_merge_conflict_names_both_origins() -> None:
    """The two origins are already `Origin`s; only the record id needs resolving."""
    conflict = MergeConflict(
        "same id, different content",
        record_id=_HOLDER,
        origin_a=Origin(file="a.py", line=1, note="first"),
        origin_b=Origin(file="b.py", line=2, note="second"),
    )
    assert describe(conflict, _holder_source()) == (
        "same id, different content\n"
        "  record: pumps.py:12 (aux/pumps/pump1)\n"
        "  first: a.py:1\n"
        "  second: b.py:2"
    )


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (SchemaError("bad schema", kind="thing"), ["  kind: thing"]),
        (ValueTypeError("bad value", path=("profile", "0", "owner")), ["  path: profile.0.owner"]),
        (ValueTypeError("bad value", path=()), ["  path: <top level>"]),
        (
            SchemaVersionError("wrong version", expected=3, actual=4),
            ["  expected: 3", "  actual: 4"],
        ),
    ],
    ids=["schema", "value-type", "value-type-top-level", "schema-version"],
)
def test_describe_an_error_without_ids_adds_its_typed_fields(error: Any, detail: list[str]) -> None:
    """These errors carry no id, so `describe` adds only their own labelled fields."""
    assert describe(error, _Source()).splitlines()[1:] == detail


def test_describe_shows_the_record_that_holds_a_schema_or_value_error() -> None:
    """A `SchemaError` or `ValueTypeError` that names its record gets a `record:` line first."""
    schema = SchemaError("bad field", kind="thing", record_id=_HOLDER)
    value = ValueTypeError("bad value", path=("ext", "x"), record_id=_HOLDER)
    assert describe(schema, _holder_source()).splitlines()[1:] == [
        "  record: pumps.py:12 (aux/pumps/pump1)",
        "  kind: thing",
    ]
    assert describe(value, _holder_source()).splitlines()[1:] == [
        "  record: pumps.py:12 (aux/pumps/pump1)",
        "  path: ext.x",
    ]


def test_describe_shows_the_subjects_of_an_error_that_carries_them() -> None:
    """A layout `HintError` is not known here: `describe` reads any `subjects` it carries."""

    class _SubjectsError(ModelError):
        subjects = (_HOLDER, _MISSING)

    assert describe(_SubjectsError("bad hint"), _holder_source()).splitlines()[1:] == [
        "  subject: pumps.py:12 (aux/pumps/pump1)",
        f"  subject: unknown origin (kind {_MISSING.kind})",
    ]
