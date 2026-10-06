"""Registries: record kinds, value classes and namespaces (design/kernel-records.md 5.3).

Registration is global, one-way and never undone: nothing is unregistered, so a duplicate
kind is always an error and a test-local kind needs a name no other test uses. These
module-level containers are, with `register_enum`'s set and `Draft`, the kernel's only
mutable state: the kinds, the records by class name, the `@value` classes, the namespace
order, and the three slots for `Id`, `AuthoringKey` and `Value`. Those slots are filled once,
at import, by `ids` and `values`, because `schema` must recognise them and cannot import
either (`ids` imports `record`, which imports `schema`).
"""

import re
from typing import TypeAliasType

from .errors import SchemaError

# One lowercase segment, optionally a dot and a second one. This keeps the `\x1f` that
# `make_id` joins with, and the `:` canonical form puts between kind and hex, out of kinds.
_KIND_NAME = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?")

_kinds: dict[str, type] = {}
_records_by_name: dict[str, list[type]] = {}
_value_classes: set[type] = set()
_namespaces_after_core: tuple[str, ...] = ()
_id_class: type | None = None
_authoring_key_alias: TypeAliasType | None = None
_value_alias: TypeAliasType | None = None


def register_id(id_class: type, authoring_key: TypeAliasType) -> None:
    """Record `Id` and `AuthoringKey`; `ids` calls this right after defining them."""
    global _id_class, _authoring_key_alias  # noqa: PLW0603 -- the registry is filled once at import
    _id_class = id_class
    _authoring_key_alias = authoring_key


def register_value_alias(alias: TypeAliasType) -> None:
    """Record the `Value` alias; `values` calls this right after defining it."""
    global _value_alias  # noqa: PLW0603 -- the registry is filled once at import
    _value_alias = alias


def registered_id_class() -> type | None:
    """Return `Id`, or `None` if `ids` has not been imported."""
    return _id_class


def registered_authoring_key() -> TypeAliasType | None:
    """Return `AuthoringKey`, or `None` if `ids` has not been imported."""
    return _authoring_key_alias


def registered_value_alias() -> TypeAliasType | None:
    """Return `Value`, or `None` if `values` has not been imported."""
    return _value_alias


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


def register_value_class(cls: type) -> None:
    """Record that `cls` was declared with `@value`, so `check_value` may accept its instances."""
    _value_classes.add(cls)


def is_value_class(cls: type) -> bool:
    """Whether `cls` was declared with `@value`."""
    return cls in _value_classes


def register_namespaces(*order: str) -> None:
    """Declare the namespaces after the implicit, always-first `core`, earliest first.

    `vocab` calls this once with `("facet", "layout")`. A reference field may target a
    kind in the same or an earlier namespace only, so no `core` or `facet` kind can
    reference a `layout.*` kind; `field_specs` enforces it (design/kernel-records.md 5.3, decision
    0009). Registering the same order again is a no-op.

    Raises:
        SchemaError: `core` is in `order`, or a different order is already registered.
    """
    global _namespaces_after_core  # noqa: PLW0603 -- the registry is filled once at import
    if "core" in order:
        msg = "`core` is implicit and always first, so it is not registered"
        raise SchemaError(msg, kind="core")
    if _namespaces_after_core and _namespaces_after_core != order:
        msg = f"namespaces are already registered as {_namespaces_after_core}, not {order}"
        raise SchemaError(msg, kind=order[0] if order else "core")
    _namespaces_after_core = order


def namespace_of(kind: str) -> str:
    """Return `kind`'s prefix before the first dot, or `"core"` for an undotted kind."""
    prefix, dot, _ = kind.partition(".")
    return prefix if dot else "core"


def registered_namespaces() -> tuple[str, ...]:
    """Return every registered namespace in order: `core`, then the ones `vocab` declared."""
    return ("core", *_namespaces_after_core)


def namespace_rank(namespace: str) -> int | None:
    """Return `namespace`'s place in the registered order (`core` is 0), or `None` if unknown."""
    order = ("core", *_namespaces_after_core)
    return order.index(namespace) if namespace in order else None
