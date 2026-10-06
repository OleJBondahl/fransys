"""WP5 tests: `check_record`, the field-against-annotation check `freeze()` runs
(design/kernel-model.md 5.5)."""

import types
from decimal import Decimal
from enum import Enum
from typing import Any

import pytest

from fransys_model.kernel import (
    AuthoringKey,
    Id,
    SchemaError,
    Value,
    ValueTypeError,
    record,
    register_enum,
    value,
)
from fransys_model.kernel.conform import Reference, check_record


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


def test_a_conforming_record_has_no_errors_and_reports_every_reference() -> None:
    """References are found at the top level, in a tuple, and inside a nested value."""
    errors, references = check_record(_subject())
    assert errors == ()
    kind = "conform_target_probe"
    assert {(ref.path, ref.kind) for ref in references} == {
        ("target", kind),
        ("many.0", kind),
        ("many.1", kind),
        ("inner.owner", kind),
    }


def test_an_optional_reference_that_is_set_is_reported_and_one_that_is_none_is_not() -> None:
    """`Id[K] | None` is a reference only when it holds an id."""
    _, without = check_record(_subject())
    _, with_it = check_record(_subject(maybe=_OTHER_TARGET))
    assert "maybe" not in {ref.path for ref in without}
    assert Reference(path="maybe", target=_OTHER_TARGET, kind="conform_target_probe") in with_it


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


@pytest.mark.parametrize("overrides", list(_SHAPE_MISMATCHES.values()), ids=list(_SHAPE_MISMATCHES))
def test_a_value_that_does_not_match_its_annotation_is_one_schema_error(
    overrides: dict[str, Any],
) -> None:
    """Exact types: `True` is not an `int`, `1` is not a `Decimal`, a list is not a tuple."""
    errors, references = check_record(_subject(**overrides))
    assert len(errors) == 1
    assert isinstance(errors[0], SchemaError)
    assert errors[0].record_id == _SUBJECT
    assert errors[0].kind == "conform_subject_probe"
    field = next(iter(overrides))
    assert not any(ref.path.startswith(field) for ref in references)


def test_a_mismatch_deep_in_a_container_names_its_path() -> None:
    """The path leads to the element: the tuple index, the mapping key, the nested field."""
    errors, _ = check_record(_subject(many=(_TARGET, "x")))
    assert "many.1" in str(errors[0])
    wrong_tags: Any = (1,)
    errors, _ = check_record(_subject(inner=_Inner(owner=_TARGET, tags=wrong_tags)))
    assert "inner.tags.0" in str(errors[0])


def test_one_error_per_field_and_every_bad_field_is_reported() -> None:
    """Two bad fields give two errors: the walk moves on to the next field."""
    errors, _ = check_record(_subject(name=1, count="2"))
    assert len(errors) == 2


def test_a_value_outside_the_closed_set_is_a_value_type_error_naming_the_record() -> None:
    """`ext` accepts any `Value`, so a float there is a legality problem, not a shape one."""
    errors, references = check_record(_subject(ext=frozendict({"x": 1.5})))
    assert len(errors) == 1
    assert isinstance(errors[0], ValueTypeError)
    assert errors[0].path == ("ext", "x")
    assert errors[0].record_id == _SUBJECT
    assert not any(ref.path.startswith("ext") for ref in references)


