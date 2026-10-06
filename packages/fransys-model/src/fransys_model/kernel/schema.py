"""The annotation grammar: what a `@record` or `@value` field may be (design/kernel-records.md 5.3).

`validate_annotations` runs on the `class` statement, so it sees only what already
resolves; `record.field_specs` runs it again once forward names have resolved. Nothing
here registers anything.
"""

import dataclasses
import types
from annotationlib import Format, ForwardRef, get_annotations
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import Any, TypeAliasType, cast, get_args, get_origin

from .errors import SchemaError
from .registry import (
    is_value_class,
    records_named,
    registered_authoring_key,
    registered_id_class,
    registered_value_alias,
)

_LEAVES = (str, int, bool, Decimal, NoneType)


def fields_of(cls: type) -> tuple[dataclasses.Field[Any], ...]:
    """Return `cls`'s dataclass fields, in declaration order.

    Raises `SchemaError` when `cls` is not a dataclass (not declared with `@record` or `@value`).
    """
    if not dataclasses.is_dataclass(cls):
        msg = f"{cls.__qualname__} is not a @record or @value class"
        raise SchemaError(msg, kind=cls.__qualname__)
    return dataclasses.fields(cls)


def annotations_of(cls: type) -> dict[str, Any]:
    """Return the annotation of every field of `cls`, inherited fields included.

    Only real fields: a `ClassVar` or an inherited protocol's annotation is not one.
    """
    names = {field.name for field in fields_of(cls)}
    return {
        name: annotation
        for base in reversed(cls.__mro__)
        for name, annotation in get_annotations(base, format=Format.FORWARDREF).items()
        if name in names
    }


@dataclasses.dataclass(frozen=True, slots=True)
class FieldInfo:
    """One class's fields, resolved once: declaration order, sorted names, and annotations.

    `fields` keeps declaration order for a walk checking fields as declared; `names` is sorted for
    a writer keying alphabetically. `annotations` sits beside both: a class's shape is derived once.
    """

    fields: tuple[dataclasses.Field[Any], ...]
    names: tuple[str, ...]
    annotations: dict[str, Any]


def field_info(cls: type) -> FieldInfo:
    """Return `cls`'s `FieldInfo`: `fields_of(cls)` and `annotations_of(cls)`, resolved once."""
    fields = fields_of(cls)
    return FieldInfo(
        fields=fields,
        names=tuple(sorted(field.name for field in fields)),
        annotations=annotations_of(cls),
    )


def cached_field_info(cls: type, specs: dict[type, FieldInfo]) -> FieldInfo:
    """Return `cls`'s `FieldInfo`, deriving it once into `specs` and reusing it after.

    `specs` is one call's own memo, never a cache that outlives it: `freeze()` builds an empty
    dict per call, shared by every record and nested `@value` class, so each kind resolves once.
    """
    info = specs.get(cls)
    if info is None:
        info = field_info(cls)
        specs[cls] = info
    return info


def id_type() -> type:
    """Return `Id`, which `ids` registered when it was imported.

    `schema` cannot import `ids`: `ids` imports `record`, which imports `schema`.
    Raises `SchemaError` if `ids` has not been imported yet, so `Id` is not registered.
    """
    id_class = registered_id_class()
    if id_class is None:
        msg = "Id is not registered: `ids` registers it at import and has not been imported"
        raise SchemaError(msg, kind="id")
    return id_class


def key_and_value_aliases() -> tuple[TypeAliasType, TypeAliasType]:
    """Return `AuthoringKey` and `Value`, which `ids` and `values` registered at import.

    Raises `SchemaError` when `ids` or `values` is not imported yet, so no alias is registered.
    """
    authoring_key = registered_authoring_key()
    if authoring_key is None:
        msg = (
            "AuthoringKey is not registered: `ids` registers it at import and has not been imported"
        )
        raise SchemaError(msg, kind="id")
    value_alias = registered_value_alias()
    if value_alias is None:
        msg = "Value is not registered: `values` registers it at import and has not been imported"
        raise SchemaError(msg, kind="value")
    return authoring_key, value_alias


def schema_error(cls: type, name: str, why: str) -> SchemaError:
    """Build the `SchemaError` for field `name` of `cls`, naming its kind if it has one."""
    kind = vars(cls).get("__kind__", cls.__qualname__)
    return SchemaError(f"{cls.__qualname__}.{name}: {why}", kind=kind)


