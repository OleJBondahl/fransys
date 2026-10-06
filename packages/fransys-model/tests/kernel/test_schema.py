"""WP3 tests: the registries, the annotation grammar and the namespace rule
(design/kernel-records.md 5.3).

Kinds and class names are unique per test: the registries are global and never cleared,
so a rejected definition must leave nothing behind and an accepted one must not clash.
"""

import types
from collections.abc import Callable
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Protocol, cast

import pytest

from fransys_model.kernel import (
    AuthoringKey,
    Id,
    SchemaError,
    Value,
    field_specs,
    lookup_kind,
    namespace_of,
    record,
    register_kind,
    register_namespaces,
    registry,
    schema,
    value,
)
from fransys_model.kernel.registry import is_value_class, records_named

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


def test_registering_the_same_class_again_is_a_no_op(thing_cls: type) -> None:
    """Only a different class under a taken kind is an error, and no second name entry appears."""
    register_kind("thing", thing_cls)
    assert lookup_kind("thing") is thing_cls
    assert records_named("Thing") == (thing_cls,)


@pytest.mark.parametrize(
    "kind",
    ["", "Thing", "a.b.c", "layout.", ".page", "a b", "a-b", "1a", "a:b", "a" + chr(31) + "b"],
    ids=[
        "empty",
        "upper",
        "two-dots",
        "empty-second",
        "empty-first",
        "space",
        "dash",
        "digit",
        "colon",
        "separator",
    ],
)
def test_register_kind_rejects_a_malformed_kind_name(kind: str) -> None:
    """A kind may hold neither the id separator nor the `:` canonical form uses."""
    with pytest.raises(SchemaError, match="not a lowercase name"):
        register_kind(kind, _Plain)


@pytest.mark.parametrize(
    ("kind", "namespace"),
    [("item", "core"), ("facet.terminal", "facet"), ("layout.page", "layout")],
)
def test_namespace_of_is_the_prefix_before_the_first_dot(kind: str, namespace: str) -> None:
    """An undotted kind is in `core`."""
    assert namespace_of(kind) == namespace


def test_register_namespaces_is_idempotent_and_refuses_a_different_order() -> None:
    """Registering the same order twice is fine; a different order is a `SchemaError`."""
    register_namespaces("facet", "layout")
    register_namespaces("facet", "layout")
    with pytest.raises(SchemaError, match="already registered"):
        register_namespaces("layout", "facet")


def test_register_namespaces_refuses_core() -> None:
    """`core` is implicit and always first."""
    with pytest.raises(SchemaError, match="implicit"):
        register_namespaces("core", "facet")


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


@pytest.mark.parametrize("annotation", list(_ACCEPTED.values()), ids=list(_ACCEPTED))
def test_value_accepts_every_allowed_annotation(annotation: object) -> None:
    """Each shape in the closed set of kernel-records.md 5.3 passes the class-definition check."""
    built = _dyn_value(_make_class("AcceptedProbe", {"field": annotation}))
    assert is_value_class(built)


@pytest.mark.parametrize("annotation", list(_REJECTED.values()), ids=list(_REJECTED))
def test_value_rejects_a_disallowed_annotation_at_definition(annotation: object) -> None:
    """Anything outside the closed set fails on the `class` statement, not at `freeze()`."""
    with pytest.raises(SchemaError, match=r"RejectedProbe\.field"):
        _dyn_value(_make_class("RejectedProbe", {"field": annotation}))


def test_value_needs_no_id_key_or_ext() -> None:
    """Only a `@record` carries identity."""

    @value
    class Bare:
        text: str

    assert is_value_class(Bare)


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


@pytest.mark.parametrize(
    ("annotations", "options"), list(_BAD_RECORDS.values()), ids=list(_BAD_RECORDS)
)
def test_record_rejects_a_bad_shape_at_definition(
    annotations: dict[str, Any], options: dict[str, Any]
) -> None:
    """A record missing or mis-declaring `id`, `key`, `ext` or its cardinality never registers."""
    cls = _make_class("Probe", annotations, ext=frozendict())
    with pytest.raises(SchemaError):
        record(kind="bad_shape_probe", **options)(cls)
    with pytest.raises(SchemaError, match="no class is registered"):
        lookup_kind("bad_shape_probe")