def test_a_non_finite_decimal_matches_its_shape_but_is_not_a_legal_value() -> None:
    """The two checks do not overlap: shape passes, legality fails."""
    errors, _ = check_record(_subject(amount=Decimal("NaN")))
    assert [type(error) for error in errors] == [ValueTypeError]


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
    field with its type instead (design/kernel-records.md 5.1).
    """
    placed = (unreadable,) if nested else unreadable
    errors, references = check_record(_subject(ext=frozendict({"x": placed})))
    assert len(errors) == 1
    assert isinstance(errors[0], SchemaError)
    assert "cannot be read back" in str(errors[0])
    assert not any(ref.path.startswith("ext") for ref in references)


def test_the_native_types_are_accepted_where_no_type_is_declared() -> None:
    """`str`, `int`, `bool`, `None`, `Id` and tuples and mappings of them round-trip."""
    everything = frozendict(
        {
            "s": "text",
            "i": 3,
            "b": True,
            "n": None,
            "id": _TARGET,
            "t": ("a", 1, _TARGET),
            "m": frozendict({"k": (1, frozendict({"j": _OTHER_TARGET}))}),
        }
    )
    errors, _ = check_record(_subject(ext=everything))
    assert errors == ()


def test_a_record_whose_own_id_holds_something_illegal_is_a_value_type_error() -> None:
    """The primary key is not a reference, but its parts are still checked."""
    smuggled: Any = b"bytes"
    bad_id = Id(kind="conform_target_probe", value=smuggled)
    errors, references = check_record(_Target(id=bad_id, key=("a",)))
    assert len(errors) == 1
    assert isinstance(errors[0], ValueTypeError)
    assert errors[0].path == ("id", "value")
    assert references == ()


def test_a_record_whose_id_is_not_an_id_is_a_schema_error() -> None:
    """`Draft.add` refuses this first; `check_record` is also called on records it never saw."""
    not_an_id: Any = "x"
    errors, references = check_record(_Target(id=not_an_id, key=("a",)))
    assert [type(error) for error in errors] == [SchemaError]
    assert "is not an Id" in str(errors[0])
    assert references == ()


def test_check_record_raises_for_a_class_whose_forward_name_cannot_be_resolved() -> None:
    """An `Id[...]` naming a class nobody registered is the class's problem: it raises.

    `freeze()` resolves each kind's specs once first, so it never reaches this per record.
    """

    def body(namespace: dict[str, Any]) -> None:
        namespace["__annotations__"] = {
            "id": cast_id("GhostHolderProbe"),
            "key": AuthoringKey,
            "ext": frozendict[str, Value],
            "ghost": cast_id("NoSuchRecordAnywhere"),
        }
        namespace["ext"] = frozendict()

    holder = record(kind="ghost_holder_probe")(
        types.new_class("GhostHolderProbe", (), exec_body=body)
    )
    instance = holder(
        id=Id(kind="ghost_holder_probe", value="4" * 32),
        key=("a",),
        ghost=_TARGET,
    )
    with pytest.raises(SchemaError, match="is not a registered record"):
        check_record(instance)


def cast_id(name: str) -> Any:
    """`Id["Name"]` without the type checker objecting to a string type argument."""
    generic: Any = Id
    return generic[name]


# --- B10: forward-name resolution must thread `owner` through every nested shape --------------
#
# `resolve_target` only reads `owner` on its *failure* path (the message it raises): a
# successfully-resolved forward name never touches it, so a passing case cannot tell a
# threaded `owner` from a dropped one. Each shape below therefore nests an `Id[ForwardName]`
# whose name is never registered, so resolution fails and the raised `SchemaError.kind` (and
# its message, naming the outer class) pins which `owner` actually reached `resolve_target`.


def _p6_forward_holder_body(namespace: dict[str, Any]) -> None:
    namespace["__annotations__"] = {"ref": cast_id("P6NeverRegisteredTargetB10")}


P6ForwardHolder = value(types.new_class("P6ForwardHolder", (), exec_body=_p6_forward_holder_body))
"""A `@value` holding an `Id[ForwardName]` whose name is never registered (B10).

