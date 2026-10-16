"""The sheet frame and title block symbols, against the numbers the old Typst frame drew.

EXPECTED holds the numbers of the old `fransys_pdf._frame` for four sheets, with and without a
notice, frozen as literals (a band of 20 mm on the first three, 32 mm on the last). The symbols
are data (`symbols/sheet-*.toml`, `title-block*.toml`); each test passes the values derive's
`sheet_frame` computes and reads what symdef's stretch, table and translate made of them.
"""

from itertools import accumulate
from typing import Any, NamedTuple

import pytest
from symdef import InvalidValueError, Line, Polyline, Weight

from electrical_symbols import (
    TITLE_BLOCK_MIN_BAND_MM,
    TITLE_BLOCK_MIN_WIDTH_MM,
    frame_border,
    frame_strip,
    notice_table,
    slot_box_mm,
    slot_room,
    slot_widths,
    title_block,
    title_logo,
)


class _Sheet(NamedTuple):
    width: float
    height: float
    x0: float
    y0: float
    content_width: float
    content_height: float
    columns: int
    rows: int


SHEETS = {
    "a3": _Sheet(420, 297, 5, 5, 410, 267, 8, 6),
    "a2": _Sheet(594, 420, 5, 5, 584, 390, 12, 8),
    "a4": _Sheet(297, 210, 5, 5, 287, 180, 6, 4),
    "a4t": _Sheet(297, 210, 6, 4, 285, 170, 5, 3),
}
EXPECTED: dict[tuple[str, bool], dict[str, Any]] = {
    ("a3", False): {
        "border": [5.0, 5.0, 410.0, 287.0],
        "band_top": 272.0,
        "band": 20.0,
        "cols": (60.0, 60.0, 100.0, 55.0, 35.0, 35.0, 45.0, 20.0),
        "notice_inner": (43.0, 18.0),
        "k": 8,
        "widths": {
            "title": 218.0,
            "number": 53.0,
            "revision": 33.0,
            "revision_date": 33.0,
            "customer": 58.0,
            "author": 58.0,
            "page_title": 98.0,
            "scope": 53.0,
            "sheet": 33.0,
        },
    },
    ("a3", True): {
        "border": [5.0, 5.0, 410.0, 287.0],
        "band_top": 272.0,
        "band": 20.0,
        "cols": (45.0, 26.0, 100.0, 55.0, 35.0, 35.0, 94.0, 20.0),
        "notice_inner": (92.0, 18.0),
        "k": 8,
        "widths": {
            "title": 169.0,
            "number": 53.0,
            "revision": 33.0,
            "revision_date": 33.0,
            "customer": 43.0,
            "author": 24.0,
            "page_title": 98.0,
            "scope": 53.0,
            "sheet": 33.0,
        },
    },
    ("a2", False): {
        "border": [5.0, 5.0, 584.0, 410.0],
        "band_top": 395.0,
        "band": 20.0,
        "cols": (
            86.76923076923077,
            86.76923076923077,
            144.6153846153846,
            79.53846153846153,
            50.61538461538461,
            50.61538461538461,
            65.07692307692308,
            20.0,
        ),
        "notice_inner": (63.07692307692308, 18.0),
        "k": 8,
        "widths": {
            "title": 316.1538461538462,
            "number": 77.53846153846153,
            "revision": 48.61538461538461,
            "revision_date": 48.61538461538461,
            "customer": 84.76923076923077,
            "author": 84.76923076923077,
            "page_title": 142.6153846153846,
            "scope": 77.53846153846153,
            "sheet": 48.61538461538461,
        },
    },
    ("a2", True): {
        "border": [5.0, 5.0, 584.0, 410.0],
        "band_top": 395.0,
        "band": 20.0,
        "cols": (
            65.07692307692308,
            37.6,
            144.6153846153846,
            79.53846153846153,
            50.61538461538461,
            50.61538461538461,
            135.93846153846152,
            20.0,
        ),
        "notice_inner": (133.93846153846152, 18.0),
        "k": 8,
        "widths": {
            "title": 245.2923076923077,
            "number": 77.53846153846153,
            "revision": 48.61538461538461,
            "revision_date": 48.61538461538461,
            "customer": 63.07692307692308,
            "author": 35.6,
            "page_title": 142.6153846153846,
            "scope": 77.53846153846153,
            "sheet": 48.61538461538461,
        },
    },
    ("a4", False): {
        "border": [5.0, 5.0, 287.0, 200.0],
        "band_top": 185.0,
        "band": 20.0,
        "cols": (
            41.07692307692308,
            41.07692307692308,
            68.46153846153847,
            37.65384615384615,
            23.96153846153846,
            23.96153846153846,
            30.807692307692307,
            20.0,
        ),
        "notice_inner": (28.807692307692307, 18.0),
        "k": 8,
        "widths": {
            "title": 148.61538461538464,
            "number": 35.65384615384615,
            "revision": 21.96153846153846,
            "revision_date": 21.96153846153846,
            "customer": 39.07692307692308,
            "author": 39.07692307692308,
            "page_title": 66.46153846153847,
            "scope": 35.65384615384615,
            "sheet": 21.96153846153846,
        },
    },
    ("a4", True): {
        "border": [5.0, 5.0, 287.0, 200.0],
        "band_top": 185.0,
        "band": 20.0,
        "cols": (
            30.807692307692307,
            17.8,
            68.46153846153847,
            37.65384615384615,
            23.96153846153846,
            23.96153846153846,
            64.35384615384615,
            20.0,
        ),
        "notice_inner": (62.35384615384615, 18.0),
        "k": 8,
        "widths": {
            "title": 115.06923076923077,
            "number": 35.65384615384615,
            "revision": 21.96153846153846,
            "revision_date": 21.96153846153846,
            "customer": 28.807692307692307,
            "author": 15.8,
            "page_title": 66.46153846153847,
            "scope": 35.65384615384615,
            "sheet": 21.96153846153846,
        },
    },
    ("a4t", False): {
        "border": [6.0, 4.0, 285.0, 202.0],
        "band_top": 174.0,
        "band": 32.0,
        "cols": (
            38.92307692307692,
            38.92307692307692,
            64.87179487179488,
            35.67948717948718,
            22.705128205128204,
            22.705128205128204,
            29.192307692307693,
            32.0,
        ),
        "notice_inner": (27.192307692307693, 30.0),
        "k": 13,
        "widths": {
            "title": 140.71794871794873,
            "number": 33.67948717948718,
            "revision": 20.705128205128204,
            "revision_date": 20.705128205128204,
            "customer": 36.92307692307692,
            "author": 36.92307692307692,
            "page_title": 62.871794871794876,
            "scope": 33.67948717948718,
            "sheet": 20.705128205128204,
        },
    },
    ("a4t", True): {
        "border": [6.0, 4.0, 285.0, 202.0],
        "band_top": 174.0,
        "band": 32.0,
        "cols": (
            29.192307692307693,
            16.866666666666667,
            64.87179487179488,
            35.67948717948718,
            22.705128205128204,
            22.705128205128204,
            60.97948717948718,
            32.0,
        ),
        "notice_inner": (58.97948717948718, 30.0),
        "k": 13,
        "widths": {
            "title": 108.93076923076924,
            "number": 33.67948717948718,
            "revision": 20.705128205128204,
            "revision_date": 20.705128205128204,
            "customer": 27.192307692307693,
            "author": 14.866666666666667,
            "page_title": 62.871794871794876,
            "scope": 33.67948717948718,
            "sheet": 20.705128205128204,
        },
    },
}