def test_record_rejects_an_ext_without_a_default() -> None:
    """A required `ext` would make every record spell it out; it must default to empty."""
    cls = _make_class("NoDefaultProbe", _base("NoDefaultProbe"))
    with pytest.raises(SchemaError, match="needs a default"):
        record(kind="no_default_probe")(cls)


def test_record_accepts_a_facet_shaped_declaration() -> None:
    """`subject` naming a plain `Id[K]` field with `unique=True` registers."""
    built = _record_class(
        "FacetShapeProbe",
        "facet_shape_probe",
        {"subject": _id_to("FacetShapeProbe")},
        subject="subject",
        unique=True,
    )
    assert lookup_kind("facet_shape_probe") is built
    assert vars(built)["__subject__"] == "subject"


# --- field specs and the namespace rule -------------------------------------------------------


def test_field_specs_resolves_a_forward_name_by_class_name() -> None:
    """A name only imported for type checking is found among the registered records."""
    _record_class("ForwardTargetProbe", "forward_target_probe")
    holder = _dyn_value(_make_class("ForwardHolderProbe", {"target": _id_to("ForwardTargetProbe")}))
    assert {spec.name: spec.ref_kind for spec in field_specs(holder)} == {
        "target": "forward_target_probe"
    }


def test_field_specs_finds_references_inside_optional_tuple_and_mapping() -> None:
    """A reference is found however it is wrapped, and a plain field has none."""
    _record_class("ShapesTargetProbe", "shapes_target_probe")
    target = _id_to("ShapesTargetProbe")
    holder = _dyn_value(
        _make_class(
            "ShapesHolderProbe",
            {
                "plain": str,
                "optional": target | None,
                "many": tuple[target, ...],
                "by_name": frozendict[str, target],
            },
        )
    )
    specs = field_specs(holder)
    assert [spec.name for spec in specs] == ["plain", "optional", "many", "by_name"]
    assert [spec.ref_kind for spec in specs] == [None] + ["shapes_target_probe"] * 3


def test_field_specs_refuses_a_forward_name_that_is_not_registered() -> None:
    """A name nobody registered is a `SchemaError` telling the author to import its module."""
    holder = _dyn_value(_make_class("LostHolderProbe", {"target": _id_to("NeverRegisteredProbe")}))
    with pytest.raises(SchemaError, match="is not a registered record"):
        field_specs(holder)


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


@pytest.mark.parametrize(
    ("owner_kind", "target", "accepted"),
    [
        ("ns_owner_core_core", "core", True),
        ("ns_owner_core_facet", "facet", False),
        ("ns_owner_core_layout", "layout", False),
        ("facet.ns_owner_facet_core", "core", True),
        ("facet.ns_owner_facet_facet", "facet", True),
        ("facet.ns_owner_facet_layout", "layout", False),
        ("layout.ns_owner_layout_core", "core", True),
        ("layout.ns_owner_layout_facet", "facet", True),
        ("layout.ns_owner_layout_layout", "layout", True),
    ],
)
def test_a_reference_may_point_to_the_same_or_an_earlier_namespace(
    owner_kind: str, target: str, *, accepted: bool
) -> None:
    """kernel-records.md 5.3: engineering never looks up to layout, and layout may look down."""
    register_namespaces("facet", "layout")
    owner = _record_class(
        "NsOwner" + owner_kind.replace(".", "_"),
        owner_kind,
        {"ref": _id_to(_NS_TARGETS[target].__name__)},
    )
    if accepted:
        refs = {spec.name: spec.ref_kind for spec in field_specs(owner)}
        assert refs["ref"] == vars(_NS_TARGETS[target])["__kind__"]
    else:
        with pytest.raises(SchemaError, match="later or unregistered"):
            field_specs(owner)


def test_a_kind_in_an_unregistered_namespace_is_refused() -> None:
    """A kind whose namespace nobody registered cannot be checked, so it is an error."""
    register_namespaces("facet", "layout")
    owner = _record_class("NowhereOwnerProbe", "nowhere.owner_probe")
    with pytest.raises(SchemaError, match="not registered"):
        field_specs(owner)


