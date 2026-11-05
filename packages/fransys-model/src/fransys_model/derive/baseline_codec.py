"""The listing's JSON codec and section check: `dumps`, `loads`, ..."""

import dataclasses
from typing import cast
lazy from collections.abc import Mapping

from fransys_model.elecdef import Rating
from fransys_model.kernel import JsonValue, SchemaError, SchemaVersionError, read_json, value_data, value_from, write_json
from fransys_model.vocab.operating import Operating

from .baseline_codec_keys import (
    BOUNDARY_KEYS,
    END_KEYS,
    ITEM_KEYS,
    NET_KEYS,
    key_fields,
    key_kwargs,
)
from .baseline_item_order import key_ordered
from .baseline_rules import KEYED_LISTING_VERSION
from .rows_baseline import (
    BaselineBoundary,
    BaselineConductor,
    BaselineItem,
    BaselineMate,
    BaselineNestedUnit,
    BaselineNet,
    BaselineUnit,
    Listing,
)

# -- dumps / loads (canonical JSON) ----------------------------------------


def _unit_dict(u: BaselineUnit) -> dict[str, JsonValue]:
    return {"name": u.name, "version": u.version, "revision": u.revision, "interface": u.interface}


def _item_dict(i: BaselineItem) -> dict[str, JsonValue]:
    row: dict[str, JsonValue] = {
        "designation": i.designation,
        "mpn": i.mpn,
        "manufacturer": i.manufacturer,
        "installed": i.installed,
        "external": i.external,
        "position": i.position,
    }
    if i.parent is not None:
        row["parent"] = i.parent  # written only when set: an older listing keeps its bytes
    return row | key_fields(i, ITEM_KEYS)


def _nested_unit_dict(u: BaselineNestedUnit) -> dict[str, JsonValue]:
    return {
        "name": u.name,
        "version": u.version,
        "revision": u.revision,
        "interface": u.interface,
        "instances": list(u.instances),
    }


def _boundary_dict(b: BaselineBoundary) -> dict[str, JsonValue]:
    return {
        "function": b.designation,
        "ports": list(b.ports),
        "rating": None if b.rating is None else value_data(b.rating),
        "operating": None if b.operating is None else value_data(b.operating),
    } | key_fields(b, BOUNDARY_KEYS)


def _conductor_dict(c: BaselineConductor) -> dict[str, JsonValue]:
    return {
        "kind": c.kind,
        "a": c.a,
        "b": c.b,
        "carrier": c.carrier,
        "colour": c.colour,
        "gauge_mm2": c.gauge_mm2,
        "length_mm": c.length_mm,
        "label": c.label,
    } | key_fields(c, END_KEYS)


def _mate_dict(m: BaselineMate) -> dict[str, JsonValue]:
    return {"a": m.a, "b": m.b} | key_fields(m, END_KEYS)


def _net_dict(n: BaselineNet) -> dict[str, JsonValue]:
    row: dict[str, JsonValue] = {
        "name": n.name,
        "class": n.net_class,
        "potential": n.potential,
        "ports": list(n.ports),
    }
    return row | key_fields(n, NET_KEYS)


def dumps(listing: Listing) -> str:
    """`listing` as canonical JSON: UTF-8, sorted keys, one trailing newline.

    Args:
        listing: The listing to encode.

    Returns:
        The JSON text, which `loads` reads back.
    """
    data: dict[str, JsonValue] = {
        "listing_version": KEYED_LISTING_VERSION,
        "unit": _unit_dict(listing.unit),
        "items": [_item_dict(row) for row in listing.items],
        "units": [_nested_unit_dict(row) for row in listing.units],
        "boundary": [_boundary_dict(row) for row in listing.boundary],
        "conductors": [_conductor_dict(row) for row in listing.conductors],
        "mates": [_mate_dict(row) for row in listing.mates],
        "nets": [_net_dict(row) for row in listing.nets],
    }
    return write_json(data, compact=True) + "\n"


def _mapping(value: object) -> frozendict[str, object]:
    """`value` as a mapping, else `SchemaError`: the runtime check every `loads` reader needs.

    `value` is `object` (as `read_json` returns), the same shape `kernel.decode._mapping` narrows.
    """
    if isinstance(value, dict | frozendict):
        return frozendict[str, object](value)
    msg = "a baseline listing entry is not a mapping"
    raise SchemaError(msg, kind="listing")


def _array(value: object) -> tuple[object, ...]:
    """`value` as a tuple, the runtime check every `loads` reader needs.

    Raises `SchemaError` when `value` is not an array.
    """
    if isinstance(value, (tuple, list)):
        return tuple(value)
    msg = "a baseline listing entry is not an array"
    raise SchemaError(msg, kind="listing")


def _unit_from(value: object) -> BaselineUnit:
    d = _mapping(value)
    return BaselineUnit(
        name=cast("str", d["name"]),
        version=cast("int", d["version"]),
        revision=cast("int", d["revision"]),
        interface=cast("str", d["interface"]),
    )