Built via `types.new_class` with a runtime `__annotations__` dict, like
`test_check_record_raises_for_a_class_whose_forward_name_cannot_be_resolved` above: `ty`
parses a real class-body annotation statically and rejects a function call there, even
though `cast_id` only ever runs at import time.
"""


@record(kind="p6_owner_optional_b10")
class P6OwnerOptionalB10:
    id: Id[P6OwnerOptionalB10]
    key: AuthoringKey
    maybe: P6ForwardHolder | None
    ext: frozendict[str, Value] = frozendict()


@record(kind="p6_owner_tuple_b10")
class P6OwnerTupleB10:
    id: Id[P6OwnerTupleB10]
    key: AuthoringKey
    many: tuple[P6ForwardHolder, ...]
    ext: frozendict[str, Value] = frozendict()


@record(kind="p6_owner_mapping_b10")
class P6OwnerMappingB10:
    id: Id[P6OwnerMappingB10]
    key: AuthoringKey
    by_name: frozendict[str, P6ForwardHolder]
    ext: frozendict[str, Value] = frozendict()


@record(kind="p6_owner_direct_b10")
class P6OwnerDirectB10:
    id: Id[P6OwnerDirectB10]
    key: AuthoringKey
    holder: P6ForwardHolder
    ext: frozendict[str, Value] = frozendict()


_P6_DUMMY_REF = Id(kind="p6_dummy_target_b10", value="9" * 32)


def test_owner_threads_through_an_optional_value_to_resolve_its_forward_id() -> None:
    """B10: the union branch (conform.py:114) must pass the real `owner` down, not `None`."""
    instance = P6OwnerOptionalB10(
        id=Id(kind="p6_owner_optional_b10", value="1" * 32),
        key=("a",),
        maybe=P6ForwardHolder(ref=_P6_DUMMY_REF),
    )
    with pytest.raises(SchemaError) as excinfo:
        check_record(instance)
    assert excinfo.value.kind == "p6_owner_optional_b10"
    assert "P6OwnerOptionalB10" in str(excinfo.value)
    assert "is not a registered record" in str(excinfo.value)


def test_owner_threads_through_a_tuple_of_values_to_resolve_its_forward_id() -> None:
    """B10: `_walk_tuple` (conform.py:116/147) must pass the real `owner` down, not `None`."""
    instance = P6OwnerTupleB10(
        id=Id(kind="p6_owner_tuple_b10", value="1" * 32),
        key=("a",),
        many=(P6ForwardHolder(ref=_P6_DUMMY_REF),),
    )
    with pytest.raises(SchemaError) as excinfo:
        check_record(instance)
    assert excinfo.value.kind == "p6_owner_tuple_b10"
    assert "P6OwnerTupleB10" in str(excinfo.value)
    assert "is not a registered record" in str(excinfo.value)


def test_owner_threads_through_a_mapping_of_values_to_resolve_its_forward_id() -> None:
    """B10: `_walk_mapping` (conform.py:118/157) must pass the real `owner` down, not `None`."""
    instance = P6OwnerMappingB10(
        id=Id(kind="p6_owner_mapping_b10", value="1" * 32),
        key=("a",),
        by_name=frozendict({"x": P6ForwardHolder(ref=_P6_DUMMY_REF)}),
    )
    with pytest.raises(SchemaError) as excinfo:
        check_record(instance)
    assert excinfo.value.kind == "p6_owner_mapping_b10"
    assert "P6OwnerMappingB10" in str(excinfo.value)
    assert "is not a registered record" in str(excinfo.value)


def test_owner_threads_into_a_directly_nested_value_to_resolve_its_forward_id() -> None:
    """B10: `_walk_value` (conform.py:122/180) must pass the real `owner` down, not `None`."""
    instance = P6OwnerDirectB10(
        id=Id(kind="p6_owner_direct_b10", value="1" * 32),
        key=("a",),
        holder=P6ForwardHolder(ref=_P6_DUMMY_REF),
    )
    with pytest.raises(SchemaError) as excinfo:
        check_record(instance)
    assert excinfo.value.kind == "p6_owner_direct_b10"
    assert "P6OwnerDirectB10" in str(excinfo.value)
    assert "is not a registered record" in str(excinfo.value)


# --- B11: a field annotated bare `None` (design/kernel-records.md 5.3)
# --------------------------------------------


def test_a_field_annotated_bare_none_accepts_none_and_refuses_anything_else() -> None:
    """conform.py:124: `expected = NoneType if annotation is None else annotation`.

    A field annotated literally `None` (not `NoneType`, not quoted) is a value of `None`
    itself; anything else there is one shape mismatch.
    """

    @record(kind="p6_none_field_owner_b11")
    class P6NoneFieldOwner:
        id: Id[P6NoneFieldOwner]
        key: AuthoringKey
        x: None
        ext: frozendict[str, Value] = frozendict()

    assert P6NoneFieldOwner.__annotations__["x"] is None

    good_fields: dict[str, Any] = {
        "id": Id(kind="p6_none_field_owner_b11", value="1" * 32),
        "key": ("a",),
        "x": None,
    }
    errors, _ = check_record(P6NoneFieldOwner(**good_fields))
    assert errors == ()

    bad_fields: dict[str, Any] = {
        **good_fields,
        "id": Id(kind="p6_none_field_owner_b11", value="2" * 32),
        "x": "not none",
    }
    errors, _ = check_record(P6NoneFieldOwner(**bad_fields))
    assert len(errors) == 1
    assert isinstance(errors[0], SchemaError)


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


@pytest.mark.parametrize(
    ("cls", "kind"), list(_ID_REFUSAL_TABLE.values()), ids=list(_ID_REFUSAL_TABLE)
)
def test_a_record_whose_id_is_not_an_id_pins_the_schema_errors_kind(cls: type, kind: str) -> None:
    """conform.py:83: the raised `SchemaError.kind` is the class's own kind, not a default."""
    not_an_id: Any = "x"
    errors, references = check_record(cls(id=not_an_id, key=("a",)))
    assert len(errors) == 1
    assert isinstance(errors[0], SchemaError)
    assert errors[0].kind == kind
    assert references == ()
