"""Registries: record kinds, value classes and namespaces (design/kernel-records.md 5.3).

Registration is global, one-way and never undone: nothing is unregistered, so a duplicate
kind is always an error and a test-local kind needs a name no other test uses. These
module-level containers are, with `register_enum`'s set and `Draft`, the kernel's only
mutable state: the kinds, the records by class name, the `@value` classes, the namespace
order, the domain's schema version, and the three slots for `Id`, `AuthoringKey` and `Value`.
Those slots are filled once, at import, by `ids` and `values`, because `schema` must recognise
them and cannot import either (`ids` imports `record`, which imports `schema`).
"""

import re
from enum import Enum
from types import NoneType, UnionType
from typing import TypeAliasType, TypeVar, get_args, get_origin

from .errors import SchemaError

# One lowercase segment, optionally a dot and a second one. This keeps the `\x1f` that
# `make_id` joins with, and the `:` canonical form puts between kind and hex, out of kinds.
_KIND_NAME = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?")

_kinds: dict[str, type] = {}
_records_by_name: dict[str, list[type]] = {}
_value_classes: dict[type, str] = {}
_enums_by_name: set[type] = set()
_class_by_tag: dict[str, type] = {}


class _Reg:
    namespaces_after_core: tuple[str, ...] = ()
    schema_version: int | None = None
    id_class: type | None = None
    authoring_key_alias: TypeAliasType | None = None
    value_alias: TypeAliasType | None = None


def register_id(id_class: type, authoring_key: TypeAliasType) -> None:
    """Record `Id` and `AuthoringKey`; `ids` calls this right after defining them."""
    _Reg.id_class = id_class
    _Reg.authoring_key_alias = authoring_key


def register_value_alias(alias: TypeAliasType) -> None:
    """Record the `Value` alias; `values` calls this right after defining it."""
    _Reg.value_alias = alias


def registered_id_class() -> type | None:
    """Return `Id`, or `None` if `ids` has not been imported."""
    return _Reg.id_class


def registered_authoring_key() -> TypeAliasType | None:
    """Return `AuthoringKey`, or `None` if `ids` has not been imported."""
    return _Reg.authoring_key_alias


def registered_value_alias() -> TypeAliasType | None:
    """Return `Value`, or `None` if `values` has not been imported."""
    return _Reg.value_alias


def register_kind(kind: str, cls: type) -> None:
    """Register `cls` as the table type for `kind`.

    Registering the same class again is a no-op.

    Raises:
        SchemaError: `kind` is not a valid kind name, is registered to a different class, or
            `cls` is already registered under a different kind.
    """
    if _KIND_NAME.fullmatch(kind) is None:
        msg = f"kind {kind!r} is not a lowercase name with at most one dot"
        raise SchemaError(msg, kind=kind)
    registered = _kinds.get(kind)
    if registered is cls:
        return
    if registered is not None:
        msg = f"kind {kind!r} is already registered to {registered.__qualname__}"
        raise SchemaError(msg, kind=kind)
    if cls in _records_by_name.get(cls.__name__, ()):
        msg = f"{cls.__qualname__} is already registered under another kind"
        raise SchemaError(msg, kind=kind)
    _kinds[kind] = cls
    _records_by_name.setdefault(cls.__name__, []).append(cls)


def lookup_kind(kind: str) -> type:
    """Return the class registered for `kind`.

    Raises:
        SchemaError: no class is registered for `kind`.
    """
    cls = _kinds.get(kind)
    if cls is None:
        msg = f"no class is registered for kind {kind!r}"
        raise SchemaError(msg, kind=kind)
    return cls


def records_named(name: str) -> tuple[type, ...]:
    """Return every registered record class called `name`.

    A forward reference such as `Id[Function]` names a class the module could not import
    at runtime; this is how `field_specs` finds it.
    """
    return tuple(_records_by_name.get(name, ()))


def register_value_class(cls: type, tag: str | None = None, *, by_name: bool = False) -> None:
    """Record that `cls` is a value class or an allowed enum, so `check_value` accepts it.

    `tag` names it where a slot holds one of several classes; the default is module and name.
    `by_name` stores the members of an enum by name, not by value.
    """
    _value_classes[cls] = name = tag or f"{cls.__module__}.{cls.__qualname__}"
    _class_by_tag[name] = cls
    if by_name:
        _enums_by_name.add(cls)