CASES = list(EXPECTED)
IDS = [f"{name}-{'notice' if notice else 'plain'}" for name, notice in CASES]
BODY_CAP = 2.5  # the house value capital height, the page counter box's height
# The house stack in a row, label (cap 1.8) over value (cap 2.5) with a 1 mm gap, centred: the
# capitals' centres 1.75 mm above and 1.4 mm below the row's middle; the data sets the second
# on the 0.125 grid, 1.375 (0.025 mm off the old frame)
VALUE_FROM_MIDDLE = 1.375


def _border(name):
    box = SHEETS[name]
    return frame_border((box.x0, box.y0), box.width - 2 * box.x0, box.height - 2 * box.y0)


def _strips(name):
    """The four strips with the values derive's `sheet_frame` passes, by side."""
    box = SHEETS[name]
    col, row = box.content_width / box.columns, box.content_height / box.rows
    return {
        "top": frame_strip("top", (box.x0, 0), (col, box.y0), box.columns, "x"),
        "bottom": frame_strip(
            "bottom", (box.x0, box.height - box.y0), (col, box.y0), box.columns, "x"
        ),
        "left": frame_strip("left", (0, box.y0), (box.x0, row), box.rows, "y"),
        "right": frame_strip("right", (box.width - box.x0, box.y0), (box.x0, row), box.rows, "y"),
    }


