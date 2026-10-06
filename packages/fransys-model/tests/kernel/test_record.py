"""WP3 acceptance tests: `kernel.record` (ROADMAP WP3, design/kernel-records.md 5.3)."""

import dataclasses
import types
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from fransys_model.kernel import (
    AuthoringKey,
    Id,
    SchemaError,
    Value,
    field_specs,
    key_text,
    lookup_kind,
    record,
    register_namespaces,
    value,
)


def cast_id(name: str) -> Any:
    """`Id["Name"]` without the type checker objecting to a string type argument."""
    generic: Any = Id
    return generic[name]


def test_record_yields_frozen_slotted_kw_only_dataclass(thing_cls: type) -> None:
    """`@record` produces a frozen, slotted, keyword-only dataclass."""
    an_id = Id(kind="thing", value="0" * 32)
    instance = thing_cls(id=an_id, key=("a",), name="pump")
    with pytest.raises(dataclasses.FrozenInstanceError):
        instance.name = "other"
    assert not hasattr(instance, "__dict__")
    with pytest.raises(TypeError):
        thing_cls(an_id, ("a",), "pump")


def test_record_registers_the_kind(thing_cls: type) -> None:
    """`@record(kind="thing")` is later found via `lookup_kind`."""
    assert lookup_kind("thing") is thing_cls


def test_record_refuses_duplicate_kind() -> None:
    """Registering a second, different class under an already-used kind is a `SchemaError`."""

    @record(kind="duplicate_kind_probe")
    class First:
        id: Id[First]
        key: AuthoringKey
        ext: frozendict[str, Value] = frozendict()

    with pytest.raises(SchemaError):

        @record(kind="duplicate_kind_probe")
        class Second:
            id: Id[Second]
            key: AuthoringKey
            ext: frozendict[str, Value] = frozendict()


def test_record_requires_id_key_ext() -> None:
    """A `@record` class missing `id`, `key` or `ext` is a `SchemaError`."""
    with pytest.raises(SchemaError):

        @record(kind="missing_fields_probe")
        class Incomplete:
            name: str


def test_field_specs_lists_reference_fields_with_target_kind() -> None:
    """`Id[K]`, `Id[K] | None` and `tuple[Id[K], ...]` are recognised as references.

    A plain field has `ref_kind is None`.
    """

    @record(kind="referenced_probe")
    class Referenced:
        id: Id[Referenced]
        key: AuthoringKey
        ext: frozendict[str, Value] = frozendict()

    @value
    class Refs:
        plain: str
        single: Id[Referenced]
        optional: Id[Referenced] | None
        many: tuple[Id[Referenced], ...]

    specs = {spec.name: spec for spec in field_specs(Refs)}
    assert specs["plain"].ref_kind is None
    assert specs["single"].ref_kind == "referenced_probe"
    assert specs["optional"].ref_kind == "referenced_probe"
    assert specs["many"].ref_kind == "referenced_probe"


def test_disallowed_annotation_fails_at_class_definition_time() -> None:
    """A disallowed field type fails at class-definition time, not later at `freeze()`."""
    with pytest.raises(SchemaError):

        @record(kind="bad_field_probe")
        class Bad:
            id: Id[Bad]
            key: AuthoringKey
            ext: frozendict[str, Value] = frozendict()
            fraction: float


@pytest.mark.parametrize(
    ("key", "text"),
    [
        (("a",), "a"),
        (("a", "b"), "a/b"),
        (("a", "b", "c"), "a/b/c"),
        ((), ""),
    ],
)
def test_key_text_joins_the_authoring_key_with_slashes(
    thing_cls: type, key: AuthoringKey, text: str
) -> None:
    """`key_text` is the key's parts joined with `/`, and empty for an empty key."""
    instance = thing_cls(id=Id(kind="thing", value="0" * 32), key=key, name="pump")
    assert key_text(instance) == text


