"""`cable_blocks`: one SVG per cable block, from hand-built records (CT5-2, CD7 to CD11)."""

from decimal import Decimal
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

import pytest
from _cable_build import G, World
from fransys_render import cable_blocks
from fransys_render._constants import ASCENT_RATIO
from fransys_render._numbers import format_decimal, grid_to_mm

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.layout import BlockRow, BoxKind, EndStyle

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item

SVG = "{http://www.w3.org/2000/svg}"
TOP, BOTTOM = BlockRow.TOP, BlockRow.BOTTOM
CELLS = (3 * G, 5 * G, 7 * G)
DASH = "stroke-dasharray"


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)  # noqa: S314 -- the SVG is this package's own output


def _of(root: ET.Element, tag: str, css: str) -> list[ET.Element]:
    """Elements `tag` whose class holds `css`, in document order."""
    return [e for e in root.iter(SVG + tag) if css in e.get("class", "").split()]


def _by_y(elements: list[ET.Element]) -> list[ET.Element]:
    """`elements` from the top of the block down; record order is by id, not by row."""
    return sorted(elements, key=lambda e: Decimal(e.get("y") or 0))


def _texts(root: ET.Element, css: str) -> list[str]:
    """The texts of class `css`, from the top of the block down."""
    return [e.text or "" for e in _by_y(_of(root, "text", css))]


def _mm(g: int | Decimal, module: Decimal = Decimal("2.5")) -> str:
    return format_decimal(grid_to_mm(0, g, module))


def _pair(
    *, harness_box: bool = True, module: Decimal | None = None
) -> tuple[Model, str, dict[str, Id[Item]]]:
    """Harness `WH2` of cables `W1` (shielded, 3000 mm, 2 cores) and `W2`, from `A1` to `B1`."""
    world = World()
    sheet = None if module is None else world.sheet(module)
    harness = world.item("wh2", "WH2")
    w1 = world.cable("w1", "W1", ("BK1", ""), parent=harness, shielded=True, length=3000)
    w2 = world.cable("w2", "W2", ("BN",), parent=harness)
    a1, a = world.device("a1", "A1", "1", "2", "3")
    b1, b = world.device("b1", "B1", "1", "2", "3")
    c1 = world.core("c1", w1, (a["1"], b["1"]), 1, label="no. 1")
    c2 = world.core("c2", w1, (a["2"], b["2"]), 2)
    c3 = world.core("c3", w2, (a["3"], b["3"]), 1)
    block = world.block(harness, sheet=sheet)
    if harness_box:
        world.box(block, harness, BoxKind.HARNESS, (G, 5 * G, 8 * G, 7 * G))
    world.box(block, w1, BoxKind.CABLE, (2 * G, 6 * G, 4 * G, 5 * G))
    world.box(block, w2, BoxKind.CABLE, (6 * G, 6 * G, 2 * G, 5 * G))
    world.end(block, a1, TOP, EndStyle.SOLID, tuple(zip(a.values(), CELLS, strict=True)))
    world.end(block, b1, BOTTOM, EndStyle.SOLID, tuple(zip(b.values(), CELLS, strict=True)))
    for conductor, x in zip((c1, c2, c3), CELLS, strict=True):
        world.wire(block, conductor, x)
    model = world.model()
    key = cable_block_key(None, harness)
    return model, key, {"harness": harness, "w1": w1, "w2": w2}


def _lone() -> tuple[Model, str]:
    """Cable `W0`, the lone cable of part-less harness `WH1`: a cable block, no harness box."""
    world = World()
    harness = world.item("wh1", "WH1")
    w0 = world.cable("w0", "W0", ("BK",), parent=harness)
    a1, a = world.device("a1", "A1", "1")
    b1, b = world.device("b1", "B1", "1")
    c1 = world.core("c1", w0, (a["1"], b["1"]), 1)
    block = world.block(w0)
    world.box(block, w0, BoxKind.CABLE, (2 * G, 6 * G, 6 * G, 5 * G))
    world.end(block, a1, TOP, EndStyle.SOLID, ((a["1"], CELLS[0]),))
    world.end(block, b1, BOTTOM, EndStyle.SOLID, ((b["1"], CELLS[0]),))
    world.wire(block, c1, CELLS[0])
    return world.model(), cable_block_key(None, w0)


