"""Outlines, boxes, fan-outs and harness lines draw in their own place order, not id order.

Each case holds three records whose id order differs from their place order (checked first), so
a page that fell back to `page_slice` would list them wrong.
"""

from fransys_render._fan_outs import fan_outs_group
from fransys_render._outlines import _outline_glyph, outlines_group

from fransys_model.derive.order import drawn_lines_on_page, drawn_on_page
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    ConnectorBox,
    DrawingSet,
    FanLeg,
    HarnessFanOut,
    HarnessLine,
    Orientation,
    Outline,
    Page,
    PageRole,
    PlacementView,
    RoutePoint,
    SymbolPlacement,
    page_slice,
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
    Unit,
    UnitRelease,
    functions,
)

_ORIGIN = Origin(file="packages/fransys-render/tests/test_drawn_order_sites.py", line=1, note="x")
_DRAWING_SET = DrawingSet(
    id=make_id(DrawingSet, ("ds",)), key=("ds",), location=None, number=1, produced_by="test"
)
_PAGE = Page(
    id=make_id(Page, ("p",)),
    key=("p",),
    drawing_set=_DRAWING_SET.id,
    number=1,
    role=PageRole.CONTROL,
    sheet_format=None,
    groups=(),
    produced_by="test",
)
_RELEASE = UnitRelease(
    id=make_id(UnitRelease, ("r",)),
    key=("r",),
    name="demo",
    version=1,
    revision=1,
    interface="1",
    title="",
)
_UNIT_RECORD = Unit(id=make_id(Unit, ("u",)), key=("u",), release=_RELEASE.id, parent=None)
_UNIT = _UNIT_RECORD.id
_ITEM = Item(
    id=make_id(Item, ("h",)),
    key=("h",),
    part=None,
    parent=None,
    position=None,
    tag="H1",
    description="Invented",
)
_HARNESS = _ITEM.id
_FUNCTION = Function(
    id=make_id(Function, ("f",)),
    key=("f",),
    item=_ITEM.id,
    template=None,
    name="a",
    kind=FunctionKind.GENERIC,
)
_PORTS = tuple(
    Port(
        id=make_id(Port, ("port", n)),
        key=("port", n),
        function=_FUNCTION.id,
        template=None,
        name=n,
        role=PortRole.GENERIC,
    )
    for n in ("1", "2")
)
_CONDUCTOR = Conductor(
    id=make_id(Conductor, ("c",)),
    key=("c",),
    a=_PORTS[0].id,
    b=_PORTS[1].id,
    kind=ConductorKind.WIRE,
    carrier=None,
)
_SUPPORT = (_RELEASE, _UNIT_RECORD, _ITEM, _FUNCTION, *_PORTS, _CONDUCTOR)
_SPOTS = ((10, 4), (10, 10), (30, 10))  # place order


def _against_id_order(kind, tag):
    """Name -> spot, the last id getting the first place, so id order is the reverse of place."""
    names = sorted("abc", key=lambda n: make_id(kind, (tag, n)), reverse=True)
    return dict(zip(names, _SPOTS, strict=True))


def _model(*records):
    draft = Draft()
    draft.extend([_DRAWING_SET, _PAGE, *_SUPPORT, *records], origin=_ORIGIN)
    return freeze(draft)


def _outline(name, x, y):
    key = ("outline", name)
    return Outline(
        id=make_id(Outline, key),
        key=key,
        unit=_UNIT,
        page=_PAGE.id,
        x=x,
        y=y,
        width=5,
        height=5,
        produced_by="test",
    )


def _box(name, x, y):
    key = ("box", name)
    return ConnectorBox(
        id=make_id(ConnectorBox, key),
        key=key,
        page=_PAGE.id,
        function=_FUNCTION.id,
        x=x,
        y=y,
        width=5,
        height=5,
        texts=(),
        cells=(),
        produced_by="test",
    )


def _fan(name, x, y):
    key = ("fan", name)
    leg = FanLeg(index=0, conductor=_CONDUCTOR.id, points=(RoutePoint(index=0, x=x, y=y),))
    return HarnessFanOut(
        id=make_id(HarnessFanOut, key),
        key=key,
        page=_PAGE.id,
        harness=_HARNESS,
        branch=0,
        x=x,
        y=y,
        legs=(leg,),
        produced_by="test",
    )