def test_a_reference_into_an_unregistered_namespace_is_refused() -> None:
    """The target's namespace must be a registered one too."""
    register_namespaces("facet", "layout")
    _record_class("NowhereTargetProbe", "nowhere.target_probe")
    owner = _record_class(
        "PointsNowhereProbe", "points_nowhere_probe", {"ref": _id_to("NowhereTargetProbe")}
    )
    with pytest.raises(SchemaError, match="later or unregistered"):
        field_specs(owner)


def test_the_namespace_rule_follows_references_inside_nested_values() -> None:
    """A core record cannot reach `layout` by hiding the reference in a nested `@value`."""
    register_namespaces("facet", "layout")
    inner = _dyn_value(_make_class("HiddenRefProbe", {"target": _id_to("NsLayoutTarget")}))
    outer = _record_class("CoreHiderProbe", "core_hider_probe", {"inner": inner})
    with pytest.raises(SchemaError, match="later or unregistered"):
        field_specs(outer)
    assert {spec.name: spec.ref_kind for spec in field_specs(inner)} == {
        "target": "layout.ns_target"
    }


def test_a_layout_record_may_hold_a_value_that_references_core() -> None:
    """The same nesting is fine going down."""
    register_namespaces("facet", "layout")
    inner = _dyn_value(_make_class("DownRefProbe", {"target": _id_to("NsCoreTarget")}))
    outer = _record_class(
        "LayoutHolderProbe", "layout.holder_probe", {"inner": inner, "again": _tuple_of(inner)}
    )
    assert [spec.name for spec in field_specs(outer)] == ["id", "key", "ext", "inner", "again"]


def test_a_records_id_is_its_primary_key_and_not_a_reference() -> None:
    """design/kernel-records.md 5.2: only the *other* `Id[K]` fields are references."""
    _record_class("IdSpecTargetProbe", "id_spec_target_probe")
    owner = _record_class(
        "IdSpecOwnerProbe", "id_spec_owner_probe", {"other": _id_to("IdSpecTargetProbe")}
    )
    assert {spec.name: spec.ref_kind for spec in field_specs(owner)} == {
        "id": None,
        "key": None,
        "ext": None,
        "other": "id_spec_target_probe",
    }


def test_a_string_annotation_is_refused_with_advice() -> None:
    """A quoted annotation (or a `__future__` import) is opaque, so the message says so."""
    with pytest.raises(SchemaError, match="string annotations are not supported"):
        _dyn_value(_make_class("QuotedProbe", {"field": "Id[X]"}))


def test_a_rejected_value_class_is_not_registered() -> None:
    """The check runs before registration, so a bad class leaves nothing behind."""
    before = set(registry._value_classes)
    with pytest.raises(SchemaError):
        _dyn_value(_make_class("UnregisteredProbe", {"field": float}))
    assert registry._value_classes == before


def test_the_schema_helpers_return_what_ids_and_values_registered() -> None:
    """`ids` and `values` register `Id`, `AuthoringKey` and `Value` at import."""
    assert schema.id_type() is Id
    assert schema.key_and_value_aliases() == (AuthoringKey, Value)


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
# P5a: mutation-testing hardening for schema.py, lines 28-161 (fields_of,
# id_type, key_and_value_aliases, schema_error, resolve_target,
# validate_annotations / _check_annotation, _check_class). `_check_generic`
# and `_check_id_target` (schema.py:164+) are P5b's; not touched here.
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


def test_fields_of_a_non_dataclass_pins_kind_to_its_qualname() -> None:
    """B-locator schema.py:36: the `kind=cls.__qualname__` argument must survive verbatim."""
    with pytest.raises(SchemaError) as excinfo:
        schema.fields_of(_P5aPlain)
    assert excinfo.value.kind == _P5aPlain.__qualname__


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


def test_schema_error_kind_is_the_classs_own_kind_when_it_has_one() -> None:
    """B-locator schema.py:90: `vars(cls).get("__kind__", cls.__qualname__)` must read the
    real `"__kind__"` key and return its value, not the qualname fallback.
    """
    err = schema.schema_error(_P5aKinded, "field", "why")
    assert err.kind == "p5a_kinded_probe"