def is_value_class(cls: type) -> bool:
    """Whether `cls` is a registered value class (`@value` or a family library's)."""
    return cls in _value_classes and not issubclass(cls, Enum)


def is_registered_enum(cls: type) -> bool:
    """Whether `cls` was registered as an allowed enum."""
    return cls in _value_classes and issubclass(cls, Enum)


def is_enum_by_name(cls: type) -> bool:
    """Whether the members of `cls` are stored by name."""
    return cls in _enums_by_name


def class_for_tag(tag: object) -> type | None:
    """The registered class stored under `tag`, or `None`."""
    return _class_by_tag.get(tag) if isinstance(tag, str) else None


def optional_arm(annotation: object) -> object:
    """The one class of `V | None`, or the first of a union of several."""
    return next(arm for arm in get_args(annotation) if arm is not NoneType)


def slot_tag(annotation: object, value: object) -> str | None:
    """The class tag of `value` when `annotation` names more than one class, else `None`.

    Such a slot is a type variable, a union of several classes or a base class of `value`'s
    class. Its value is stored with that tag, so a reader tells the arms apart.
    """
    cls = type(value)
    arms = get_args(annotation) if get_origin(annotation) is UnionType else (annotation,)
    fits = any(isinstance(arm, type) and issubclass(cls, arm) for arm in arms)
    tagged = isinstance(annotation, TypeVar) or (fits and set(arms) - {NoneType, cls})
    return _value_classes[cls] if tagged and cls in _value_classes else None


def register_namespaces(*order: str) -> None:
    """Declare the namespaces after the implicit, always-first `core`, earliest first.

    `vocab` calls this once with `("facet", "layout")`. A reference field may target a
    kind in the same or an earlier namespace only, so no `core` or `facet` kind can
    reference a `layout.*` kind; `field_specs` enforces it (design/kernel-records.md 5.3, decision
    0009). Registering the same order again is a no-op.

    Raises:
        SchemaError: `core` is in `order`, or a different order is already registered.
    """
    if "core" in order:
        msg = "`core` is implicit and always first, so it is not registered"
        raise SchemaError(msg, kind="core")
    if _Reg.namespaces_after_core and _Reg.namespaces_after_core != order:
        msg = f"namespaces are already registered as {_Reg.namespaces_after_core}, not {order}"
        raise SchemaError(msg, kind=order[0] if order else "core")
    _Reg.namespaces_after_core = order


def register_schema_version(version: int) -> None:
    """Declare the schema version the domain's records carry; `vocab` calls this once.

    `freeze` stamps it into every digest and `from_data` refuses any other. Registering the
    same number again is a no-op.

    Raises:
        SchemaError: `version` is not an int of 1 or more, or a different one is registered.
    """
    if type(version) is not int or version < 1:
        msg = f"the schema version must be an int of 1 or more, not {version!r}"
        raise SchemaError(msg, kind="schema_version")
    if _Reg.schema_version is not None and _Reg.schema_version != version:
        msg = f"the schema version is already registered as {_Reg.schema_version}, not {version}"
        raise SchemaError(msg, kind="schema_version")
    _Reg.schema_version = version


def registered_schema_version() -> int:
    """Return the registered schema version, or raise `SchemaError` if no domain registered one."""
    if _Reg.schema_version is None:
        msg = "no schema version is registered; the domain's vocabulary must be imported"
        raise SchemaError(msg, kind="schema_version")
    return _Reg.schema_version


def namespace_of(kind: str) -> str:
    """Return `kind`'s prefix before the first dot, or `"core"` for an undotted kind."""
    prefix, dot, _ = kind.partition(".")
    return prefix if dot else "core"


def registered_namespaces() -> tuple[str, ...]:
    """Return every registered namespace in order: `core`, then the ones `vocab` declared."""
    return ("core", *_Reg.namespaces_after_core)


def namespace_rank(namespace: str) -> int | None:
    """Return `namespace`'s place in the registered order (`core` is 0), or `None` if unknown."""
    order = ("core", *_Reg.namespaces_after_core)
    return order.index(namespace) if namespace in order else None