def _band(name, *, notice):
    """The title block and the logo cell in the band, as render places them."""
    box, want = SHEETS[name], EXPECTED[(name, notice)]
    band, top = want["band"], want["band_top"]
    width = box.width - 2 * box.x0 - band
    block = title_block((box.x0, top), width, band, notice=notice)
    return block, title_logo((box.x0 + width, top), band)


def _xs(name, *, notice):
    return list(accumulate(EXPECTED[(name, notice)]["cols"], initial=SHEETS[name].x0))


def _flat(pairs):
    return [c for pair in pairs for c in pair]


def _segments(symbol, weight):
    return [e for e in symbol.elements if isinstance(e, Line) and e.weight is weight]


@pytest.mark.parametrize("name", SHEETS)
def test_the_border_is_the_old_rectangle_and_thick(name):
    x, y, w, h = EXPECTED[(name, False)]["border"]
    (border,) = _border(name).elements
    assert isinstance(border, Polyline)
    corners = [(p.x, p.y) for p in border.points]
    assert corners == pytest.approx([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], abs=1e-9)
    assert border.closed
    assert border.weight is Weight.THICK


@pytest.mark.parametrize("name", SHEETS)
def test_the_ticks_run_across_each_strip_between_the_cells(name):
    box = SHEETS[name]
    ticks = {
        (e.start.x, e.start.y, e.end.x, e.end.y)
        for strip in _strips(name).values()
        for e in _segments(strip, Weight.NORMAL)
    }
    cw, rh = box.content_width / box.columns, box.content_height / box.rows
    expected = set()
    for i in range(1, box.columns):
        x = box.x0 + i * cw
        expected |= {(x, 0, x, box.y0), (x, box.height - box.y0, x, box.height)}
    for i in range(1, box.rows):
        y = box.y0 + i * rh
        expected |= {(0, y, box.x0, y), (box.width - box.x0, y, box.width, y)}
    assert _flat(sorted(ticks)) == pytest.approx(_flat(sorted(expected)), abs=1e-9)
    assert len(ticks) == 2 * (box.columns - 1) + 2 * (box.rows - 1)


@pytest.mark.parametrize("name", SHEETS)
def test_a_strip_cell_s_thick_edge_lies_on_the_border(name):
    x, y, w, h = EXPECTED[(name, False)]["border"]
    on_border = {"top": ("y", y), "bottom": ("y", y + h), "left": ("x", x), "right": ("x", x + w)}
    box = SHEETS[name]
    for side, strip in _strips(name).items():
        axis, at = on_border[side]
        edges = _segments(strip, Weight.THICK)
        assert len(edges) == (box.columns if axis == "y" else box.rows)
        for e in edges:
            assert getattr(e.start, axis) == pytest.approx(at, abs=1e-9)
            assert getattr(e.end, axis) == pytest.approx(at, abs=1e-9)