def test_schema_error_kind_falls_back_to_qualname_without_one() -> None:
    """B-locator schema.py:90: the same `.get(...)` call's default, for a class with no kind."""
    err = schema.schema_error(_P5aPlain, "field", "why")
    assert err.kind == _P5aPlain.__qualname__


def test_resolve_target_refuses_a_type_with_no_kind() -> None:
    """B7 schema.py:116: `not isinstance(target, type) or "__kind__" not in vars(target)`.

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


def test_check_class_refuses_a_bare_record_class_naming_it() -> None:
    """B8 schema.py:157: `if "__kind__" in vars(annotation):` must recognise a real record.

    Both case-mutated string-literal rows the report lists (`"XX__kind__XX"`, `"__KIND__"`)
    are the same source line and both branches still raise `schema_error(cls, name, why)`
    with the same `.kind` and the same `Cls.field:` prefix -- they differ only in `why`'s
    wording, so the review reclassifies those two rows as accepted prose survivors (not B),
    per the ruling's own T definition. This test pins only the locator the ruling allows:
    `.kind` and the `Cls.field:` substring, never the full sentence.
    """
    with pytest.raises(SchemaError, match=r"_P5aKinded\.field:") as excinfo:
        schema._check_class(_P5aRecordProbe, _P5aKinded, "field")
    assert excinfo.value.kind == "p5a_kinded_probe"


# --- end P5a additions -------------------------------------------------------------------------


# ============================================================================
# P5b: mutation-testing hardening for schema.py, lines 164-195 (_check_generic,
# _check_id_target). Continues P5a's range (28-163); not touched here.
# ============================================================================


def test_check_generic_refuses_an_invalid_type_inside_an_optional() -> None:
    """B9 schema.py:167,170 (#5, #20): `V | None` with an invalid `V` (`float`).

    Kills the Optional-member-selection swap (`is not NoneType` -> `is NoneType`, which
    would pick `NoneType` itself -- always in `_LEAVES`, so always accepted -- instead of
    `V`) and the recursive check's annotation being replaced by `None` (which also always
    accepts, via the `annotation is None` early return). Both mutants wrongly ACCEPT this
    field; only the real code refuses it.
    """
    cls = _make_class("P5bOptionalInvalidProbe", {"field": float | None})
    with pytest.raises(SchemaError) as excinfo:
        _dyn_value(cls)
    assert excinfo.value.kind == cls.__qualname__


def test_check_generic_accepts_a_valid_type_inside_an_optional() -> None:
    """The happy path for the same shape: `str | None` is accepted.

    Does not by itself discriminate the B9 mutants (both also happen to accept this shape,
    since a valid `V` and the mutants' `NoneType`/`None` substitutes all take an accepting
    path) -- it is the positive half of the pair, confirming the grammar still admits what
    design/kernel-records.md 5.3 allows.
    """
    built = _dyn_value(_make_class("P5bOptionalValidProbe", {"field": str | None}))
    assert is_value_class(built)


def test_check_generic_refuses_an_invalid_value_type_inside_a_frozendict() -> None:
    """B9 schema.py:178 (#64): the mapping value's checked annotation replaced by `None`.

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


@pytest.mark.parametrize("case", list(_P5B_GENERIC_REFUSALS), ids=list(_P5B_GENERIC_REFUSALS))
def test_check_generic_and_id_target_refusals_pin_kind_from_the_owning_class(case: str) -> None:
    """One case per refusal call site in `_check_generic`/`_check_id_target` (schema.py:164+).

    Pins `.kind` via `schema_error`'s own rule, never the message wording: every T row at
    these five call sites only swaps the message text or replaces `name`/`why` with `None`
    (message-only mutants), so a `.kind` assertion is the locator, not a `match=`.
    """
    annotation = _P5B_GENERIC_REFUSALS[case]
    cls = _make_class(f"P5bGenericProbe_{case}", {"field": annotation})
    with pytest.raises(SchemaError) as excinfo:
        _dyn_value(cls)
    assert excinfo.value.kind == cls.__qualname__


def test_check_id_target_refuses_id_of_any_on_a_record() -> None:
    """schema.py:188-191 `_check_id_target`: `Id[Any]` is refused on a `@record` (only a
    `@value`'s finding-subject field may hold it).
    """
    with pytest.raises(SchemaError) as excinfo:
        _record_class("P5bAnyIdOwnerProbe", "p5b_any_id_owner_probe", {"other": Id[Any]})
    assert excinfo.value.kind == "p5b_any_id_owner_probe"


# --- end P5b additions -------------------------------------------------------------------------


def test_a_record_subclass_is_a_schema_error_not_a_key_error() -> None:
    """A subclass inherits fields without annotations of its own; it must not leak a `KeyError`."""
    parent = _record_class("InheritParentProbe", "inherit_parent_probe")
    with pytest.raises(SchemaError, match="must be annotated Id"):
        record(kind="inherit_child_probe")(_make_class("InheritChildProbe", {}, bases=(parent,)))


def test_field_specs_lists_the_inherited_fields_of_a_value_subclass() -> None:
    """`dataclasses.fields` and the annotations agree on inherited fields."""
    parent = _dyn_value(_make_class("InheritedValueProbe", {"text": str}))
    child = _dyn_value(_make_class("InheritingValueProbe", {"count": int}, bases=(parent,)))
    assert [spec.name for spec in field_specs(child)] == ["text", "count"]


def test_a_forward_name_that_later_resolves_to_a_bad_class_is_refused() -> None:
    """The definition-time pass could not see `_LateBound`; `field_specs` re-checks it."""
    with pytest.raises(SchemaError, match="not an allowed type"):
        field_specs(_LateBadUser)


def test_a_forward_name_that_later_resolves_to_an_enum_is_accepted() -> None:
    """The same re-check passes an allowed type."""
    assert [spec.name for spec in field_specs(_LateGoodUser)] == ["flavour"]


def test_a_forward_name_inside_a_container_is_rechecked_too() -> None:
    """`tuple[_LateBound, ...]` hides the name one level down; the re-check still finds it."""
    with pytest.raises(SchemaError, match="not an allowed type"):
        field_specs(_LateBadContainerUser)


def test_a_value_that_holds_itself_through_another_value_terminates() -> None:
    """`_CycleA` holds `_CycleB` holds `_CycleA`: the walk must stop, not recurse forever."""
    owner = _record_class("CycleOwnerProbe", "cycle_owner_probe", {"cycle": _CycleA})
    assert [spec.name for spec in field_specs(owner)] == ["id", "key", "ext", "cycle"]


def test_a_class_variable_is_not_a_field() -> None:
    """Only dataclass fields are checked, so a `ClassVar` constant is allowed."""

    @value
    class WithConstant:
        limit: ClassVar[float] = 1.5
        text: str

    assert [spec.name for spec in field_specs(WithConstant)] == ["text"]


def test_a_value_may_inherit_a_protocol_that_declares_class_variables() -> None:
    """`ValueRecord`-style protocols carry `ClassVar` annotations that are not fields."""

    class Shape(Protocol):
        marker: ClassVar[int]

    built = _dyn_value(_make_class("ProtocolChildProbe", {"text": str}, bases=(Shape,)))
    assert [spec.name for spec in field_specs(built)] == ["text"]


def test_field_specs_of_a_class_that_is_not_a_dataclass_is_a_schema_error() -> None:
    """A plain class was never declared with `@record` or `@value`."""
    with pytest.raises(SchemaError, match="is not a @record or @value class"):
        field_specs(_Plain)


def test_one_class_may_not_be_registered_under_two_kinds() -> None:
    """A second kind would leave `__kind__` naming the first and make its name ambiguous."""
    built = _record_class("TwoKindsProbe", "two_kinds_first_probe")
    with pytest.raises(SchemaError, match="already registered under another kind"):
        register_kind("two_kinds_second_probe", built)
    assert records_named("TwoKindsProbe") == (built,)


def test_core_is_always_the_first_namespace() -> None:
    """`core` needs no `register_namespaces` call: it has rank 0 whatever else is registered."""
    assert registry.namespace_rank("core") == 0


# These name classes defined below them, so the class-definition check sees a forward
# reference and only `field_specs` can judge them.


@value
class _LateBadUser:
    bad: _LateBound


@value
class _LateGoodUser:
    flavour: _LateFlavour


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


class _LateFlavour(Enum):
    SWEET = "sweet"