# =================================================================================================
# P7A -- record._targets / record._check_namespaces (mutmut trial 9ab42bae, work order B10
# record-side, plus its T-locator rows). Classes and kinds are prefixed `p7a_` /`P7a` so they
# never collide with P6's `p6_`-prefixed conform.py fixtures for the same conceptual bug (owner
# dropped while threading into a recursive call) or with any other part's probes. Do not add
# anything below this banner outside `_targets`/`_check_namespaces` (record.py:206-247); a second
# subagent (P7b) extends `FieldSpec`/`field_specs` coverage (record.py:119-166) separately, after
# this section, below.
# =================================================================================================

# --- B10: `owner` and `seen` must thread through `_targets`'s OWN recursive calls -------------
#
# `resolve_target` (schema.py) only reads `owner` on its *failure* path, in the `SchemaError` it
# raises via `schema_error(owner, label, why)`; `schema_error` does `vars(cls).get(...)`, so a
# dropped `owner` (mutated to `None`) does not raise `SchemaError` at all -- it crashes with
# `TypeError`, since `vars(None)` has no `__dict__`. `seen` gates whether `_targets` ever
# descends into a nested `@value` at all (`seen is not None and ... and annotation not in seen`);
# a dropped `seen` (mutated to `None`) makes that guard fail, so `_targets` silently never enters
# the nested value and never finds the target -- no error at all. Each case below nests an
# `Id[ForwardName]` whose name nobody ever registers, so a correctly-threaded `owner`/`seen` is
# the only way anything raises `SchemaError` at all: a dropped `owner` crashes with the wrong
# exception type, and a dropped `seen` raises nothing.


def _p7a_leaf_holder_b10_body(namespace: dict[str, Any]) -> None:
    namespace["__annotations__"] = {"ref": cast_id("P7aNeverRegisteredGenericLeafB10")}


P7aLeafHolderB10 = value(
    types.new_class("P7aLeafHolderB10", (), exec_body=_p7a_leaf_holder_b10_body)
)
"""A `@value` reached only after two stacked generic recursions (record.py:219, B10).

Built via `types.new_class` with a runtime `__annotations__` dict: `ty` parses a real
class-body annotation statically and rejects `cast_id(...)`'s function-call syntax there.
"""


@record(kind="p7a_owner_generic_b10")
class P7aOwnerGenericB10:
    id: Id[P7aOwnerGenericB10]
    key: AuthoringKey
    many: tuple[P7aLeafHolderB10 | None, ...]
    ext: frozendict[str, Value] = frozendict()


def test_owner_and_seen_survive_two_levels_of_generics_recursion_in_targets() -> None:
    """B10(a): record.py:219's own recursive call must thread the real `owner` and `seen`.

    `tuple[X | None, ...]` forces two stacked calls through record.py:219 (the tuple's own
    arg-loop, then the union's) before `_targets` ever reaches the nested `@value`
    `P7aLeafHolderB10`. Its `ref` names a forward class nobody registered, so the field's
    `ref_kind` seeding (`field_specs` seeds `seen=None` on purpose there, so it never
    descends and never raises) cannot pre-empt this: only `_check_namespaces`'s real,
    growing `seen` set reaches it. A dropped `owner` crashes past a clean `SchemaError`
    (`TypeError` from `vars(None)`); a dropped `seen` stops the descent before the
    forward name is ever looked up, so nothing raises at all.
    """
    with pytest.raises(SchemaError) as excinfo:
        field_specs(P7aOwnerGenericB10)
    assert excinfo.value.kind == "p7a_owner_generic_b10"
    assert "is not a registered record" in str(excinfo.value)


def _p7a_inner_nested_value_b10_body(namespace: dict[str, Any]) -> None:
    namespace["__annotations__"] = {"leaf": cast_id("P7aNeverRegisteredNestedLeafB10")}


P7aInnerNestedValueB10 = value(
    types.new_class("P7aInnerNestedValueB10", (), exec_body=_p7a_inner_nested_value_b10_body)
)
"""A `@value` reached only via record.py:228's own recursive call (B10)."""


