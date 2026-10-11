"""layout-0171: how far a power symbol under a coil pushes its contact table down, as a value."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point, port_page_at, push_clear

from .texts.power import symbol_place

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import SymbolGeometry
    from fransys_model.kernel import AuthoringKey

    from .images import _Reserve
    from .types import DrawnFunction, Handle, PowerEnd, Profile


@dataclass(frozen=True)
class Foot:
    """A cell's table stand in its own frame: `x` and `top` of its table, what is drawn under it."""

    x: int
    top: int
    blockers: tuple[Box, ...]


def table_x(origin: Point, geometry: SymbolGeometry) -> int:
    """layout-0123 F1: the x a coil's table starts: its rightmost bottom port, half a grid out."""
    ports = [p for p in geometry.ports if p.facing is Facing.S] or list(geometry.ports)
    return max(port_page_at(origin, p).x for p in ports) + WIRING_GRID // 2


def marker_feet(
    drawn: Sequence[DrawnFunction], power: Sequence[PowerEnd], profile: Profile
) -> dict[Handle, Foot]:
    """Each function with a power symbol on a bottom port: its first-lead symbols as blockers."""
    symbol_of = {one.port: one.symbol for one in power}
    found = {}
    for one in drawn:
        named = {p.symbol_port: symbol_of[p.port] for p in one.ports if p.port in symbol_of}
        placed = [
            symbol_place(named[p.name], (one.function, 0, 0), pin=p.at, facing=p.facing, grids=1)
            for p in one.geometry.ports
            if p.facing is Facing.S and p.name in named
        ]
        if placed:
            keepout = one.geometry.keepout
            found[one.function] = Foot(
                x=table_x(Point(x=0, y=0), one.geometry),
                top=keepout.y + keepout.height + profile.marker_padding,
                blockers=tuple(box for s in placed for box in (s.body, s.lead)),
            )
    return found


def table_push(foot: Foot | None, height: int, profile: Profile) -> int:
    """How far below `foot.top` a table `height` tall stands once `push_clear` has cleared it."""
    if foot is None:
        return 0
    box = Box(x=foot.x, y=foot.top, width=1, height=height)
    return push_clear(box, foot.blockers, gap=profile.marker_padding, axis="y").y - foot.top


def with_marker_push(
    reserves: Mapping[tuple[AuthoringKey, Handle], _Reserve],
    feet: Mapping[Handle, Foot],
    profile: Profile,
) -> dict[tuple[AuthoringKey, Handle], _Reserve]:
    """layout-0171: a table's room grows by its push below the power symbol under its coil."""
    found = dict(reserves)
    for place, reserve in reserves.items():
        if reserve.tables:
            push = table_push(feet.get(place[1]), reserve.tables[0], profile)
            found[place] = replace(reserve, down=reserve.down + push)
    return found
