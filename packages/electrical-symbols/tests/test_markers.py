"""The reference markers are symbol data (es-0072): three symbols, one wire style, one text rule.

The expected values are the ones the geometry bar (ELECTRICAL-MARKERS, Ruling 5) found equal to
what render draws today: sizes in module units (8 G), text points under `text_block = "grid"`.
Layout fits a marker at 8 G text height (1.0 module) and draws its text at the printed font
(2.4691 mm over the 2.5 mm module); both heights are used below.
"""

import pytest
from symdef import Orientation, Weight, body_box, fitted_symbol, orient, slot_lines, wire

from electrical_symbols import LIBRARY

FIT_HEIGHT = 1.0
DRAW_HEIGHT = 2.4691 / 2.5
KEYS = ("marker-arrow", "marker-arrow-turned", "marker-box")


def _fitted(key, text, orientation=Orientation.R0):
    return orient(
        fitted_symbol(LIBRARY.symbols[key], {"ref": text}, LIBRARY, FIT_HEIGHT), orientation
    )


def _text_points(symbol, text):
    placed = slot_lines(symbol.slots[0], text, DRAW_HEIGHT, LIBRARY.font, LIBRARY.grid)
    return [(p.point.x, p.point.y, p.anchor, p.turned) for p in placed]


def _outline(symbol):
    return [(p.x, p.y) for p in symbol.elements[0].points]


def test_the_library_holds_the_markers_and_their_rules() -> None:
    assert all(key in LIBRARY.symbols for key in KEYS)
    assert LIBRARY.font is not None
    assert LIBRARY.font.text_block == "grid"
    assert [w.id for w in LIBRARY.wires if w.id == "marker"] == ["marker"]


def test_the_marker_wire_is_a_solid_normal_line() -> None:
    drawn = wire(LIBRARY, "marker", [(0, 0), (1, 0)])
    line = drawn.elements[0]
    assert (line.weight, line.style.value) == (Weight.NORMAL, "solid")  # ty: ignore[unresolved-attribute]  a Polyline


def test_an_arrow_grows_with_its_text_and_centres_it_at_floor_of_half_its_width() -> None:
    text = "-W1 → -H1 p2:1B"  # 67 G wide, odd: the centre is 33 divisions from the edge
    arrow = _fitted("marker-arrow", text)
    box = body_box(arrow, LIBRARY.font)
    assert (box.width, box.height) == (8.375, 1.5)
    assert _outline(arrow) == [(0, 0), (0.375, -0.75), (8.375, -0.75), (8.375, 0.75), (0.375, 0.75)]
    ((x, y, anchor, turned),) = _text_points(arrow, text)
    assert (anchor, turned) == ("middle", False)
    assert (x, y) == pytest.approx((4.125, 0.2503749))


@pytest.mark.parametrize(
    ("orientation", "end", "text_y"),
    [(Orientation.R0, 5.875, 2.875), (Orientation.R180, -5.875, -3.0)],
)
def test_a_turned_arrow_reads_along_the_wire_south_or_north(orientation, end, text_y) -> None:
    text = "#99-p99:8F"  # layout's widest reference: 47 G
    arrow = _fitted("marker-arrow-turned", text, orientation)
    ((x, y, anchor, turned),) = _text_points(arrow, "#1-p4:1A")
    assert turned
    assert anchor == "middle"
    assert (x, y) == pytest.approx((0.2503749, text_y))
    assert max(_outline(arrow), key=lambda p: abs(p[1]))[1] == end


def test_a_box_holds_one_or_several_lines_centred() -> None:
    one = _fitted("marker-box", "-W1 → -H1 p5:2B, -X4 p1:4D")
    assert _outline(one) == [(0, 0), (13.375, 0), (13.375, 1.5), (0, 1.5)]
    ((x, y, _, _),) = _text_points(one, "-W1 → -H1 p5:2B, -X4 p1:4D")
    assert (x, y) == pytest.approx((6.625, 1.0003749))
    two = "a\nbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    box = body_box(_fitted("marker-box", two), LIBRARY.font)
    assert (box.width, box.height) == (16.0, 2.5)
    rows = [y for _, y, _, _ in _text_points(_fitted("marker-box", two), two)]
    assert rows == pytest.approx([1.0003749, 2.0003749])
