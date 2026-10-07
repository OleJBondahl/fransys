"""Bound-lead visibility: a lead draws only when its port has a route, marker or marking label
on it; an unbound lead always draws (spec TL3, decision render-0002).
"""

from decimal import Decimal

from fransys_render import pages
from fransys_render._leads import _absolute, _route_ends, visible_symbol, wired_local_ports
from fransys_render._symbol_geometry import oriented_symbol, to_grid
from fransys_render._symbols import symbols_group

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    FanLeg,
    HarnessFanOut,
    Label,
    LabelKind,
    LinkMarker,
    MarkerSide,
    Orientation,
    Page,
    PageRole,
    Route,
    RoutePoint,
    SheetFormat,
    SymbolPlacement,
    layout_of,
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

_ORIGIN = Origin(file="packages/fransys-render/tests/test_leads.py", line=1, note="invented")
_TERMINAL = "terminal"


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part, *, number=1):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=number, produced_by="test"
    )


def _page(key_part, *, drawing_set, sheet_format, number=1):
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format.id,
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
    """A bare item/function/port, one pin (mirrors `test_markers.py:_pin`)."""
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


def _placement(key_part, *, function, page, x, y, symbol=_TERMINAL):  # noqa: PLR0913 -- one keyword per field
    key = ("symbol_placement", key_part)
    return SymbolPlacement(
        id=make_id(SymbolPlacement, key),
        key=key,
        function=function.id,
        page=page.id,
        x=x,
        y=y,
        orientation=Orientation.R0,
        poles=1,
        symbol=symbol,
        library_version="test",
        produced_by="test",
    )


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


def _route_ending_at(key_part, *, page, at):
    """A route between two fresh, unrelated ports, one endpoint at `at` (grid units).

    Purely geometric (spec TL3, render-0002): this package matches a route's endpoint against
    a symbol port's own position, never the route's `a`/`b` port identity, so the route's own
    ports need no relation to the placement under test.
    """
    ax, ay = at
    item1, fn1, port1 = _pin(f"{key_part}-1", "P1")
    item2, fn2, port2 = _pin(f"{key_part}-2", "P2")
    conductor = _conductor(key_part, a=port1.id, b=port2.id)
    points = (RoutePoint(index=0, x=ax, y=ay), RoutePoint(index=1, x=ax, y=ay - 8))
    route = Route(
        id=make_id(Route, ("route", key_part)),
        key=("route", key_part),
        page=page.id,
        conductor=conductor.id,
        net=None,
        a=port1.id,
        b=port2.id,
        points=points,
        produced_by="test",
    )
    return route, (item1, fn1, port1, item2, fn2, port2, conductor)


def _marker_id(key_part):
    return make_id(LinkMarker, ("link_marker", key_part))


def _marker(key_part, *, page, port, at, partner_key_part, width=13, height=8):  # noqa: PLR0913 -- one keyword per field
    x, y = at
    return LinkMarker(
        id=_marker_id(key_part),
        key=("link_marker", key_part),
        page=page.id,
        port=port.id,
        side=MarkerSide.OWNER,
        partner=_marker_id(partner_key_part),
        x=x,
        y=y,
        width=width,
        height=height,
        produced_by="test",
    )


def _label(key_part, *, page, kind, x, y, port=None, function=None, slot=""):  # noqa: PLR0913 -- one keyword per field
    key = ("label", key_part)
    return Label(
        id=make_id(Label, key),
        key=key,
        page=page.id,
        function=None if function is None else function.id,
        port=None if port is None else port.id,
        conductor=None,
        kind=kind,
        slot=slot,
        x=x,
        y=y,
        width=4,
        height=2,
        produced_by="test",
    )


def _local(local_x, local_y, *, placement):
    """A local module-unit offset (terminal's own port position) as absolute grid units."""
    return placement.x + to_grid(local_x), placement.y + to_grid(local_y)


# --- Acceptance 3: a terminal wired on N only draws one circle, one lead -----------------------


