"""Tests for the registries, the annotation grammar and the namespace rule.

Kinds and class names are unique per test: the registries are global and never cleared,
so a rejected definition must leave nothing behind and an accepted one must not clash.
"""

import types
from collections.abc import Callable
from decimal import Decimal
from enum import Enum
from typing import Any, cast

import pytest

from fransys_model.kernel import (
    AuthoringKey,
    Id,
    SchemaError,
    Value,
    field_specs,
    lookup_kind,
    record,
    registry,
    schema,
    value,
)

# --- helpers: build a class from a dict of annotations, as a `class` statement would ---------


def _make_class(
    name: str, annotations: dict[str, Any], *, bases: tuple[type, ...] = (), **defaults: Any
) -> Any:
    """Build a class at runtime, so it is `Any` to the type checker."""

    def body(namespace: dict[str, Any]) -> None:
        namespace["__annotations__"] = annotations
        namespace.update(defaults)

    return types.new_class(name, bases, exec_body=body)


def _id_to(name: str) -> Any:
    """`Id["Name"]`: a reference to a record called `name`, resolved later by class name."""
    return cast("Any", Id)[name]


_dyn_value: Any = value  # classes built at runtime are `Any` to the type checker


def _tuple_of(item: Any) -> Any:
    return cast("Any", tuple)[item, ...]


def _base(name: str) -> dict[str, Any]:
    return {"id": _id_to(name), "key": AuthoringKey, "ext": frozendict[str, Value]}


def _record_class(name: str, kind: str, extra: dict[str, Any] | None = None, **options: Any) -> Any:
    annotations = {**_base(name), **(extra or {})}
    return record(kind=kind, **options)(_make_class(name, annotations, ext=frozendict()))


class _Flavour(Enum):
    SWEET = "sweet"


@value
class _Inner:
    text: str


class _Plain:
    pass


type _OtherAlias = int


@record(kind="rejected_embed_probe")
class _Embeddable:
    id: Id[_Embeddable]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


# --- registry ---------------------------------------------------------------------------------


def test_lookup_kind_of_an_unregistered_kind_is_a_schema_error() -> None:
    """An unknown kind is a `SchemaError`, not a `KeyError`."""
    with pytest.raises(SchemaError, match="no class is registered"):
        lookup_kind("never_registered_probe")


# --- `@value` and the annotation grammar ------------------------------------------------------

_ACCEPTED = {
    "str": str,
    "int": int,
    "bool": bool,
    "none": None,
    "decimal": Decimal,
    "enum": _Flavour,
    "value-class": _Inner,
    "tuple": tuple[str, ...],
    "frozendict": frozendict[str, int],
    "optional": str | None,
    "optional-tuple": tuple[int, ...] | None,
    "value-alias": Value,
    "key-alias": AuthoringKey,
    "id-of-record": Id[_Embeddable],
    "optional-id": Id[_Embeddable] | None,
    "id-of-any": Id[Any],
    "forward-name": _id_to("NotDefinedYetProbe"),
    "mapping-of-tuples": frozendict[str, tuple[int, ...]],
}

_REJECTED = {
    "float": float,
    "bytes": bytes,
    "object": object,
    "any": Any,
    "list": list[int],
    "dict": dict[str, int],
    "set": set[int],
    "frozenset": frozenset[int],
    "callable": Callable[[], int],
    "union": str | int,
    "three-way-union": int | str | None,
    "open-tuple": tuple[int],
    "pair-tuple": tuple[int, int],
    "int-keyed-frozendict": frozendict[int, str],
    "plain-class": _Plain,
    "record-instead-of-id": _Embeddable,
    "id-of-non-record": Id[_Plain],
    "quoted-annotation": "Id[X]",
    "other-alias": _OtherAlias,
    "bare-id": Id,
}


@pytest.mark.parametrize("annotation", list(_REJECTED.values()), ids=list(_REJECTED))
def test_value_rejects_a_disallowed_annotation_at_definition(annotation: object) -> None:
    """Anything outside the closed set fails on the `class` statement, not at `freeze()`."""
    with pytest.raises(SchemaError, match=r"RejectedProbe\.field"):
        _dyn_value(_make_class("RejectedProbe", {"field": annotation}))