@value
class P7aOuterNestedValueB10:
    """Wraps `P7aInnerNestedValueB10` one level, so record.py:228 recurses into it."""

    mid: P7aInnerNestedValueB10


@record(kind="p7a_owner_nested_value_b10")
class P7aOwnerNestedValueB10:
    id: Id[P7aOwnerNestedValueB10]
    key: AuthoringKey
    top: P7aOuterNestedValueB10
    ext: frozendict[str, Value] = frozendict()


def test_owner_and_seen_survive_one_level_of_nested_value_recursion_in_targets() -> None:
    """B10(b): record.py:228's own recursive call must thread the real `owner` and `seen`.

    `_check_namespaces` enters `P7aOuterNestedValueB10` directly, then record.py:228
    recurses into its `mid` field, `P7aInnerNestedValueB10`, whose `leaf` names a forward
    class nobody registered. A dropped `owner` at that one call crashes with `TypeError`
    instead of raising `SchemaError` once resolution fails; a dropped `seen` there stops
    `_targets` from ever entering `P7aInnerNestedValueB10` at all (`seen is not None`
    fails), so the unresolved name is never even looked up and nothing raises. Only
    correct threading raises a clean, correctly-kinded `SchemaError`.
    """
    with pytest.raises(SchemaError) as excinfo:
        field_specs(P7aOwnerNestedValueB10)
    assert excinfo.value.kind == "p7a_owner_nested_value_b10"
    assert "is not a registered record" in str(excinfo.value)


def _p7a_direct_value_for_check_namespaces_b10_body(namespace: dict[str, Any]) -> None:
    namespace["__annotations__"] = {"leaf": cast_id("P7aNeverRegisteredDirectB10")}


P7aDirectValueForCheckNamespacesB10 = value(
    types.new_class(
        "P7aDirectValueForCheckNamespacesB10",
        (),
        exec_body=_p7a_direct_value_for_check_namespaces_b10_body,
    )
)
"""A `@value` whose `leaf` is unresolvable; only `_check_namespaces` reaches it, since
`field_specs`'s own `ref_kind` seeding always passes `seen=None` and so never descends
into a directly nested `@value` at all (B10).
"""


@record(kind="p7a_owner_direct_checknamespaces_b10")
class P7aOwnerDirectCheckNamespacesB10:
    id: Id[P7aOwnerDirectCheckNamespacesB10]
    key: AuthoringKey
    holder: P7aDirectValueForCheckNamespacesB10
    ext: frozendict[str, Value] = frozendict()


def test_owner_survives_check_namespaces_own_call_into_targets() -> None:
    """B10(c): `_check_namespaces`'s own call to `_targets` (record.py:239) must pass `cls`.

    `holder`'s annotation is itself the `@value` `P7aDirectValueForCheckNamespacesB10`
    (no generic wrapping), so `_check_namespaces`'s direct, top-level call into `_targets`
    is the very call that must carry `owner` for its nested `leaf` (an unresolvable
    forward name) to ever be reached and to fail cleanly. If record.py:239 drops `owner`
    to `None`, the eventual `schema_error(None, ...)` crashes with `TypeError`
    (`vars(None)` has no `__dict__`) instead of raising `SchemaError`, so
    `pytest.raises(SchemaError)` cannot catch it.
    """
    with pytest.raises(SchemaError) as excinfo:
        field_specs(P7aOwnerDirectCheckNamespacesB10)
    assert excinfo.value.kind == "p7a_owner_direct_checknamespaces_b10"
    assert "is not a registered record" in str(excinfo.value)


# --- T-locator: one parametrised test per `SchemaError` raise site reachable through
# `_targets`/`_check_namespaces`, pinning `.kind` only (never message wording) ------------------
#
# Three distinct raise sites are reachable here: `_check_namespaces`'s own two raises
# (record.py:236, an owning kind whose namespace nobody registered; record.py:246, a
# reference into a later or unregistered namespace) and `resolve_target`'s failure raise,
# reached through `_targets`'s `id_type` branch, for a forward name nobody ever registers.
# Each one's `.kind` is the *owning* record's kind, never the target's.


