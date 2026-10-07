"""Symbol adapter: the only module that touches the symbol libraries (docs/design/geometry.md 5.2).

It calls `LIBRARY.get`, `repeat` and `orient`, then converts the libraries' `float`
module units to integer grid units once. Nothing above this module sees a `float`.
"""

from enum import Enum
from functools import cache
from typing import TYPE_CHECKING

from graphical_symbols import Orientation as LibraryOrientation
from graphical_symbols import UnknownSymbolError as LibraryUnknownSymbolError
from graphical_symbols import body_box, keepout_box, orient, repeat, slot_box
from graphical_symbols.model import nodes_of

from electrical_symbols import (
    GENERIC_BOX_KEY,
    LIBRARY,
    NORTH,
    PORT_PITCH_G,
    SOUTH,
    box_port_name,
    default_order,
    default_sides,
    draw_order,
    generic_box,
    is_generic_box,
    text_width,
)
from electrical_symbols import library_version as _electrical_symbols_library_version
from fransys_model.kernel import register_enum, value
from fransys_model.layout import Orientation

from .box_reach import Reach, spread
from .boxes import Box
from .errors import GeometryError, UnknownSymbolError
from .units import G_PER_MODULE, Point, to_grid

__all__ = (  # re-exported by `geometry`: the generic box's home is `electrical_symbols.box_ports`
    "GENERIC_BOX_KEY",
    "NORTH",
    "OPPOSITE",
    "PORT_PITCH_G",
    "SOUTH",
    "Orientation",
    "box_port_name",
    "default_order",
    "default_sides",
    "draw_order",
    "text_width",
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from graphical_symbols import Box as LibraryBox
    from graphical_symbols import Point as LibraryPoint
    from graphical_symbols import Symbol


@register_enum
class Facing(Enum):
    """The side a port or slot points to; y grows down, so `N` is towards smaller y."""

    N = "n"
    E = "e"
    S = "s"
    W = "w"


OPPOSITE: Mapping[Facing, Facing] = frozendict(
    {Facing.N: Facing.S, Facing.E: Facing.W, Facing.S: Facing.N, Facing.W: Facing.E}
)


@value
class PortGeometry:
    """One symbol port, relative to the symbol origin. `name` is the symbol port id."""

    name: str
    at: Point
    facing: Facing


def port_page_at(origin: Point, port: PortGeometry) -> Point:
    """A port's position on the page: the placed function's origin plus the port's own offset."""
    return Point(x=origin.x + port.at.x, y=origin.y + port.at.y)


@value
class SlotGeometry:
    """One label space of a symbol: `"tag"`, `"marking.<port>"` or `"value"`."""

    slot: str
    at: Point
    side: Facing
    box: Box


@value
class ThroughPath:
    """The base-symbol port names of a symbol's through path: `"in"`/`"out"`, `"com"`/`"no"`."""

    start: str
    end: str


@value
class SymbolGeometry:
    """One oriented, repeated symbol; `nodes` lists port-name tuples, a port in none is alone."""

    key: str
    poles: int
    orientation: Orientation
    body: Box
    keepout: Box
    through: ThroughPath | None
    ports: tuple[PortGeometry, ...]
    slots: tuple[SlotGeometry, ...]
    nodes: tuple[tuple[str, ...], ...] = ()

    @property
    def generic_box(self) -> bool:
        """Whether this is the labelled-box placeholder (`electrical_symbols.is_generic_box`)."""
        return is_generic_box(self.key)


def symbol_geometry(
    key: str, *, poles: int = 1, orientation: Orientation = Orientation.R0
) -> SymbolGeometry:
    """Look up `key`, repeat it `poles` times, orient it and convert to grid units."""
    return _cached_geometry(key, poles, orientation)


@cache
def _cached_geometry(key: str, poles: int, orientation: Orientation) -> SymbolGeometry:
    """Build and cache the geometry; `symbol_geometry("k")` and `poles=1` share one entry."""
    if poles < 1:
        msg = f"a symbol has at least one pole, got {poles}"
        raise GeometryError(msg)
    try:
        base = LIBRARY.get(key)
    except LibraryUnknownSymbolError:
        msg = f"no symbol {key!r} in the symbol library"
        raise UnknownSymbolError(msg, key=key) from None
    if poles > 1:
        if not any(path.through for path in base.paths):
            msg = f"symbol {key!r} has no through path, so it cannot be repeated {poles} times"
            raise GeometryError(msg)
        base = repeat(base, poles)
    return convert(
        orient(base, LibraryOrientation[orientation.name]), poles=poles, orientation=orientation
    )


def generic_box_geometry(
    port_names: tuple[str, ...],
    sides: tuple[str, ...] = (),
    reach: tuple[Reach, ...] = (),
    *,
    offsets: tuple[float, ...] = (),
    stand: int = 0,
) -> SymbolGeometry:
    """The labelled-box placeholder, pins `reach` apart (model-0129) or at `offsets` (0107).

    `stand` is the width in G of the power symbol and text standing at a pin: the pitch fits it.
    """
    if offsets:
        return _generic(port_names, sides, offsets)
    base = _generic(port_names, sides, stand=stand)
    if not reach:
        return base
    spots = {p.name: (p.facing.value, p.at.x) for p in base.ports}
    placed = spread(spots, reach, channel_pitch())
    if all(placed[name] == spots[name][1] for name in spots):
        return base
    return _generic(port_names, sides, tuple(placed[name] / G_PER_MODULE for name in port_names))


@cache
def channel_pitch() -> int:
    """V5: a box channel's pitch, 1.5 times the pole pitch (a 3-pole symbol's phase distance)."""
    ports = {p.name: p.at.x for p in symbol_geometry("circuit-breaker", poles=3).ports}
    return (ports["2.in"] - ports["1.in"]) * 3 // 2


def _generic(
    port_names: tuple[str, ...],
    sides: tuple[str, ...],
    offsets: tuple[float, ...] = (),
    *,
    stand: int = 0,
) -> SymbolGeometry:
    """One generic box converted to grid units."""
    return convert(
        orient(generic_box(port_names, sides, offsets, stand), LibraryOrientation.R0),
        poles=1,
        orientation=Orientation.R0,
    )


def convert(symbol: Symbol, *, poles: int, orientation: Orientation) -> SymbolGeometry:
    """Convert one library symbol, already repeated and oriented, to grid units."""
    # `repeat` prefixes pole 1's ports `1.`; the through path names the base ports.
    pole_prefix = "1." if poles > 1 else ""
    through = next(
        (
            ThroughPath(
                start=path.from_port.removeprefix(pole_prefix),
                end=path.to_port.removeprefix(pole_prefix),
            )
            for path in symbol.paths
            if path.through
        ),
        None,
    )
    ports = tuple(
        PortGeometry(name=port.id, at=_point(port.position), facing=Facing[port.direction.name])
        for port in symbol.ports
    )
    slots = tuple(
        SlotGeometry(
            slot=slot.id,
            at=_point(slot.position),
            side=Facing[slot.side.name],
            box=_box(slot_box(slot)),
        )
        for slot in symbol.slots
    )
    node_groups = tuple(sorted(tuple(sorted(node.ports)) for node in nodes_of(symbol)))
    return SymbolGeometry(
        key=symbol.reference.number,
        poles=poles,
        orientation=orientation,
        body=_box(body_box(symbol)),
        keepout=_box(keepout_box(symbol)),
        through=through,
        ports=tuple(sorted(ports, key=lambda port: port.name)),
        slots=tuple(sorted(slots, key=lambda slot: slot.slot)),
        nodes=node_groups,
    )


def _point(point: LibraryPoint) -> Point:
    return Point(x=to_grid(point.x), y=to_grid(point.y))


def _box(box: LibraryBox) -> Box:
    x, y = to_grid(box.min.x), to_grid(box.min.y)
    return Box(x=x, y=y, width=to_grid(box.max.x) - x, height=to_grid(box.max.y) - y)


def library_version() -> str:
    """Return the symbol library version recorded in every `layout.symbol_placement`."""
    return _electrical_symbols_library_version()
