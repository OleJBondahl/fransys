"""Conformance: every field of a record matches its annotation (design/kernel-model.md 5.5).

`freeze()` calls `check_record` on each record. The walk checks a value's shape against
its annotation by exact type, so `True` is not an `int` and `1` is not a `Decimal`; then
`check_value` checks that every leaf is legal. Every `Id` met on the way is returned as a
`Reference`, wherever it sits, for `freeze()` to resolve.
"""

import dataclasses
import types
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from .errors import ModelError, SchemaError, ValueTypeError
from .registry import is_value_class
from .schema import FieldInfo, cached_field_info, id_type, key_and_value_aliases, resolve_target
from .values import check_value

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .ids import Id
    from .record import Record

_EXACT = (str, int, bool, Decimal)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Reference:
    """An `Id` held by a record: where it sits, what it names, what its field declares.

    `path` is dotted from the record's field name (`entries.0.function`). `kind` is the declared
    kind, or `None` for an `Id` under `ext`, `Value` or `Id[Any]`, where only existence is checked.
    """

    path: str
    target: Id[Any]
    kind: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class _Mismatch:
    path: str
    why: str


def check_record(record: Record) -> tuple[tuple[ModelError, ...], tuple[Reference, ...]]:
    """Return the problems with `record`'s fields, and every reference it holds.

    One error per field: `SchemaError` for a mismatched annotation, `ValueTypeError` for a bad one.
    Resolves the class fresh; a caller checking many records shares one memo via `_check_record`.
    """
    return _check_record(record, {})


def _check_record(
    record: Record, specs: dict[type, FieldInfo]
) -> tuple[tuple[ModelError, ...], tuple[Reference, ...]]:
    info = cached_field_info(type(record), specs)
    errors = []
    references = []
    for field in info.fields:
        error, found = _check_field(record, field.name, info.annotations[field.name], specs)
        if error is not None:
            errors.append(error)
        references.extend(found)
    return tuple(errors), tuple(references)


def _check_field(
    record: Record, name: str, annotation: object, specs: dict[type, FieldInfo]
) -> tuple[ModelError | None, tuple[Reference, ...]]:
    cls = type(record)
    kind = vars(cls)["__kind__"]
    value = getattr(record, name)
    if name == "id":  # the primary key: not a reference; `Draft.add` checks its kind
        if type(value) is not id_type():
            return SchemaError(f"{cls.__qualname__}.id is not an Id", kind=kind), ()
        return _legality(record, name, value), ()
    walked = tuple(_walk(value, annotation, name, cls, specs))
    for item in walked:
        if isinstance(item, _Mismatch):
            message = f"{cls.__qualname__}.{item.path}: {item.why}"
            return SchemaError(message, kind=kind, record_id=record.id), ()
    error = _legality(record, name, value)
    if error is not None:
        return error, ()
    return None, tuple(item for item in walked if isinstance(item, Reference))


def _legality(record: Record, name: str, value: object) -> ValueTypeError | None:
    """Return the `ValueTypeError`, naming `record`, if `value` is not an allowed value."""
    try:
        check_value(value, path=(name,))
    except ValueTypeError as exc:
        return ValueTypeError(str(exc), path=exc.path, record_id=record.id)
    return None


def _walk(
    value: object, annotation: object, path: str, owner: type, specs: dict[type, FieldInfo]
) -> Iterator[Reference | _Mismatch]:
    if annotation is key_and_value_aliases()[0]:  # AuthoringKey is `tuple[str, ...]`
        annotation = annotation.__value__
    origin = get_origin(annotation)
    if origin is types.UnionType:
        member = next(arg for arg in get_args(annotation) if arg is not NoneType)
        if value is not None:
            yield from _walk(value, member, path, owner, specs)
    elif origin is tuple:
        yield from _walk_tuple(value, get_args(annotation)[0], path, owner, specs)
    elif origin is frozendict:
        yield from _walk_mapping(value, get_args(annotation)[1], path, owner, specs)
    elif origin is id_type():
        yield from _walk_id(value, get_args(annotation)[0], path, owner)
    elif isinstance(annotation, type) and is_value_class(annotation):
        yield from _walk_value(value, annotation, path, owner, specs)
    elif _is_exact(annotation):
        expected = NoneType if annotation is None else annotation
        if type(value) is not expected:
            yield _wrong(path, expected, value)
    else:  # `Value`, `Id[Any]`, or a name that never resolves at runtime: no shape to check
        yield from _undeclared(value, path)