@record(kind="p7a_elsewhere.unregistered_namespace_b10")
class P7aElsewhereOwnerProbeB10:
    id: Id[P7aElsewhereOwnerProbeB10]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@record(kind="layout.p7a_ns_target_b10")
class P7aLayoutTargetB10:
    id: Id[P7aLayoutTargetB10]
    key: AuthoringKey
    ext: frozendict[str, Value] = frozendict()


@record(kind="p7a_core_owner_b10")
class P7aCoreOwnerB10:
    id: Id[P7aCoreOwnerB10]
    key: AuthoringKey
    ref: Id[P7aLayoutTargetB10]
    ext: frozendict[str, Value] = frozendict()


def _p7a_unresolved_forward_owner_b10_body(namespace: dict[str, Any]) -> None:
    namespace["__annotations__"] = {
        "id": cast_id("P7aUnresolvedForwardOwnerB10"),
        "key": AuthoringKey,
        "ref": cast_id("P7aNeverRegisteredTopLevelB10"),
        "ext": frozendict[str, Value],
    }
    namespace["ext"] = frozendict()


P7aUnresolvedForwardOwnerB10 = record(kind="p7a_unresolved_forward_owner_b10")(
    types.new_class(
        "P7aUnresolvedForwardOwnerB10", (), exec_body=_p7a_unresolved_forward_owner_b10_body
    )
)


@pytest.mark.parametrize(
    ("cls", "expected_kind"),
    [
        (P7aElsewhereOwnerProbeB10, "p7a_elsewhere.unregistered_namespace_b10"),
        (P7aCoreOwnerB10, "p7a_core_owner_b10"),
        (P7aUnresolvedForwardOwnerB10, "p7a_unresolved_forward_owner_b10"),
    ],
)
def test_targets_and_check_namespaces_raise_sites_pin_the_owning_kind(
    cls: type, expected_kind: str
) -> None:
    """Every `SchemaError` reachable through `_targets`/`_check_namespaces` names the owner."""
    register_namespaces("facet", "layout")
    with pytest.raises(SchemaError) as excinfo:
        field_specs(cls)
    assert excinfo.value.kind == expected_kind


# =================================================================================================
# P7B -- record.field_specs / FieldSpec / _check_required_fields / _check_cardinality (mutmut
# trial 9ab42bae, work order B12 plus its T-locator rows). B12 deleted `FieldSpec.annotation`
# (record.py): unread outside `field_specs` itself, and design/kernel-records.md 5.3 and
# design/kernel-model.md 5.5 name `FieldSpec` only as "a plain frozen dataclass", never that field.
# Of this module's 48 survivor rows, P7a's block above covers 6 (`_targets`/`_check_namespaces`,
# record.py:206-247); this block covers the other 42
# (`field_specs`/`_check_required_fields`/`_check_cardinality`, record.py:134-203; the
# `record`/`value` decorators have none in the report). Of those 42, 39 mutate only a
# `schema_error`/`SchemaError` call's field-name or message-text argument -- `.kind` comes from
# `vars(cls).get("__kind__", ...)` alone, never from those arguments, so no assertion this policy
# allows (`.kind` only, never message wording) can tell them apart; noted, not tested, per the
# order. The remaining 3 (record.py:180, `_check_required_fields`'s id-annotation guard) mutate
# `getattr(id_target, "__name__", None)` to always read `None`; this only changes the outcome when
# `id_target` is already a resolved real class (not a `ForwardRef`) whose name happens to equal
# `cls.__name__` -- per the function's own comment (record.py:178), that never happens, since
# `slots=True` rebuilds the class, so `id` can never validly name the final object. The report tags
# all three "[unclear]", not "missing-test", agreeing they read as equivalent mutants. Classes and
# kinds below are prefixed `p7b_`/`P7b` so they never collide with any other part's probes.
# =================================================================================================