def test_a_record_field_may_not_be_id_of_any() -> None:
    """`Id[Any]` names no kind, so only a `@value` (a finding's subjects) may hold it."""
    with pytest.raises(SchemaError, match="only for a @value"):
        _record_class("AnyIdProbe", "any_id_probe", {"other": Id[Any]})


# --- `@record` --------------------------------------------------------------------------------


def _without(name: str) -> dict[str, Any]:
    return {key: hint for key, hint in _base("Probe").items() if key != name}


_BAD_RECORDS: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "no-id": (_without("id"), {}),
    "no-key": (_without("key"), {}),
    "no-ext": (_without("ext"), {}),
    "id-of-another-class": ({**_base("Probe"), "id": _id_to("Other")}, {}),
    "id-not-an-id": ({**_base("Probe"), "id": str}, {}),
    "key-not-the-alias": ({**_base("Probe"), "key": tuple[str, ...]}, {}),
    "ext-wrong-type": ({**_base("Probe"), "ext": frozendict[str, str]}, {}),
    "unique-without-subject": (_base("Probe"), {"unique": True}),
    "subject-not-a-field": (_base("Probe"), {"subject": "nope", "unique": True}),
    "subject-optional": (
        {**_base("Probe"), "owner": _id_to("Probe") | None},
        {"subject": "owner", "unique": True},
    ),
    "subject-tuple": (
        {**_base("Probe"), "owner": _tuple_of(_id_to("Probe"))},
        {"subject": "owner", "unique": True},
    ),
}


# --- field specs and the namespace rule -------------------------------------------------------


def test_field_specs_refuses_an_ambiguous_forward_name() -> None:
    """Two records with one class name cannot be told apart by a forward reference."""
    _record_class("Twin", "twin_probe_a")
    _record_class("Twin", "twin_probe_b")
    holder = _dyn_value(_make_class("TwinHolderProbe", {"target": _id_to("Twin")}))
    with pytest.raises(SchemaError, match="is ambiguous"):
        field_specs(holder)


_NS_TARGETS = {
    "core": _record_class("NsCoreTarget", "ns_core_target"),
    "facet": _record_class("NsFacetTarget", "facet.ns_target"),
    "layout": _record_class("NsLayoutTarget", "layout.ns_target"),
}


def test_a_string_annotation_is_refused_with_advice() -> None:
    """A quoted annotation (or a `__future__` import) is opaque, so the message says so."""
    with pytest.raises(SchemaError, match="string annotations are not supported"):
        _dyn_value(_make_class("QuotedProbe", {"field": "Id[X]"}))


@pytest.mark.parametrize(
    ("slot", "helper", "named"),
    [
        ("_id_class", schema.id_type, "Id is not registered"),
        ("_authoring_key_alias", schema.key_and_value_aliases, "AuthoringKey is not registered"),
        ("_value_alias", schema.key_and_value_aliases, "Value is not registered"),
    ],
)
def test_a_schema_helper_called_before_its_registration_names_it(
    monkeypatch: pytest.MonkeyPatch, slot: str, helper: Callable[[], object], named: str
) -> None:
    """With the registry slot empty, the helper raises a `SchemaError` naming what is missing."""
    monkeypatch.setattr(registry, slot, None)
    with pytest.raises(SchemaError, match=named):
        helper()


# ============================================================================
# Mutation-testing hardening for schema.py, lines 28-161 (fields_of,
# id_type, key_and_value_aliases, schema_error, resolve_target,
# validate_annotations / _check_annotation, _check_class). `_check_generic`
# and `_check_id_target` (schema.py:164+) are covered in the next section.
# ============================================================================


class _P5aPlain:
    """A plain class: not a dataclass, and no `__kind__`."""


class _P5aKinded:
    """A plain class carrying `__kind__` directly, without `record()` or the registry."""

    __kind__ = "p5a_kinded_probe"