def _external() -> tuple[Model, str, str]:
    """Cable `W3` in unit `top` from `N1` (top row) to external `+EXT-M1`; the two readings.

    The absolute block draws `M1` dashed (CD10); the unit's block, solid.
    """
    world = World()
    top = world.unit("top")
    ext = world.location("EXT")
    w3 = world.cable("w3", "W3", ("BK",), unit=top)
    n1, n = world.device("n1", "N1", "1", unit=top)
    m1, m = world.device("m1", "M1", "1", external_at=ext)
    c1 = world.core("c1", w3, (n["1"], m["1"]), 1)
    for unit, style in ((None, EndStyle.DASHED), (top, EndStyle.SOLID)):
        block = world.block(w3, unit=unit)
        world.box(block, w3, BoxKind.CABLE, (2 * G, 6 * G, 6 * G, 5 * G))
        world.end(block, n1, TOP, EndStyle.SOLID, ((n["1"], CELLS[0]),))
        world.end(block, m1, BOTTOM, style, ((m["1"], CELLS[0]),))
        world.wire(block, c1, CELLS[0])
    model = world.model()
    return model, cable_block_key(None, w3), cable_block_key(top, w3)


def _nested() -> tuple[Model, str]:
    """The same cable in unit `nested`, whose reading blanks external `M1` (CD11)."""
    world = World()
    top = world.unit("top")
    nested = world.unit("nested", parent=top)
    ext = world.location("EXT")
    w3 = world.cable("w3", "W3", ("BK",), unit=nested)
    n1, n = world.device("n1", "N1", "1", unit=nested)
    m1, m = world.device("m1", "M1", "1", external_at=ext)
    c1 = world.core("c1", w3, (n["1"], m["1"]), 1)
    block = world.block(w3, unit=nested)
    world.box(block, w3, BoxKind.CABLE, (2 * G, 6 * G, 6 * G, 5 * G))
    world.end(block, n1, TOP, EndStyle.SOLID, ((n["1"], CELLS[0]),))
    world.end(block, m1, BOTTOM, EndStyle.BLANK, ())
    world.wire(block, c1, CELLS[0], stub_b=True)
    return world.model(), cable_block_key(nested, w3)


def test_a_two_cable_harness_block_has_one_dashed_rect_around_two_solid_cable_rects() -> None:
    """Acceptance 7: the harness box record draws dashed, each cable box solid, harness outside."""
    model, key, _ = _pair()
    root = _parse(cable_blocks(model)[key])
    (harness,) = _of(root, "rect", "harness-box")
    cables = _of(root, "rect", "cable-box")
    assert harness.get(DASH) is not None
    assert len(cables) == 2
    assert all(c.get(DASH) is None for c in cables)
    assert [e.get(DASH) for e in _of(root, "rect", "end-box")] == [None, None]
    inner = [Decimal(c.get("x") or 0) for c in cables]
    assert Decimal(harness.get("x") or 0) < min(inner)
    right = max(Decimal(c.get("x") or 0) + Decimal(c.get("width") or 0) for c in cables)
    assert Decimal(harness.get("x") or 0) + Decimal(harness.get("width") or 0) > right
    assert "-WH2" in _texts(root, "heading")


def test_a_lone_cable_block_with_no_harness_box_has_no_dashed_rect() -> None:
    """Acceptance 7: render draws no dashed box unless a `HARNESS` box record exists."""
    model, key = _lone()
    root = _parse(cable_blocks(model)[key])
    (cable,) = _of(root, "rect", "cable-box")
    assert cable.get(DASH) is None
    assert _texts(root, "heading") == ["-WH1"]
    assert _of(root, "rect", "harness-box") == []
    assert [e for e in root.iter() if e.get(DASH) is not None] == []


def test_core_texts_have_single_spaces_and_the_heading_says_shielded() -> None:
    """Acceptance 6: `5`-style core with no colour and no label, the label after the colour."""
    model, key, _ = _pair()
    root = _parse(cable_blocks(model)[key])
    assert _texts(root, "core") == ["1 BK1 no. 1", "2", "1 BN"]
    assert _texts(root, "heading") == ["-WH2", "-WH2-W1, shielded, 3000 mm", "-WH2-W2"]


