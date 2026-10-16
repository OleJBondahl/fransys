"""JSON form of every core value: to_plain gives dicts and lists, from_plain reads them back.

The two roots, PlacementProblem and CoreLayout, carry a top-level "format": FORMAT; from_plain
refuses a root with another format (or none) and names it. Annotations resolve against the
names of values.py and outputs.py (outputs.py imports its value types for the checker only).
"""

import annotationlib
import dataclasses
import enum
import types
import typing
from collections.abc import Mapping
from typing import cast

from . import outputs, values

FORMAT = 1
ROOTS = (values.PlacementProblem, outputs.CoreLayout)
_NAMES = vars(values) | vars(outputs)
_SCALARS = (int, float, str, bool, type(None))


def to_plain(value: object) -> dict[str, object]:
    """A dataclass becomes a dict, a tuple a list, a frozenset a sorted list."""
    plain = cast("dict[str, object]", _plain(value))
    return {"format": FORMAT, **plain} if isinstance(value, ROOTS) else plain


def _plain(value: object) -> object:
    if isinstance(value, _SCALARS):
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple | list):
        return [_plain(v) for v in value]
    msg = f"no JSON form for {type(value).__name__}"
    raise TypeError(msg)


def from_plain[T](cls: type[T], data: Mapping[str, object]) -> T:
    """Rebuild a value of dataclass type cls from its plain form."""
    if cls in ROOTS and data.get("format") != FORMAT:
        msg = f"{cls.__name__}: format {data.get('format')!r} is not readable, this reads {FORMAT}"
        raise ValueError(msg)
    return cast("T", _read(cls, data, ""))


def _read(cls: object, data: object, where: str) -> object:
    """Where names the field being read, for the error of a value outside its vocabulary."""
    if dataclasses.is_dataclass(cls) and isinstance(cls, type) and isinstance(data, Mapping):
        hints = typing.get_type_hints(cls, localns=_NAMES, format=annotationlib.Format.FORWARDREF)
        kwargs = {
            f.name: _read(hints[f.name], data[f.name], f"{cls.__name__}.{f.name}")
            for f in dataclasses.fields(cls)
            if f.name in data
        }
        return cls(**kwargs)
    origin = typing.get_origin(cls)
    if origin is None:
        return _scalar(cls, data, where)
    return _generic(cls, origin, data, where)


def _scalar(cls: object, data: object, where: str) -> object:
    if isinstance(cls, type) and issubclass(cls, enum.Enum):
        if data not in [m.value for m in cls]:
            msg = f"{where}: {data!r} is not one of {', '.join(m.value for m in cls)}"
            raise ValueError(msg)
        return cls(data)
    if cls is float and isinstance(data, int):
        return float(data)
    if isinstance(cls, type) and isinstance(data, cls):
        return data
    msg = f"expected {cls}, got {type(data).__name__}"
    raise TypeError(msg)


def _generic(cls: object, origin: object, data: object, where: str) -> object:
    args = typing.get_args(cls)
    if origin is typing.Literal:
        if data not in args:
            msg = f"{where}: {data!r} is not one of {', '.join(map(str, args))}"
            raise ValueError(msg)
        return data
    items = cast("list[object]", data)
    if origin is types.UnionType:
        return (
            None
            if data is None
            else _read(next(a for a in args if a is not type(None)), data, where)
        )
    if origin is tuple:
        if Ellipsis in args:
            return tuple(_read(args[0], v, where) for v in items)
        return tuple(_read(a, v, where) for a, v in zip(args, items, strict=True))
    if origin is frozenset:
        return frozenset(_read(args[0], v, where) for v in items)
    msg = f"no JSON form for {cls}"
    raise TypeError(msg)
