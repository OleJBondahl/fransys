"""Encoding: the model as nested data and as canonical JSON (design/kernel-model.md 5.6).

The walk is driven by each field's annotation, so a `Decimal`, an enum member or a nested
`@value` needs no tag: the reader knows what it is from the same annotation. Only at a
position that declares no type (`Value`, so everything under `ext`) is a mapping written as
`{"$map": ...}` and an `Id` as `{"$id": ...}`, so the reader can tell them from a plain
mapping and a plain string.
"""

import json
import types
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from .errors import ValueTypeError
from .ids import render_id
from .registry import is_value_class
from .schema import FieldInfo, cached_field_info, id_type, key_and_value_aliases
lazy from .model import Model

if TYPE_CHECKING:
    from .ids import Id
    from .record import Record

type JsonValue = (
    bool
    | int
    | str
    | list[JsonValue]
    | tuple[JsonValue, ...]
    | dict[str, JsonValue]
    | frozendict[str, JsonValue]
    | None
)
"""What `write_json` accepts: the JSON data model, nothing else."""

MAP_TAG = "$map"
ID_TAG = "$id"


def to_data(model: Model) -> frozendict[str, Any]:
    """Render `model` as nested `frozendict`s, tuples and primitives only.

    Keys are sorted, tables hold their records in `Id` order and aliases are sorted pairs.
    Origins are not written (a moved line is not a change to the plant), nor are `hashes`,
    `digests` and `digest`, which are derived and recomputed on load.
    """
    aliases = tuple(
        (render_id(old), render_id(new))
        for old, new in sorted(model.aliases.items(), key=lambda pair: pair[0])
    )
    tables = frozendict(
        {
            kind: tuple(
                record_data(record) for _, record in sorted(table.items(), key=lambda pair: pair[0])
            )
            for kind, table in sorted(model.tables.items(), key=lambda pair: pair[0])
        }
    )
    return frozendict(
        {"aliases": aliases, "schema_version": model.schema_version, "tables": tables}
    )


def record_data(record: Record) -> frozendict[str, Any]:
    """Render `record` as a mapping with every field present, keys sorted.

    Resolves `record`'s own class fresh; a caller writing many records should call `_record_data`
    with one memo shared across the batch, as nested `@value` types repeat.
    """
    return _record_data(record, {})


def _record_data(record: Record, specs: dict[type, FieldInfo]) -> frozendict[str, Any]:
    info = cached_field_info(type(record), specs)
    return frozendict(
        {
            name: _encode_value(getattr(record, name), info.annotations[name], specs)
            for name in info.names
        }
    )


def _encode_value(value: object, annotation: object, specs: dict[type, FieldInfo]) -> object:
    """Render `value` as its annotation says a reader will expect it."""
    if annotation is key_and_value_aliases()[0]:  # AuthoringKey is `tuple[str, ...]`
        annotation = annotation.__value__
    origin = get_origin(annotation)
    if origin is types.UnionType:
        member = next(arg for arg in get_args(annotation) if arg is not NoneType)
        return None if value is None else _encode_value(value, member, specs)
    if origin is tuple:
        items = cast("tuple[object, ...]", value)
        return tuple(_encode_value(item, get_args(annotation)[0], specs) for item in items)
    if origin is frozendict:
        pairs = cast("frozendict[str, object]", value)
        item_annotation = get_args(annotation)[1]
        return frozendict(
            {key: _encode_value(pairs[key], item_annotation, specs) for key in sorted(pairs)}
        )
    if origin is id_type():
        return render_id(cast("Id[Any]", value))
    return _encode_plain(value, annotation, specs)


def _encode_plain(value: object, annotation: object, specs: dict[type, FieldInfo]) -> object:
    """Render a value whose annotation is a class or a scalar, not a generic."""
    if isinstance(annotation, type) and is_value_class(annotation):
        info = cached_field_info(annotation, specs)
        return frozendict(
            {
                name: _encode_value(getattr(value, name), info.annotations[name], specs)
                for name in info.names
            }
        )
    if annotation is Decimal:
        return decimal_text(cast("Decimal", value))
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return cast("Enum", value).value
    # a dict cannot reach here: check_value (values.py:81-98), run at conform.py:99 during
    # freeze(), refuses a bare dict on every field before a Model exists (design/kernel-records.md
    # 5.1)
    if annotation in (str, int, bool) or annotation is None:
        return value
    return _encode_undeclared(value)


def _encode_undeclared(value: object) -> object:
    """Render `value` where no type is declared: tag a mapping and an `Id`, nothing else.

    A leaf that is none of `str`, `int`, `bool`, `None` is left as it is, and `write_json`
    refuses it; `freeze()` has already kept every such value out of a model.
    """
    if type(value) is tuple:
        return tuple(_encode_undeclared(item) for item in value)
    if type(value) is frozendict:
        pairs = cast("frozendict[str, object]", value)
        return frozendict(
            {MAP_TAG: frozendict({key: _encode_undeclared(pairs[key]) for key in sorted(pairs)})}
        )
    if type(value) is id_type():
        return frozendict({ID_TAG: render_id(cast("Id[Any]", value))})
    return value


def decimal_text(number: Decimal) -> str:
    """Write `number` in its one canonical form: plain digits, no trailing zeros, zero as `0`.

    Not `normalize()`: it rounds to the context precision and would drop digits.
    """
    if number == 0:
        return "0"
    text = format(number, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def write_json(data: JsonValue, *, compact: bool = False) -> str:
    """Write `data` as canonical JSON: keys sorted, non-ASCII kept as it is.

    The readable form is indented and ends in a newline, for golden files. The compact form
    has neither and is what is hashed. A lone surrogate in a string is written as it is:
    encode with `surrogatepass` before hashing.
    """
    if compact:
        return json.dumps(
            data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=_plain
        )
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2, default=_plain) + "\n"


def _plain(value: object) -> object:
    """`json` calls this for what it cannot write itself: nothing reaching it is acceptable.

    `json` handles `frozendict` natively (it is a builtin mapping type), so this only ever
    refuses.
    """
    msg = f"a {type(value).__name__} cannot be written as JSON"
    raise ValueTypeError(msg, path=())