def test_each_pin_cell_has_its_marking_and_a_divider_between_neighbours() -> None:
    """A top and a bottom end of three pins: six markings, two dividers per end."""
    model, key, _ = _pair()
    root = _parse(cable_blocks(model)[key])
    assert _texts(root, "pin") == ["1", "2", "3", "1", "2", "3"]
    dividers = [Decimal(d.get("x1") or 0) for d in _of(root, "line", "pin-cell")]
    edges = [Decimal(_mm(x)) for x in (4 * G, 6 * G) * 2]
    assert sorted(dividers) == sorted(edges)


def test_the_block_is_sized_and_scaled_by_its_own_sheet_module() -> None:
    """Q5: a block on a sheet of module 2 mm lands every record coordinate at `g * 2 / 8` mm."""
    model, key, _ = _pair(module=Decimal(2))
    root = _parse(cable_blocks(model)[key])
    two = Decimal(2)
    (harness,) = _of(root, "rect", "harness-box")
    assert [harness.get(a) for a in ("x", "y", "width", "height")] == [
        _mm(G, two),
        _mm(5 * G, two),
        _mm(8 * G, two),
        _mm(7 * G, two),
    ]
    wires = _of(root, "polyline", "core")
    assert sorted(w.get("points") or "" for w in wires) == sorted(
        f"{_mm(x, two)},{_mm(a, two)} {_mm(x, two)},{_mm(b, two)}"
        for x in CELLS
        for a, b in ((4 * G, 6 * G), (11 * G, 13 * G))
    )
    texts = _of(root, "text", "core")
    font = Decimal(8) * two / 8
    assert sorted(_axis(t, font) for t in texts) == sorted(Decimal(_mm(x, two)) for x in CELLS)
    assert root.get("width") == f"{Decimal(_mm(10 * G, two)) + Decimal('0.25')}mm"
    house = _parse(cable_blocks(_pair()[0])[key])
    assert _of(house, "rect", "harness-box")[0].get("x") == _mm(G)
    assert _mm(G) != _mm(G, two)


def test_an_external_end_is_dashed_and_by_others_in_the_absolute_reading_only() -> None:
    """Acceptance 8: `+EXT-M1 (by others)` on a dashed end box; plain and solid in a unit's."""
    model, absolute, in_unit = _external()
    blocks = cable_blocks(model)
    assert set(blocks) == {absolute, in_unit}
    outer = _parse(blocks[absolute])
    inner = _parse(blocks[in_unit])
    (solid,) = _of(outer, "rect", "end-box")
    assert solid.get(DASH) is None
    edges = _of(outer, "line", "end-box")
    assert len(edges) == 4
    assert all(e.get(DASH) is not None for e in edges)
    assert _texts(outer, "end-label") == ["-N1", "+EXT-M1 (by others)"]
    assert [e.get(DASH) for e in _of(inner, "rect", "end-box")] == [None, None]
    assert _of(inner, "line", "end-box") == []
    assert _texts(inner, "end-label") == ["-N1", "+EXT-M1"]


def test_the_end_label_stands_above_a_top_box_and_below_a_bottom_one() -> None:
    """The label's baseline is above the top box's rect and below the bottom box's dashed edges."""
    model, absolute, _ = _external()
    root = _parse(cable_blocks(model)[absolute])
    (top_rect,) = _of(root, "rect", "end-box")
    bottom_edge = max(Decimal(e.get("y1") or 0) for e in _of(root, "line", "end-box"))
    top_label, bottom_label = _by_y(_of(root, "text", "end-label"))
    assert Decimal(top_label.get("y") or 0) < Decimal(top_rect.get("y") or 0)
    assert Decimal(bottom_label.get("y") or 0) > bottom_edge


def test_a_dashed_end_boxs_top_and_bottom_edges_start_at_the_same_left_corner() -> None:
    """Both horizontal edges run left to right from the box's left x: their dashes are in phase."""
    model, absolute, _ = _external()
    root = _parse(cable_blocks(model)[absolute])
    flat = [e for e in _of(root, "line", "end-box") if e.get("y1") == e.get("y2")]
    assert len(flat) == 2
    assert flat[0].get("x1") == flat[1].get("x1") == _mm(2 * G)
    assert all(Decimal(e.get("x1") or 0) < Decimal(e.get("x2") or 0) for e in flat)


