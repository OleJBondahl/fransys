"""Route polylines and junction dots (spec D8, the routes/junctions part of this work package)."""

from decimal import Decimal

from fransys_render import pages
from fransys_render._numbers import format_decimal, grid_to_mm
from fransys_render._routes import _point_mm, routes_group, routes_on_page

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Page,
    PageRole,
    Route,
    RoutePoint,
    SheetFormat,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    Function,
    FunctionKind,
    Item,
    Port,
    PortRole,
)

_ORIGIN = Origin(
    file="packages/fransys-render/tests/test_routes_junctions.py",
    line=1,
    note="invented route",
)

# `pages()` returns one SVG per `layout.page`; every model here has exactly one page.
_ONE_PAGE = 1


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part, *, number=1):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=number, produced_by="test"
    )


def _page(key_part, *, drawing_set, number=1, sheet_format=None):
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None if sheet_format is None else sheet_format.id,
        groups=(),
        produced_by="test",
    )


def _sheet_format(key_part, *, width_mm=300, height_mm=200):
    key = ("sheet_format", key_part)
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=key_part,
        width_mm=width_mm,
        height_mm=height_mm,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm - 20,
        content_height_mm=height_mm - 40,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )


def _pin(key_part, designation):
    """A bare item/function/port, one pin (mirrors `fransys_pdf/tests/_build.py:pin`)."""
    item_key = ("item", key_part)
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag=designation,
        description="Invented",
    )
    function_key = ("function", key_part)
    fn = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port_key = (*function_key, "1")
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    return item, fn, port


