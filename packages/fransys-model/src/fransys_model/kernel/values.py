"""Kernel values: the closed leaf-type set a record may hold (kernel-records.md, decision 0006)."""

import dataclasses
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, cast

from .errors import ValueTypeError
from .ids import Id
from .registry import is_value_class, register_value_alias

if TYPE_CHECKING:
    from collections.abc import Mapping

    from _typeshed import DataclassInstance


class ValueRecord(Protocol):
    """Structural stand-in for an instance of a `@value`-decorated class.

    Any frozen, slotted dataclass without identity qualifies; no explicit inheritance
    is required.
    """

    __dataclass_fields__: ClassVar[Mapping[str, Any]]


type Value = (
    str
    | int
    | bool
    | Decimal
    | Enum
    | Id[Any]
    | tuple[Value, ...]
    | frozendict[str, Value]
    | ValueRecord
    | None
)
register_value_alias(Value)

# Exact types only: a `str` or `int` subclass could carry mutable state of its own.
_LEAF_TYPES = frozenset({str, int, bool, NoneType})

# Canonical JSON writes and reads every value as text, and a huge one would not survive it:
# CPython refuses to turn an int of more than 640 digits (its smallest configurable limit)
# into text, and `format(Decimal, "f")` spells out an exponent digit by digit.
_MAX_INT_BITS = 2048  # 617 digits
MAX_EXPONENT = 1000

_registered_enums: set[type[Enum]] = set()


def register_enum[E: Enum](cls: type[E]) -> type[E]:
    """Mark `cls` as an allowed `Value` leaf.

    `check_value` rejects any `Enum` subclass that was never passed through this
    decorator.
    """
    _registered_enums.add(cls)
    return cls


def check_value(value: object, *, path: tuple[str, ...] = ()) -> None:
    """Recursively reject anything outside the closed set in design/kernel-records.md 5.1.

    `path` names where in the containing structure `value` was found (a field name, a
    tuple index, a `frozendict` key), so the error can point at more than the top level.

    An instance of a `@value` class is accepted when every field passes. A `@record`
    instance is not: a table record is held by `Id`, never nested.

    Raises:
        ValueTypeError: `value`, or something nested inside it, is not an allowed leaf
            type: `float`, `list`, `dict`, `set`, `bytes`, a callable, an unregistered
            `Enum` subclass or a member whose value is not a `str` or `int`, a non-finite
            `Decimal` or one with an exponent beyond 1000, an `int` of more than 2048 bits,
            a dataclass that is not a `@value` class, or a `frozendict` with a non-`str` key.
    """
    kind = type(value)
    if kind is int:
        _check_int(cast("int", value), path)
    elif kind in _LEAF_TYPES:
        return
    elif kind is Decimal:
        _check_decimal(cast("Decimal", value), path)
    elif isinstance(value, Enum):
        _check_enum(value, path)
    else:
        _check_container(value, path)


def _check_container(value: object, path: tuple[str, ...]) -> None:
    kind = type(value)
    if kind is tuple:
        for index, item in enumerate(cast("tuple[object, ...]", value)):
            check_value(item, path=(*path, str(index)))
    elif kind is frozendict:
        _check_frozendict(cast("frozendict[Any, Any]", value), path)
    elif is_value_class(kind):
        _check_value_record(cast("DataclassInstance", value), path)
    else:
        raise _reject(path, f"{kind.__name__} is not an allowed value type")


def _check_int(number: int, path: tuple[str, ...]) -> None:
    if number.bit_length() > _MAX_INT_BITS:
        raise _reject(
            path, f"int of {number.bit_length()} bits is over the {_MAX_INT_BITS}-bit limit"
        )


def _check_decimal(number: Decimal, path: tuple[str, ...]) -> None:
    # NaN != NaN and sNaN raises on compare and hash, so neither can be a quantity.
    if not number.is_finite():
        raise _reject(path, f"Decimal {number} is not finite")
    if abs(number.adjusted()) > MAX_EXPONENT:
        raise _reject(path, f"Decimal {number} has an exponent beyond {MAX_EXPONENT}")


def _check_enum(member: Enum, path: tuple[str, ...]) -> None:
    if type(member) not in _registered_enums:
        raise _reject(path, f"enum {type(member).__name__} is not registered with register_enum")
    # Enums serialise by value, so a float or tuple member would smuggle itself in.
    if type(member.value) not in (str, int):
        raise _reject(path, f"enum member {member} has a {type(member.value).__name__} value")
    if type(member.value) is int:
        _check_int(member.value, path)


def _check_frozendict(mapping: frozendict[Any, Any], path: tuple[str, ...]) -> None:
    for key, item in mapping.items():
        if type(key) is not str:
            raise _reject(path, f"a frozendict key is a {type(key).__name__}, not a str")
        check_value(item, path=(*path, key))


def _check_value_record(instance: DataclassInstance, path: tuple[str, ...]) -> None:
    # `@value` makes the class frozen and slotted, so only its fields can hold something bad.
    for field in dataclasses.fields(instance):
        check_value(getattr(instance, field.name), path=(*path, field.name))


def _reject(path: tuple[str, ...], why: str) -> ValueTypeError:
    where = ".".join(path) or "<top level>"
    return ValueTypeError(f"{where}: {why}", path=path)
