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
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from . import registry
from .draft import Draft
from .encode import CLASS_TAG, CLASS_VALUE, ID_TAG, MAP_TAG, decimal_text
from .errors import FreezeError, ModelError, SchemaError, SchemaVersionError
from .freeze import freeze
from .ids import parse_id
from .origin import Origin
from .schema import annotations_of, fields_of, id_type, key_and_value_aliases
from .values import MAX_EXPONENT
lazy from .encode import JsonValue
lazy from .model import Model

if TYPE_CHECKING:
    from .record_protocol import Record

_KIND = "canonical"
_PAIR = 2
_SCHEMA_VERSION_KEY = "schema_version"
_ORIGIN = Origin(file="<canonical>", line=0, note="")


def from_data(data: JsonValue) -> Model:
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
    _check_version(envelope.get(_SCHEMA_VERSION_KEY))
    if set(envelope) != {"aliases", _SCHEMA_VERSION_KEY, "tables"}:
        msg = f"the data must have exactly aliases, schema_version and tables, not {sorted(envelope)}"
        raise SchemaError(msg, kind=_KIND)
    tables = _tables(envelope["tables"])
    aliases = _pairs(envelope["aliases"])
    try:
        return _build(tables, aliases)
    except RecursionError as exc:
        msg = "the data is nested too deeply"
        raise SchemaError(msg, kind=_KIND) from exc


def _check_version(version: object) -> None:
    """Refuse a stored version that is not an int, or not the one the domain registered."""
    if type(version) is not int:
        msg = f"`{_SCHEMA_VERSION_KEY}` is missing or not an int"
        raise SchemaError(msg, kind=_KIND)
    expected = registry.registered_schema_version()
    if version != expected:
        msg = f"this build reads schema version {expected}, not {version}"
        raise SchemaVersionError(msg, expected=expected, actual=version)


def _build(tables: dict[str, tuple[frozendict[str, Any], ...]], aliases: tuple[tuple[str, str], ...]) -> Model:
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
        tables[kind] = tuple(_mapping(row, f"tables.{kind}[{index}]") for index, row in enumerate(_array(rows, f"table `{kind}`")))
    return tables


def _fill(draft: Draft, tables: dict[str, tuple[frozendict[str, Any], ...]]) -> tuple[ModelError, ...]:
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
    cls = registry.lookup_kind(kind)
    kwargs = _fields(cls, item, kind)
    return cls(**kwargs)


def _fields(cls: type, item: frozendict[str, Any], what: str) -> dict[str, Any]:
    """Decode `item` into constructor arguments: every field present, none unknown."""
    annotations = annotations_of(cls)
    fields = fields_of(cls)
    names = {field.name for field in fields}
    optional = {field.name for field in fields if field.metadata.get("omit_none")}
    unknown, missing = sorted(set(item) - names), sorted(names - optional - set(item))
    if unknown or missing:
        msg = f"{what}: unknown fields {unknown}, missing fields {missing}"
        raise SchemaError(msg, kind=what)
    # A field the record derives itself (`init=False`) is written, but not read back.
    return {field.name: _field(field.name, item.get(field.name), annotations[field.name]) for field in fields if field.init}


def _field(name: str, value: object, annotation: object) -> object:
    try:
        return _decode_value(value, annotation)
    except SchemaError as exc:
        msg = f"field `{name}`: {exc}"
        raise SchemaError(msg, kind=exc.kind) from exc


def value_from[T](data: JsonValue, cls: type[T]) -> T:
    """The value of class `cls` that `value_data` wrote as `data`.

    Example: `value_from(value_data(rating), Rating) == rating`. A shape that does not fit `cls` is
    a `SchemaError`.
    """
    return cast("T", _decode_value(data, cls))


def _decode_value(value: object, annotation: object) -> object:
    """Turn `value` back into what `annotation` declares, converting only what JSON cannot say."""
    if annotation is key_and_value_aliases()[0]:  # AuthoringKey is `tuple[str, ...]`
        annotation = annotation.__value__
    origin = get_origin(annotation)
    if origin is types.UnionType:
        return None if value is None else _decode_value(value, registry.optional_arm(annotation))
    if origin in (tuple, frozenset):
        return _decode_seq(value, origin, get_args(annotation)[0])
    if origin is frozendict:
        return _decode_mapping(value, get_args(annotation)[1])
    if origin is id_type():
        return parse_id(value) if isinstance(value, str) else value
    return _decode_plain(value, annotation)


def _decode_seq(value: object, origin: type, item_annotation: object) -> object:
    if not isinstance(value, (tuple, list)):
        return value
    return origin(_decode_value(item, item_annotation) for item in value)


def _decode_mapping(value: object, item_annotation: object) -> object:
    if not isinstance(value, (frozendict, dict)):
        return value
    return frozendict({key: _decode_value(item, item_annotation) for key, item in value.items()})


def _decode_plain(value: object, annotation: object) -> object:
    if isinstance(value, (frozendict, dict)) and CLASS_TAG in value:  # a slot of several classes
        annotation = registry.class_for_tag(value[CLASS_TAG])
        if annotation is None or set(value) != {CLASS_TAG, CLASS_VALUE}:
            msg = f"`{CLASS_TAG}` names no registered class, or `{CLASS_VALUE}` is missing"
            raise SchemaError(msg, kind=_KIND)
        value = value[CLASS_VALUE]
    if isinstance(annotation, type) and registry.is_value_class(annotation):
        return _decode_class(value, annotation)
    if annotation is Decimal:
        return decimal_value(value)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return enum_value(value, annotation)
    if annotation in (str, int, bool) or annotation is None:
        return value
    return _decode_undeclared(value)


def _decode_class(value: object, cls: type) -> object:
    """Rebuild `cls` from its object; anything else is left for `freeze()` to refuse."""
    if not isinstance(value, (frozendict, dict)):
        return value
    fields = _fields(cls, frozendict(value), cls.__name__)
    # init=False: the constructor takes `*items`
    init = cast("Any", cls).__dataclass_params__.init
    return cls(**fields) if init else cls(*next(iter(fields.values())))


def _decode_undeclared(value: object) -> object:
    """Read `value` where no type is declared: arrays are tuples, objects are `$map` or `$id`."""
    if isinstance(value, (tuple, list)):
        return tuple(_decode_undeclared(item) for item in value)
    if isinstance(value, (frozendict, dict)):
        if set(value) == {MAP_TAG} and isinstance(value[MAP_TAG], (frozendict, dict)):
            return frozendict({key: _decode_undeclared(item) for key, item in value[MAP_TAG].items()})
        if set(value) == {ID_TAG} and isinstance(value[ID_TAG], str):
            return parse_id(value[ID_TAG])
        msg = f"an object here must be exactly one of `{MAP_TAG}` or `{ID_TAG}`, not {sorted(value)}"
        raise SchemaError(msg, kind=_KIND)
    return value


def decimal_value(value: object) -> object:
    """Read a canonical decimal string; anything else is left for `freeze()` to refuse."""
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


def enum_value(value: object, enum_class: type[Enum]) -> object:
    """Read a member by its name when `enum_class` is stored by name, else by its value."""
    by_name = registry.is_enum_by_name(enum_class)
    try:
        member = enum_class[cast("str", value)] if by_name else enum_class(value)
        if by_name or type(value) is type(member.value):  # `True` equals 1, not what was written
            return member
    except ValueError, TypeError, KeyError:
        pass
    msg = f"{value!r} is not a member of {enum_class.__name__}"
    raise SchemaError(msg, kind=_KIND)