def _two_pin_by_others() -> tuple[Model, str]:
    """Cable `W5` of two cores from `A1` to a two-pin end `B1` drawn dashed (by others)."""
    world = World()
    w5 = world.cable("w5", "W5", ("BK", "BN"))
    a1, a = world.device("a1", "A1", "1", "2")
    b1, b = world.device("b1", "B1", "1", "2")
    cores = [world.core(f"c{n}", w5, (a[str(n)], b[str(n)]), n) for n in (1, 2)]
    block = world.block(w5)
    world.box(block, w5, BoxKind.CABLE, (2 * G, 6 * G, 6 * G, 5 * G))
    world.end(block, a1, TOP, EndStyle.SOLID, tuple(zip(a.values(), CELLS, strict=False)))
    world.end(block, b1, BOTTOM, EndStyle.DASHED, tuple(zip(b.values(), CELLS, strict=False)))
    for conductor, x in zip(cores, CELLS, strict=False):
        world.wire(block, conductor, x)
    return world.model(), cable_block_key(None, w5)


def test_a_by_others_boxs_divider_has_its_outlines_dash_pattern_and_phase() -> None:
    """A dashed two-pin end's divider runs top down from the box's top, as its side edges do."""
    model, key = _two_pin_by_others()
    root = _parse(cable_blocks(model)[key])
    sides = [e for e in _of(root, "line", "end-box") if e.get("x1") == e.get("x2")]
    (divider,) = [d for d in _of(root, "line", "pin-cell") if d.get("y1") == _mm(13 * G)]
    assert len(sides) == 2
    for side in sides:
        assert divider.get(DASH) == side.get(DASH) is not None
        assert (divider.get("y1"), divider.get("y2")) == (side.get("y1"), side.get("y2"))


def _axis(text: ET.Element, font: Decimal) -> Decimal:
    """The x the turned text's em box is centred on, from its baseline x."""
    return (Decimal(text.get("x") or 0) + font * (Decimal("0.5") - ASCENT_RATIO)).quantize(
        Decimal("0.000001")
    )


def _level_middle(text: ET.Element, font: Decimal) -> Decimal:
    """The y the level text's em box is centred on, from its baseline y."""
    return (Decimal(text.get("y") or 0) - font * ASCENT_RATIO + font / 2).quantize(
        Decimal("0.000001")
    )


def _mixed() -> tuple[Model, str]:
    """Cable `W6`: core 1 `A1.1` to `B1.1`, core 2 a row link `A1.2` to `A1.3` (CD5 at L1)."""
    world = World()
    harness = world.item("wh6", "WH6")
    w6 = world.cable("w6", "W6", ("BK", "BN"), parent=harness)
    a1, a = world.device("a1", "A1", "1", "2", "3")
    b1, b = world.device("b1", "B1", "1")
    c1 = world.core("c1", w6, (a["1"], b["1"]), 1)
    c2 = world.core("c2", w6, (a["2"], a["3"]), 2)
    block = world.block(w6)
    world.box(block, w6, BoxKind.CABLE, (2 * G, 6 * G, 6 * G, 5 * G))
    world.end(block, a1, TOP, EndStyle.SOLID, tuple(zip(a.values(), CELLS, strict=True)))
    world.end(block, b1, BOTTOM, EndStyle.SOLID, ((b["1"], CELLS[0]),))
    world.wire(block, c1, CELLS[0])
    world.link(block, c2, (CELLS[1], CELLS[2]))
    return world.model(), cable_block_key(None, w6)


