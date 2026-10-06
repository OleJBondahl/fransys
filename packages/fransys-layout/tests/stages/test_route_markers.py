"""`route`'s marker-lane exemption (route.md 6.5, links.md 6.6, open-questions.md 13.18; decision
layout-0038).

A link marker's box is registered under its own port's owning function, so the same
`own`/`lane` mechanism that frees an endpoint symbol's own keep-out box along its port's
outward lane also frees a marker's box, and only along that one port's own lane.

PART A3's two tests exercise `route._own_ends`, `route.py`'s private per-edge lookup of the
edge's own ends, and `Space.obstacles`, the same pattern `test_route.py` already uses for
`_routing.shortest_path`; each
still resolves its box's owner through the real `_owner_of`, so a break in `_marker_owner`'s
mapping fails them too, but `Space.obstacles`'s lane arithmetic (pre-existing WP13 code) is what
they are really pinned on. The end-to-end registration path -- `route(markers=...)` actually
freeing a port's own stub -- is proven by PART A4's four tests and the `LayoutError` test
below, both through the public `route()`. All data is invented.
"""

import dataclasses

import pytest
from routing import route
from samples import PROFILE, SHEET, connection, drawn, hid, through_geometry

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Orientation,
    Point,
    PortGeometry,
    SymbolGeometry,
    ThroughPath,
    contains,
)
from fransys_layout.stages import (
    Connection,
    DrawnFunction,
    DrawnPort,
    LinkMarker,
    MarkerSide,
    PlacedFunction,
    PortRef,
    Role,
)
from fransys_layout.stages.lookups import drawn_of as _drawn_of
from fransys_layout.stages.lookups import owner_of as _owner_of
from fransys_layout.stages.lookups import placed_of as _placed_of
from fransys_layout.stages.route import (
    _edges,
    _marker_owner,
    _own_ends,
    _Page,
)
from fransys_layout.stages.space import Shape, Space


def _sideways(one):
    """`one` drawn with `in` on its W side and `out` on its E side, on the wiring grid."""
    geometry = dataclasses.replace(
        through_geometry(),
        ports=(
            PortGeometry(name="in", at=Point(x=-16, y=0), facing=Facing.W),
            PortGeometry(name="out", at=Point(x=16, y=0), facing=Facing.E),
        ),
    )
    return dataclasses.replace(one, geometry=geometry)


