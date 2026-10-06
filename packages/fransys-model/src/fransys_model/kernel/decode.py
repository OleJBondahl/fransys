"""Decoding: canonical data and JSON back into a `Model` (design/kernel-model.md 5.6).

`from_data` builds a `Draft` from the data and hands it to `freeze()`, so a loaded model has
passed exactly the checks an authored one has. The decoder converts only what it has to:
an `Id` from its text, a `Decimal` from its string, an enum from its value, the tagged
forms under `ext`, arrays to tuples. A value of the wrong JSON type is left alone, and
`freeze()` reports it with its exact path.
"""

import types
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import NoneType
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from .draft import Draft
from .encode import ID_TAG, MAP_TAG, decimal_text
from .errors import FreezeError, ModelError, SchemaError, SchemaVersionError
from .freeze import freeze
from .ids import parse_id
from .model import SCHEMA_VERSION
from .origin import Origin
from .registry import is_value_class, lookup_kind
from .schema import annotations_of, fields_of, id_type, key_and_value_aliases
from .values import MAX_EXPONENT
lazy from .model import Model

if TYPE_CHECKING:
    from .record import Record

_KIND = "canonical"
_PAIR = 2
_SCHEMA_VERSION_KEY = "schema_version"
_ORIGIN = Origin(file="<canonical>", line=0, note="")


def from_data(data: object) -> Model:
    """Rebuild a `Model` from `data`, running full `freeze()` validation.

    Origins are not in the data, so every record is attributed to `<canonical>:0`. Hashes and
    digests are not in it either: `freeze()` computes them again.

    Raises:
        SchemaVersionError: `data["schema_version"]` is an `int` this build does not know.
        SchemaError: the envelope is malformed (not a mapping, a missing or extra key, a
            table that is not an array of mappings, a malformed alias entry).
        FreezeError: one or more records could not be built or did not validate.
    """
    envelope = _mapping(data, "the data")
    version = envelope.get(_SCHEMA_VERSION_KEY)
    if type(version) is not int:
        msg = f"`{_SCHEMA_VERSION_KEY}` is missing or not an int"
        raise SchemaError(msg, kind=_KIND)
    if version != SCHEMA_VERSION:
        msg = f"this build reads schema version {SCHEMA_VERSION}, not {version}"
        raise SchemaVersionError(msg, expected=SCHEMA_VERSION, actual=version)
    if set(envelope) != {"aliases", _SCHEMA_VERSION_KEY, "tables"}:
        msg = (
            f"the data must have exactly aliases, schema_version and tables, not {sorted(envelope)}"
        )
        raise SchemaError(msg, kind=_KIND)
    tables = _tables(envelope["tables"])
    aliases = _pairs(envelope["aliases"])
    try:
        return _build(tables, aliases)
    except RecursionError as exc:
        msg = "the data is nested too deeply"
        raise SchemaError(msg, kind=_KIND) from exc


def _build(
    tables: dict[str, tuple[frozendict[str, Any], ...]], aliases: tuple[tuple[str, str], ...]
) -> Model:
    draft = Draft()
    errors = _fill(draft, tables) + _alias(draft, aliases)
    if errors:
        raise FreezeError(errors)
    return freeze(draft)


def _mapping(value: object, what: str) -> frozendict[str, Any]:
    if isinstance(value, dict):
        return frozendict(value)
    if isinstance(value, frozendict):
        return value
    msg = f"{what} is not a mapping"
    raise SchemaError(msg, kind=_KIND)