def test_acceptance_3_terminal_wired_on_n_only_draws_one_circle_one_lead():
    drawing_set = _drawing_set("acc3")
    sheet = _sheet_format("acc3")
    page = _page("acc3", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("acc3", "X1")
    placement = _placement("acc3", function=fn, page=page, x=100, y=100)
    at = _local(0, -1, placement=placement)
    route, route_records = _route_ending_at("acc3", page=page, at=at)

    model = _model(drawing_set, sheet, page, item, fn, port, placement, route, *route_records)

    group = symbols_group(model, page)
    assert group.count("<circle") == 1
    assert group.count("<line") == 1
    assert 'x1="0" y1="-0.25" x2="0" y2="-1"' in group  # the N lead, and only the N lead


def test_a_bare_terminal_draws_only_the_circle():
    drawing_set = _drawing_set("bare")
    sheet = _sheet_format("bare")
    page = _page("bare", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("bare", "X2")
    placement = _placement("bare", function=fn, page=page, x=0, y=0)
    model = _model(drawing_set, sheet, page, item, fn, port, placement)

    group = symbols_group(model, page)
    assert group.count("<circle") == 1
    assert group.count("<line") == 0


def test_two_ports_wired_draw_two_leads():
    drawing_set = _drawing_set("two")
    sheet = _sheet_format("two")
    page = _page("two", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("two", "X3")
    placement = _placement("two", function=fn, page=page, x=0, y=0)
    route_n, records_n = _route_ending_at("two-n", page=page, at=_local(0, -1, placement=placement))
    route_s, records_s = _route_ending_at("two-s", page=page, at=_local(0, 1, placement=placement))

    model = _model(
        drawing_set,
        sheet,
        page,
        item,
        fn,
        port,
        placement,
        route_n,
        *records_n,
        route_s,
        *records_s,
    )

    group = symbols_group(model, page)
    assert group.count("<circle") == 1
    assert group.count("<line") == 2


# --- A link marker sitting on the port also draws its lead --------------------------------------


def test_a_link_marker_on_the_port_draws_its_lead():
    drawing_set = _drawing_set("mk")
    sheet = _sheet_format("mk")
    page = _page("mk", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("mk", "X4")
    placement = _placement("mk", function=fn, page=page, x=0, y=0)
    at = _local(0, 1, placement=placement)  # the S port
    marker = _marker("mk", page=page, port=port, at=at, partner_key_part="mk-partner")
    # LinkMarker.partner is a required reference: a lone marker still needs a real partner
    # record on the other end (elsewhere on the page is enough for this unit test).
    other_item, other_fn, other_port = _pin("mk-other", "X4b")
    partner = _marker("mk-partner", page=page, port=other_port, at=(50, 50), partner_key_part="mk")

    model = _model(
        drawing_set,
        sheet,
        page,
        item,
        fn,
        port,
        placement,
        marker,
        other_item,
        other_fn,
        other_port,
        partner,
    )

    group = symbols_group(model, page)
    assert group.count("<line") == 1
    assert 'x1="0" y1="0.25" x2="0" y2="1"' in group  # the S lead


def test_a_fan_out_leg_ending_on_the_port_draws_its_lead():
    """HL17, layout-0158: a harness line's leg ends on its pin as a wire does, so the lead draws."""
    drawing_set = _drawing_set("fl")
    sheet = _sheet_format("fl")
    page = _page("fl", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("fl", "X6")
    placement = _placement("fl", function=fn, page=page, x=0, y=0)
    at = _local(0, 1, placement=placement)  # the S port
    other_item, other_fn, other_port = _pin("fl-other", "X6b")
    conductor = _conductor("fl", a=port.id, b=other_port.id)
    leg = FanLeg(
        index=0,
        conductor=conductor.id,
        points=(
            RoutePoint(index=0, x=at[0], y=at[1] + 32),
            RoutePoint(index=1, x=at[0], y=at[1] + 8),
            RoutePoint(index=2, x=at[0], y=at[1]),
        ),
    )
    key = ("harness_fan_out", "fl")
    fan = HarnessFanOut(
        id=make_id(HarnessFanOut, key),
        key=key,
        page=page.id,
        harness=item.id,
        branch=1,
        x=at[0],
        y=at[1] + 32,
        legs=(leg,),
        produced_by="test",
    )
    records = (drawing_set, sheet, page, item, fn, port, placement, other_item, other_fn)
    model = _model(*records, other_port, conductor, fan)

    group = symbols_group(model, page)
    assert group.count("<line") == 1
    assert 'x1="0" y1="0.25" x2="0" y2="1"' in group  # the S lead


# --- A marking label naming the port also draws its lead (unit-tested: terminal has no marking
# slots of its own, spec TL2, so this exercises the mechanism directly against a hand-built model)


def test_a_marking_label_on_the_port_is_counted_as_wired():
    drawing_set = _drawing_set("lb")
    sheet = _sheet_format("lb")
    page = _page("lb", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("lb", "X5")
    placement = _placement("lb", function=fn, page=page, x=0, y=0)
    label = _label("lb", page=page, kind=LabelKind.MARKING, x=5, y=5, port=port, slot="marking.e")
    model = _model(drawing_set, sheet, page, item, fn, port, placement, label)

    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    wired = wired_local_ports(model, page, placement, symbol)
    assert wired == frozenset({"e"})


def test_a_marking_label_for_a_different_placement_does_not_count():
    drawing_set = _drawing_set("lb2")
    sheet = _sheet_format("lb2")
    page = _page("lb2", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("lb2", "X6")
    other_item, other_fn, other_port = _pin("lb2-other", "X7")
    placement = _placement("lb2", function=fn, page=page, x=0, y=0)
    # The label's subject port belongs to a different function -- same slot name, wrong owner.
    label = _label(
        "lb2", page=page, kind=LabelKind.MARKING, x=5, y=5, port=other_port, slot="marking.e"
    )
    model = _model(
        drawing_set, sheet, page, item, fn, port, other_item, other_fn, other_port, placement, label
    )

    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    assert wired_local_ports(model, page, placement, symbol) == frozenset()


def test_a_tag_label_does_not_count_as_a_marking():
    drawing_set = _drawing_set("lb3")
    sheet = _sheet_format("lb3")
    page = _page("lb3", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("lb3", "X8")
    placement = _placement("lb3", function=fn, page=page, x=0, y=0)
    label = _label("lb3", page=page, kind=LabelKind.TAG, x=5, y=5, function=fn, slot="tag")
    model = _model(drawing_set, sheet, page, item, fn, port, placement, label)

    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    assert wired_local_ports(model, page, placement, symbol) == frozenset()


# --- Routes and markers on another page, or another port, do not wire this one ------------------


def test_a_route_on_a_different_page_does_not_count():
    drawing_set = _drawing_set("op")
    sheet = _sheet_format("op")
    page = _page("op", drawing_set=drawing_set, sheet_format=sheet)
    other_page = _page("op2", drawing_set=drawing_set, sheet_format=sheet, number=2)
    item, fn, port = _pin("op", "X9")
    placement = _placement("op", function=fn, page=page, x=0, y=0)
    route, records = _route_ending_at("op", page=other_page, at=_local(0, -1, placement=placement))
    model = _model(drawing_set, sheet, page, other_page, item, fn, port, placement, route, *records)

    group = symbols_group(model, page)
    assert group.count("<line") == 0


def test_a_route_that_does_not_reach_a_port_does_not_count():
    drawing_set = _drawing_set("miss")
    sheet = _sheet_format("miss")
    page = _page("miss", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("miss", "X10")
    placement = _placement("miss", function=fn, page=page, x=0, y=0)
    off_by_one = _local(0, -1, placement=placement)
    route, records = _route_ending_at("miss", page=page, at=(off_by_one[0] + 1, off_by_one[1]))
    model = _model(drawing_set, sheet, page, item, fn, port, placement, route, *records)

    group = symbols_group(model, page)
    assert group.count("<line") == 0


# --- `visible_symbol` keeps every non-lead element and every unbound element unconditionally ----


def test_visible_symbol_keeps_the_unbound_circle_and_every_unwired_lead_out():
    drawing_set = _drawing_set("vs")
    sheet = _sheet_format("vs")
    page = _page("vs", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("vs", "X11")
    placement = _placement("vs", function=fn, page=page, x=0, y=0)
    model = _model(drawing_set, sheet, page, item, fn, port, placement)

    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    result = visible_symbol(model, page, placement, symbol)
    kinds = [type(e).__name__ for e in result.elements]
    assert kinds == ["Circle"]


# --- Both goldens draw without a bound-lead crash (terminals wired on n/s, so e/w drop) ----------


def test_both_goldens_still_render_with_leads_wired(cabinet_laid_out, cabinet_narrow_laid_out):
    for model in (cabinet_laid_out, cabinet_narrow_laid_out):
        svgs = pages(model)
        assert len(svgs) > 0


# --- `_absolute` adds the local offset to the placement's own position, on both axes ------------


def test_absolute_adds_the_x_offset_it_does_not_subtract_it():
    placement = SymbolPlacement(
        id=make_id(SymbolPlacement, ("symbol_placement", "abs")),
        key=("symbol_placement", "abs"),
        function=make_id(Function, ("function", "abs")),
        page=make_id(Page, ("page", "abs")),
        x=10,
        y=20,
        orientation=Orientation.R0,
        poles=1,
        symbol=_TERMINAL,
        library_version="test",
        produced_by="test",
    )

    result = _absolute(placement, local_x=3.0, local_y=5.0)

    expected_x = placement.x + to_grid(3.0)
    assert result[0] == expected_x
    assert result[0] != placement.x - to_grid(3.0)


# --- `_route_ends` reports each route's first and last point, never a middle one ----------------


def test_route_ends_is_the_first_and_last_point_of_a_three_point_route():
    drawing_set = _drawing_set("rend")
    sheet = _sheet_format("rend")
    page = _page("rend", drawing_set=drawing_set, sheet_format=sheet)
    item1, fn1, port1 = _pin("rend-1", "P1")
    item2, fn2, port2 = _pin("rend-2", "P2")
    conductor = _conductor("rend", a=port1.id, b=port2.id)
    points = (
        RoutePoint(index=0, x=1, y=2),
        RoutePoint(index=1, x=3, y=4),
        RoutePoint(index=2, x=5, y=6),
    )
    route = Route(
        id=make_id(Route, ("route", "rend")),
        key=("route", "rend"),
        page=page.id,
        conductor=conductor.id,
        net=None,
        a=port1.id,
        b=port2.id,
        points=points,
        produced_by="test",
    )
    model = _model(drawing_set, sheet, page, item1, fn1, port1, item2, fn2, port2, conductor, route)

    # freeze() stores a/b in id order and reverses `points` to match (Route's own docstring),
    # so the frozen route -- not the pre-freeze construction above -- is the source of truth
    # for which point is first and which is last.
    frozen_route = next(iter(layout_of(model, Route).values()))
    assert len(frozen_route.points) == 3
    first, middle, last = frozen_route.points
    assert first.x != last.x  # otherwise a swapped first/last would go undetected below

    assert _route_ends(model, page) == frozenset({(first.x, first.y), (last.x, last.y)})
    assert (middle.x, middle.y) not in _route_ends(model, page)