def _jumper() -> tuple[Model, str]:
    """Cable `W7`, two row-link cores on end `A1` (CD-H8 at V1): no core reaches the box."""
    world = World()
    harness = world.item("wh7", "WH7")
    w7 = world.cable("w7", "W7", ("BK", "BN"), parent=harness)
    a1, a = world.device("a1", "A1", "1", "2", "3", "4")
    c1 = world.core("c1", w7, (a["1"], a["2"]), 1)
    c2 = world.core("c2", w7, (a["3"], a["4"]), 2)
    block = world.block(w7)
    xs = (*CELLS, 9 * G)
    world.box(block, w7, BoxKind.CABLE, (2 * G, 6 * G, 8 * G, 5 * G))
    world.end(block, a1, TOP, EndStyle.SOLID, tuple(zip(a.values(), xs, strict=True)), width=8 * G)
    world.link(block, c1, xs[:2])
    world.link(block, c2, xs[2:])
    return world.model(), cable_block_key(None, w7)


def test_a_row_links_core_text_is_level_and_centred_on_its_point() -> None:
    """CD8 L1: the link's `<text>` has no `transform`, is anchored middle, and its x and vertical
    middle are `text_x` and `text_y` in mm, not turned along a wire.

    Probe: `_wire` always calling `upward_text`.
    """
    model, key = _mixed()
    root = _parse(cable_blocks(model)[key])
    (text,) = [t for t in _of(root, "text", "core") if t.text == "2 BN"]
    assert text.get("transform") is None
    assert text.get("text-anchor") == "middle"
    assert text.get("x") == _mm(6 * G)
    assert _level_middle(text, Decimal("2.5")) == Decimal(_mm(5 * G))


def test_a_non_link_core_beside_a_link_keeps_its_turned_text() -> None:
    """The positive control: in the same block the through core's text is still `rotate(-90 ...)`.

    Probe: `_wire` drawing every core's text level.
    """
    model, key = _mixed()
    root = _parse(cable_blocks(model)[key])
    (text,) = [t for t in _of(root, "text", "core") if t.text == "1 BK"]
    assert (text.get("transform") or "").startswith("rotate(-90 ")
    assert text.get("y") == _mm(7 * G)


def test_a_row_link_draws_its_straight_run_as_a_three_point_and_a_two_point_polyline() -> None:
    """The records' `run_a` (pin, corner, corner) and `run_b` (pin, corner) are both drawn.

    Probe: `_wire` skipping `run_a`.
    """
    model, key = _mixed()
    root = _parse(cable_blocks(model)[key])
    runs = [w.get("points") or "" for w in _of(root, "polyline", "core")]
    x1, x2, top, corner = (_mm(v) for v in (CELLS[1], CELLS[2], 4 * G, 5 * G))
    first = f"{x1},{top} {x1},{corner} {x2},{corner}"
    second = f"{x2},{top} {x2},{corner}"
    assert [len(r.split()) for r in runs].count(3) == 1
    assert runs[runs.index(first) + 1] == second
    assert len(runs) == 4


def test_a_cable_of_only_row_links_draws_the_end_row_the_links_and_an_empty_cable_box() -> None:
    """CD-H8 at V1: end box with pin cells, polylines, level texts, cable box with its heading;
    no core text stands inside the box.

    Probe: `row_links` replaced by `()` in cables.py.
    """
    model, key = _jumper()
    root = _parse(cable_blocks(model)[key])
    (end,) = _of(root, "rect", "end-box")
    (box,) = _of(root, "rect", "cable-box")
    assert _texts(root, "pin") == ["1", "2", "3", "4"]
    assert len(_of(root, "line", "pin-cell")) == 3
    assert [len((w.get("points") or "").split()) for w in _of(root, "polyline", "core")] == [
        3,
        2,
    ] * 2
    texts = _of(root, "text", "core")
    assert sorted(t.text or "" for t in texts) == ["1 BK", "2 BN"]
    assert all(t.get("transform") is None for t in texts)
    assert _texts(root, "heading") == ["-WH7"]
    assert Decimal(end.get("y") or 0) < Decimal(box.get("y") or 0)
    low, high = (
        Decimal(box.get("y") or 0),
        Decimal(box.get("y") or 0) + Decimal(box.get("height") or 0),
    )
    assert [t for t in texts if low <= Decimal(t.get("y") or 0) <= high] == []