def _line(name, points):
    key = ("line", name)
    return HarnessLine(
        id=make_id(HarnessLine, key),
        key=key,
        page=_PAGE.id,
        harness=_HARNESS,
        branch=0,
        points=tuple(RoutePoint(index=i, x=x, y=y) for i, (x, y) in enumerate(points)),
        text_x=0,
        text_y=0,
        produced_by="test",
    )


def _place_order_differs_from_id_order(model, record_type):
    by_id = page_slice(model, record_type, _PAGE)
    by_place = drawn_on_page(model, record_type, _PAGE)
    assert [r.key for r in by_id] != [r.key for r in by_place]
    return by_place


def test_outlines_are_drawn_top_down_then_left_to_right():
    model = _model(
        *(_outline(n, x, y) for n, (x, y) in _against_id_order(Outline, "outline").items())
    )
    drawn = _place_order_differs_from_id_order(model, Outline)
    assert [(o.x, o.y) for o in drawn] == [(10, 4), (10, 10), (30, 10)]
    sheet = sheet_format_of(model, _PAGE.sheet_format)
    assert outlines_group(model, _PAGE) == "".join(_outline_glyph(sheet, o) for o in drawn)


def test_fan_outs_are_drawn_top_down_then_left_to_right():
    model = _model(
        *(_fan(n, x, y) for n, (x, y) in _against_id_order(HarnessFanOut, "fan").items())
    )
    drawn = _place_order_differs_from_id_order(model, HarnessFanOut)
    assert [(f.x, f.y) for f in drawn] == [(10, 4), (10, 10), (30, 10)]
    assert fan_outs_group(model, _PAGE).count("<polyline") == 3


def test_harness_lines_are_drawn_by_their_wire_run():
    spots = _against_id_order(HarnessLine, "line")
    model = _model(*(_line(n, [(x, y + 5), (x, y)]) for n, (x, y) in spots.items()))
    by_id = page_slice(model, HarnessLine, _PAGE)
    drawn = drawn_lines_on_page(model, _PAGE)
    assert [r.key for r in by_id] != [r.key for r in drawn]
    assert [(line.points[-1].x, line.points[-1].y) for line in drawn] == list(_SPOTS)


def test_connector_boxes_are_drawn_top_down_then_left_to_right():
    model = _model(*(_box(n, x, y) for n, (x, y) in _against_id_order(ConnectorBox, "box").items()))
    drawn = _place_order_differs_from_id_order(model, ConnectorBox)
    assert [(b.x, b.y) for b in drawn] == [(10, 4), (10, 10), (30, 10)]


def test_symbols_on_one_spot_are_drawn_by_their_printed_designation():
    """Same place, so the designation decides: `-K2` before `-K10`, against the ids' order."""
    by_id = sorted("ab", key=lambda n: make_id(SymbolPlacement, ("sym", n)))
    tags = dict(zip(by_id, ("K10", "K2"), strict=True))
    records = []
    for name, tag in tags.items():
        item = Item(
            id=make_id(Item, ("i", name)),
            key=("i", name),
            part=None,
            parent=None,
            position=None,
            tag=tag,
            description="Invented",
        )
        function = Function(
            id=make_id(Function, ("fn", name)),
            key=("fn", name),
            item=item.id,
            template=None,
            name="a",
            kind=FunctionKind.GENERIC,
        )
        placement = SymbolPlacement(
            id=make_id(SymbolPlacement, ("sym", name)),
            key=("sym", name),
            function=function.id,
            page=_PAGE.id,
            x=0,
            y=0,
            orientation=Orientation.R0,
            poles=1,
            symbol="unused",
            library_version="irrelevant",
            produced_by="test",
            view=PlacementView.FUNCTION,
        )
        records += [item, function, placement]
    model = _model(*records)
    drawn = _place_order_differs_from_id_order(model, SymbolPlacement)
    assert [functions(model)[p.function].item for p in drawn] == [
        make_id(Item, ("i", n)) for n in (by_id[1], by_id[0])
    ]
