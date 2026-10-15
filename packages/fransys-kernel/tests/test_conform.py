"""Tests: `check_record`, the field-against-annotation check `freeze()` runs."""

import types
from decimal import Decimal
from enum import Enum
from typing import Any

import pytest

from fransys_kernel import (
    AuthoringKey,
    Id,
    SchemaError,
    Value,
    record,
    register_enum,
    value,
)
from fransys_kernel.conform import check_record


@register_enum
class _Colour(Enum):
    RED = "red"


@register_enum
class _Other(Enum):
    BLUE = "blue"


@record(kind="conform_target_probe")
class _Target:
    id: Id[_Target]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@value
class _Inner:
    owner: Id[_Target]
    tags: tuple[str, ...]


@record(kind="conform_subject_probe")
class _Subject:
    id: Id[_Subject]
    key: AuthoringKey
    name: str
    count: int
    flag: bool
    amount: Decimal
    colour: _Colour
    tags: tuple[str, ...]
    scores: frozendict[str, int]
    target: Id[_Target]
    maybe: Id[_Target] | None
    many: tuple[Id[_Target], ...]
    inner: _Inner
    note: str | None = None
    ext: frozendict[str, Value] = frozendict()


_TARGET = Id(kind="conform_target_probe", value="1" * 32)
_OTHER_TARGET = Id(kind="conform_target_probe", value="2" * 32)
_SUBJECT = Id(kind="conform_subject_probe", value="3" * 32)


def _subject(**overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "id": _SUBJECT,
        "key": ("a",),
        "name": "pump",
        "count": 2,
        "flag": True,
        "amount": Decimal("1.5"),
        "colour": _Colour.RED,
        "tags": ("x", "y"),
        "scores": frozendict({"a": 1}),
        "target": _TARGET,
        "maybe": None,
        "many": (_TARGET, _OTHER_TARGET),
        "inner": _Inner(owner=_TARGET, tags=("t",)),
    }
    return _Subject(**{**fields, **overrides})


_SHAPE_MISMATCHES = {
    "int-in-str": {"name": 1},
    "str-in-int": {"count": "1"},
    "bool-in-int": {"count": True},
    "int-in-bool": {"flag": 1},
    "int-in-decimal": {"amount": 1},
    "float-in-decimal": {"amount": 1.5},
    "other-enum": {"colour": _Other.BLUE},
    "str-in-enum": {"colour": "red"},
    "list-in-tuple": {"tags": ["x"]},
    "int-in-tuple-of-str": {"tags": (1,)},
    "str-value-in-int-mapping": {"scores": frozendict({"a": "x"})},
    "bool-value-in-int-mapping": {"scores": frozendict({"a": True})},
    "dict-in-frozendict": {"scores": {"a": 1}},
    "str-in-id": {"target": "x"},
    "int-in-optional-id": {"maybe": 5},
    "str-in-tuple-of-ids": {"many": (_TARGET, "x")},
    "none-in-value-class": {"inner": None},
    "wrong-value-class": {"inner": _Target(id=_TARGET, key=("a",))},
    "int-in-optional-str": {"note": 5},
    "int-in-key": {"key": (1,)},
    "str-as-key": {"key": "a"},
}


def test_an_id_under_ext_is_a_reference_with_no_declared_kind() -> None:
    """Where no kind is declared only existence can be checked: `kind` is `None`."""
    nested = frozendict({"owner": _OTHER_TARGET, "list": (_TARGET, "text")})
    _, references = check_record(_subject(ext=frozendict({"a": _TARGET, "b": nested})))
    under_ext = {(ref.path, ref.kind) for ref in references if ref.path.startswith("ext")}
    assert under_ext == {
        ("ext.a", None),
        ("ext.b.owner", None),
        ("ext.b.list.0", None),
    }


@pytest.mark.parametrize(
    "unreadable",
    [Decimal("1.5"), _Colour.RED, _Inner(owner=_TARGET, tags=())],
    ids=["decimal", "enum", "value-class"],
)
@pytest.mark.parametrize("nested", [False, True], ids=["direct", "in-tuple"])
def test_a_type_that_cannot_be_read_back_is_refused_where_no_type_is_declared(
    unreadable: Any, *, nested: bool
) -> None:
    """Under `ext` a `Decimal` is a string, an enum a string or number, a value class a mapping.

    The reader cannot tell them from plain values, so freeze refuses them there: declare a
    field with its type instead.
    """
    placed = (unreadable,) if nested else unreadable
    errors, references = check_record(_subject(ext=frozendict({"x": placed})))
    assert len(errors) == 1
    assert isinstance(errors[0], SchemaError)
    assert "cannot be read back" in str(errors[0])
    assert not any(ref.path.startswith("ext") for ref in references)


