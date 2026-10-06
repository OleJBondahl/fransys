"""WP8 acceptance skeletons and unit tests: `stages.route` (ROADMAP WP8, design/route.md 6.5)."""

import dataclasses
import importlib
from itertools import pairwise

import pytest
from routing import route
from samples import PROFILE, SHEET, connection, drawn, hid, placed, through_geometry

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Point,
    PortGeometry,
)
from fransys_layout.stages import Connection, DrawnPort, NetGroup, PortRef, Role
from fransys_layout.stages._routing import shortest_path
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


def test_two_stacked_ports_get_one_straight_wire() -> None:
    """`out` of function 1 at (104, 112) to `in` of function 2 at (104, 184): two points."""
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=200)),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    (wire,) = routes
    assert _points(wire) == [Point(x=104, y=112), Point(x=104, y=184)]
    assert (wire.a, wire.b) == (hid("port", 12), hid("port", 21))
    assert findings == ()


def test_a_route_between_columns_is_orthogonal_on_the_wiring_grid() -> None:
    """Every vertex is on the wiring grid and every segment is horizontal or vertical."""
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
    assert _is_orthogonal(points)
    assert all(p.x % WIRING_GRID == 0 and p.y % WIRING_GRID == 0 for p in points)


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


def test_a_route_goes_around_an_unrelated_symbol_and_a_reserved_label() -> None:
    """Function 3 sits between the endpoints; the wire may not cross its keep-out box."""
    obstacle = placed(3, x=104, y=200)
    label = Box(x=160, y=180, width=40, height=8)
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), obstacle, placed(2, x=104, y=304)),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(label,),
        profile=PROFILE,
        sheet=SHEET,
    )
    points = _points(routes[0])
    assert len(points) > 2
    assert not any(96 < p.x < 152 and 184 < p.y < 216 for p in points)


def test_same_net_branches_may_share_cells_other_nets_pay_for_crossing() -> None:
    """Two connections of one physical net share a trunk from the common port.

    The two loads sit apart (decision 0013): with both on one x the second branch would
    have to leave the trunk one step early to arrive along its port's facing, so no
    router could give the two routes an equal second vertex.
    """
    first = connection(1, 1, 2)
    second = dataclasses.replace(connection(2, 1, 3), physical_net=first.physical_net)
    routes, _ = route(
        (first, second),
        (),
        (
            placed(1, x=104, y=96),
            placed(2, x=304, y=304, name="b"),
            placed(3, x=504, y=304, name="c"),
        ),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0])[0] == _points(routes[1])[0]
    assert _points(routes[0])[1] == _points(routes[1])[1]
    assert len(_cells(routes[0]) & _cells(routes[1])) > 1


def test_two_nets_cross_at_a_penalty_and_do_not_run_along_each_other() -> None:
    """The second net crosses the first once instead of running beside it."""
    routes, findings = route(
        (connection(1, 1, 2), connection(2, 3, 4)),
        (),
        (
            placed(1, x=104, y=96),
            placed(2, x=104, y=304),
            placed(3, x=304, y=96, name="b"),
            placed(4, x=8, y=304, name="c"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert findings == ()
    assert routes[0].physical_net != routes[1].physical_net
    assert len(_cells(routes[0]) & _cells(routes[1])) == 1


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


def test_a_connection_with_an_end_on_another_page_is_left_to_links() -> None:
    """`route` draws only connections whose two ends are placed on this page."""
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96),),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert routes == ()
    assert findings == ()


def test_routing_is_independent_of_input_order() -> None:
    """Connections are routed in handle order, whatever order they arrive in."""
    connections = (connection(1, 1, 2), connection(2, 3, 4))
    functions = (
        placed(1, x=104, y=96),
        placed(2, x=304, y=304, name="b"),
        placed(3, x=304, y=96, name="b"),
        placed(4, x=104, y=304),
    )
    drawn_functions = tuple(drawn(n) for n in (1, 2, 3, 4))
    forward, _ = route(
        connections, (), functions, drawn_functions, reserved=(), profile=PROFILE, sheet=SHEET
    )
    backward, _ = route(
        connections[::-1],
        (),
        functions[::-1],
        drawn_functions[::-1],
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert forward == backward


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


def test_spanning_tree_ties_break_by_port_handle_order() -> None:
    """All three port pairs are 192 G apart: the edges with the lower `(a, b)` handles win."""
    routes, _ = route(
        (),
        (_net_group(7, ((1, 12), (2, 22), (3, 32))),),
        (
            placed(1, x=104, y=96),
            placed(2, x=296, y=96, name="b"),
            placed(3, x=200, y=192, name="c"),
        ),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [(r.a, r.b) for r in routes] == [
        (hid("port", 12), hid("port", 22)),
        (hid("port", 12), hid("port", 32)),
    ]


def test_a_wall_with_a_gap_outside_the_first_box_needs_the_one_widening() -> None:
    """The wall spans the padded box; the retry searches the whole content box and gets by."""
    wall = (Box(x=-64, y=196, width=336, height=8),)
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        reserved=wall,
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(routes) == 1
    assert findings == ()


@pytest.mark.parametrize(
    ("second_at", "searches"),
    [(Point(x=1216, y=840), 1), (Point(x=64, y=240), 2)],
    ids=["padded box already covers the content box", "widening adds room"],
)
def test_a_failed_edge_is_searched_again_only_when_the_widening_adds_room(
    monkeypatch, second_at: Point, searches: int
) -> None:
    """A walled-in edge is searched again only when the widening adds room.

    The ports' padded box equals the content box when they sit at its opposite corners, so
    the widened search would repeat the first one and is skipped.
    """
    module = importlib.import_module("fransys_layout.stages.route")
    calls = []

    def counted(*args):
        calls.append(args)
        return shortest_path(*args)

    monkeypatch.setattr(module, "shortest_path", counted)
    wall = (
        Box(x=16, y=65, width=96, height=8),
        Box(x=16, y=48, width=40, height=25),
        Box(x=72, y=48, width=40, height=25),
    )
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=64, y=48), placed(2, x=second_at.x, y=second_at.y)),
        (drawn(1), drawn(2)),
        reserved=wall,
        profile=PROFILE,
        sheet=SHEET,
    )
    assert routes == ()
    assert [f.code for f in findings] == [ROUTE_FAILED]
    assert len(calls) == searches


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