def _array(value: object, what: str) -> tuple[object, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(value)
    msg = f"{what} is not an array"
    raise SchemaError(msg, kind=_KIND)


def _pairs(value: object) -> tuple[tuple[str, str], ...]:
    pairs = []
    for entry in _array(value, "`aliases`"):
        items = _array(entry, "an alias entry")
        if len(items) != _PAIR or not all(isinstance(item, str) for item in items):
            msg = "an alias entry must be a pair of `kind:value` strings"
            raise SchemaError(msg, kind=_KIND)
        pairs.append((cast("str", items[0]), cast("str", items[1])))
    return tuple(pairs)


def _tables(value: object) -> dict[str, tuple[frozendict[str, Any], ...]]:
    """Check the shape of `tables` before any record is built: kind to array of mappings."""
    tables = {}
    for kind, rows in _mapping(value, "`tables`").items():
        tables[kind] = tuple(
            _mapping(row, f"tables.{kind}[{index}]")
            for index, row in enumerate(_array(rows, f"table `{kind}`"))
        )
    return tables


def _fill(
    draft: Draft, tables: dict[str, tuple[frozendict[str, Any], ...]]
) -> tuple[ModelError, ...]:
    """Build every record and add it to `draft`; return what went wrong, in data order."""
    errors = []
    for kind in sorted(tables):
        for index, row in enumerate(tables[kind]):
            try:
                draft.add(_record(kind, row), origin=_ORIGIN)
            except SchemaError as exc:
                errors.append(SchemaError(f"tables.{kind}[{index}]: {exc}", kind=exc.kind))
            except ModelError as exc:
                errors.append(exc)
    return tuple(errors)


def _alias(draft: Draft, aliases: tuple[tuple[str, str], ...]) -> tuple[ModelError, ...]:
    errors = []
    for old, new in aliases:
        try:
            draft.alias(parse_id(old), parse_id(new))
        except ModelError as exc:
            errors.append(exc)
    return tuple(errors)


def _record(kind: str, item: frozendict[str, Any]) -> Record:
    cls = lookup_kind(kind)
    kwargs = _fields(cls, item, kind)
    return cls(**kwargs)


def _fields(cls: type, item: frozendict[str, Any], what: str) -> dict[str, Any]:
    """Decode `item` into constructor arguments: every field present, none unknown."""
    annotations = annotations_of(cls)
    fields = fields_of(cls)
    names = {field.name for field in fields}
    unknown, missing = sorted(set(item) - names), sorted(names - set(item))
    if unknown or missing:
        msg = f"{what}: unknown fields {unknown}, missing fields {missing}"
        raise SchemaError(msg, kind=what)
    # A field the record derives itself (`init=False`) is written, but not read back.
    return {
        field.name: _field(field.name, item[field.name], annotations[field.name])
        for field in fields
        if field.init
    }


def _field(name: str, value: object, annotation: object) -> object:
    try:
        return _decode_value(value, annotation)
    except SchemaError as exc:
        msg = f"field `{name}`: {exc}"
        raise SchemaError(msg, kind=exc.kind) from exc


def _decode_value(value: object, annotation: object) -> object:
    """Turn `value` back into what `annotation` declares, converting only what JSON cannot say."""
    if annotation is key_and_value_aliases()[0]:  # AuthoringKey is `tuple[str, ...]`
        annotation = annotation.__value__
    origin = get_origin(annotation)
    if origin is types.UnionType:
        member = next(arg for arg in get_args(annotation) if arg is not NoneType)
        return None if value is None else _decode_value(value, member)
    if origin is tuple:
        return _decode_tuple(value, get_args(annotation)[0])
    if origin is frozendict:
        return _decode_mapping(value, get_args(annotation)[1])
    if origin is id_type():
        return parse_id(value) if isinstance(value, str) else value
    return _decode_plain(value, annotation)


def _decode_tuple(value: object, item_annotation: object) -> object:
    if not isinstance(value, (tuple, list)):
        return value
    return tuple(_decode_value(item, item_annotation) for item in value)


def _decode_mapping(value: object, item_annotation: object) -> object:
    if not isinstance(value, (frozendict, dict)):
        return value
    return frozendict({key: _decode_value(item, item_annotation) for key, item in value.items()})


def _decode_plain(value: object, annotation: object) -> object:
    if isinstance(annotation, type) and is_value_class(annotation):
        if isinstance(value, (frozendict, dict)):
            return annotation(**_fields(annotation, frozendict(value), annotation.__name__))
        return value
    if annotation is Decimal:
        return _decimal(value)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return _enum(value, annotation)
    if annotation in (str, int, bool) or annotation is None:
        return value
    return _decode_undeclared(value)


def _decode_undeclared(value: object) -> object:
    """Read `value` where no type is declared: arrays are tuples, objects are `$map` or `$id`."""
    if isinstance(value, (tuple, list)):
        return tuple(_decode_undeclared(item) for item in value)
    if isinstance(value, (frozendict, dict)):
        if set(value) == {MAP_TAG} and isinstance(value[MAP_TAG], (frozendict, dict)):
            return frozendict(
                {key: _decode_undeclared(item) for key, item in value[MAP_TAG].items()}
            )
        if set(value) == {ID_TAG} and isinstance(value[ID_TAG], str):
            return parse_id(value[ID_TAG])
        msg = (
            f"an object here must be exactly one of `{MAP_TAG}` or `{ID_TAG}`, not {sorted(value)}"
        )
        raise SchemaError(msg, kind=_KIND)
    return value


def _decimal(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        msg = f"{value!r} is not a decimal number"
        raise SchemaError(msg, kind=_KIND) from exc
    # NaN and an absurd exponent are `freeze()`'s to refuse, with the field's path.
    if not number.is_finite() or abs(number.adjusted()) > MAX_EXPONENT:
        return number
    if decimal_text(number) != value:
        msg = f"{value!r} is not in canonical form, which is {decimal_text(number)!r}"
        raise SchemaError(msg, kind=_KIND)
    return number


def _enum(value: object, enum_class: type[Enum]) -> object:
    msg = f"{value!r} is not a member of {enum_class.__name__}"
    try:
        member = enum_class(value)
    except (ValueError, TypeError) as exc:
        raise SchemaError(msg, kind=_KIND) from exc
    if type(value) is not type(member.value):  # `True` equals 1, but is not what was written
        raise SchemaError(msg, kind=_KIND)
    return member
