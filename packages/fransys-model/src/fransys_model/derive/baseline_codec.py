"""The listing's JSON codec and section check (baseline spec L2): `dumps`, `loads`, ..."""

import dataclasses
from decimal import Decimal
from typing import cast

from fransys_model.kernel import SchemaError, SchemaVersionError
from fransys_model.kernel.encode import JsonValue, decimal_text, write_json
from fransys_model.kernel.jsonread import read_json
from fransys_model.vocab.ratings import BreakingPoint, Operating, Rating

from .rows import (
    BaselineBoundary,
    BaselineConductor,
    BaselineItem,
    BaselineMate,
    BaselineNestedUnit,
    BaselineNet,
    BaselineUnit,
    Listing,
)

_LISTING_VERSION = 1


# -- dumps / loads (canonical JSON, baseline spec L2) ----------------------------------------


_POINT_FIELDS = frozenset({"breaking_ac", "breaking_dc"})
# The fields RATINGS-3 added: written only off their default, so an older listing keeps its bytes.
_NEW_FIELDS = _POINT_FIELDS | {"fault_current_ac_a", "fault_current_dc_a", "fault_time_constant_ms"}


def _decimal_text_or_none(v: Decimal | None) -> str | None:
    return None if v is None else decimal_text(v)


def _point_dict(point: BreakingPoint) -> dict[str, JsonValue]:
    return {
        "voltage_v": decimal_text(point.voltage_v),
        "current_a": decimal_text(point.current_a),
        "time_constant_ms": _decimal_text_or_none(point.time_constant_ms),
    }


def _field_json(v: object) -> JsonValue:
    if isinstance(v, tuple):
        return [_point_dict(point) for point in v]
    return _decimal_text_or_none(cast("Decimal | None", v))


def _decimal_dict(value: Rating | Operating | None) -> dict[str, JsonValue] | None:
    """A `Rating`/`Operating`'s own fields, `Decimal` as text; a new field only when set."""
    if value is None:
        return None
    named = {field.name: getattr(value, field.name) for field in dataclasses.fields(value)}
    return {
        name: _field_json(v)
        for name, v in named.items()
        if name not in _NEW_FIELDS or v not in (None, ())
    }


def _point_from(value: object) -> BreakingPoint:
    d = _mapping(value)
    tc = cast("str | None", d["time_constant_ms"])
    return BreakingPoint(
        voltage_v=Decimal(cast("str", d["voltage_v"])),
        current_a=Decimal(cast("str", d["current_a"])),
        time_constant_ms=None if tc is None else Decimal(tc),
    )


def _field_from(key: str, v: object) -> object:
    if key in _POINT_FIELDS:
        return tuple(_point_from(point) for point in _array(v))
    return None if v is None else Decimal(cast("str", v))


def _decimal_value[T](cls: type[T], value: object) -> T | None:
    if value is None:
        return None
    return cls(**{key: _field_from(key, v) for key, v in _mapping(value).items()})


def _unit_dict(u: BaselineUnit) -> dict[str, JsonValue]:
    return {"name": u.name, "version": u.version, "revision": u.revision, "interface": u.interface}


def _item_dict(i: BaselineItem) -> dict[str, JsonValue]:
    return {
        "designation": i.designation,
        "mpn": i.mpn,
        "manufacturer": i.manufacturer,
        "installed": i.installed,
        "external": i.external,
        "position": i.position,
    }


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
        "rating": _decimal_dict(b.rating),
        "operating": _decimal_dict(b.operating),
    }


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
    }


def _mate_dict(m: BaselineMate) -> dict[str, JsonValue]:
    return {"a": m.a, "b": m.b}


def _net_dict(n: BaselineNet) -> dict[str, JsonValue]:
    return {"name": n.name, "class": n.net_class, "potential": n.potential, "ports": list(n.ports)}


def dumps(listing: Listing) -> str:
    """`listing` as canonical JSON (baseline spec L2): UTF-8, sorted keys, one trailing newline.

    Args:
        listing: The listing to encode.

    Returns:
        The JSON text, which `loads` reads back.
    """
    data: dict[str, JsonValue] = {
        "listing_version": _LISTING_VERSION,
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
        rating=_decimal_value(Rating, d["rating"]),
        operating=_decimal_value(Operating, d["operating"]),
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
    )


def _mate_from(value: object) -> BaselineMate:
    d = _mapping(value)
    return BaselineMate(a=cast("str", d["a"]), b=cast("str", d["b"]))


def _net_from(value: object) -> BaselineNet:
    d = _mapping(value)
    return BaselineNet(
        name=cast("str | None", d["name"]),
        net_class=cast("str", d["class"]),
        potential=cast("str | None", d["potential"]),
        ports=cast("tuple[str, ...]", _array(d["ports"])),
    )


def loads(text: str) -> Listing:
    """A `Listing` read back from `dumps`' canonical JSON.

    Args:
        text: The JSON text `dumps` wrote.

    Returns:
        The decoded `Listing`.

    Raises:
        SchemaError: the text is not valid canonical JSON, or its envelope is malformed.
        SchemaVersionError: `text`'s `listing_version` is not `1`, the only shape this build
            knows.
    """
    data = _mapping(read_json(text))
    version = data.get("listing_version")
    if type(version) is not int:
        msg = "`listing_version` is missing or not an int"
        raise SchemaError(msg, kind="listing")
    if version != _LISTING_VERSION:
        msg = f"listing_version {version} is not known; this build reads only {_LISTING_VERSION}"
        raise SchemaVersionError(msg, expected=_LISTING_VERSION, actual=version)
    return Listing(
        unit=_unit_from(data["unit"]),
        items=tuple(_item_from(d) for d in _array(data["items"])),
        units=tuple(_nested_unit_from(d) for d in _array(data["units"])),
        boundary=tuple(_boundary_from(d) for d in _array(data["boundary"])),
        conductors=tuple(_conductor_from(d) for d in _array(data["conductors"])),
        mates=tuple(_mate_from(d) for d in _array(data["mates"])),
        nets=tuple(_net_from(d) for d in _array(data["nets"])),
    )


def differing_sections(a: Listing, b: Listing) -> tuple[str, ...]:
    """The names of `a`'s and `b`'s top-level fields that differ, in field order (L2).

    Args:
        a: One listing.
        b: The listing to compare it with.

    Returns:
        The differing `Listing` field names; `()` when the listings are equal.
    """
    return tuple(
        field.name
        for field in dataclasses.fields(Listing)
        if getattr(a, field.name) != getattr(b, field.name)
    )