def test_a_wall_with_a_gap_under_the_port_routes_and_reports_nothing() -> None:
    """The twin of the enclosed port: the same three boxes, the one below the port shortened."""
    routes, findings = _stacked(
        wall=(
            Box(x=56, y=113, width=40, height=8),
            Box(x=56, y=96, width=40, height=25),
            Box(x=112, y=96, width=40, height=25),
        )
    )
    assert _points(routes[0]) == [Point(x=104, y=112), Point(x=104, y=288)]
    assert findings == ()


def test_two_ports_on_one_cell_give_a_two_point_route() -> None:
    """A junction symbol can put both ends on one cell; then there is no step to take."""
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=128)),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [Point(x=104, y=112), Point(x=104, y=112)]
    assert findings == ()


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


def test_an_east_port_inside_its_own_keep_out_box_still_leaves_along_its_lane() -> None:
    """The library keeps the lane free, so the endpoint symbol's own box never blocks it."""
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (_sideways(1, x=104, y=112), _sideways(2, x=304, y=112)),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [Point(x=112, y=112), Point(x=296, y=112)]
    assert findings == ()


def test_a_third_symbols_keep_out_box_blocks_that_same_lane() -> None:
    """The twin: an unrelated symbol on the line is an obstacle, edges included."""
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        (_sideways(1, x=104, y=112), _sideways(2, x=304, y=112), _sideways(3, x=208, y=112)),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(_points(routes[0])) > 2
    assert not any(200 < p.x < 256 and 104 < p.y < 120 for p in _points(routes[0]))


