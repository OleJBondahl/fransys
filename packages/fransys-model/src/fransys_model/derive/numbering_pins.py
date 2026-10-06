"""FD3: the numbering pins stored at release (`baseline/numbering.json`), and their codec.

`pins(model, unit)` builds `items` only -- `retired` is always `()` here, since computing it
needs a pin SOURCE, a release-time fact (which on-disk release is the source) `derive` cannot
read at all (`fransys_model` reads no file, root CLAUDE.md invariant 6); that is
`fransys`'s own job (FD5), which fills `retired` in with `dataclasses.replace` before
`dumps`. Follows `derive/baseline.py`'s own codec shape: canonical JSON,
`kernel.encode.write_json`/`kernel.jsonread.read_json`, `SchemaVersionError` on any other
`numbering_version`.

Reached as `fransys_model.derive.numbering_pins.<name>`, never re-exported from
`derive/__init__.py` -- `derive.baseline`'s own precedent, and `derive.unit_relative_key`'s
(orchestrator appendix point 4).
"""

from typing import cast

from fransys_model.kernel import AuthoringKey, Id, Model, SchemaError, SchemaVersionError
from fransys_model.kernel.encode import JsonValue, write_json
from fransys_model.kernel.jsonread import read_json
from fransys_model.vocab.numbering_codes import item_class_code
from fransys_model.vocab.tables import items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.vocab.core import Item, Unit

from .designation import designating_ancestors, own_designation_or_none
from .instance_tag import unit_tag
from .lookups import terminal_items
from .rows import NumberingItem, NumberingPins, NumberingRetired
from .unit_relative_key import unit_relative_key
from .unit_release import unit_release

_NUMBERING_VERSION = 1


def item_position(
    model: Model, item: Id[Item]
) -> tuple[AuthoringKey, AuthoringKey | None, str | None]:
    """`item`'s own `(key, scope, code)` (FD2, FD3), for ANY item, printed or not.

    `key` is `unit_relative_key`. `scope` is `unit_relative_key` of `item`'s nearest
    designating ancestor (`designating_ancestors`'s last element), `None` when it has none.
    `code` is `item`'s part's `class_code`, `None` for a part-less item. The same three facts
    `pins()` stores per printed item, but computed here with no gate on
    `own_designation_or_none`: `fransys.build(releases=)`'s own seeding needs an
    untagged, unnumbered item's structural position too, which `pins()` itself never returns
    a row for (it has no own text yet).
    """
    code = item_class_code(model, item)
    ancestors = designating_ancestors(model, item)
    scope = unit_relative_key(model, ancestors[-1]) if ancestors else None
    return unit_relative_key(model, item), scope, code


def unit_position(model: Model, unit: Id[Unit]) -> tuple[AuthoringKey, None, str | None]:
    """A unit instance's own `(key, scope, code)` (UT4), the instance twin of `item_position`.

    `key` is the instance's key without its parent's prefix, so it ends in `"unit"`; `scope`
    is `None` (an instance sits in its parent's top group); `code` is its release's
    `class_code`, `None` when empty.
    """
    record = units_table(model)[unit]
    parent = None if record.parent is None else units_table(model)[record.parent]
    key = record.key if parent is None else record.key[len(parent.key) - 1 :]
    return key, None, unit_release(model, unit).class_code or None


def _unit_rows(model: Model, unit: Id[Unit]) -> list[NumberingItem]:
    """One row per tagged instance directly inside `unit` (UT4), in `items`' own shape."""
    rows = []
    for child in units_table(model).values():
        if child.parent != unit or (text := unit_tag(model, child.id)) is None:
            continue
        key, scope, code = unit_position(model, child.id)
        rows.append(
            NumberingItem(
                key=key, scope=scope, code=code, text=text, authored=child.tag is not None
            )
        )
    return rows


