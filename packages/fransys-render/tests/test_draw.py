"""`svg`: a hand-built Drawing drawn against symdef called in the plain way (the oracle)."""

import dataclasses
from decimal import Decimal
from typing import Any

import pytest
import symdef
from fransys_el import style
from fransys_render.draw import DrawError, format_decimal, svg
from symdef import Weight

from electrical_symbols import LIBRARY, drawn_slots, drawn_symbol
from fransys_layout.core.values import Box, Size
from fransys_layout.drawing import (
    Drawing,
    DrawnMarker,
    DrawnOutline,
    DrawnSymbol,
    DrawnText,
    DrawnWire,
)

STYLE = style(LIBRARY)
_DASH, _GAP, _DOT, _DOT_GAP = dict(STYLE.dashes)["outline"]
_OUTLINE_DASH = (_DASH, _GAP, _DOT, _DOT_GAP)
M = Decimal(str(STYLE.module_mm))


def drawing(symbols=(), wires=(), **fields: Any) -> Drawing:
    base = {"markers": (), "texts": (), "outlines": ()}
    return Drawing(
        Size(800, 400), tuple(symbols), tuple(wires), library_version="v", **base | fields
    )


def oracle(symbol, **kwargs):
    font = LIBRARY.font
    assert font is not None
    ratio = Decimal(font.cap_height) / Decimal(font.units_per_em)
    dash, gap = dict(STYLE.dashes)["symbol"]
    label = dict(STYLE.texts)["label"]
    size = (Decimal(str(label.height_mm)) / ratio).quantize(Decimal("0.0001"))
    return symdef.to_fragment_mm(
        symbol,
        module_mm=STYLE.module_mm,
        weights_mm={Weight.NORMAL: STYLE.line_thin_mm, Weight.THICK: STYLE.line_thick_mm},
        dash_mm=(dash, gap),
        dash_dot_mm=_OUTLINE_DASH,
        font_family=label.family,
        font_mm=float(size),
        cap_ratio=float(ratio),
        required_slots=LIBRARY.required_slots,
        **kwargs,
    )


def sym(**kw: Any) -> DrawnSymbol:
    base: dict[str, Any] = {"id": "s", "key": "break-contact", "x": 0, "y": 0, "orient": "R0"}
    return DrawnSymbol(**(base | kw))


def test_symbol_with_slots_matches_the_plain_symdef_call():
    drawn = sym(x=80, y=16, slots=(("tag", "-A1"),))
    body = oracle(LIBRARY.get("break-contact"), texts={"tag": "-A1"})
    width, height = format_g(800), format_g(400)
    expected = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm"'
        f' viewBox="0 0 {width} {height}">'
        f'<g transform="translate({format_g(80)},{format_g(16)})">{body}</g></svg>'
    )
    assert svg(drawing([drawn]), LIBRARY, STYLE) == expected


def test_deterministic():
    d = drawing([sym(slots=(("tag", "-A1"),))])
    assert svg(d, LIBRARY, STYLE) == svg(d, LIBRARY, STYLE)


def test_translate_coordinates_are_g_to_mm_without_trailing_zeros():
    text = svg(drawing([sym(x=8, y=0)]), LIBRARY, STYLE)
    assert f"translate({format_g(8)},0)" in text


def format_g(g):
    return f"{(Decimal(g) * M / 8).normalize():f}"


def test_stretched_symbol_matches_symdef_stretch():
    drawn = sym(key="card", stretch=(("x", 320),), leads=("c1", "c2", "c3", "c4"))
    base = symdef.stretch(LIBRARY.get("card"), "x", 40.0)
    assert oracle(base) in svg(drawing([drawn]), LIBRARY, STYLE)


def test_turned_symbol_matches_symdef_orient():
    base = symdef.orient(LIBRARY.get("break-contact"), symdef.Orientation.MR90)
    assert oracle(base) in svg(drawing([sym(orient="MR90")]), LIBRARY, STYLE)


def test_a_table_symbol_is_refused_naming_the_symbol():
    with pytest.raises(DrawError, match=r"symbol 's'.*3 rows.*`texts`"):
        svg(drawing([sym(n=3)]), LIBRARY, STYLE)


def test_no_leads_draws_no_bound_lead():
    base = symdef.leads(symdef.stretch(LIBRARY.get("card"), "x", 40.0), ())
    text = svg(drawing([sym(key="card", stretch=(("x", 320),))]), LIBRARY, STYLE)
    assert oracle(base) in text
    plain = oracle(symdef.stretch(LIBRARY.get("card"), "x", 40.0))
    assert plain not in text


def test_listed_leads_keep_only_their_bound_leads():
    base = symdef.leads(symdef.stretch(LIBRARY.get("card"), "x", 40.0), ("c1", "c3"))
    drawn = sym(key="card", stretch=(("x", 320),), leads=("c1", "c3"))
    assert oracle(base) in svg(drawing([drawn]), LIBRARY, STYLE)