def test_a_net_group_with_one_port_on_the_page_draws_nothing() -> None:
    """A tree over one port has no edges, and a port on another page is not one of its ports."""
    routes, findings = route(
        (),
        (_net_group(7, ((1, 12), (2, 22))),),
        (placed(1, x=104, y=96),),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert routes == ()
    assert findings == ()


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


def test_routes_come_out_in_connection_then_port_handle_order() -> None:
    """Conductors sort before net groups, because a handle orders by `(kind, value)` first."""
    routes, _ = route(
        (connection(1, 1, 2),),
        (_net_group(7, ((3, 32), (4, 42))),),
        (
            placed(1, x=104, y=96),
            placed(2, x=104, y=304),
            placed(3, x=304, y=96, name="b"),
            placed(4, x=504, y=96, name="c"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [r.connection for r in routes] == [hid("conductor", 1), hid("net", 7)]


def test_the_result_is_equal_under_every_input_shuffle() -> None:
    """Connections, net groups, placed and drawn functions and obstacles all permute freely."""
    connections = (connection(1, 1, 2), connection(2, 3, 4))
    groups = (_net_group(7, ((1, 11), (3, 31))), _net_group(8, ((2, 22), (4, 42))))
    functions = (
        placed(1, x=104, y=96),
        placed(2, x=304, y=304, name="b"),
        placed(3, x=504, y=96, name="c"),
        placed(4, x=704, y=304, name="d"),
    )
    drawings = tuple(drawn(n) for n in (1, 2, 3, 4))
    walls = (Box(x=400, y=400, width=40, height=8), Box(x=600, y=200, width=40, height=8))
    forward = route(
        connections, groups, functions, drawings, reserved=walls, profile=PROFILE, sheet=SHEET
    )
    backward = route(
        connections[::-1],
        groups[::-1],
        functions[::-1],
        drawings[::-1],
        reserved=walls[::-1],
        profile=PROFILE,
        sheet=SHEET,
    )
    assert forward == backward
    assert forward[0] != ()


def test_one_function_placed_twice_on_the_page_raises() -> None:
    """Two placements of one function are an engine-assembly fault, not an authored one."""
    with pytest.raises(LayoutError):
        route(
            (connection(1, 1, 2),),
            (),
            (placed(1, x=104, y=96), placed(1, x=304, y=96, name="b"), placed(2, x=104, y=304)),
            (drawn(1), drawn(2)),
            reserved=(),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_one_placement_of_each_function_does_not_raise() -> None:
    """The twin: the same page without the second placement of function 1."""
    routes, _ = _stacked()
    assert len(routes) == 1


def test_one_function_drawn_twice_raises() -> None:
    """Two `DrawnFunction`s for one function would let the last win: an assembly fault."""
    with pytest.raises(LayoutError, match="drawn twice"):
        route(
            (connection(1, 1, 2),),
            (),
            (placed(1, x=104, y=96), placed(2, x=104, y=304)),
            (drawn(1), drawn(2), drawn(1)),
            reserved=(),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_one_drawn_function_of_each_does_not_raise() -> None:
    """The twin: the same page without the second `DrawnFunction` of function 1."""
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=304)),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(routes) == 1


def test_placed_functions_from_two_pages_raise() -> None:
    """`route` runs per page and takes the page from the functions it is given."""
    with pytest.raises(LayoutError):
        _stacked(page=2)


def test_placed_functions_from_one_page_give_that_page() -> None:
    """The twin: both on page 1, and the route carries that drawing set and page."""
    routes, _ = _stacked()
    assert (routes[0].drawing_set, routes[0].page) == (1, 1)


def test_a_connected_function_that_is_not_drawn_raises() -> None:
    """A placed function with no drawn function cannot be looked up: an assembly fault."""
    with pytest.raises(LayoutError):
        route(
            (connection(1, 1, 2),),
            (),
            (placed(1, x=104, y=96), placed(2, x=104, y=304)),
            (drawn(1),),
            reserved=(),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_a_port_that_is_not_one_of_its_functions_drawn_ports_raises() -> None:
    """The connection names port 21, which this drawn function does not carry."""
    stranger = dataclasses.replace(
        drawn(2), ports=(DrawnPort(port=hid("port", 99), symbol_port="in"),)
    )
    with pytest.raises(LayoutError, match="drawn ports"):
        route(
            (connection(1, 1, 2),),
            (),
            (placed(1, x=104, y=96), placed(2, x=104, y=304)),
            (drawn(1), stranger),
            reserved=(),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_a_symbol_port_that_the_placed_symbol_lacks_raises() -> None:
    """The twin of the port lookup: the port is drawn, at a symbol port that does not exist."""
    stranger = dataclasses.replace(
        drawn(2), ports=(DrawnPort(port=hid("port", 21), symbol_port="middle"),)
    )
    with pytest.raises(LayoutError, match="port of the symbol"):
        route(
            (connection(1, 1, 2),),
            (),
            (placed(1, x=104, y=96), placed(2, x=104, y=304)),
            (drawn(1), stranger),
            reserved=(),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_a_placed_port_off_the_wiring_grid_raises() -> None:
    """An off-grid end would put the whole polyline off the grid (decision 0012's rule)."""
    with pytest.raises(LayoutError):
        _stacked(x=105)


def test_a_placed_port_on_the_wiring_grid_does_not_raise() -> None:
    """The twin: one grid unit further right, and the wire is drawn."""
    routes, _ = _stacked(x=112)
    assert _points(routes[0])[-1] == Point(x=112, y=288)


def test_an_empty_page_draws_nothing() -> None:
    """No placed function is no page: there is nothing to route and nothing to report."""
    assert route(
        (connection(1, 1, 2),),
        (),
        (),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    ) == ((), ())


def test_a_route_carries_the_page_its_functions_are_placed_on() -> None:
    """Drawing set and page come from `placed`, because `route` is given no page plan."""
    functions = tuple(
        dataclasses.replace(placed(number, x=x, y=y, page=4), drawing_set=3)
        for number, x, y in ((1, 104, 96), (2, 104, 304))
    )
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        functions,
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert (routes[0].drawing_set, routes[0].page) == (3, 4)
    assert routes[0].physical_net == hid("net", 1)


def test_net_group_edges_come_out_in_port_order_not_in_tree_order() -> None:
    """The tree finds the short edges first; the result is ordered by `(connection, a, b)`."""
    routes, _ = route(
        (),
        (_net_group(7, ((1, 12), (2, 22), (3, 32), (4, 42))),),
        (
            placed(1, x=104, y=96),
            placed(2, x=704, y=96, name="b"),
            placed(3, x=808, y=96, name="c"),
            placed(4, x=304, y=96, name="d"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [(r.a, r.b) for r in routes] == [
        (hid("port", 12), hid("port", 42)),
        (hid("port", 22), hid("port", 32)),
        (hid("port", 22), hid("port", 42)),
    ]


def test_a_second_branch_of_one_net_follows_the_trunk_the_first_laid() -> None:
    """Cells of the same net cost nothing, so the branch jogs east rather than drop alone."""
    routes, _ = route(
        (),
        (_net_group(7, ((1, 12), (2, 22), (3, 32))),),
        (
            placed(1, x=104, y=96),
            placed(2, x=296, y=96, name="b"),
            placed(3, x=200, y=192, name="c"),
        ),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [
        Point(x=104, y=112),
        Point(x=104, y=120),
        Point(x=296, y=120),
        Point(x=296, y=112),
    ]
    # The branch to port 32 rides the first edge's free trunk to x = 184 before it drops.
    assert _points(routes[1]) == [
        Point(x=104, y=112),
        Point(x=104, y=120),
        Point(x=184, y=120),
        Point(x=184, y=216),
        Point(x=200, y=216),
        Point(x=200, y=208),
    ]


def test_another_net_steps_aside_instead_of_running_along_a_drawn_route() -> None:
    """Every cell of another net costs the crossing penalty, so a shared lane is expensive."""
    second = dataclasses.replace(connection(2, 3, 4), physical_net=hid("net", 9))
    routes, _ = route(
        (connection(1, 1, 2), second),
        (),
        (
            placed(1, x=104, y=96),
            placed(2, x=304, y=304, name="b"),
            placed(3, x=208, y=96, name="c"),
            placed(4, x=408, y=304, name="d"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    # Turning where the first route runs would share thirteen cells with it; it turns higher.
    assert _points(routes[0])[1] == Point(x=104, y=280)
    assert _points(routes[1])[1] == Point(x=208, y=272)
    assert _cells(routes[0]) & _cells(routes[1]) == set()


def test_another_nets_cells_are_never_free_even_when_crossing_is_cheap() -> None:
    """A cheap crossing is still a crossing: only this net's own cells cost nothing."""
    cheap = dataclasses.replace(PROFILE, route_crossing_penalty=2)
    second = dataclasses.replace(connection(2, 3, 4), physical_net=hid("net", 9))
    routes, _ = route(
        (connection(1, 1, 2), second),
        (),
        (
            placed(1, x=104, y=96),
            placed(2, x=304, y=304, name="b"),
            placed(3, x=208, y=96, name="c"),
            placed(4, x=408, y=304, name="d"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(),
        profile=cheap,
        sheet=SHEET,
    )
    assert _cells(routes[0]) & _cells(routes[1]) == set()


def test_the_first_search_stays_in_the_padded_box_although_a_free_trunk_lies_outside() -> None:
    """The second branch pays for its own detour: its own net's trunk is out of bounds."""
    second = dataclasses.replace(connection(2, 3, 4), physical_net=hid("net", 1))
    routes, findings = route(
        (connection(1, 1, 2), second),
        (),
        (
            placed(1, x=104, y=96),
            placed(2, x=104, y=832),
            placed(3, x=200, y=96, name="b"),
            placed(4, x=200, y=816, name="b"),
        ),
        (drawn(1), drawn(2), drawn(3), drawn(4)),
        reserved=(Box(x=160, y=396, width=80, height=8),),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [Point(x=104, y=112), Point(x=104, y=816)]
    # Riding that free trunk would be far cheaper, and it is 32 G outside the padded box.
    assert len(_points(routes[1])) > 2
    assert all(136 <= point.x <= 264 for point in _points(routes[1]))
    assert findings == ()


def test_a_route_between_two_columns_turns_exactly_twice() -> None:
    """A turn costs, so the wire drops, crosses and drops again; nothing staircases."""
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(2, x=304, y=304, name="b")),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [
        Point(x=104, y=112),
        Point(x=104, y=280),
        Point(x=304, y=280),
        Point(x=304, y=288),
    ]


def test_a_wire_keeps_one_step_clear_of_a_keep_out_edge() -> None:
    """The obstacle test is closed: the detour runs at x = 88, not along the box at x = 96."""
    routes, _ = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), placed(3, x=104, y=200), placed(2, x=104, y=304)),
        (drawn(1), drawn(2), drawn(3)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [
        Point(x=104, y=112),
        Point(x=104, y=176),
        Point(x=88, y=176),
        Point(x=88, y=280),
        Point(x=104, y=280),
        Point(x=104, y=288),
    ]


def test_a_label_box_that_only_touches_the_port_cell_does_not_seal_the_port() -> None:
    """The two endpoint cells are always free; the twin box, one step lower, does seal it."""
    corner = Box(x=40, y=96, width=64, height=16)
    routes, findings = _stacked(wall=(corner,))
    assert _points(routes[0]) == [Point(x=104, y=112), Point(x=104, y=288)]
    assert findings == ()
    over, failures = _stacked(wall=(dataclasses.replace(corner, y=104),))
    assert over == ()
    assert [f.code for f in failures] == [ROUTE_FAILED]


def test_a_route_may_run_along_the_content_box_border() -> None:
    """The region border is inside the search: a wall from x = 8 leaves only x = 0."""
    routes, findings = _stacked(wall=(Box(x=8, y=196, width=1400, height=8),))
    assert Point(x=0, y=192) in _points(routes[0])
    assert findings == ()


def test_the_widened_search_still_stays_inside_the_content_box() -> None:
    """The wall reaches past the page on the left, so the way around it is to the right."""
    routes, _ = _stacked(wall=(Box(x=-64, y=196, width=336, height=8),))
    assert all(point.x >= 0 for point in _points(routes[0]))
    assert Point(x=280, y=192) in _points(routes[0])


def test_ports_below_the_content_box_still_route_after_the_widening() -> None:
    """The widening keeps the padded box, so an overfull page is not cut off from itself."""
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=896), placed(2, x=104, y=1104)),
        (drawn(1), drawn(2)),
        reserved=(Box(x=-64, y=996, width=336, height=8),),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0])[-1] == Point(x=104, y=1088)
    assert findings == ()


def test_two_ports_of_one_facing_on_one_cell_give_a_two_point_route() -> None:
    """Both ends face south, so no grid path could join them; the polyline is the point."""
    routes, findings = route(
        (
            Connection(
                handle=hid("conductor", 1),
                physical_net=hid("net", 1),
                role=Role.CONTROL,
                a=PortRef(function=hid("function", 1), port=hid("port", 12)),
                b=PortRef(function=hid("function", 2), port=hid("port", 22)),
            ),
        ),
        (),
        (placed(1, x=104, y=96), placed(2, x=104, y=96, name="b")),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [Point(x=104, y=112), Point(x=104, y=112)]
    assert findings == ()


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


def test_a_port_whose_facing_step_is_blocked_fails_although_it_could_leave_sideways() -> None:
    """The port is at a corner of its box, so west is free; the facing rule still binds."""
    routes, findings = _sideways_escape(Box(x=96, y=120, width=64, height=8))
    assert routes == ()
    assert [f.code for f in findings] == [ROUTE_FAILED]


def test_the_same_port_routes_when_its_facing_step_is_clear() -> None:
    """The twin: the lid one step lower, so the wire takes its step south and turns west."""
    routes, findings = _sideways_escape(Box(x=96, y=128, width=64, height=8))
    assert _points(routes[0])[:2] == [Point(x=104, y=112), Point(x=104, y=120)]
    assert findings == ()


def test_a_north_port_under_its_own_slot_is_still_reached_from_above() -> None:
    """The port sits inside its keep-out box, and only its own lane may pass through it."""
    tall = dataclasses.replace(through_geometry(), keepout=Box(x=-8, y=-24, width=56, height=40))
    routes, findings = route(
        (connection(1, 1, 2),),
        (),
        (placed(1, x=104, y=96), dataclasses.replace(placed(2, x=104, y=304), geometry=tall)),
        (drawn(1), drawn(2)),
        reserved=(),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert _points(routes[0]) == [Point(x=104, y=112), Point(x=104, y=288)]
    assert findings == ()
