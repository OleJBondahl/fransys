"""JSON form of every core value: to_plain gives dicts and lists, from_plain reads them back.

The two roots, PlacementProblem and CoreLayout, carry a top-level "format": FORMAT; from_plain
refuses a root with another format (or none) and names it. Annotations resolve against the
names of values.py, sym_values.py, annex_values.py, series_values.py and outputs.py (outputs.py
imports its types for the checker). A Series or a Parallel carries a "kind" key, so a part reads
back as it was.
"""

import annotationlib
import dataclasses
import enum
import types
import typing
from collections.abc import Mapping
from typing import cast

from . import annex_values, outputs, series_values, sym_values, values
from .errors import CoreError

FORMAT = 1
ROOTS = (values.PlacementProblem, outputs.CoreLayout)
_NAMES = vars(values) | vars(sym_values) | vars(series_values) | vars(outputs) | vars(annex_values)
_KINDS = ((series_values.Series, "series"), (series_values.Parallel, "parallel"))
_SCALARS = (int, float, str, bool, type(None))


def to_plain(value: object) -> dict[str, object]:
    """A dataclass becomes a dict, a tuple a list, a frozenset a sorted list."""
    plain = cast("dict[str, object]", _plain(value))
    return {"format": FORMAT, **plain} if isinstance(value, ROOTS) else plain


def _plain(value: object) -> object:
    if isinstance(value, _SCALARS):
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        tag = [{"kind": k} for c, k in _KINDS if c is type(value)]
        fields = {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
        return (tag[0] | fields) if tag else fields
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple | list):
        return [_plain(v) for v in value]
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
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
    if isinstance(cls, typing.TypeAliasType):
        cls = cls.__value__
    if dataclasses.is_dataclass(cls) and isinstance(cls, type) and isinstance(data, Mapping):
        hints = typing.get_type_hints(cls, localns=_NAMES, format=annotationlib.Format.FORWARDREF)
        _require(cls, dataclasses.fields(cls), data)
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


def _require(
    cls: type, fields: tuple[dataclasses.Field[object], ...], data: Mapping[str, object]
) -> None:
    """A field with no default must be in the data: a missing one is named, never defaulted."""
    for f in fields:
        required = f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        if required and f.name not in data:
            msg = f"{cls.__name__}: missing required key {f.name!r}"
            raise CoreError(msg)


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
    if origin is Mapping:
        found = cast("dict[str, object]", data).items()
        return frozendict({_read(args[0], k, where): _read(args[1], v, where) for k, v in found})
    items = cast("list[object]", data)
    if origin is types.UnionType:
        return None if data is None else _read(_member(args, data), data, where)
    if origin is tuple:
        if Ellipsis in args:
            return tuple(_read(args[0], v, where) for v in items)
        return tuple(_read(a, v, where) for a, v in zip(args, items, strict=True))
    if origin is frozenset:
        return frozenset(_read(args[0], v, where) for v in items)
    msg = f"no JSON form for {cls}"
    raise TypeError(msg)


def _member(args: tuple[object, ...], data: object) -> object:
    """The member of a union that data is: the class its "kind" names, else the first one."""
    tagged = [(c, kind) for c, kind in _KINDS if c in args]
    if tagged and isinstance(data, Mapping):
        named = [c for c, kind in tagged if kind == data.get("kind")]
        if not named:
            msg = f"{data!r} names no kind of {tagged}"
            raise CoreError(msg)
        return named[0]
    if isinstance(data, str) and str in args:
        return str
    return next(a for a in args if a is not type(None))