def _p7b_missing_required_fields() -> None:
    @record(kind="p7b_missing_required_fields_b12")
    class P7bMissingRequiredFields:
        name: str


def _p7b_bad_id_annotation() -> None:
    @record(kind="p7b_bad_id_annotation_b12")
    class P7bBadIdAnnotation:
        id: Id[int]
        key: AuthoringKey
        ext: frozendict[str, Value] = frozendict()


def _p7b_bad_second_field_annotation() -> None:
    @record(kind="p7b_bad_second_field_annotation_b12")
    class P7bBadSecondFieldAnnotation:
        id: Id[P7bBadSecondFieldAnnotation]
        key: str
        ext: frozendict[str, Value] = frozendict()


def _p7b_bad_ext_annotation() -> None:
    @record(kind="p7b_bad_ext_annotation_b12")
    class P7bBadExtAnnotation:
        id: Id[P7bBadExtAnnotation]
        key: AuthoringKey
        ext: str = ""


def _p7b_ext_missing_default() -> None:
    @record(kind="p7b_ext_missing_default_b12")
    class P7bExtMissingDefault:
        id: Id[P7bExtMissingDefault]
        key: AuthoringKey
        ext: frozendict[str, Value]


@pytest.mark.parametrize(
    ("factory", "expected_kind", "expected_class", "expected_field"),
    [
        (
            _p7b_missing_required_fields,
            "p7b_missing_required_fields_b12",
            "P7bMissingRequiredFields",
            "id",
        ),
        (_p7b_bad_id_annotation, "p7b_bad_id_annotation_b12", "P7bBadIdAnnotation", "id"),
        (
            _p7b_bad_second_field_annotation,
            "p7b_bad_second_field_annotation_b12",
            "P7bBadSecondFieldAnnotation",
            "key",
        ),
        (_p7b_bad_ext_annotation, "p7b_bad_ext_annotation_b12", "P7bBadExtAnnotation", "ext"),
        (_p7b_ext_missing_default, "p7b_ext_missing_default_b12", "P7bExtMissingDefault", "ext"),
    ],
)
def test_check_required_fields_raise_sites_pin_the_owning_kind(
    factory: Callable[[], None], expected_kind: str, expected_class: str, expected_field: str
) -> None:
    """Every `SchemaError` `_check_required_fields` raises names the class being defined.

    `.kind` alone leaves the `name` argument (`required`, or a literal `"id"`/`"key"`/
    `"ext"`) unpinned: mutating it to `None` only shows up in the message's `Cls.field:`
    prefix, which the ruling allows pinning as a substring (P13's mutmut rerun found this).
    """
    with pytest.raises(SchemaError, match=rf"{expected_class}\.{expected_field}:") as excinfo:
        factory()
    assert excinfo.value.kind == expected_kind


def _p7b_unique_without_subject() -> None:
    @record(kind="p7b_unique_without_subject_b12", unique=True)
    class P7bUniqueWithoutSubject:
        id: Id[P7bUniqueWithoutSubject]
        key: AuthoringKey
        ext: frozendict[str, Value] = frozendict()


def _p7b_subject_not_plain_id() -> None:
    @record(kind="p7b_subject_not_plain_id_b12", subject="subject")
    class P7bSubjectNotPlainId:
        id: Id[P7bSubjectNotPlainId]
        key: AuthoringKey
        subject: str
        ext: frozendict[str, Value] = frozendict()


@pytest.mark.parametrize(
    ("factory", "expected_kind"),
    [
        (_p7b_unique_without_subject, "p7b_unique_without_subject_b12"),
        (_p7b_subject_not_plain_id, "p7b_subject_not_plain_id_b12"),
    ],
)
def test_check_cardinality_raise_sites_pin_the_owning_kind(
    factory: Callable[[], None], expected_kind: str
) -> None:
    """Every `SchemaError` `_check_cardinality` raises names the class being defined."""
    with pytest.raises(SchemaError) as excinfo:
        factory()
    assert excinfo.value.kind == expected_kind
