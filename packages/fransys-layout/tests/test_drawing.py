"""The drawn values round-trip through the core's JSON form (layout-0315)."""

import json

import pytest

from fransys_layout import drawing
from fransys_layout.core import from_plain, to_plain
from fransys_layout.core.values import Box, Size


def _text() -> drawing.DrawnText:
    return drawing.DrawnText("K1", Box(1, 2, 3, 4), "tag", "NW")


def _drawing() -> drawing.Drawing:
    return drawing.Drawing(
        area=Size(400, 300),
        symbols=(
            drawing.DrawnSymbol(
                "s1",
                "contact.make",
                16,
                24,
                "MR90",
                (("tag", "K1"),),
                (("x", 32),),
                n=3,
                muted=True,
                tint="#aabbcc",
                texts=(("a", "b"), ("c",)),
            ),
        ),
        wires=(drawing.DrawnWire("w1", ((0, 0), (8, 0), (8, 8)), "wire", 2, _text()),),
        markers=(drawing.DrawnMarker("m1", "ref.out", 8, 8, "E", (("name", "A"),), None),),
        texts=(_text(),),
        outlines=(drawing.DrawnOutline("o1", "unit", ((0, 0), (9, 9)), None),),
        library_version="0.12.0",
    )


def _style() -> drawing.Style:
    return drawing.Style(
        tints=("#000000",) * 8,
        wires=(("wire", drawing.WireStyle(width_mm=0.25, dash_mm=(4.0, 1.0))),),
        texts=(("label", drawing.TextStyle(1.8, "Font")),),
        dashes=(("symbol", (1.25, 0.625)),),
        line_thin_mm=0.25,
        line_thick_mm=0.5,
        line_rule_mm=0.18,
        junction_dot_mm=1.0,
        muted_colour="grey",
        module_mm=2.5,
        wiring_grid=8,
        g_per_module=8,
    )


def _sheet() -> drawing.Sheet:
    return drawing.Sheet(420.0, 297.0, frame_key="frame", slots=(("title", "T"),))


@pytest.mark.parametrize("value", [_drawing(), _style(), _sheet()], ids=lambda v: type(v).__name__)
def test_every_drawn_value_round_trips(value):
    plain = to_plain(value)
    assert from_plain(type(value), json.loads(json.dumps(plain))) == value


def test_a_populated_value_has_no_field_the_json_form_drops():
    """Every field of every type is in the plain form of a populated value."""
    for value in (_drawing(), _style(), _sheet(), *_drawing().symbols, *_drawing().wires):
        assert set(to_plain(value)) == set(type(value).__dataclass_fields__)