def test_offsets_place_the_ports_along_the_stretch_axis():
    base = symdef.stretch(LIBRARY.get("card"), "x", 40.0, offsets={"c1": 6.0, "c2": 14.0})
    base = symdef.leads(base, ("c1", "c2"))
    drawn = sym(
        key="card", stretch=(("x", 320),), offsets=(("c1", 48), ("c2", 112)), leads=("c1", "c2")
    )
    assert oracle(base) in svg(drawing([drawn]), LIBRARY, STYLE)


@pytest.mark.parametrize("stretch", [(), (("x", 320), ("y", 80))])
def test_offsets_need_exactly_one_stretch_axis(stretch):
    drawn = sym(key="card", stretch=stretch, offsets=(("c1", 48),))
    with pytest.raises(DrawError, match=r"symbol 's'.*offsets"):
        svg(drawing([drawn]), LIBRARY, STYLE)


def test_muted_and_tint_reach_the_toolkit():
    base = LIBRARY.get("break-contact")
    expected = oracle(base, tint="red", muted=STYLE.muted_colour)
    assert expected in svg(drawing([sym(muted=True, tint="red")]), LIBRARY, STYLE)


def test_wire_polyline_is_the_symdef_wire_in_absolute_mm():
    points = ((0, 0), (80, 0), (80, 48))
    base = symdef.wire(LIBRARY, "link", [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0)])
    wire = DrawnWire("w", points, "link")
    text = svg(drawing(wires=[wire]), LIBRARY, STYLE)
    assert text.endswith(oracle(base) + "</svg>")
    assert "translate" not in text


def test_two_drawings_differing_in_one_point_differ():
    a = DrawnWire("w", ((0, 0), (80, 0)), "wire")
    b = DrawnWire("w", ((0, 0), (88, 0)), "wire")
    assert svg(drawing(wires=[a]), LIBRARY, STYLE) != svg(drawing(wires=[b]), LIBRARY, STYLE)


def test_a_bundle_draws_one_line_per_lane_at_the_library_pitch():
    one = svg(drawing(wires=[DrawnWire("w7", ((0, 0), (80, 0)), "trunk")]), LIBRARY, STYLE)
    three = svg(
        drawing(wires=[DrawnWire("w7", ((0, 0), (80, 0)), "trunk", lanes=3)]), LIBRARY, STYLE
    )
    assert one.count("<polyline") == 1
    assert three.count("<polyline") == 3
    assert 'points="0,2.5 25,2.5"' in three
    assert 'points="0,5 25,5"' in three


def test_a_slanted_bundle_is_refused_naming_the_wire():
    wire = DrawnWire("w9", ((0, 0), (80, 24)), "trunk", lanes=2)
    with pytest.raises(DrawError, match=r"w9.*2 lanes.*horizontal or vertical"):
        svg(drawing(wires=[wire]), LIBRARY, STYLE)


def _count_texts(text: str) -> int:
    return text.count("<text ")


def test_texts_are_drawn_one_tag_each():
    texts = tuple(DrawnText(f"-A{i}", Box(8 * i, 8, 40, 8), "TAG", "NW") for i in range(3))
    assert _count_texts(svg(drawing(texts=texts), LIBRARY, STYLE)) == 3


def test_a_text_is_symdef_s_corner_text_and_text_tag():
    out = svg(drawing(texts=(DrawnText("-A1", Box(16, 16, 40, 8), "TAG", "SE"),)), LIBRARY, STYLE)
    label = dict(STYLE.texts)["label"]
    font = LIBRARY.font
    assert font is not None
    ratio = font.cap_height / font.units_per_em
    size = round(label.height_mm / ratio, 4)
    m, g = STYLE.module_mm, STYLE.g_per_module
    placed = symdef.corner_text(
        symdef.Box(symdef.Point(16 / g, 16 / g), symdef.Point(56 / g, 24 / g)), "SE", size / m, font
    )
    tag = symdef.text_tag(
        "-A1",
        symdef.Point(placed.point.x * m, placed.point.y * m),
        size,
        anchor=placed.anchor,
        font_family=label.family,
        turn=placed.turned,
    )
    assert tag in out
    assert 'text-anchor="end"' in tag


def test_a_wire_label_is_drawn_after_its_wire():
    label = DrawnText("N1", Box(0, 0, 8, 8), "WIRE", "NW")
    wire = dataclasses.replace(DrawnWire("w8", ((0, 0), (8, 0)), "wire"), label=label)
    out = svg(drawing(wires=[wire]), LIBRARY, STYLE)
    assert _count_texts(out) == 1


def test_an_unknown_corner_is_symdef_s_error_and_not_a_guess():
    anchor: Any = "XX"
    text = DrawnText("-A1", Box(16, 16, 40, 8), "TAG", anchor)
    with pytest.raises(symdef.InvalidValueError, match="corner 'XX' is not valid"):
        svg(drawing(texts=(text,)), LIBRARY, STYLE)


def _placed(body, x_g, y_g):
    x, y = Decimal(x_g) * M / STYLE.g_per_module, Decimal(y_g) * M / STYLE.g_per_module
    return f'<g transform="translate({format_decimal(x)},{format_decimal(y)})">{body}</g>'


