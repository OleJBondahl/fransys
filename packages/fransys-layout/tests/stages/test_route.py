"""Acceptance skeletons and unit tests: `stages.route`."""

import dataclasses
from itertools import pairwise

from routing import route
from samples import PROFILE, SHEET, connection, drawn, hid, placed, through_geometry

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Point,
    PortGeometry,
)
from fransys_layout.stages import NetGroup, PortRef, Role
from fransys_layout.stages.route import ROUTE_FAILED
from fransys_model.kernel import Severity


def _points(a_route):
    return [p.at for p in a_route.points]


def _is_orthogonal(points) -> bool:
    return all(a.x == b.x or a.y == b.y for a, b in pairwise(points))


def _cells(a_route) -> set:
    """Every wiring-grid cell the polyline covers, corners and endpoints included."""
    covered = set()
    for a, b in pairwise(_points(a_route)):
        step = WIRING_GRID if (b.x, b.y) > (a.x, a.y) else -WIRING_GRID
        if a.x == b.x:
            covered |= {(a.x, y) for y in range(a.y, b.y + step, step)}
        else:
            covered |= {(x, a.y) for x in range(a.x, b.x + step, step)}
    return covered


def test_a_route_leaves_each_port_along_its_facing() -> None:
    """The first segment continues S from `out`, the last arrives N of `in`."""
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=304, y=304, name="b")),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    points = _points(routes[0])
    assert points[1].x == points[0].x
    assert points[1].y >= points[0].y + WIRING_GRID
    assert points[-2].x == points[-1].x
    assert points[-2].y <= points[-1].y - WIRING_GRID


def test_an_enclosed_port_gives_route_failed_and_no_route() -> None:
    """A port walled in by reserved boxes cannot be reached: a finding, never a diagonal."""
    wall = (
        Box(x=56, y=113, width=96, height=8),
        Box(x=56, y=96, width=40, height=25),
        Box(x=112, y=96, width=40, height=25),
    )
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        reserved=wall,
        profile=PROFILE,
        sheet=SHEET,
    )
    assert routes == ()
    assert [f.code for f in findings] == [ROUTE_FAILED]
    assert findings[0].subjects == (hid("conductor", 1),)


def _net_group(number: int, ports: tuple[tuple[int, int], ...]) -> NetGroup:
    """Net `number` over `(function, port)` pairs, with no conductors."""
    return NetGroup(
        net=hid("net", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        ports=tuple(PortRef(function=hid("function", f), port=hid("port", p)) for f, p in ports),
    )


def test_a_net_group_is_routed_as_a_minimum_spanning_tree() -> None:
    """Three ports give two edges, the two shortest, each identified by its port pair."""
    routes, findings = route(
        (),
        (_net_group(7, ((1, 12), (2, 22), (3, 32))),),
        (
            placed(1, x=104, y=96),
            placed(2, x=304, y=96, name="b"),
            placed(3, x=1104, y=96, name="c"),
        ),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [(r.connection, r.a, r.b) for r in routes] == [
        (hid("net", 7), hid("port", 12), hid("port", 22)),
        (hid("net", 7), hid("port", 22), hid("port", 32)),
    ]
    assert findings == ()


# --- unit tests --------------------------------------------------------------------------


def _stacked(*, wall: tuple[Box, ...] = (), x: int = 104, page: int = 1):
    """Function 1 above function 2, wired by conductor 1, with `wall` in the way."""
    return route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=x, y=304, page=page)),
        (drawn(1), drawn(2)),
        reserved=wall,
        profile=PROFILE,
        sheet=SHEET,
    )


def _sideways(number: int, *, x: int, y: int):
    """Function `number` drawn as a horizontal symbol whose `out` port is inside its keep-out."""
    geometry = dataclasses.replace(
        through_geometry(),
        body=Box(x=-8, y=-8, width=16, height=16),
        keepout=Box(x=-8, y=-8, width=56, height=16),
        ports=(
            PortGeometry(name="in", at=Point(x=-8, y=0), facing=Facing.W),
            PortGeometry(name="out", at=Point(x=8, y=0), facing=Facing.E),
        ),
    )
    return dataclasses.replace(placed(number, x=x, y=y), geometry=geometry)


def test_a_failed_net_group_edge_is_named_by_its_net_and_its_two_ports() -> None:
    """A conductor names itself; a net edge names the net and the pair, so each edge is one."""
    routes, findings = route(
        (),
        (_net_group(7, ((1, 12), (2, 22))),),
        (placed(1, x=104, y=96), placed(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        reserved=(
            Box(x=56, y=113, width=96, height=8),
            Box(x=56, y=96, width=40, height=25),
            Box(x=112, y=96, width=40, height=25),
        ),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert routes == ()
    assert [(f.code, f.subjects) for f in findings] == [
        (ROUTE_FAILED, (hid("net", 7), hid("port", 12), hid("port", 22)))
    ]
    assert findings[0].severity is Severity.ERROR


def test_findings_come_out_sorted_by_code_and_subjects() -> None:
    """Two walled-in conductors arrive in the other order and are reported in handle order."""
    wall = (
        Box(x=56, y=113, width=96, height=8),
        Box(x=56, y=96, width=40, height=25),
        Box(x=112, y=96, width=40, height=25),
    )
    _, findings = route(
        (connection(2, 1, 3), connection(1, 1, 2)),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=304), placed(3, x=304, y=304, name="b")),
        (drawn(1), drawn(2), drawn(3)),
        reserved=wall,
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [f.subjects for f in findings] == [(hid("conductor", 1),), (hid("conductor", 2),)]


def _cornered(number: int, *, x: int, y: int):
    """Function `number` with its ports at the corners of its keep-out box, not mid-edge."""
    geometry = dataclasses.replace(
        through_geometry(),
        ports=(
            PortGeometry(name="in", at=Point(x=-8, y=-16), facing=Facing.N),
            PortGeometry(name="out", at=Point(x=-8, y=16), facing=Facing.S),
        ),
    )
    return dataclasses.replace(placed(number, x=x, y=y), geometry=geometry)


def _sideways_escape(lid: Box):
    """A corner port with `lid` below it; west of the port is open, so only the rule binds."""
    return route(
        (connection(1, 1, 2),),
        (),
        (_cornered(1, x=112, y=96), placed(2, x=8, y=304, name="b")),
        (drawn(1), drawn(2)),
        reserved=(lid,),
        profile=PROFILE,
        sheet=SHEET,
    )
