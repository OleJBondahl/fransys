"""`geometry.symbols`.

These run against the real symbol library: the adapter is the one place it is used.
"""

import dataclasses

import pytest

from fransys_layout.geometry import (
    Box,
    Facing,
    Orientation,
    Point,
    PortGeometry,
    UnknownSymbolError,
    symbol_geometry,
)


def test_unknown_symbol_raises_and_names_the_key() -> None:
    """An unknown key raises; no placeholder geometry is returned."""
    with pytest.raises(UnknownSymbolError) as excinfo:
        symbol_geometry("no-such-symbol")
    assert excinfo.value.key == "no-such-symbol"


@dataclasses.dataclass(frozen=True)
class _CarriesAFloat:
    x: float


def _leaves(obj: object) -> list[object]:
    if isinstance(obj, tuple):
        return [leaf for item in obj for leaf in _leaves(item)]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return [leaf for f in dataclasses.fields(obj) for leaf in _leaves(getattr(obj, f.name))]
    return [obj]


# The eight orientations as (mirror in x first?, clockwise quarter turns), written out here
# independently of the library so the adapter's output is checked against a second source.
_TRANSFORMS = {
    Orientation.R0: (False, 0),
    Orientation.R90: (False, 1),
    Orientation.R180: (False, 2),
    Orientation.R270: (False, 3),
    Orientation.MR0: (True, 0),
    Orientation.MR90: (True, 1),
    Orientation.MR180: (True, 2),
    Orientation.MR270: (True, 3),
}
_MIRRORED_FACING = {Facing.N: Facing.N, Facing.E: Facing.W, Facing.S: Facing.S, Facing.W: Facing.E}
_TURNED_FACING = {Facing.N: Facing.E, Facing.E: Facing.S, Facing.S: Facing.W, Facing.W: Facing.N}


def _mirror(at: Point) -> Point:
    return Point(x=-at.x, y=at.y)


def _turn(at: Point) -> Point:
    return Point(x=-at.y, y=at.x)


def _transformed(at: Point, facing: Facing, orientation: Orientation) -> tuple[Point, Facing]:
    mirrored, turns = _TRANSFORMS[orientation]
    if mirrored:
        at, facing = _mirror(at), _MIRRORED_FACING[facing]
    for _ in range(turns):
        at, facing = _turn(at), _TURNED_FACING[facing]
    return at, facing


def _on_body_side(port: PortGeometry, body: Box) -> bool:
    return {
        Facing.N: port.at.y == body.y,
        Facing.S: port.at.y == body.y + body.height,
        Facing.W: port.at.x == body.x,
        Facing.E: port.at.x == body.x + body.width,
    }[port.facing]


# `connection-point` is a junction dot whose four ports all sit at its centre, inside its body
# box, so it is the one library symbol that does not put a port on the side it faces (geometry.md
# 5.2).
_OFF_BODY_SIDE_CONTRACT = {"connection-point"}