def test_an_outline_is_its_frame_stretched_to_its_points():
    points = ((16, 24), (96, 24), (96, 72), (16, 72), (16, 24))
    frame = LIBRARY.get("unit-outline")
    g = STYLE.g_per_module
    frame = symdef.stretch(symdef.stretch(frame, "x", 80 / g), "y", 48 / g)
    text = svg(drawing(outlines=(DrawnOutline("o", "unit-outline", points, None),)), LIBRARY, STYLE)
    assert _placed(oracle(frame), 16, 24) in text


def test_an_outline_label_is_drawn_after_the_frame():
    label = DrawnText("-A1", Box(16, 16, 40, 8), "TAG", "NW")
    points = ((16, 24), (96, 72))
    plain = svg(drawing(outlines=(DrawnOutline("o", "group-frame", points, None),)), LIBRARY, STYLE)
    labelled = svg(
        drawing(outlines=(DrawnOutline("o", "group-frame", points, label),)), LIBRARY, STYLE
    )
    assert _count_texts(labelled) == _count_texts(plain) + 1


def test_a_marker_is_its_symbol_turned_to_its_side_with_its_slots():
    marker = DrawnMarker("m", "reference-marker", 40, 8, "S", (("ref", "7/2"),), "#ff0000")
    turned = symdef.orient(LIBRARY.get("reference-marker"), symdef.Orientation.R90)
    text = svg(drawing(markers=(marker,)), LIBRARY, STYLE)
    assert _placed(oracle(turned, tint="#ff0000", texts={"ref": "7/2"}), 40, 8) in text


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("markers", DrawnMarker("m", "nope", 0, 0, "N", (), None), r"marker 'm'.*nope"),
        ("outlines", DrawnOutline("o", "nope", ((0, 0), (8, 8)), None), r"outline 'o'.*nope"),
        (
            "outlines",
            DrawnOutline("o", "unit-outline", ((0, 0), (8, 0), (8, 8)), None),
            r"outline 'o'.*rectangle",
        ),
        (
            "markers",
            DrawnMarker("m", "reference-marker", 0, 0, "Q", (), None),  # ty: ignore[invalid-argument-type] -- a bad side
            r"marker 'm'.*'Q'",
        ),
    ],
)
def test_a_bad_outline_or_marker_raises_naming_it(field, value, message):
    with pytest.raises(DrawError, match=message):
        svg(drawing(**{field: (value,)}), LIBRARY, STYLE)


def test_a_box_is_the_symbol_drawn_symbol_builds_at_its_offsets():
    texts = (("1",), ("2",), ("3",))
    drawn = sym(key="generic-box", texts=texts, offsets=(("1", 0), ("2", 16), ("3", 32)))
    base = drawn_symbol("generic-box", texts, library=LIBRARY, offsets={"1": 0, "2": 16, "3": 32})
    text = svg(drawing([drawn]), LIBRARY, STYLE)
    assert oracle(symdef.leads(base, ())) in text


def test_a_contact_table_is_the_fitted_table_of_its_texts():
    texts = (("NO", "NC"), ("13-14 N/A", "21-22 N/A"))
    slots = tuple(drawn_slots("contact-head", texts).items())
    drawn = sym(key="contact-head", texts=texts, slots=slots)
    base = drawn_symbol("contact-head", texts, library=LIBRARY)
    text = svg(drawing([drawn]), LIBRARY, STYLE)
    assert oracle(symdef.leads(base, ()), texts=dict(slots)) in text
    assert "21-22 N/A" in text
    assert ">NO<" in text


_POLE_LEADS = ("1.in", "1.out", "2.in", "2.out", "3.in", "3.out")


def test_poles_repeat_the_symbol_before_its_leads():
    drawn = sym(key="make-contact", poles=3, leads=_POLE_LEADS)
    base = symdef.leads(symdef.repeat(LIBRARY.get("make-contact"), 3), _POLE_LEADS)
    assert oracle(base) in svg(drawing([drawn]), LIBRARY, STYLE)


def test_a_pole_lead_on_a_single_pole_symbol_is_refused_naming_symbol_and_port():
    with pytest.raises(DrawError, match=r"'s' \('make-contact', 1 poles\).*'1.in'"):
        svg(drawing([sym(key="make-contact", leads=("1.in",))]), LIBRARY, STYLE)


def test_sheet_mm_draws_the_whole_sheet_with_the_drawing_at_the_content_box():
    """render-0027: the content box offset is a translate, the viewBox the sheet."""
    page = drawing(wires=[DrawnWire("w", ((0, 0), (80, 0)), "wire")])
    plain = svg(page, LIBRARY, STYLE)
    sheet = svg(page, LIBRARY, STYLE, sheet_mm=(420, 297, 5, 7))
    body = plain.split(">", 1)[1].removesuffix("</svg>")
    assert 'viewBox="0 0 420 297"' in sheet
    assert f'<g transform="translate(5 7)">{body}</g></svg>' in sheet


def test_draw_error_is_on_the_surface_with_its_docstring():
    import fransys_render

    assert fransys_render.DrawError is DrawError
    assert "DrawError" in fransys_render.__all__
    assert fransys_render.DrawError.__doc__
    assert issubclass(fransys_render.DrawError, ValueError)