def test_a_core_text_is_turned_and_centred_on_its_wires_axis() -> None:
    """N1, render-0008: the core text reads upward (`rotate(-90 x y)`), its middle on the wire's
    axis and on `text_y`, not beside the wire.

    Probe: `upward_text` drawing the text flat.
    """
    model, key, _ = _pair()
    root = _parse(cable_blocks(model)[key])
    texts = _of(root, "text", "core")
    assert {t.get("text-anchor") for t in texts} == {"middle"}
    assert {t.get("transform") for t in texts} == {
        f"rotate(-90 {t.get('x')} {_mm(7 * G)})" for t in texts
    }
    assert {t.get("y") for t in texts} == {_mm(7 * G)}
    assert sorted(_axis(t, Decimal("2.5")) for t in texts) == sorted(Decimal(_mm(x)) for x in CELLS)


def test_a_blank_end_draws_no_box_and_no_text_only_the_wire_stub() -> None:
    """Acceptance 9: in the nested unit's reading `M1` is blank; `N1`'s box and the wire remain."""
    model, key = _nested()
    root = _parse(cable_blocks(model)[key])
    (box,) = _of(root, "rect", "end-box")
    assert box.get("y") == _mm(2 * G)
    assert _texts(root, "end-label") == ["-N1"]
    assert _texts(root, "pin") == ["1"]
    runs = [w.get("points") for w in _of(root, "polyline", "core")]
    assert runs == [
        f"{_mm(CELLS[0])},{_mm(4 * G)} {_mm(CELLS[0])},{_mm(6 * G)}",
        f"{_mm(CELLS[0])},{_mm(11 * G)} {_mm(CELLS[0])},{_mm(12 * G)}",
    ]
    assert _of(root, "line", "pin-cell") == []


def test_the_keys_are_the_block_keys_and_two_calls_give_the_same_svg() -> None:
    """The mapping is keyed by `cable_block_key` of each reading, and is deterministic."""
    model, absolute, in_unit = _external()
    first = cable_blocks(model)
    assert set(first) == {absolute, in_unit}
    assert "~" in in_unit
    assert "~" not in absolute
    assert cable_blocks(model) == first


def test_a_model_with_no_cable_block_has_no_svg() -> None:
    """No `layout.cable_block` record, no entry."""
    assert len(cable_blocks(World().model())) == 0


@pytest.mark.parametrize("module", [Decimal(2), Decimal("2.5")])
def test_every_emitted_rect_corner_is_a_whole_grid_position(module: Decimal) -> None:
    """Acceptance 5 at the render edge: each box x and y converts back to a wiring-grid multiple."""
    model, key, _ = _pair(module=module)
    root = _parse(cable_blocks(model)[key])
    step = module * G / 8
    for rect in root.iter(SVG + "rect"):
        for attr in ("x", "y"):
            assert Decimal(rect.get(attr) or 0) % step == 0


def test_a_cell_two_cores_land_on_has_its_divider_at_its_own_left_edge() -> None:
    """CD6 at P1: the second pin holds two places (4G wide), its centre at 6G, its edge at 4G.

    Probe: take the divider half a pitch from the centre, whatever the places; it lands at 5G.
    """
    world = World()
    w0 = world.cable("w0", "W0", ("BK", "BN", "GY"))
    a1, a = world.device("a1", "A1", "1", "2")
    b1, b = world.device("b1", "B1", "1", "2", "3")
    c1 = world.core("c1", w0, (a["1"], b["1"]), 1)
    c2 = world.core("c2", w0, (a["2"], b["2"]), 2)
    c3 = world.core("c3", w0, (a["2"], b["3"]), 3)
    block = world.block(w0)
    world.box(block, w0, BoxKind.CABLE, (2 * G, 6 * G, 6 * G, 5 * G))
    world.end(
        block, a1, TOP, EndStyle.SOLID, ((a["1"], 3 * G), (a["2"], 6 * G, 4 * G)), width=6 * G
    )
    world.end(block, b1, BOTTOM, EndStyle.SOLID, tuple(zip(b.values(), CELLS, strict=True)))
    for conductor, x in zip((c1, c2, c3), (3 * G, 5 * G, 7 * G), strict=True):
        world.wire(block, conductor, x)
    root = _parse(cable_blocks(world.model())[cable_block_key(None, w0)])
    top = [d for d in _of(root, "line", "pin-cell") if d.get("y1") == _mm(2 * G)]
    assert [Decimal(d.get("x1") or 0) for d in top] == [Decimal(_mm(4 * G))]