def _is_exact(annotation: object) -> bool:
    """Whether a value must be exactly this scalar type, `None`, or this enum's own member."""
    return (
        annotation is None
        or annotation in _EXACT
        or (isinstance(annotation, type) and issubclass(annotation, Enum))
    )


def _walk_tuple(
    value: object, item_annotation: object, path: str, owner: type, specs: dict[type, FieldInfo]
) -> Iterator[Reference | _Mismatch]:
    if type(value) is not tuple:
        yield _wrong(path, tuple, value)
        return
    for index, item in enumerate(value):
        yield from _walk(item, item_annotation, f"{path}.{index}", owner, specs)


def _walk_mapping(
    value: object, item_annotation: object, path: str, owner: type, specs: dict[type, FieldInfo]
) -> Iterator[Reference | _Mismatch]:
    if type(value) is not frozendict:
        yield _wrong(path, frozendict, value)
        return
    for key, item in value.items():
        yield from _walk(item, item_annotation, _key_path(path, key), owner, specs)


def _walk_id(
    value: object, target: object, path: str, owner: type
) -> Iterator[Reference | _Mismatch]:
    if type(value) is not id_type():
        yield _wrong(path, id_type(), value)
        return
    yield Reference(
        path=path, target=cast("Id[Any]", value), kind=resolve_target(target, owner, path)
    )


def _walk_value(
    value: object, value_class: type, path: str, owner: type, specs: dict[type, FieldInfo]
) -> Iterator[Reference | _Mismatch]:
    if type(value) is not value_class:
        yield _wrong(path, value_class, value)
        return
    info = cached_field_info(value_class, specs)
    for field in info.fields:
        nested = getattr(value, field.name)
        yield from _walk(nested, info.annotations[field.name], f"{path}.{field.name}", owner, specs)


def _undeclared(value: object, path: str) -> Iterator[Reference | _Mismatch]:
    """Yield every `Id` inside `value`, whose annotation declares no kind for it.

    Also yields a mismatch for a `Decimal`, an enum member or a `@value` instance: written with no
    declared type they come back as a plain string, number or mapping (kernel-model.md 5.6).
    """
    if type(value) is id_type():
        yield Reference(path=path, target=cast("Id[Any]", value), kind=None)
    elif type(value) is tuple:
        for index, item in enumerate(value):
            yield from _undeclared(item, f"{path}.{index}")
    elif type(value) is frozendict:
        for key, item in value.items():
            yield from _undeclared(item, _key_path(path, key))
    elif type(value) is Decimal or isinstance(value, Enum) or is_value_class(type(value)):
        why = (
            f"a {type(value).__name__} cannot be read back where no type is declared "
            "(`Value`, `ext`, or a name imported only for type checking): declare the field"
        )
        yield _Mismatch(path, why)


def _key_path(path: str, key: object) -> str:
    """Extend `path` by a mapping key: dotted if it reads as a name, quoted if not.

    A key containing a dot must not look like a nested field, or two locations would share
    a path and their errors could tie in the sort, which would then follow insertion order.
    """
    if type(key) is not str:  # `check_value` refuses it; never `str()` a key, an int can be huge
        return f"{path}[<{type(key).__name__} key>]"
    return f"{path}.{key}" if key.isidentifier() else f"{path}[{key!r}]"


def _wrong(path: str, expected: object, value: object) -> _Mismatch:
    name = getattr(expected, "__name__", repr(expected))
    return _Mismatch(path, f"expected {name}, got {type(value).__name__}")
