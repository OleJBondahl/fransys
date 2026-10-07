"""Fan-out legs draw as plain wires and never make or change a junction dot (render-0010)."""

from fransys_render import pages
from fransys_render._fan_outs import fan_outs_group
from fransys_render._junctions import junction_locations
from fransys_render._numbers import format_decimal, grid_to_mm

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    FanLeg,
    HarnessFanOut,
    Page,
    PageRole,
    Route,
    RoutePoint,
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

_ORIGIN = Origin(file="packages/fransys-render/tests/test_fan_outs.py", line=1, note="invented")
_Q = (10, 10)


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _page():
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, ("drawing_set", "fo")),
        key=("drawing_set", "fo"),
        location=None,
        number=1,
        produced_by="test",
    )
    page = Page(
        id=make_id(Page, ("page", "fo")),
        key=("page", "fo"),
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="test",
    )
    return drawing_set, page


def _pin(name):
    item = Item(
        id=make_id(Item, ("item", name)),
        key=("item", name),
        part=None,
        parent=None,
        position=None,
        tag=name,
        description="Invented",
    )
    fn = Function(
        id=make_id(Function, ("function", name)),
        key=("function", name),
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port = Port(
        id=make_id(Port, ("function", name, "1")),
        key=("function", name, "1"),
        function=fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    return item, fn, port


def _conductor(name, a, b):
    return Conductor(
        id=make_id(Conductor, ("conductor", name)),
        key=("conductor", name),
        a=a.id,
        b=b.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def _route(name, page, conductor, points_xy):
    a, b = conductor.a, conductor.b
    points = tuple(RoutePoint(index=i, x=x, y=y) for i, (x, y) in enumerate(points_xy))
    return Route(
        id=make_id(Route, ("route", name)),
        key=("route", name),
        page=page.id,
        conductor=conductor.id,
        net=None,
        a=a,
        b=b,
        points=points,
        produced_by="test",
    )


def _wire(name, page, points_xy):
    """A route between two fresh ports; returns its records and both ports."""
    item1, fn1, port1 = _pin(f"{name}-1")
    item2, fn2, port2 = _pin(f"{name}-2")
    conductor = _conductor(name, port1, port2)
    route = _route(name, page, conductor, points_xy)
    return (item1, fn1, port1, item2, fn2, port2, conductor, route), port1, port2


def _fan_out(page, name, legs_xy, *, join=None):
    item = Item(
        id=make_id(Item, ("item", f"h-{name}")),
        key=("item", f"h-{name}"),
        part=None,
        parent=None,
        position=None,
        tag="W1",
        description="Invented",
    )
    extras, legs = [], []
    for i, xy in enumerate(legs_xy):
        item1, fn1, port1 = _pin(f"leg-{name}-{i}-1")
        item2, fn2, port2 = _pin(f"leg-{name}-{i}-2")
        conductor = _conductor(f"leg-{name}-{i}", join if join and i == 0 else port1, port2)
        extras += [item1, fn1, port1, item2, fn2, port2, conductor]
        points = tuple(RoutePoint(index=j, x=x, y=y) for j, (x, y) in enumerate(xy))
        legs.append(FanLeg(index=i, conductor=conductor.id, points=points))
    fan_out = HarnessFanOut(
        id=make_id(HarnessFanOut, ("fan_out", name)),
        key=("fan_out", name),
        page=page.id,
        harness=item.id,
        branch=0,
        x=_Q[0],
        y=_Q[1],
        legs=tuple(legs),
        produced_by="test",
    )
    return (item, *extras, fan_out)


def _mm(sheet, x, y):
    cx = format_decimal(grid_to_mm(sheet.content_x_mm, x, sheet.module_mm))
    cy = format_decimal(grid_to_mm(sheet.content_y_mm, y, sheet.module_mm))
    return f"{cx},{cy}"


def _elbow_and_leg():
    """A two-direction elbow through `_Q` plus a fan-out whose first leg starts at `_Q`."""
    drawing_set, page = _page()
    elbow, a, _b = _wire("elbow", page, [(0, 10), _Q, (20, 10)])
    fan = _fan_out(page, "f", [[_Q, (10, 30)], [_Q, (10, 40), (30, 40)]], join=a)
    return drawing_set, page, elbow, fan


def test_legs_draw_as_wire_polylines_without_text_or_dot():
    drawing_set, page, elbow, fan = _elbow_and_leg()
    model = _model(drawing_set, page, *elbow, *fan)
    sheet = sheet_format_of(model, page.sheet_format)
    group = fan_outs_group(model, page)
    first = f'<polyline class="wire" points="{_mm(sheet, *_Q)} {_mm(sheet, 10, 30)}"/>'
    second = (
        f'<polyline class="wire" points="{_mm(sheet, *_Q)} {_mm(sheet, 10, 40)} '
        f'{_mm(sheet, 30, 40)}"/>'
    )
    assert group == first + second
    assert first + second in next(iter(pages(model).values()))
    assert "<text" not in group
    assert "junction" not in group
    assert fan_outs_group(_model(drawing_set, page), page) == ""


def test_leg_start_on_a_two_direction_wire_makes_no_junction():
    drawing_set, page, elbow, fan = _elbow_and_leg()
    model = _model(drawing_set, page, *elbow, *fan)
    assert junction_locations(model, page) == ()
    assert 'class="junction"' not in next(iter(pages(model).values()))


def test_control_a_third_real_route_makes_the_dot():
    drawing_set, page, elbow, fan = _elbow_and_leg()
    down, down_a, _down_b = _wire("down", page, [_Q, (10, 30)])
    # A conductor with no route of its own merges the two nets.
    elbow_b = elbow[5]
    join = _conductor("join", elbow_b, down_a)
    model = _model(drawing_set, page, *elbow, *down, join, *fan)
    assert junction_locations(model, page) == (_Q,)