def _stub_box(at: Point, facing: Facing, *, width: int = 40, height: int = 8) -> Box:
    """The marker box one wiring-grid step out along `facing`, as `links.marker_box` builds it."""
    match facing:
        case Facing.E:
            return Box(x=at.x + WIRING_GRID, y=at.y - height // 2, width=width, height=height)
        case Facing.W:
            return Box(
                x=at.x - WIRING_GRID - width, y=at.y - height // 2, width=width, height=height
            )
        case Facing.N:
            return Box(
                x=at.x - width // 2, y=at.y - WIRING_GRID - height, width=width, height=height
            )
        case Facing.S:
            return Box(x=at.x - width // 2, y=at.y + WIRING_GRID, width=width, height=height)


def _old_box(at: Point, facing: Facing, *, width: int = 40, height: int = 8) -> Box:
    """The pre-layout-0038 marker box, anchored at the port: the four-facing can-fail twin."""
    match facing:
        case Facing.E:
            return Box(x=at.x, y=at.y - height // 2, width=width, height=height)
        case Facing.W:
            return Box(x=at.x - width, y=at.y - height // 2, width=width, height=height)
        case Facing.N:
            return Box(x=at.x - width // 2, y=at.y - height, width=width, height=height)
        case Facing.S:
            return Box(x=at.x - width // 2, y=at.y, width=width, height=height)


def _marker(port, at: Point, facing: Facing) -> LinkMarker:
    return LinkMarker(
        connection=hid("conductor", 99),
        port=port,
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=at,
        box=_stub_box(at, facing),
        partner_page=1,
    )


# --- PART A3: the two mandatory can-fail proofs -----------------------------------------


def _dual_port_geometry() -> SymbolGeometry:
    """Function F: port `p` faces W (its lane is the horizontal line y = p.at.y); `q` faces S."""
    return SymbolGeometry(
        key="dual-port",
        poles=1,
        orientation=Orientation.R0,
        body=Box(x=-8, y=-8, width=16, height=16),
        keepout=Box(x=-8, y=-8, width=16, height=16),
        through=ThroughPath(start="p", end="q"),
        ports=(
            PortGeometry(name="p", at=Point(x=-16, y=0), facing=Facing.W),
            PortGeometry(name="q", at=Point(x=0, y=16), facing=Facing.S),
        ),
        slots=(),
    )


def _dual_port_obstacle(marker_port: int, marker_box: Box):
    """The marker box's one `Obstacle` for the F.p to G wire, the marker at F's `marker_port`."""
    f_placed = PlacedFunction(
        function=hid("function", 1),
        drawing_set=1,
        page=1,
        column=("invented", "a"),
        at=Point(x=200, y=200),
        geometry=_dual_port_geometry(),
    )
    g_placed = PlacedFunction(
        function=hid("function", 2),
        drawing_set=1,
        page=1,
        column=("invented", "b"),
        at=Point(x=104, y=304),
        geometry=through_geometry(),
    )
    f_drawn = DrawnFunction(
        function=hid("function", 1),
        item=hid("item", 1),
        key=("invented", "f"),
        kind="contact_no",
        geometry=_dual_port_geometry(),
        ports=(
            DrawnPort(port=hid("port", 11), symbol_port="p"),
            DrawnPort(port=hid("port", 12), symbol_port="q"),
        ),
        primary_in="p",
        primary_out="q",
    )
    g_drawn = drawn(2)
    conn = Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", 1), port=hid("port", 11)),
        b=PortRef(function=hid("function", 2), port=hid("port", 21)),
    )
    marker = dataclasses.replace(
        _marker(hid("port", marker_port), Point(x=200, y=216), Facing.S), box=marker_box
    )
    placed_of = _placed_of((f_placed, g_placed), "route")
    drawn_of = _drawn_of((f_drawn, g_drawn), "route")
    owner_of = _owner_of((f_drawn, g_drawn))
    edges, ends = _edges((conn,), (), placed_of, drawn_of)
    (edge,) = edges
    page = _Page(
        ends=ends,
        space=Space(shapes=(Shape(owner=_marker_owner(marker, owner_of), box=marker.box),)),
        content=Box(x=0, y=0, width=SHEET.content_width, height=SHEET.content_height),
        profile=PROFILE,
    )
    (obstacle,) = page.space.obstacles(_own_ends(edge, ends), Box(x=0, y=0, width=400, height=400))
    return obstacle


def test_a_marker_at_one_port_does_not_excuse_a_sibling_port_at_all() -> None:
    """A marker at port `q` of function F frees no lane for the wire that leaves F's port `p`.

    F has two non-collinear ports: `p` faces W at (184, 200); `q` faces S at (200, 216). The
    marker sits at `q`, its box south of it. The routed wire ends at `p`, so it may only run
    through this box along `q`'s own stub lane (decision layout-0038), and it has none:
    the obstacle carries no lane, and every step that touches the box stays blocked. Before
    the fix the box was keyed to F, so `p`'s own outward lane was granted through `q`'s box
    (a wire from a sibling port ran through a marker; WIRE-X56).

    Can-fail twin (Edit + revert in `Space.obstacles`): grant every own end of the owner
    function a lane through the box, whatever port the marker is at. The assertion fails.
    """
    obstacle = _dual_port_obstacle(12, Box(x=160, y=224, width=80, height=8))
    assert obstacle.lanes == ()


def test_a_marker_at_a_port_frees_that_ports_own_lane_and_nothing_else() -> None:
    """The positive half: a marker at `p` frees `p`'s own outward lane through its box.

    The marker box stands one grid step west of `p` (W-facing, at (184, 200)); the wire that
    leaves `p` runs along y = 200 through it, and only there: a step on the box's top row is
    not on the lane, so it stays blocked.
    """
    box = _stub_box(Point(x=184, y=200), Facing.W)
    obstacle = _dual_port_obstacle(11, box)
    assert any(
        contains(one.extent, Box(x=box.x, y=200, width=8, height=0)) for one in obstacle.lanes
    )
    assert not any(
        contains(one.extent, Box(x=box.x, y=box.y, width=8, height=0)) for one in obstacle.lanes
    )


def test_a_marker_owned_by_another_function_still_blocks_that_functions_own_wire() -> None:
    """A marker box owned by a function that is not one of this edge's own two never excuses it.

    Function 3 owns the marker; the edge routed is function 1 to function 2 (the straight
    column x = 104). `own` only ever holds the ports of THIS edge's own two endpoints, so
    `own.get(function_3, ())` is empty and the box gets zero lanes: every step touching it
    is blocked, full stop -- the guarantee the owner's original 13.18 acceptance already
    relied on, still true after decision layout-0038.

    Can-fail twin (verified by hand, Edit + revert in `Space.obstacles`, not committed):
    unconditionally add the box itself as a permitting lane for every obstacle, regardless
    of owner. Under that twin a step straight through the box becomes exempt, which the
    second assertion below then catches.
    """
    marker = _marker(hid("port", 32), Point(x=104, y=200), Facing.S)
    marker = dataclasses.replace(marker, box=Box(x=96, y=200, width=16, height=8))
    placed_of = _placed_of((_at(1, x=104, y=96), _at(2, x=104, y=304)), "route")
    drawn_of = _drawn_of((drawn(1), drawn(2)), "route")
    owner_of = _owner_of((drawn(1), drawn(2), drawn(3)))
    edges, ends = _edges((connection(1, 1, 2),), (), placed_of, drawn_of)
    (edge,) = edges
    page = _Page(
        ends=ends,
        space=Space(shapes=(Shape(owner=_marker_owner(marker, owner_of), box=marker.box),)),
        content=Box(x=0, y=0, width=SHEET.content_width, height=SHEET.content_height),
        profile=PROFILE,
    )
    (obstacle,) = page.space.obstacles(_own_ends(edge, ends), Box(x=0, y=0, width=400, height=400))
    assert obstacle.lanes == ()
    through_step = Box(x=104, y=200, width=0, height=8)
    assert not any(contains(one.extent, through_step) for one in obstacle.lanes)


def _at(number: int, *, x: int, y: int) -> PlacedFunction:
    return PlacedFunction(
        function=hid("function", number),
        drawing_set=1,
        page=1,
        column=("invented", "a" if number == 1 else "b"),
        at=Point(x=x, y=y),
        geometry=through_geometry(),
    )


# --- PART A4: the four-facing stage tests ------------------------------------------------


@pytest.mark.parametrize("facing", [Facing.N, Facing.S, Facing.E, Facing.W])
def test_a_marker_at_a_port_still_lets_a_routed_conductor_leave_it(facing: Facing) -> None:
    """A marker at a port, on each of N, S, E and W, still lets that port's own wire leave.

    Can-fail proof: the OLD behaviour (box anchored at the port, entered as an anonymous
    `reserved` obstacle with no exemption -- pre-layout-0038) gives `ROUTE_FAILED` on every
    one of the four facings; only the new stub geometry, registered under its own port's
    function, routes.
    """
    if facing in (Facing.S, Facing.N):
        first = drawn(1)
        second = drawn(2)
        if facing is Facing.S:
            conn = connection(1, 1, 2)
            placements = (_at(1, x=104, y=96), _at(2, x=104, y=304))
            at, port = Point(x=104, y=112), hid("port", 12)
        else:
            conn = connection(2, 2, 1)
            placements = (_at(2, x=104, y=-32), _at(1, x=104, y=96))
            at, port = Point(x=104, y=80), hid("port", 11)
    else:
        first = _sideways(drawn(1))
        second = _sideways(drawn(2))
        placements = (_sideways(_at(1, x=104, y=96)), _sideways(_at(2, x=304, y=96)))
        conn = connection(1, 1, 2)
        if facing is Facing.E:
            at, port = Point(x=120, y=96), hid("port", 12)
        else:
            at, port = Point(x=288, y=96), hid("port", 21)

    marker = _marker(port, at, facing)
    routes, findings = route(
        (conn,),
        (),
        placements,
        (first, second),
        reserved=(),
        markers=(marker,),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert routes
    assert "ROUTE_FAILED" not in {f.code for f in findings}

    old_box = _old_box(at, facing)
    old_routes, old_findings = route(
        (conn,),
        (),
        placements,
        (first, second),
        reserved=(old_box,),
        markers=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert not old_routes
    assert "ROUTE_FAILED" in {f.code for f in old_findings}


# --- review 3: one box shared by the markers of several ports ---------------------------


def _pair_geometry(facing: Facing) -> SymbolGeometry:
    """F with two ports `a` and `b` on one side: both S at y=16, or both E at x=16."""
    if facing is Facing.S:
        ports = (Point(x=0, y=16), Point(x=16, y=16))
        keepout = Box(x=-8, y=-16, width=40, height=32)
    else:
        ports = (Point(x=16, y=0), Point(x=16, y=16))
        keepout = Box(x=-8, y=-16, width=24, height=48)
    return SymbolGeometry(
        key="pair",
        poles=1,
        orientation=Orientation.R0,
        body=keepout,
        keepout=keepout,
        through=None,
        ports=(
            PortGeometry(name="a", at=ports[0], facing=facing),
            PortGeometry(name="b", at=ports[1], facing=facing),
        ),
        slots=(),
    )


def _shared_box_scene(facing: Facing, index: int):
    """F at (200, 200) with one box shared by the markers of both its ports, and a wire from
    port `index` (0: `a`, 1: `b`) straight out through the box to G, which stands in line.

    Returns what `route` takes: the connection, the placements, the drawn functions and the
    two markers, whose boxes are one and the same rectangle.
    """
    geometry = _pair_geometry(facing)
    f_at = Point(x=200, y=200)
    ports = [Point(x=f_at.x + p.at.x, y=f_at.y + p.at.y) for p in geometry.ports]
    if facing is Facing.S:
        box = Box(x=192, y=224, width=40, height=8)
        g_placed = _at(2, x=ports[index].x, y=304)
        g_drawn = drawn(2)
    else:
        box = Box(x=224, y=192, width=40, height=32)
        g_placed = _sideways(_at(2, x=344, y=ports[index].y))
        g_drawn = _sideways(drawn(2))
    f_placed = PlacedFunction(
        function=hid("function", 1),
        drawing_set=1,
        page=1,
        column=("invented", "a"),
        at=f_at,
        geometry=geometry,
    )
    f_drawn = DrawnFunction(
        function=hid("function", 1),
        item=hid("item", 1),
        key=("invented", "f"),
        kind="contact_no",
        geometry=geometry,
        ports=(
            DrawnPort(port=hid("port", 11), symbol_port="a"),
            DrawnPort(port=hid("port", 12), symbol_port="b"),
        ),
        primary_in="a",
        primary_out="b",
    )
    conn = Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", 1), port=hid("port", 11 + index)),
        b=PortRef(function=hid("function", 2), port=hid("port", 21)),
    )
    markers = tuple(
        dataclasses.replace(
            _marker(hid("port", 11 + i), ports[i], facing), box=box, shared_box=True, lead=i == 0
        )
        for i in range(2)
    )
    return conn, (f_placed, g_placed), (f_drawn, g_drawn), markers


@pytest.mark.parametrize("facing", [Facing.S, Facing.E])
@pytest.mark.parametrize("index", [0, 1])
def test_a_shared_marker_box_lets_the_wire_of_any_of_its_ports_run_through_it(
    facing: Facing, index: int
) -> None:
    """One box shared by the markers of two ports (a D2 shared box, an off stub row) is
    one obstacle per marker, and every one of them frees the lane of an edge that ends on ANY
    port that owns that box: the wire out of port `a` or `b` runs straight through it, on S
    and on E.

    UNDO: in `Space.obstacles` build `lanes` from `own_ends.get(shape.owner, ())` alone (each
    entry frees only its own port's lane); the other entry of the same box then blocks the wire.
    """
    conn, placements, functions, markers = _shared_box_scene(facing, index)
    assert markers[0].box == markers[1].box
    routes, findings = route(
        (conn,),
        (),
        placements,
        functions,
        reserved=(),
        markers=markers,
        profile=PROFILE,
        sheet=SHEET,
    )
    assert "ROUTE_FAILED" not in {f.code for f in findings}
    (found,) = routes
    assert len(found.points) == 2  # the straight lane: it ran through the shared box


def test_a_shared_marker_box_owned_by_other_ports_still_blocks_every_step() -> None:
    """A box shared by markers at ports of function 3 frees no lane for an edge 1 to 2.

    UNDO: in `Space.obstacles` build every obstacle's `lanes` from all the edge's ends.
    """
    box = Box(x=96, y=200, width=32, height=8)
    markers = tuple(
        dataclasses.replace(
            _marker(hid("port", 31 + i), Point(x=104 + 8 * i, y=192), Facing.S), box=box
        )
        for i in range(2)
    )
    placed_of = _placed_of((_at(1, x=104, y=96), _at(2, x=104, y=304)), "route")
    drawn_of = _drawn_of((drawn(1), drawn(2)), "route")
    owner_of = _owner_of((drawn(1), drawn(2), drawn(3)))
    edges, ends = _edges((connection(1, 1, 2),), (), placed_of, drawn_of)
    (edge,) = edges
    page = _Page(
        ends=ends,
        space=Space(
            shapes=tuple(Shape(owner=_marker_owner(m, owner_of), box=m.box) for m in markers)
        ),
        content=Box(x=0, y=0, width=SHEET.content_width, height=SHEET.content_height),
        profile=PROFILE,
    )
    obstacles = page.space.obstacles(_own_ends(edge, ends), Box(x=0, y=0, width=400, height=400))
    assert len(obstacles) == 2
    assert all(obstacle.lanes == () for obstacle in obstacles)


def test_a_turned_marker_leaves_its_ports_wire_free_beside_it() -> None:
    """A wired reference turned E (I4): its box stands one grid off the port's wire, which
    still runs straight past it. A turned box cannot differ from a plain one for the router:
    it owns a lane only at its own port, and that lane never meets a box beside the stub.
    """
    at = Point(x=104, y=112)
    box = Box(x=112, y=116, width=40, height=8)
    marker = dataclasses.replace(
        _marker(hid("port", 12), at, Facing.S), box=box, turn=Point(x=104, y=120)
    )
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (_at(1, x=104, y=96), _at(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        reserved=(),
        markers=(marker,),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert "ROUTE_FAILED" not in {f.code for f in findings}
    (found,) = routes
    assert len(found.points) == 2


# --- coverage: a marker's port that no drawn function claims ----------------------------


def test_a_markers_port_not_among_the_drawn_functions_ports_is_a_layout_error() -> None:
    """`_marker_owner` raises when a marker's port belongs to no drawn function on the page."""
    marker = _marker(hid("port", 999), Point(x=104, y=112), Facing.S)
    with pytest.raises(LayoutError, match="not among the drawn functions"):
        route(
            (connection(1, 1, 2),),
            (),
            (_at(1, x=104, y=96), _at(2, x=104, y=304)),
            (drawn(1), drawn(2)),
            reserved=(),
            markers=(marker,),
            profile=PROFILE,
            sheet=SHEET,
        )