def _item_from(value: object) -> BaselineItem:
    d = _mapping(value)
    return BaselineItem(
        designation=cast("str", d["designation"]),
        mpn=cast("str", d["mpn"]),
        manufacturer=cast("str", d["manufacturer"]),
        installed=cast("bool", d["installed"]),
        external=cast("bool", d["external"]),
        position=cast("int | None", d["position"]),
        parent=cast("str | None", d.get("parent")),
        **key_kwargs(d, ITEM_KEYS),
    )


def _nested_unit_from(value: object) -> BaselineNestedUnit:
    d = _mapping(value)
    return BaselineNestedUnit(
        name=cast("str", d["name"]),
        version=cast("int", d["version"]),
        revision=cast("int", d["revision"]),
        interface=cast("str", d["interface"]),
        instances=cast("tuple[str, ...]", _array(d["instances"])),
    )


def _boundary_from(value: object) -> BaselineBoundary:
    d = _mapping(value)
    return BaselineBoundary(
        designation=cast("str", d["function"]),
        ports=cast("tuple[str, ...]", _array(d["ports"])),
        rating=None if d["rating"] is None else value_from(cast("JsonValue", d["rating"]), Rating),
        operating=None if d["operating"] is None else value_from(cast("JsonValue", d["operating"]), Operating),
        **key_kwargs(d, BOUNDARY_KEYS),
    )


def _conductor_from(value: object) -> BaselineConductor:
    d = _mapping(value)
    return BaselineConductor(
        kind=cast("str", d["kind"]),
        a=cast("str", d["a"]),
        b=cast("str", d["b"]),
        carrier=cast("str | None", d["carrier"]),
        colour=cast("str | None", d["colour"]),
        gauge_mm2=cast("str | None", d["gauge_mm2"]),
        length_mm=cast("int | None", d["length_mm"]),
        label=cast("str | None", d["label"]),
        **key_kwargs(d, END_KEYS),
    )


def _mate_from(value: object) -> BaselineMate:
    d = _mapping(value)
    return BaselineMate(a=cast("str", d["a"]), b=cast("str", d["b"]), **key_kwargs(d, END_KEYS))


def _net_from(value: object) -> BaselineNet:
    d = _mapping(value)
    return BaselineNet(
        name=cast("str | None", d["name"]),
        net_class=cast("str", d["class"]),
        potential=cast("str | None", d["potential"]),
        ports=cast("tuple[str, ...]", _array(d["ports"])),
        **key_kwargs(d, NET_KEYS),
    )


def loads(text: str) -> Listing:
    """A `Listing` read back from `dumps`' canonical JSON.

    Args:
        text: The JSON text `dumps` wrote.

    Returns:
        The decoded `Listing`.

    Raises:
        SchemaError: the text is not valid canonical JSON, or its envelope is malformed.
        SchemaVersionError: `text`'s `listing_version` is not `3`, the one shape this build reads:
            keyed rows with `rating` and `operating` in the kernel's canonical form.
    """
    data = _mapping(read_json(text))
    if (version := _version_of(data)) != KEYED_LISTING_VERSION:
        msg = (
            f"listing_version {version} is not known; this build reads {KEYED_LISTING_VERSION}: rebuild the release and re-cut it with fr.rebaseline"
        )
        raise SchemaVersionError(msg, expected=KEYED_LISTING_VERSION, actual=version)
    return Listing(
        unit=_unit_from(data["unit"]),
        items=tuple(_item_from(d) for d in _array(data["items"])),
        units=tuple(_nested_unit_from(d) for d in _array(data["units"])),
        boundary=tuple(_boundary_from(d) for d in _array(data["boundary"])),
        conductors=tuple(_conductor_from(d) for d in _array(data["conductors"])),
        mates=tuple(_mate_from(d) for d in _array(data["mates"])),
        nets=tuple(_net_from(d) for d in _array(data["nets"])),
    )


def _version_of(data: Mapping[str, object]) -> int:
    version = data.get("listing_version")
    if type(version) is not int:
        msg = "`listing_version` is missing or not an int"
        raise SchemaError(msg, kind="listing")
    return version


def stored_version(text: str) -> int:
    """The `listing_version` of stored listing `text`, whatever it is; `loads` refuses all but 3."""
    return _version_of(_mapping(read_json(text)))


def without_parent(listing: Listing) -> Listing:
    """`listing` with every item's `parent` dropped: parent is never compared (model-0212)."""
    items = tuple(dataclasses.replace(row, parent=None) for row in listing.items)
    return dataclasses.replace(listing, items=items)


def matches(stored_text: str, fresh: Listing) -> bool:
    """Whether the stored listing text equals `fresh`, `parent` aside (model-0212).

    Equal bytes match at once; otherwise the two parse and compare as `differing_sections` does.
    """
    if stored_text == dumps(fresh):
        return True
    return not differing_sections(loads(stored_text), fresh)


def differing_sections(a: Listing, b: Listing) -> tuple[str, ...]:
    """The names of `a`'s and `b`'s top-level fields that differ, in field order.

    `parent` is not compared. Returns `()` when the listings are equal.
    """
    a, b = without_parent(a), without_parent(b)
    a = dataclasses.replace(a, items=key_ordered(a.items))
    b = dataclasses.replace(b, items=key_ordered(b.items))
    return tuple(field.name for field in dataclasses.fields(Listing) if getattr(a, field.name) != getattr(b, field.name))