def resolve_target(target: object, owner: type, label: str) -> str | None:
    """Return the kind that `Id[target]` names, or `None` for `Id[Any]`.

    A class target gives its `__kind__`; a forward name is found by class name among the records.
    Raises `SchemaError` if the name is unknown or shared by two records, or is not a record.
    """
    if target is Any:
        return None
    if isinstance(target, ForwardRef):
        named = target.__forward_arg__
        matches = records_named(named)
        if len(matches) != 1:
            why = (
                "is ambiguous"
                if matches
                else "is not a registered record (is its module imported?)"
            )
            raise schema_error(owner, label, f"Id[{named}] {why}")
        target = matches[0]
    if not isinstance(target, type) or "__kind__" not in vars(target):
        raise schema_error(owner, label, f"Id[{target!r}] does not name a record kind")
    return cast("str", vars(target)["__kind__"])  # vars() values are Any; `@record` sets a str


def validate_annotations(cls: type) -> None:
    """Reject a field whose annotation is outside the closed set in design/kernel-records.md 5.3.

    A name that is still a forward reference passes; `field_specs` checks it again once resolved.
    Raises `SchemaError` if `cls` has a field annotated with a type outside the closed set.
    """
    for name, annotation in annotations_of(cls).items():
        _check_annotation(annotation, cls, name)


def _check_annotation(annotation: object, cls: type, name: str) -> None:
    origin = get_origin(annotation)
    if origin is not None:
        _check_generic(annotation, origin, cls, name)
    elif isinstance(annotation, str):
        why = "string annotations are not supported: drop the quotes and any `__future__` import"
        raise schema_error(cls, name, why)
    elif annotation is None or annotation in _LEAVES or isinstance(annotation, ForwardRef):
        return
    elif isinstance(annotation, TypeAliasType):
        if annotation not in key_and_value_aliases():
            raise schema_error(cls, name, f"alias {annotation!r} is not an allowed annotation")
    elif isinstance(annotation, type):
        _check_class(annotation, cls, name)
    else:
        raise schema_error(cls, name, f"{annotation!r} is not an allowed annotation")


def _check_class(annotation: type, cls: type, name: str) -> None:
    if annotation is id_type():
        raise schema_error(cls, name, "write Id[K], not a bare Id")
    if issubclass(annotation, Enum) or is_value_class(annotation):
        return
    if "__kind__" in vars(annotation):
        target = annotation.__name__
        why = f"{target} is a record: hold an Id[{target}], not the record"
        raise schema_error(cls, name, why)
    raise schema_error(cls, name, f"{annotation.__name__} is not an allowed type")


def _check_generic(annotation: object, origin: object, cls: type, name: str) -> None:
    args = get_args(annotation)
    if origin is types.UnionType:
        members = [arg for arg in args if arg is not NoneType]
        if len(args) != 2 or len(members) != 1:  # noqa: PLR2004 -- `V | None` is two members
            raise schema_error(cls, name, "a union must be `V | None`")
        _check_annotation(members[0], cls, name)
    elif origin is tuple:
        if len(args) != 2 or args[1] is not Ellipsis:  # noqa: PLR2004 -- `tuple[V, ...]`
            raise schema_error(cls, name, "a tuple must be `tuple[V, ...]`")
        _check_annotation(args[0], cls, name)
    elif origin is frozendict:
        if len(args) != 2 or args[0] is not str:  # noqa: PLR2004 -- `frozendict[str, V]`
            raise schema_error(cls, name, "a frozendict must be `frozendict[str, V]`")
        _check_annotation(args[1], cls, name)
    elif origin is id_type():
        _check_id_target(args[0], cls, name)
    else:
        raise schema_error(cls, name, f"{annotation!r} is not an allowed annotation")


def _check_id_target(target: object, cls: type, name: str) -> None:
    if isinstance(target, ForwardRef):
        return
    if target is Any:
        if "__kind__" in vars(cls):
            why = "Id[Any] is only for a @value; a record names its target kind"
            raise schema_error(cls, name, why)
        return
    if not isinstance(target, type) or "__kind__" not in vars(target):
        raise schema_error(cls, name, f"Id[{target!r}] does not name a record kind")
