"""Record gates E11 and E12 (spec SURFACE-COHERENCE R1): hint fields and port-end types."""

import dataclasses
import inspect
import typing
from types import UnionType

from fransys_model import layout
from fransys_model.kernel import Id
from fransys_model.layout import AUTHORED_KINDS, GroupHint, OrderHint, SideHint
from fransys_model.vocab import Port

POSITION_FIELDS = frozenset(["x", "y", "page", "at", "position"])
RESULT_MODULES = frozenset(["results", "harness_results", "cable_results"])
ENDPOINT_FIELDS = frozenset(["a", "b", "far", "near", "from_", "to", "port"])
PORT_ID = Id[Port]


def position_fields(kinds: typing.Iterable[typing.Any]) -> list[str]:
    """E11: `Kind.field` for each dataclass field of the kinds that names a position."""
    return [
        f"{kind.__name__}.{f.name}"
        for kind in kinds
        for f in dataclasses.fields(kind)
        if f.name in POSITION_FIELDS
    ]


def _is_port_id(annotation: object) -> bool:
    """True for `Id[Port]` and `Id[Port] | None`: the two forms an endpoint may take."""
    if typing.get_origin(annotation) is UnionType:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return len(args) == 1 and _is_port_id(args[0])
    return annotation == PORT_ID


def endpoint_fields(kinds: typing.Iterable[typing.Any]) -> list[tuple[str, object]]:
    """E12 rows: (`Kind.field`, resolved annotation) for each endpoint-named field."""
    return [
        (f"{kind.__name__}.{name}", hint)
        for kind in kinds
        for name, hint in typing.get_type_hints(kind).items()
        if name in ENDPOINT_FIELDS
    ]


def untyped_endpoints(rows: list[tuple[str, object]]) -> list[str]:
    """E12: the rows whose annotation is not `Id[Port]` (or that, or `None`)."""
    return [site for site, hint in rows if not _is_port_id(hint)]


def _result_records() -> list[type]:
    exported = (getattr(layout, name) for name in layout.__all__)
    return [
        c
        for c in exported
        if inspect.isclass(c)
        and dataclasses.is_dataclass(c)
        and c.__module__.rsplit(".", 1)[-1] in RESULT_MODULES
    ]


def test_authored_hints_hold_no_position_field():
    # AUTHORED_KINDS is public in fransys_model.layout.__all__; the hint classes are in it.
    assert {GroupHint, OrderHint, SideHint} <= set(AUTHORED_KINDS), "walk missed the hints"
    assert position_fields(AUTHORED_KINDS) == []


def test_result_port_ends_are_port_ids():
    records = _result_records()
    rows = endpoint_fields(records)
    sites = {site for site, _ in rows}
    assert {"LinkMarker.far", "PinCell.port", "PowerSymbol.port"} <= sites
    assert len(rows) == 5, sites
    assert untyped_endpoints(rows) == []


def test_the_position_gate_can_fail():
    @dataclasses.dataclass
    class Planted:
        x: int
        side: str

    @dataclasses.dataclass
    class Clean:
        side: str

    assert position_fields([Planted]) == ["Planted.x"]
    assert position_fields([Clean]) == []


def test_the_endpoint_gate_can_fail():
    @dataclasses.dataclass
    class Planted:
        a: str
        b: Id[Port]
        far: Id[Port] | None
        port: Id[Port] | None
        near: Id[Port] | int

    bad = untyped_endpoints(endpoint_fields([Planted]))
    assert bad == ["Planted.a", "Planted.near"]