@pytest.mark.parametrize("name", SHEETS)
def test_every_strip_cell_has_a_label_centred_in_it(name):
    box = SHEETS[name]
    strips = _strips(name)
    for side in strips:
        count = box.columns if side in {"top", "bottom"} else box.rows
        assert [s.id for s in strips[side].slots] == [f"{k}.label" for k in range(1, count + 1)]
    cw, rh = box.content_width / box.columns, box.content_height / box.rows
    x, _, w, _ = slot_box_mm(strips["top"], "1.label")
    assert (x + w / 2, w) == pytest.approx((box.x0 + cw / 2, cw))
    first = next(s for s in strips["top"].slots if s.id == "1.label")
    assert first.position.y == pytest.approx(box.y0 / 2)
    last = next(s for s in strips["right"].slots if s.id == f"{box.rows}.label")
    assert (last.position.x, last.position.y) == pytest.approx(
        (box.width - box.x0 / 2, box.y0 + (box.rows - 0.5) * rh)
    )
    assert slot_room(strips["right"], f"{box.rows}.label")[0] == pytest.approx(box.x0)


@pytest.mark.parametrize(("name", "notice"), CASES, ids=IDS)
def test_every_column_boundary_row_boundary_and_the_band_are_the_old_ones(name, notice):
    want = EXPECTED[(name, notice)]
    block, logo = _band(name, notice=notice)
    lines = [e for e in block.lines.elements if isinstance(e, Line)]
    xs = _xs(name, notice=notice)
    top, bottom = want["band_top"], want["band_top"] + want["band"]
    mid = top + want["band"] / 2
    full = sorted(e.start.x for e in lines if e.start.y == top and e.end.y == pytest.approx(bottom))
    lower = sorted(
        e.start.x
        for e in lines
        if e.start.y == pytest.approx(mid) and e.end.y == pytest.approx(bottom)
    )
    across = [(e.start.x, e.end.x) for e in lines if e.start.y == e.end.y]
    assert full == pytest.approx(xs[3:7], abs=1e-9)
    assert lower == pytest.approx(xs[1:3], abs=1e-9)
    assert _flat(across) == pytest.approx([xs[0], xs[6]], abs=1e-9)
    assert [e.start.y for e in lines if e.start.y == e.end.y] == pytest.approx([mid], abs=1e-9)
    assert {e.weight for e in (*block.lines.elements, *logo.elements)} == {Weight.THICK}
    assert len(block.lines.elements) == 8


@pytest.mark.parametrize(("name", "notice"), CASES, ids=IDS)
def test_the_title_block_and_the_logo_cell_share_the_old_outline(name, notice):
    want = EXPECTED[(name, notice)]
    block, logo = _band(name, notice=notice)
    xs = _xs(name, notice=notice)
    top, bottom = want["band_top"], want["band_top"] + want["band"]
    for symbol, left, right in ((block.lines, xs[0], xs[7]), (logo, xs[7], xs[8])):
        rect = next(e for e in symbol.elements if isinstance(e, Polyline))
        got = [c for p in rect.points for c in (p.x, p.y)]
        assert got == pytest.approx([left, top, right, top, right, bottom, left, bottom], abs=1e-9)
        assert rect.closed


@pytest.mark.parametrize(("name", "notice"), CASES, ids=IDS)
def test_the_field_rooms_are_the_old_widths(name, notice):
    block, _ = _band(name, notice=notice)
    want = EXPECTED[(name, notice)]["widths"]
    rooms = slot_widths(block.lines) | slot_widths(block.bold)
    assert {k: rooms[k] for k in want} == pytest.approx(want, abs=1e-9)
    assert slot_room(block.bold, "title")[0] == pytest.approx(want["title"], abs=1e-9)


@pytest.mark.parametrize(("name", "notice"), CASES, ids=IDS)
def test_the_notice_cell_is_the_old_one(name, notice):
    want = EXPECTED[(name, notice)]
    block, _ = _band(name, notice=notice)
    xs = _xs(name, notice=notice)
    inner_w, inner_h = want["notice_inner"]
    assert slot_box_mm(block.lines, "notice") == pytest.approx(
        (xs[6] + 1, want["band_top"] + 1, inner_w, inner_h), abs=1e-9
    )


