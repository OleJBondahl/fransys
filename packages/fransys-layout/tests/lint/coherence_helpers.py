"""Hand-made inputs shared by the coherence tests (package-layout.md 9). All data is invented.

Function `n` has ports `10n + 1` (`in`, 16 G above its origin) and `10n + 2` (`out`, 16 G
below it). `placed(1, x=104, y=96)` therefore has `in` at (104, 80) and `out` at (104, 112);
`connection(1, 1, 2)` wires port 12 to port 21.
"""

import dataclasses
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from samples import drawn, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import (
    Layout,
    LinkCase,
    LinkDecision,
    LinkMarker,
    MarkerSide,
    NetGroup,
    PortRef,
    Role,
    Route,
    RoutePoint,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Id

NO_UNITS = MappingProxyType({})  # no function belongs to a unit: `check_coherence` cuts as before
DRAWN = (drawn(1), drawn(2), drawn(3))
PLACED = (placed(1, x=104, y=96), placed(2, x=104, y=304), placed(3, x=304, y=304, name="b"))


def port(number: int):
    """The invented id of port `number`."""
    return hid("port", number)


def wire(
    number: int,
    points: tuple[tuple[int, int], ...],
    *,
    a: int = 12,
    b: int = 21,
    page: int = 1,
) -> Route:
    """A route claiming conductor `number` between ports `a` and `b`."""
    return Route(
        connection=hid("conductor", number),
        physical_net=hid("net", number),
        drawing_set=1,
        page=page,
        a=port(a),
        b=port(b),
        points=tuple(RoutePoint(index=i, at=Point(x=x, y=y)) for i, (x, y) in enumerate(points)),
    )


def edge(net: int, a: int, b: int, points: tuple[tuple[int, int], ...], *, page: int = 1) -> Route:
    """A spanning-tree edge of net group `net` between ports `a` and `b`."""
    return dataclasses.replace(
        wire(net, points, a=a, b=b, page=page),
        connection=hid("net", net),
        physical_net=hid("net", net),
    )


def layout_of(*, routes=(), decisions=(), markers=(), functions=PLACED) -> Layout:
    """A one-page-plan layout of `functions` and whatever else a test draws."""
    return Layout(
        pages=(page_plan(("a", "b")),),
        placed=functions,
        routes=routes,
        decisions=decisions,
        markers=markers,
        labels=(),
    )


def group(number: int, ports: tuple[tuple[int, int], ...]) -> NetGroup:
    """Net group `number` holding `(function, port)` pairs."""
    return NetGroup(
        net=hid("net", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        ports=tuple(PortRef(function=hid("function", f), port=port(p)) for f, p in ports),
    )


def decision(connection: Id[Any], a: int, b: int, case: LinkCase) -> LinkDecision:
    """The decision `(connection, port a, port b)` of `case`."""
    return LinkDecision(connection=connection, a=port(a), b=port(b), case=case)


def marker(
    connection: Id[Any], at_port: int, side: MarkerSide, *, page: int, at: tuple[int, int]
) -> LinkMarker:
    """A marker of `connection` at `at_port`, standing at `at` on `page` of drawing set 1."""
    return LinkMarker(
        connection=connection,
        port=port(at_port),
        side=side,
        drawing_set=1,
        page=page,
        at=Point(x=at[0], y=at[1]),
        box=Box(x=at[0], y=at[1] - 4, width=24, height=8),
        partner_page=1,
    )


def named(findings) -> list[tuple[str, tuple]]:
    """What a test compares: each finding's code and subjects."""
    return [(one.code, one.subjects) for one in findings]


def subjects(*handles) -> tuple:
    """A finding's subjects as the kernel stores them: once each, in `Id` order."""
    return tuple(sorted(set(handles)))
