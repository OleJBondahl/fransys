"""A `layout.power_symbol` is drawn by the one placement draw path (decision render-0005)."""

from decimal import Decimal

import pytest
from fransys_render import pages
from fransys_render._symbol_geometry import oriented_power_symbol
from fransys_render._symbols import power_lead_ends, symbols_group
from graphical_symbols import Orientation as LibraryOrientation
from graphical_symbols import orient, to_fragment

from electrical_symbols import LIBRARY
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Orientation,
    Page,
    PageRole,
    PowerSymbol,
    SheetFormat,
    layout_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole

_ORIGIN = Origin(file="packages/fransys-render/tests/test_power_symbols.py", line=1, note="x")
_KEYS = ("power-supply", "ground", "protective-earth")


def _model(symbol, orientation, *, with_power=True, pin=(100, 116)):
    ds_key, sheet_key, page_key = ("drawing_set", "p"), ("sheet_format", "p"), ("page", "p")
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, ds_key), key=ds_key, location=None, number=1, produced_by="t"
    )
    sheet = SheetFormat(
        id=make_id(SheetFormat, sheet_key),
        key=sheet_key,
        name="p",
        width_mm=300,
        height_mm=200,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=280,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    page = Page(
        id=make_id(Page, page_key),
        key=page_key,
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.POWER,
        sheet_format=sheet.id,
        groups=(),
        produced_by="t",
    )
    item_key, fn_key, port_key = ("item", "p"), ("function", "p"), ("function", "p", "1")
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag="X1",
        description="Invented",
        installed=True,
    )
    fn = Function(
        id=make_id(Function, fn_key),
        key=fn_key,
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=fn.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    records = [drawing_set, sheet, page, item, fn, port]
    if with_power:
        records.append(
            PowerSymbol(
                id=make_id(PowerSymbol, port_key),
                key=port_key,
                port=port.id,
                page=page.id,
                symbol=symbol,
                x=100,
                y=100,
                pin_x=pin[0],
                pin_y=pin[1],
                orientation=orientation,
                produced_by="t",
            )
        )
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft), page


@pytest.mark.parametrize("key", _KEYS)
def test_each_power_symbol_is_drawn_at_its_origin(key):
    model, page = _model(key, Orientation.R0)
    expected = (
        '<g class="symbol" transform="translate(41.25,41.25) scale(2.5)">'
        f"{to_fragment(LIBRARY.get(key))}</g>"
    )
    assert expected in symbols_group(model, page)
    assert expected in "".join(pages(model).values())


@pytest.mark.parametrize("key", _KEYS)
def test_orientation_turns_the_symbol(key):
    model, page = _model(key, Orientation.R90)
    turned = to_fragment(orient(LIBRARY.get(key), LibraryOrientation.R90))
    plain = to_fragment(LIBRARY.get(key))
    group = symbols_group(model, page)
    assert turned in group
    assert turned != plain
    assert plain not in group


# Symbol port (origin (100, 100) plus its M offset times 8), then the record's pin, three grids
# out: the lead's length is the record's, never a render constant.
_LEADS = {
    "power-supply": ((100, 108), (100, 132), "43.75", "51.25"),
    "ground": ((100, 84), (100, 60), "36.25", "28.75"),
    "protective-earth": ((100, 84), (100, 60), "36.25", "28.75"),
}


@pytest.mark.parametrize("key", _KEYS)
def test_lead_runs_straight_from_the_symbol_port_to_the_records_pin(key):
    # UNDO: render/_symbols.py:power_lead_ends, end the lead one grid out along the port's direction
    port_end, pin_end, y1_mm, y2_mm = _LEADS[key]
    model, page = _model(key, Orientation.R0, pin=pin_end)
    power = next(iter(layout_of(model, PowerSymbol).values()))
    assert power_lead_ends(power, oriented_power_symbol(power)) == (port_end, pin_end)
    lead = f'<line class="wire" x1="41.25" y1="{y1_mm}" x2="41.25" y2="{y2_mm}"/>'
    assert lead in symbols_group(model, page)


def test_a_model_without_power_symbols_draws_no_symbol_group_content():
    model, page = _model("ground", Orientation.R0, with_power=False)
    assert symbols_group(model, page) == ""