@record(kind="p5a_record_probe")
class _P5aRecordProbe:
    id: Id[_P5aRecordProbe]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@pytest.mark.parametrize(
    ("slot", "helper", "kind"),
    [
        ("_id_class", schema.id_type, "id"),
        ("_authoring_key_alias", schema.key_and_value_aliases, "id"),
        ("_value_alias", schema.key_and_value_aliases, "value"),
    ],
)
def test_a_schema_helper_called_before_its_registration_pins_kind(
    monkeypatch: pytest.MonkeyPatch, slot: str, helper: Callable[[], object], kind: str
) -> None:
    """B-locator schema.py:65,80,84: each hardcoded `kind=` literal must survive verbatim."""
    monkeypatch.setattr(registry, slot, None)
    with pytest.raises(SchemaError) as excinfo:
        helper()
    assert excinfo.value.kind == kind


def test_resolve_target_refuses_a_type_with_no_kind() -> None:
    """schema.py:116: `not isinstance(target, type) or "__kind__" not in vars(target)`.

    The `or`->`and` mutant would refuse only when BOTH halves hold; a real class that is
    simply not a record satisfies only the second half and must still be refused.
    """
    with pytest.raises(SchemaError, match="does not name a record kind") as excinfo:
        schema.resolve_target(_P5aPlain, _P5aKinded, "field")
    assert excinfo.value.kind == "p5a_kinded_probe"


def test_check_annotation_refusal_pins_kind_from_the_owning_class() -> None:
    """B-locator schema.py:149: the top-level `else` branch's `cls` argument (kind, not `why`).

    `42` is not a type, a string, a leaf, a `ForwardRef` or a `TypeAliasType`, so it falls
    straight through every earlier branch to this one.
    """
    with pytest.raises(SchemaError) as excinfo:
        schema._check_annotation(42, _P5aKinded, "field")
    assert excinfo.value.kind == "p5a_kinded_probe"


# --- end first hardening additions ----------------------------------------------------------------


# ============================================================================
# Mutation-testing hardening for schema.py, lines 164-195 (_check_generic,
# _check_id_target). Continues the range of the section above (28-163).
# ============================================================================


def test_check_generic_refuses_an_invalid_value_type_inside_a_frozendict() -> None:
    """schema.py:178: the mapping value's checked annotation replaced by `None`.

    `frozendict[str, float]` is refused for real; the mutant's `_check_annotation(None, ...)`
    always accepts via the `annotation is None` early return, so it would wrongly pass.
    """
    cls = _make_class("P5bFrozendictInvalidProbe", {"field": frozendict[str, float]})
    with pytest.raises(SchemaError) as excinfo:
        _dyn_value(cls)
    assert excinfo.value.kind == cls.__qualname__


# --- T-locator: one case per `_check_generic`/`_check_id_target` refusal call site -------------

_P5B_GENERIC_REFUSALS: dict[str, Any] = {
    "bad_union_shape": int | str,  # schema.py:169 "a union must be `V | None`"
    "bad_tuple_shape": tuple[int, int],  # schema.py:173 "a tuple must be `tuple[V, ...]`"
    "bad_frozendict_shape": frozendict[int, str],  # schema.py:177 "a frozendict must be ..."
    "unrecognized_generic_origin": list[int],  # schema.py:182 fallback `else`
    "id_of_non_record_target": Id[_Plain],  # schema.py:194 `_check_id_target`
}


# --- end second hardening additions ---------------------------------------------------------------


def test_a_forward_name_inside_a_container_is_rechecked_too() -> None:
    """`tuple[_LateBound, ...]` hides the name one level down; the re-check still finds it."""
    with pytest.raises(SchemaError, match="not an allowed type"):
        field_specs(_LateBadContainerUser)


def test_field_specs_of_a_class_that_is_not_a_dataclass_is_a_schema_error() -> None:
    """A plain class was never declared with `@record` or `@value`."""
    with pytest.raises(SchemaError, match="is not a @record or @value class"):
        field_specs(_Plain)


# These name classes defined below them, so the class-definition check sees a forward
# reference and only `field_specs` can judge them.


@value
class _LateBadContainerUser:
    items: tuple[_LateBound, ...]


@value
class _CycleA:
    others: tuple[_CycleB, ...]


@value
class _CycleB:
    others: tuple[_CycleA, ...]


class _LateBound:
    pass