@pytest.mark.parametrize("name", ["a3", "a4t"])
def test_notice_lines_stack_from_the_cell_s_corner_at_the_pitch(name):
    want = EXPECTED[(name, True)]
    block, _ = _band(name, notice=True)
    pitch = 2.16
    lines = notice_table(block, pitch, 3)
    xs = _xs(name, notice=True)
    assert [s.id for s in lines.slots] == ["1.line", "2.line", "3.line"]
    third = lines.slots[2]
    # the line's capitals are centred in its pitch; the text starts 1 mm inside the cell
    assert (third.position.x, third.position.y) == pytest.approx(
        (xs[6] + 1, want["band_top"] + 1 + 2.5 * pitch), abs=1e-9
    )
    assert third.box[1] == pytest.approx(pitch)
    edges = _segments(lines, Weight.THICK)
    assert len(edges) == 3
    for e in edges:  # each line's edge is the notice column's boundary
        assert (e.start.x, e.end.x) == pytest.approx((xs[6], xs[6]), abs=1e-9)
        assert e.end.y <= want["band_top"] + want["band"]


@pytest.mark.parametrize("name", ["a3", "a4t"])
def test_a_cell_is_a_label_over_a_value_and_the_growth_lands_by_the_cut_weights(name):
    """Past 20 mm the six y cuts (weights 1, 4, 1 per row) take the band's growth by share of 12."""
    want = EXPECTED[(name, False)]
    block, _ = _band(name, notice=False)
    top, growth = want["band_top"], want["band"] - 20
    xs = _xs(name, notice=False)
    number_x = (xs[3] + xs[4]) / 2
    label_y = top + 3.25 + growth * 1 / 12
    value_y = top + 6.375 + growth * 5 / 12
    label = next(s for s in block.labels.slots if s.id == "label.number")
    value = next(s for s in block.lines.slots if s.id == "number")
    assert (label.position.x, label.position.y) == pytest.approx((number_x, label_y))
    assert (value.position.x, value.position.y) == pytest.approx((number_x, value_y))
    lower = next(s for s in block.lines.slots if s.id == "customer")
    assert lower.position.y == pytest.approx(top + 16.375 + growth * 11 / 12)


def test_the_title_block_has_every_value_label_and_the_page_and_logo_boxes():
    block, logo = _band("a3", notice=False)
    fields = ["number", "revision", "revision_date", "customer", "author", "page_title"]
    fields += ["scope", "sheet"]
    assert {s.id for s in block.lines.slots} == {*fields, "page", "notice"}
    assert [a.id for a in block.lines.anchors] == ["notice"]
    assert [s.id for s in block.bold.slots] == ["title"]
    assert block.bold.elements == ()
    assert block.labels.elements == ()
    assert {s.id for s in block.labels.slots} == {f"label.{f}" for f in ["title", *fields, "page"]}
    page_top = 282 + 5 + VALUE_FROM_MIDDLE - BODY_CAP / 2
    assert slot_box_mm(block.lines, "page") == pytest.approx(
        (316.0, page_top, 33.0, BODY_CAP), abs=1e-9
    )
    assert slot_box_mm(logo, "logo") == pytest.approx((395.0, 272.0, 20.0, 20.0), abs=1e-9)


def test_the_least_band_is_the_authored_one():
    assert (TITLE_BLOCK_MIN_BAND_MM, TITLE_BLOCK_MIN_WIDTH_MM) == (20, 97.5)
    with pytest.raises(InvalidValueError, match="below the natural extent"):
        title_block((5, 272), 390, 19.5, notice=False)


@pytest.mark.parametrize("call", [slot_room, slot_box_mm])
def test_an_unknown_slot_names_the_symbol_and_the_slot(call):
    with pytest.raises(KeyError, match=r"Sheet strip cell \(top\).*99\.label"):
        call(_strips("a3")["top"], "99.label")


def test_slot_room_is_width_then_height():
    # a strip label's box is the cell's width and the strip's depth less half a mm
    assert slot_room(_strips("a3")["top"], "1.label") == pytest.approx((410 / 8, 4.5))