def _conductor(key_part, *, a, b):
    key = ("conductor", key_part)
    return Conductor(
        id=make_id(Conductor, key),
        key=key,
        a=a,
        b=b,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def _route(key_part, *, page, conductor, a, b, points):  # noqa: PLR0913 -- one keyword per field
    return Route(
        id=make_id(Route, ("route", key_part)),
        key=("route", key_part),
        page=page.id,
        conductor=conductor.id,
        net=None,
        a=a,
        b=b,
        points=points,
        produced_by="test",
    )


def _route_between(key_part, *, page, points_xy):
    """A route between two fresh, otherwise-unconnected ports.

    `points_xy` is given first-port-to-second-port; `Route.__post_init__` may swap `a`/`b`
    to store them in id order, reversing `points` right along with them, so whichever port
    ends up `a` or `b` after that, its own declared location in `points_xy` is preserved
    (verified by inspection of `Route._turned_round`) -- the tests below never need to
    predict the id order themselves.
    """
    item1, fn1, port1 = _pin(f"{key_part}-1", "P1")
    item2, fn2, port2 = _pin(f"{key_part}-2", "P2")
    conductor = _conductor(key_part, a=port1.id, b=port2.id)
    points = tuple(RoutePoint(index=i, x=x, y=y) for i, (x, y) in enumerate(points_xy))
    route = _route(key_part, page=page, conductor=conductor, a=port1.id, b=port2.id, points=points)
    records = (item1, fn1, port1, item2, fn2, port2, conductor, route)
    return route, port1, port2, records


def _join(key_part, *, a, b):
    """A conductor with no route of its own, purely to merge two physical nets."""
    return _conductor(key_part, a=a, b=b)


def _one_svg(model):
    svgs = pages(model)
    assert len(svgs) == _ONE_PAGE
    return next(iter(svgs.values()))


def _circle_marker(sheet, x, y):
    cx = format_decimal(grid_to_mm(sheet.content_x_mm, x, sheet.module_mm))
    cy = format_decimal(grid_to_mm(sheet.content_y_mm, y, sheet.module_mm))
    return f'<circle class="junction" cx="{cx}" cy="{cy}"'


# --- 1. Plain routes draw the exact polyline (hand-computed from grid_to_mm) ----------------


def test_routes_draw_the_exact_polyline_string():
    drawing_set = _drawing_set("t1")
    sheet = _sheet_format("t1")
    page = _page("t1", drawing_set=drawing_set, sheet_format=sheet)

    item_x, fn_x, port_x = _pin("t1-x", "X1")
    item_y, fn_y, port_y = _pin("t1-y", "Y1")
    a_port, b_port = (port_x, port_y) if port_x.id < port_y.id else (port_y, port_x)
    conductor = _conductor("t1", a=a_port.id, b=b_port.id)
    points = (RoutePoint(index=0, x=0, y=0), RoutePoint(index=1, x=8, y=4))
    route = _route("t1", page=page, conductor=conductor, a=a_port.id, b=b_port.id, points=points)

    model = _model(
        drawing_set, sheet, page, item_x, fn_x, port_x, item_y, fn_y, port_y, conductor, route
    )

    svg = _one_svg(model)

    # grid_to_mm(10, 0, 2.5) = 10 ; grid_to_mm(10, 8, 2.5) = 10 + 8*2.5/8 = 12.5 ;
    # grid_to_mm(10, 4, 2.5) = 10 + 4*2.5/8 = 11.25
    expected = '<polyline class="wire" points="10,10 12.5,11.25"/>'
    assert expected in svg


# --- 2. Clause (i): three segment ends meet ---------------------------------------------------


def test_junction_clause_i_three_segment_ends_meet():
    q = (10, 10)
    drawing_set = _drawing_set("t2")
    page = _page("t2", drawing_set=drawing_set)

    _elbow, _elbow_a, elbow_b, elbow_records = _route_between(
        "t2-elbow", page=page, points_xy=[(0, 10), q, (20, 10)]
    )
    _ending, ending_a, _ending_b, ending_records = _route_between(
        "t2-end", page=page, points_xy=[q, (10, 30)]
    )
    join = _join("t2-join", a=elbow_b.id, b=ending_a.id)

    same_net_model = _model(drawing_set, page, *elbow_records, *ending_records, join)
    sheet = sheet_format_of(same_net_model, page.sheet_format)
    svg = _one_svg(same_net_model)
    assert _circle_marker(sheet, *q) in svg

    different_net_model = _model(drawing_set, page, *elbow_records, *ending_records)
    svg_diff = _one_svg(different_net_model)
    assert 'class="junction"' not in svg_diff


# --- 3. Clause (i): a plain elbow, alone, is not a junction -----------------------------------


def test_junction_clause_i_plain_elbow_is_not_a_junction():
    q = (10, 10)
    drawing_set = _drawing_set("t3")
    page = _page("t3", drawing_set=drawing_set)

    _elbow, _a, _b, elbow_records = _route_between(
        "t3-elbow", page=page, points_xy=[(0, 10), q, (20, 10)]
    )
    model = _model(drawing_set, page, *elbow_records)

    svg = _one_svg(model)
    assert 'class="junction"' not in svg


# --- 4. Clause (ii): a route's endpoint lies inside another route's segment -------------------


def test_junction_clause_ii_endpoint_inside_other_route_segment():
    p = (0, 10)
    drawing_set = _drawing_set("t4")
    page = _page("t4", drawing_set=drawing_set)

    _vertical, _vertical_a, vertical_b, vertical_records = _route_between(
        "t4-vertical", page=page, points_xy=[(0, 0), (0, 20)]
    )
    _ending, ending_a, _ending_b, ending_records = _route_between(
        "t4-end", page=page, points_xy=[(5, 10), p]
    )
    join = _join("t4-join", a=vertical_b.id, b=ending_a.id)

    same_net_model = _model(drawing_set, page, *vertical_records, *ending_records, join)
    sheet = sheet_format_of(same_net_model, page.sheet_format)
    svg = _one_svg(same_net_model)
    assert _circle_marker(sheet, *p) in svg

    different_net_model = _model(drawing_set, page, *vertical_records, *ending_records)
    svg_diff = _one_svg(different_net_model)
    assert 'class="junction"' not in svg_diff


# --- 5. Two routes meeting only at a port: no junction (I4 D1) ---------------------------------


def test_two_routes_meeting_only_at_a_port_are_no_junction():
    """I4 D1 (designer): a dot goes where three or more wire segments of one net meet; a
    symbol's pin is no wire segment, so two wires on one port, W and E, get no dot (the old
    clause (iii) drew one). A third wire leaving the port's point makes it a junction."""
    s = (10, 10)
    drawing_set = _drawing_set("t5")
    page = _page("t5", drawing_set=drawing_set)

    item_s, fn_s, port_s = _pin("t5-s", "S1")
    item_a, fn_a, port_a = _pin("t5-a", "A1")
    item_c, fn_c, port_c = _pin("t5-c", "C1")

    conductor1 = _conductor("t5-1", a=port_a.id, b=port_s.id)
    points1 = (RoutePoint(index=0, x=0, y=10), RoutePoint(index=1, x=s[0], y=s[1]))
    route1 = _route(
        "t5-1", page=page, conductor=conductor1, a=port_a.id, b=port_s.id, points=points1
    )

    conductor2 = _conductor("t5-2", a=port_c.id, b=port_s.id)
    points2 = (RoutePoint(index=0, x=20, y=10), RoutePoint(index=1, x=s[0], y=s[1]))
    route2 = _route(
        "t5-2", page=page, conductor=conductor2, a=port_c.id, b=port_s.id, points=points2
    )

    two_routes_model = _model(
        drawing_set,
        page,
        item_s,
        fn_s,
        port_s,
        item_a,
        fn_a,
        port_a,
        conductor1,
        route1,
        item_c,
        fn_c,
        port_c,
        conductor2,
        route2,
    )
    svg = _one_svg(two_routes_model)
    assert 'class="junction"' not in svg

    _down, down_a, _down_b, down_records = _route_between(
        "t5-down", page=page, points_xy=[s, (10, 30)]
    )
    join = _join("t5-join", a=port_s.id, b=down_a.id)
    three_model = _model(
        drawing_set,
        page,
        item_s,
        fn_s,
        port_s,
        item_a,
        fn_a,
        port_a,
        conductor1,
        route1,
        item_c,
        fn_c,
        port_c,
        conductor2,
        route2,
        *down_records,
        join,
    )
    sheet = sheet_format_of(three_model, page.sheet_format)
    assert _circle_marker(sheet, *s) in _one_svg(three_model)


def test_a_wire_joining_one_grid_out_from_a_port_gets_the_dot_at_the_t():
    """I4 D1: a side element's wire joins the coil's line one grid out from A1: the dot is
    at that T, not at the port where the line ends."""
    drawing_set = _drawing_set("t7")
    page = _page("t7", drawing_set=drawing_set)
    _line, _line_a, line_b, line_records = _route_between(
        "t7-line", page=page, points_xy=[(10, 0), (10, 20)]
    )
    _side, side_a, _side_b, side_records = _route_between(
        "t7-side", page=page, points_xy=[(30, 20), (30, 10), (10, 10)]
    )
    join = _join("t7-join", a=line_b.id, b=side_a.id)
    model = _model(drawing_set, page, *line_records, *side_records, join)
    sheet = sheet_format_of(model, page.sheet_format)
    svg = _one_svg(model)
    assert _circle_marker(sheet, 10, 10) in svg
    assert _circle_marker(sheet, 10, 20) not in svg


# --- 6. Ordering: routes by id, junctions by position (D11) ------------------------------------


def test_routes_and_junctions_are_ordered_by_id_and_position():
    drawing_set = _drawing_set("t6")
    page = _page("t6", drawing_set=drawing_set)

    _route_p, _p1, _p2, records_p = _route_between("t6-p", page=page, points_xy=[(0, 0), (10, 0)])
    _route_q, _q1, _q2, records_q = _route_between("t6-q", page=page, points_xy=[(0, 50), (10, 50)])

    _j1_elbow, _j1_a, j1_b, j1_elbow_records = _route_between(
        "t6-j1-elbow", page=page, points_xy=[(20, 20), (30, 20), (40, 20)]
    )
    _j1_end, j1_end_a, _j1_end_b, j1_end_records = _route_between(
        "t6-j1-end", page=page, points_xy=[(30, 20), (30, 40)]
    )
    j1_join = _join("t6-j1-join", a=j1_b.id, b=j1_end_a.id)

    _j2_elbow, _j2_a, j2_b, j2_elbow_records = _route_between(
        "t6-j2-elbow", page=page, points_xy=[(60, 60), (70, 60), (80, 60)]
    )
    _j2_end, j2_end_a, _j2_end_b, j2_end_records = _route_between(
        "t6-j2-end", page=page, points_xy=[(70, 60), (70, 80)]
    )
    j2_join = _join("t6-j2-join", a=j2_b.id, b=j2_end_a.id)

    model = _model(
        drawing_set,
        page,
        *records_p,
        *records_q,
        *j1_elbow_records,
        *j1_end_records,
        j1_join,
        *j2_elbow_records,
        *j2_end_records,
        j2_join,
    )

    sheet = sheet_format_of(model, page.sheet_format)
    svg = _one_svg(model)

    routes = sorted(layout_of(model, Route).values(), key=lambda route: route.id)
    expected_route_count = 6
    assert len(routes) == expected_route_count

    def _polyline_marker(route):
        pts = " ".join(
            f"{format_decimal(grid_to_mm(sheet.content_x_mm, point.x, sheet.module_mm))},"
            f"{format_decimal(grid_to_mm(sheet.content_y_mm, point.y, sheet.module_mm))}"
            for point in route.points
        )
        return f'<polyline class="wire" points="{pts}"/>'

    route_positions = [svg.index(_polyline_marker(route)) for route in routes]
    assert route_positions == sorted(route_positions)

    junction_locations = sorted([(30, 20), (70, 60)])
    expected_junction_count = 2
    assert len(junction_locations) == expected_junction_count
    junction_positions = [svg.index(_circle_marker(sheet, x, y)) for x, y in junction_locations]
    assert junction_positions == sorted(junction_positions)


# --- 7. `routes_group` joins its polylines with `""`, not any separator -----------------------


def test_routes_group_concatenates_polylines_with_no_separator():
    """Two routes on one page: the exact returned string is the two polylines, in `.id`
    order (`routes_on_page`), with nothing between them -- built from `_point_mm`, the same
    helper `routes_group` itself calls, never a hand-typed literal.
    """
    drawing_set = _drawing_set("t8")
    page = _page("t8", drawing_set=drawing_set)
    _route_p, _p1, _p2, records_p = _route_between("t8-p", page=page, points_xy=[(0, 0), (10, 0)])
    _route_q, _q1, _q2, records_q = _route_between("t8-q", page=page, points_xy=[(0, 50), (10, 50)])

    model = _model(drawing_set, page, *records_p, *records_q)
    sheet = sheet_format_of(model, page.sheet_format)

    def _polyline(route):
        points = " ".join(_point_mm(sheet, point.x, point.y) for point in route.points)
        return f'<polyline class="wire" points="{points}"/>'

    ordered = routes_on_page(model, page)
    expected_route_count = 2
    assert len(ordered) == expected_route_count
    expected = "".join(_polyline(route) for route in ordered)
    assert routes_group(model, page) == expected