def pins(model: Model, unit: Id[Unit]) -> NumberingPins:
    """`unit`'s own numbering pins (FD3): every own item that prints a designation.

    The candidate set is `passes.numbering.number`'s own: an item of `unit` itself, not a
    `terminal`, whose `own_designation_or_none` is not `None`. `key`, `scope` and `code` come
    from `item_position`; `text` is the item's OWN label, never the `item_designation` chain
    (FD5 seeds this bare text); `authored` is whether it carries a tag. Each tagged instance
    directly inside `unit` adds a row from `unit_position` (UT4), its key ending in `"unit"`.
    `retired` is always `()`: `fransys.release` fills it in.
    """
    terminals = terminal_items(model)
    rows = []
    for item in items(model).values():
        if item.unit != unit or item.id in terminals:
            continue
        text = own_designation_or_none(model, item)
        if text is None:
            continue
        key, scope, code = item_position(model, item.id)
        rows.append(
            NumberingItem(key=key, scope=scope, code=code, text=text, authored=item.tag is not None)
        )
    rows.extend(_unit_rows(model, unit))
    rows.sort(key=lambda row: row.key)
    return NumberingPins(items=tuple(rows), retired=())


def _item_dict(row: NumberingItem) -> dict[str, JsonValue]:
    return {
        "key": list(row.key),
        "scope": None if row.scope is None else list(row.scope),
        "code": row.code,
        "text": row.text,
        "authored": row.authored,
    }


def _retired_dict(row: NumberingRetired) -> dict[str, JsonValue]:
    return {
        "scope": None if row.scope is None else list(row.scope),
        "code": row.code,
        "text": row.text,
    }


def dumps(pins: NumberingPins) -> str:
    """`pins` as canonical JSON (FD3): UTF-8, sorted keys, one trailing newline."""
    data: dict[str, JsonValue] = {
        "numbering_version": _NUMBERING_VERSION,
        "items": [_item_dict(row) for row in pins.items],
        "retired": [_retired_dict(row) for row in pins.retired],
    }
    return write_json(data, compact=True) + "\n"


def _mapping(value: object) -> frozendict[str, object]:
    """`value` as a mapping, the runtime check every `loads` reader needs.

    Raises `SchemaError` when `value` is not a mapping.
    """
    if isinstance(value, (dict, frozendict)):
        return frozendict(value)
    msg = "a numbering pins entry is not a mapping"
    raise SchemaError(msg, kind="numbering_pins")


def _array(value: object) -> tuple[object, ...]:
    """`value` as a tuple, the runtime check every `loads` reader needs.

    Raises `SchemaError` when `value` is not an array.
    """
    if isinstance(value, (tuple, list)):
        return tuple(value)
    msg = "a numbering pins entry is not an array"
    raise SchemaError(msg, kind="numbering_pins")


def _key_from(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    return cast("tuple[str, ...]", _array(value))


def _item_from(value: object) -> NumberingItem:
    d = _mapping(value)
    key = _key_from(d["key"])
    if key is None:
        msg = "a numbering pins item has no key"
        raise SchemaError(msg, kind="numbering_pins")
    return NumberingItem(
        key=key,
        scope=_key_from(d["scope"]),
        code=cast("str | None", d["code"]),
        text=cast("str", d["text"]),
        authored=cast("bool", d["authored"]),
    )


def _retired_from(value: object) -> NumberingRetired:
    d = _mapping(value)
    return NumberingRetired(
        scope=_key_from(d["scope"]),
        code=cast("str | None", d["code"]),
        text=cast("str", d["text"]),
    )


def loads(text: str) -> NumberingPins:
    """A `NumberingPins` read back from `dumps`' canonical JSON.

    Raises:
        SchemaError: `text` is not valid canonical JSON, or its envelope is malformed.
        SchemaVersionError: `text`'s `numbering_version` is not `1`, the only shape this build
            knows.
    """
    data = _mapping(read_json(text))
    version = data.get("numbering_version")
    if type(version) is not int:
        msg = "`numbering_version` is missing or not an int"
        raise SchemaError(msg, kind="numbering_pins")
    if version != _NUMBERING_VERSION:
        msg = (
            f"numbering_version {version} is not known; this build reads only {_NUMBERING_VERSION}"
        )
        raise SchemaVersionError(msg, expected=_NUMBERING_VERSION, actual=version)
    return NumberingPins(
        items=tuple(_item_from(d) for d in _array(data["items"])),
        retired=tuple(_retired_from(d) for d in _array(data["retired"])),
    )


__all__ = [
    "NumberingItem",
    "NumberingPins",
    "NumberingRetired",
    "dumps",
    "item_position",
    "loads",
    "pins",
    "unit_position",
    "unit_relative_key",
]
