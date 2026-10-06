"""WP4 tests: `kernel.origin`, `describe` and the `OriginSource` lookups (design/kernel-records.md
5.4 and design/kernel-model.md 5.8)."""

from typing import TYPE_CHECKING, Any

import pytest

from fransys_model.kernel import (
    AuthoringKey,
    Finding,
    FreezeError,
    Id,
    MergeConflict,
    Model,
    Origin,
    RefError,
    SchemaError,
    SchemaVersionError,
    Severity,
    ValueTypeError,
    describe,
)

if TYPE_CHECKING:
    from collections.abc import Callable

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


def test_origin_holds_file_line_note() -> None:
    """`Origin` records where a record was authored: file, line, note."""
    origin = Origin(file="pumps.py", line=12, note="pump1 contactor")
    assert (origin.file, origin.line, origin.note) == ("pumps.py", 12, "pump1 contactor")


def test_describe_resolves_ids_to_origins(
    thing_cls: Any, origin: Origin, model_of: Callable[..., Model]
) -> None:
    """`describe` renders a problem's ids as `file:line (key)`, not bare ids (kernel-model.md)."""
    thing_id = Id(kind="thing", value="0" * 32)
    thing = thing_cls(id=thing_id, key=("pumps", "pump1"), name="pump")
    error = RefError("dangling reference", record_id=thing_id, field="a", target=thing_id)
    assert "conftest.py:1 (pumps/pump1)" in describe(error, model_of((thing, origin)))


def test_model_answers_the_origin_source_lookups(
    thing_cls: Any, origin: Origin, model_of: Callable[..., Model]
) -> None:
    """A `Model` knows the origin and key of its records, and nothing of any other id."""
    thing_id = Id(kind="thing", value="0" * 32)
    model = model_of((thing_cls(id=thing_id, key=("pumps", "pump1"), name="pump"), origin))
    assert model.origin_of(thing_id) == origin
    assert model.key_of(thing_id) == ("pumps", "pump1")
    same_kind_unknown = Id(kind="thing", value="1" * 32)
    other_kind_unknown = Id(kind="nowhere", value="0" * 32)
    for unknown in (same_kind_unknown, other_kind_unknown):
        assert model.origin_of(unknown) is None
        assert model.key_of(unknown) is None


def test_describe_a_dangling_reference_names_the_record_that_holds_it() -> None:
    """The holder has an origin; the missing target, by definition, has none."""
    error = RefError("dangling reference", record_id=_HOLDER, field="a", target=_MISSING)
    assert describe(error, _holder_source()) == (
        "dangling reference\n"
        "  record: pumps.py:12 (aux/pumps/pump1)\n"
        "  field: a\n"
        "  target: unknown origin (kind thing)"
    )


@pytest.mark.parametrize(
    ("source", "rendered"),
    [
        (_Source({_MISSING: _PUMP}, {_MISSING: ("aux", "pump")}), "pumps.py:12 (aux/pump)"),
        (_Source({_MISSING: _PUMP}, {}), "pumps.py:12"),
        (_Source({}, {_MISSING: ("aux", "pump")}), "unknown origin (aux/pump)"),
        (_Source({}, {}), "unknown origin (kind thing)"),
    ],
    ids=["origin-and-key", "origin-only", "key-only", "neither"],
)
def test_describe_falls_back_for_an_id_missing_an_origin_or_a_key(
    source: _Source, rendered: str
) -> None:
    """`describe` is total: whatever is known is shown, and the rest is named as unknown."""
    error = RefError("dangling reference", record_id=_HOLDER, field="a", target=_MISSING)
    assert describe(error, source).splitlines()[-1] == f"  target: {rendered}"


def test_describe_never_prints_an_id_value() -> None:
    """`Id.value` is for serialisation; a human sees origins, keys and kinds only."""
    error = RefError("dangling reference", record_id=_HOLDER, field="a", target=_MISSING)
    text = describe(error, _Source())
    assert "a" * 32 not in text
    assert "b" * 32 not in text


def test_describe_prints_the_message_verbatim() -> None:
    """The message is never inspected or rewritten, whatever it looks like."""
    message = "thing:" + "b" * 32 + " is not the id you think"
    error = RefError(message, record_id=_HOLDER, field="a", target=_MISSING)
    assert describe(error, _Source()).splitlines()[0] == message


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


def test_describe_a_finding_lists_its_subjects_in_id_order() -> None:
    """One line per subject, in `Id` order whatever order the validator gave."""
    finding = Finding(
        code="NET_UNREALISED",
        severity=Severity.WARNING,
        subjects=(_MISSING, _HOLDER),
        message="net not physically joined",
    )
    assert describe(finding, _holder_source()) == (
        "NET_UNREALISED (warning): net not physically joined\n"
        "  subject: pumps.py:12 (aux/pumps/pump1)\n"
        "  subject: unknown origin (kind thing)"
    )


def test_describe_a_freeze_error_numbers_and_indents_each_nested_error() -> None:
    """`FreezeError` renders every collected error with the same rules, one indent deeper."""
    aggregate = FreezeError(
        (SchemaError("bad schema", kind="thing"), ValueTypeError("bad value", path=("name",)))
    )
    assert describe(aggregate, _Source()) == (
        "2 error(s) during freeze\n"
        "  1. bad schema\n"
        "       kind: thing\n"
        "  2. bad value\n"
        "       path: name"
    )


def test_describe_a_freeze_error_nested_in_a_freeze_error() -> None:
    """Recursion handles an aggregate inside an aggregate without special cases."""
    inner = FreezeError((SchemaError("bad schema", kind="thing"),))
    assert describe(FreezeError((inner,)), _Source()) == (
        "1 error(s) during freeze\n"
        "  1. 1 error(s) during freeze\n"
        "       1. bad schema\n"
        "            kind: thing"
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


def test_describe_indents_every_line_of_a_multi_line_nested_message() -> None:
    """Only the first line carries the number; the rest line up under it."""
    aggregate = FreezeError((SchemaError("line one\nline two", kind="thing"),))
    assert describe(aggregate, _Source()) == (
        "1 error(s) during freeze\n  1. line one\n     line two\n       kind: thing"
    )


def test_describe_survives_an_empty_message_inside_a_freeze_error() -> None:
    """An empty message has no lines; the nested rendering must still have a first one."""
    aggregate = FreezeError((SchemaError("", kind="thing"),))
    assert describe(aggregate, _Source()).splitlines()[-1] == "       kind: thing"


def test_require_origin_names_the_missing_target_kind() -> None:
    """No origin for `target` is a `SchemaError` carrying the id's own kind, never `None`."""
    from fransys_model.kernel.origin import require_origin

    target = Id(kind="thing", value="0" * 32)
    with pytest.raises(SchemaError) as excinfo:
        require_origin({}, target)
    assert excinfo.value.kind == "thing"
    assert excinfo.value.record_id == target


def test_lines_renders_a_top_level_empty_message_as_an_empty_line() -> None:
    """`_lines`' fallback for an empty message is the empty string itself, not a placeholder."""
    error = SchemaError("", kind="thing")
    lines = describe(error, _Source()).splitlines()
    assert lines[0] == ""
    assert lines[1:] == ["  kind: thing"]


def test_describe_an_empty_freeze_error_and_a_finding_without_subjects() -> None:
    """The edges still render: a header alone, and a finding line with no subject lines."""
    assert describe(FreezeError(()), _Source()) == "0 error(s) during freeze"
    finding = Finding(code="NET_SHORTED", severity=Severity.ERROR, subjects=(), message="shorted")
    assert describe(finding, _Source()) == "NET_SHORTED (error): shorted"