def test_a_record_whose_id_is_not_an_id_is_a_schema_error() -> None:
    """`Draft.add` refuses this first; `check_record` is also called on records it never saw."""
    not_an_id: Any = "x"
    errors, references = check_record(_Target(id=not_an_id, key=("a",)))
    assert [type(error) for error in errors] == [SchemaError]
    assert "is not an Id" in str(errors[0])
    assert references == ()


def cast_id(name: str) -> Any:
    """`Id["Name"]` without the type checker objecting to a string type argument."""
    generic: Any = Id
    return generic[name]


# --- Forward-name resolution must thread `owner` through every nested shape --------------
#
# `resolve_target` only reads `owner` on its *failure* path (the message it raises): a
# successfully-resolved forward name never touches it, so a passing case cannot tell a
# threaded `owner` from a dropped one. Each shape below therefore nests an `Id[ForwardName]`
# whose name is never registered, so resolution fails and the raised `SchemaError.kind` (and
# its message, naming the outer class) pins which `owner` actually reached `resolve_target`.


def _p6_forward_holder_body(namespace: dict[str, Any]) -> None:
    namespace["__annotations__"] = {"ref": cast_id("NeverRegisteredTarget")}


P6ForwardHolder = value(types.new_class("P6ForwardHolder", (), exec_body=_p6_forward_holder_body))
"""A `@value` holding an `Id[ForwardName]` whose name is never registered.

Built via `types.new_class` with a runtime `__annotations__` dict, like
`test_check_record_raises_for_a_class_whose_forward_name_cannot_be_resolved` above: `ty`
parses a real class-body annotation statically and rejects a function call there, even
though `cast_id` only ever runs at import time.
"""


@record(kind="p6_owner_optional_b10")
class OwnerOptional:
    id: Id[OwnerOptional]
    key: AuthoringKey
    maybe: P6ForwardHolder | None
    ext: frozendict[str, Value] = frozendict()


@record(kind="p6_owner_tuple_b10")
class OwnerTuple:
    id: Id[OwnerTuple]
    key: AuthoringKey
    many: tuple[P6ForwardHolder, ...]
    ext: frozendict[str, Value] = frozendict()


@record(kind="p6_owner_mapping_b10")
class OwnerMapping:
    id: Id[OwnerMapping]
    key: AuthoringKey
    by_name: frozendict[str, P6ForwardHolder]
    ext: frozendict[str, Value] = frozendict()


@record(kind="p6_owner_direct_b10")
class OwnerDirect:
    id: Id[OwnerDirect]
    key: AuthoringKey
    holder: P6ForwardHolder
    ext: frozendict[str, Value] = frozendict()


_P6_DUMMY_REF = Id(kind="p6_dummy_target_b10", value="9" * 32)


def test_owner_threads_through_a_mapping_of_values_to_resolve_its_forward_id() -> None:
    """`_walk_mapping` (conform.py:118/157) must pass the real `owner` down, not `None`."""
    instance = OwnerMapping(
        id=Id(kind="p6_owner_mapping_b10", value="1" * 32),
        key=("a",),
        by_name=frozendict({"x": P6ForwardHolder(ref=_P6_DUMMY_REF)}),
    )
    with pytest.raises(SchemaError) as excinfo:
        check_record(instance)
    assert excinfo.value.kind == "p6_owner_mapping_b10"
    assert "OwnerMapping" in str(excinfo.value)
    assert "is not a registered record" in str(excinfo.value)


# --- A field annotated bare `None`
# --------------------------------------------


# --- T-locator table: conform.py's refusal call sites (conform.py:83-217) ----------------------
#
# The mutmut report lists 15 survivor rows in this range. 14 of them mutate a value that only
# ever reaches *message text* (`_wrong`'s expected/got type name, `_walk_id`'s error label,
# `_undeclared`'s wording, `_key_path`'s key repr): `SchemaError` exposes no `.path` field to
# pin them against, and pinning them would mean asserting message wording, which this table
# does not do. Skipped as pure message-text mutations (14): conform.py:144 (#4, #5),
# conform.py:167 (#24), conform.py:175 (#4, #5), conform.py:199 (#39), conform.py:200
# (#40, #41, #42), conform.py:202 (#43), conform.py:212 (#3), conform.py:217 (#4, #7, #10).
#
# The remaining row mutates a real, asserted attribute: conform.py:83 (`_check_field`'s
# `id`-is-not-an-`Id` refusal), `kind=kind` -> `kind=None`.

_ID_REFUSAL_TABLE = {
    "id-not-an-id": (_Target, "conform_target_probe"),
}
