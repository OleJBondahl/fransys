"""Link markers: stub, arrow box and text (D8's marker part, decision layout-0038)."""

import dataclasses
import re
import xml.etree.ElementTree as ET
from decimal import Decimal

import pytest
from fransys_render import _markers, pages
from fransys_render._junctions import _marker_stub
from fransys_render._markers import (
    ASCENT_RATIO,
    arrow_polygon,
    box_origin,
    geometry_facing,
    marker_facing,
    markers_group,
    markers_on_page,
    stub_end,
    text_glyph,
)
from fransys_render._numbers import format_decimal, grid_to_mm
from fransys_render._symbol_geometry import oriented_symbol
from graphical_symbols import Direction

from electrical_symbols import GENERIC_BOX_KEY
from fransys_model.derive.drawing_text import marker_text as model_marker_text
from fransys_model.kernel import Draft, Origin, evolve, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Orientation,
    Page,
    PageRole,
    PlacementView,
    SheetFormat,
    Side,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole

_ORIGIN = Origin(
    file="packages/fransys-render/tests/test_markers.py", line=1, note="invented marker"
)

_SVG_NS = "{http://www.w3.org/2000/svg}"

# The named `layout.link_marker` count of each golden (the regenerated layout engine's own
# facts, probed from the goldens; literal numbers, never `len(...)` of the collection they
# guard): the wide golden carries 8, the narrow golden 9, the two-location golden 11 (four of
# them off stubs; a reference and a stub on one port are one record, layout-0053). Step 5
# (layout-0093): M12 makes a wire that turns back round its device a reference pair, and every
# marker is a turned box (M1), its stored width and height the short and long side.
_WIDE_MARKER_COUNT = 6
_NARROW_MARKER_COUNT = 8
_TWO_LOCATION_MARKER_COUNT = 8


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
    """A bare item/function/port, one pin (mirrors `test_routes_junctions.py:_pin`).

    One port per function: `generic_box`'s port count and geometry come from
    `indexes.ports_by_function`, so a function with exactly one port gives a symbol
    with exactly one port, at a known module-unit offset (`generic_box.py`:
    `(0, -2.0)`, N-facing) -- the fixed geometry the hand-built tests below rely on.
    """
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


def _placement(key_part, *, function, page, x, y):
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
        symbol=GENERIC_BOX_KEY,
        library_version="test",
        produced_by="test",
    )


def _marker_id(key_part):
    return make_id(LinkMarker, ("link_marker", key_part))


def _marker(key_part, *, page, port, at, partner_key_part, width=13, height=8):  # noqa: PLR0913 -- two more, both defaulted, for the width/height fields (model-0037)
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


def _one_svg(model):
    svgs = pages(model)
    assert len(svgs) == 1
    return next(iter(svgs.values()))


# --- 1. Every real marker in the wide and narrow goldens draws a stub, box and text -----------


@pytest.mark.parametrize(
    ("fixture_name", "expected_count", "origin_mm"),
    [
        # The wide golden carries no sheet-format record: its A3 default sheet puts the
        # content origin at 5 mm (probed: the marker at grid x=248 draws at 5 + 248*2.5/8 =
        # 82.5 mm); the narrow golden carries its own sheet with content_x_mm = content_y_mm = 10.
        ("cabinet_laid_out", _WIDE_MARKER_COUNT, 5),
        ("cabinet_narrow_laid_out", _NARROW_MARKER_COUNT, 10),
    ],
)
def test_all_real_markers_draw_a_stub_box_and_text(
    request, fixture_name, expected_count, origin_mm
):
    model = request.getfixturevalue(fixture_name)
    markers = layout_of(model, LinkMarker)
    assert len(markers) == expected_count

    total_on_pages = sum(
        len(markers_on_page(model, page)) for page in layout_of(model, Page).values()
    )
    assert total_on_pages == expected_count

    rendered = "".join(pages(model).values())
    assert rendered.count('<polyline class="marker"') == expected_count  # one box per marker

    def mm(grid):  # module 2.5 mm
        return format_decimal(grid_to_mm(origin_mm, grid, Decimal("2.5")))

    for marker in markers.values():
        # The stub: a `<line>` from the port one WIRING_GRID step (plus any `stub` extension)
        # out along the facing. Other `<line class="marker">` elements exist, so the count
        # of lines is not asserted, only each marker's own stub.
        facing = marker_facing(model, marker)
        step = 8 + marker.stub_extra
        stub = (
            f'<line class="marker" x1="{mm(marker.x)}" y1="{mm(marker.y)}" '
            f'x2="{mm(marker.x + facing.dx * step)}" y2="{mm(marker.y + facing.dy * step)}"/>'
        )
        # A harness line's stub draws no stub: its line runs on to the box (layout-0158).
        assert (stub in rendered) is not _markers._ends_a_line(model, marker)
        # The text: no XML metacharacters in a real marker's text (`/1.3`, `-X2:1/1.5`).
        # A star reference wraps to several lines, each its own `<text>`.
        for line in model_marker_text(model, marker).split("\n"):
            assert line in rendered


def _marker_by_id_prefix(markers, prefix):
    (marker,) = (m for m in markers.values() if m.id.value.startswith(prefix))
    return marker


# --- 2. Facing determines stub/box direction: two real markers, N and S, hand-computed ---------


def test_facing_determines_stub_and_box_direction(cabinet_narrow_laid_out):
    markers = layout_of(cabinet_narrow_laid_out, LinkMarker)
    # The two narrow-golden markers with no `ext` (no `star`, `stub` or `box_x`): the plain
    # stub-and-box case, so the stub runs exactly one WIRING_GRID step.
    north_marker = _marker_by_id_prefix(markers, "87cd07ed")
    south_marker = _marker_by_id_prefix(markers, "de1d5a5f")
    # Both draw on the narrow golden's own sheet (content_x_mm=10, content_y_mm=10,
    # module_mm=2.5), proven by direct inspection of the golden (a probe script, not this
    # package's own code).
    # The columns narrowed when the top-level tags shrank to the item designation (D12,
    # layout-0066) and the image lane width changed (D7, layout-0064): both markers moved left,
    # N from x=432 to 376 and S from x=168 to 104 (regenerated goldens, 3c8bc60); the top room
    # grew by one M (TOP_HEADROOM_LANES 2 -> 3, layout-0048), so every y is 8 G lower. LD3 (c)'s
    # fixed reference box (decision layout-0089) then widened the contact-image room the column
    # is packed against (`images.widest_where`, decision layout-0091), moving N to x=392; S sits
    # in a different lane and is unaffected. Step 5 (layout-0093, S17's top room and the M1 turned
    # boxes) then put the first row 32 G lower: N at y=80, S at y=112. layout-0104's frame gap
    # then moved the page right by one grid (a text stood at x=3): N at x=400, S at x=120.
    assert (north_marker.x, north_marker.y) == (400, 80)
    assert (south_marker.x, south_marker.y) == (120, 112)
    for plain in (north_marker, south_marker):
        assert plain.stub_extra == 0
        assert plain.box_x is None
        assert plain.via_x is None

    svg = "".join(pages(cabinet_narrow_laid_out).values())

    # N facing (decision layout-0038): stub runs from the port to `(mx, my - WIRING_GRID)`.
    # grid_to_mm(10, 400, 2.5) = 10 + 400*2.5/8 = 135 ; grid_to_mm(10, 80, 2.5) = 35 ;
    # grid_to_mm(10, 80-8, 2.5) = grid_to_mm(10, 72, 2.5) = 32.5.
    north_stub = '<line class="marker" x1="135" y1="35" x2="135" y2="32.5"/>'
    assert north_stub in svg

    # S facing: stub runs from the port to `(mx, my + WIRING_GRID)`.
    # grid_to_mm(10, 120, 2.5) = 10 + 120*2.5/8 = 47.5 for x, grid_to_mm(10, 112, 2.5) = 45 for y ;
    # grid_to_mm(10, 112+8, 2.5) = grid_to_mm(10, 120, 2.5) = 47.5.
    south_stub = '<line class="marker" x1="47.5" y1="45" x2="47.5" y2="47.5"/>'
    assert south_stub in svg

    # The two stubs run opposite ways along y (N: y2 < y1 ; S: y2 > y1) -- the facing
    # really does flip the geometry, not just the absolute position: 32.5 < 35 (north
    # steps up) and 47.5 > 45 (south steps down).


# --- 3. Text is escaped and centred: the element-building function, unit-tested directly -------


def test_text_glyph_escapes_and_centres():
    raw_text = 'A&<B>"C'
    glyph = text_glyph(raw_text, Decimal(30), Decimal(15), Decimal("2.5"))

    assert 'class="label"' in glyph
    assert 'text-anchor="middle"' in glyph
    assert 'x="30"' in glyph
    assert 'y="15"' in glyph
    assert 'font-size="2.5"' in glyph
    assert "<B>" not in glyph  # the raw `<` is gone: it would otherwise open a bogus element
    assert "&amp;" in glyph
    assert "&lt;" in glyph
    assert "&gt;" in glyph

    # Round-trips through XML parsing back to the original text, `_labels.py`'s own proof.
    wrapped = f'<root xmlns="http://www.w3.org/2000/svg">{glyph}</root>'
    root = ET.fromstring(wrapped)  # noqa: S314 -- parsing our own generated fragment
    text_element = root.find(f"{_SVG_NS}text")
    assert text_element is not None
    assert text_element.text == raw_text


# --- 4. Ordering: multiple markers on one page draw in `id` order (D11) ------------------------


def test_markers_are_ordered_by_id():
    drawing_set = _drawing_set("t4")
    sheet = _sheet_format("t4")
    page = _page("t4", drawing_set=drawing_set, sheet_format=sheet)

    pins = [_pin(f"t4-{n}", f"K{n}") for n in range(4)]
    placements = [
        _placement(f"t4-{n}", function=fn, page=page, x=n * 100, y=100)
        for n, (_item, fn, _port) in enumerate(pins)
    ]
    # Each function has exactly one N-facing port at module offset (0, -2.0) -> grid (0, -16).
    markers = [
        _marker(
            f"t4-{n}",
            page=page,
            port=port,
            at=(n * 100, 100 - 16),
            partner_key_part=f"t4-{n - 1 if n % 2 else n + 1}",
        )
        for n, (_item, _fn, port) in enumerate(pins)
    ]

    records = [rec for triple in pins for rec in triple] + placements + markers
    model = _model(drawing_set, sheet, page, *records)
    svg = _one_svg(model)

    ordered_markers = sorted(layout_of(model, LinkMarker).values(), key=lambda m: m.id)
    expected_count = 4
    assert len(ordered_markers) == expected_count

    def _stub_marker(marker):
        x1 = format_decimal(grid_to_mm(sheet.content_x_mm, marker.x, sheet.module_mm))
        y1 = format_decimal(grid_to_mm(sheet.content_y_mm, marker.y, sheet.module_mm))
        return f'<line class="marker" x1="{x1}" y1="{y1}"'

    positions = [svg.index(_stub_marker(marker)) for marker in ordered_markers]
    assert positions == sorted(positions)


# --- 5. The stub touches the box with no gap, no overlap (hand-computed, render agrees) -------


@pytest.mark.parametrize(
    ("prefix", "at", "facing", "hand_box_and_stub_end"),
    [
        # N facing (decision layout-0038): box.x = mx - width//2 = 400 - 12//2 = 394 ;
        # box.y = my - WIRING_GRID - height = 80 - 8 - 42 = 30 ; stub end (mx, my - 8) = (400, 72) ;
        # the box's near edge is its bottom edge, centred on the port:
        # (box_x + width//2, box_y + height) = (394+6, 30+42) = (400, 72).
        ("87cd07ed", (400, 80), Direction.N, ((394, 30), (400, 72))),
        # S facing: box.x = 120 - 12//2 = 114 ; box.y = my + WIRING_GRID = 112 + 8 = 120 ;
        # stub end (mx, my + 8) = (120, 120) ; the near edge is the top edge:
        # (box_x + width//2, box_y) = (114+6, 120) = (120, 120).
        ("de1d5a5f", (120, 112), Direction.S, ((114, 120), (120, 120))),
    ],
)
def test_stub_touches_box_near_edge_exactly(
    cabinet_narrow_laid_out, prefix, at, facing, hand_box_and_stub_end
):
    box, hand_stub_end = hand_box_and_stub_end
    marker = _marker_by_id_prefix(layout_of(cabinet_narrow_laid_out, LinkMarker), prefix)
    assert (marker.x, marker.y) == at
    # 12 G wide, 42 G tall: a turned box (S20 M1). Its length is LD3 (c)'s fixed reference box
    # width for this sheet format (decision layout-0089, `reference_box_width`), never measured
    # from the marker's own text; its width is `text_height` (8 G) plus `2 * marker_padding`
    # (2 G, decision layout-0043's amendment).
    assert (marker.width, marker.height) == (12, 42)  # the golden's own reserved size
    assert marker.vertical
    # no stub extension, no shared box, no via: the plain WIRING_GRID step
    assert marker.stub_extra == 0
    assert marker.box_x is None
    assert marker.via_x is None
    width, height = marker.width, marker.height
    box_x, box_y = box

    # The box's near edge, hand-computed from `box` (N: bottom edge, S: top edge).
    near_y = box_y + height if facing == Direction.N else box_y
    box_near_edge = (box_x + width // 2, near_y)
    assert hand_stub_end == box_near_edge

    # Render agrees with the hand values: facing, stub end, box origin and arrow tip.
    assert marker_facing(cabinet_narrow_laid_out, marker) == facing
    assert stub_end(marker, facing) == hand_stub_end
    assert box_origin(marker, facing) == box
    assert arrow_polygon(marker, facing)[0] == hand_stub_end


# --- 6. The drawn box's size equals the record's own stored size, at several widths -----------


def test_drawn_box_size_equals_the_records_stored_size(
    cabinet_laid_out, cabinet_narrow_laid_out, cabinet_two_location_laid_out
):
    """model-0037/render-0001: the arrow box's bounding size is exactly `marker.width/height`.

    `arrow_polygon`'s tip and pulled-in corners never widen or narrow its own bounding
    box past the near-edge/top/far-edge corners it shares with a plain rectangle, so this
    box's own bounding size is a tight proxy for the drawn box render actually emits (the
    same vertices `_box_glyph` turns into the `<polyline>`; a box moved sideways by layout-0054
    is drawn as a plain rectangle of the same size). Three goldens, several stored widths --
    since LD3 (c) (decision layout-0089) the wide and narrow goldens' every marker (pair and
    star reference alike) shares one fixed length, 42 G; the two-location golden adds its own
    off stubs, measured from text and longer, {42, 47, 50, 51} G (decision layout-0043's
    amendment, D4 excludes an off stub from the fixed box unless merged with a reference) --
    so this cannot pass by coincidence of one fixed size: each golden's exact set of stored
    widths (the turned boxes' short sides: one line 12 G, two lines 20 G;
    C2, model-0139: three targets or more print one line) and of stored heights
    (their lengths) is asserted.
    """
    # RR-O5: the two-location golden's reference boxes are sized from the longest position form
    # (`#n-+<location>...p<set>.<page>:<cell>`), 56 G, no longer the fixed 42 G.
    goldens = (
        (cabinet_laid_out, _WIDE_MARKER_COUNT, {12, 20, 43}, {12, 42}),
        (cabinet_narrow_laid_out, _NARROW_MARKER_COUNT, {12, 43}, {12, 42}),
        (cabinet_two_location_laid_out, _TWO_LOCATION_MARKER_COUNT, {12, 20, 28}, {47, 51, 56}),
    )
    # HL15-HL18 (layout-0154): the 43 x 12 G boxes are the OFF line stubs of the harness lines.
    checked = 0
    line_stubs = 0
    for model, expected_count, expected_widths, expected_heights in goldens:
        markers = layout_of(model, LinkMarker)
        assert len(markers) == expected_count  # this golden's own known, named count
        assert {m.width for m in markers.values()} == expected_widths  # and its stored sides
        assert {m.height for m in markers.values()} == expected_heights
        for marker in markers.values():
            facing = marker_facing(model, marker)
            vertices = arrow_polygon(marker, facing)
            # a box moved sideways (box_x set) keeps its stub tip off the box: measure the corners
            xs = [x for x, _y in (vertices[1:] if marker.box_x is not None else vertices)]
            ys = [y for _x, y in vertices]
            drawn_width = max(xs) - min(xs)
            drawn_height = max(ys) - min(ys)
            assert drawn_width == marker.width
            assert drawn_height == marker.height
            checked += 1
            line_stubs += "line_stub" in str(marker.key)
    assert line_stubs == 3
    assert checked == _WIDE_MARKER_COUNT + _NARROW_MARKER_COUNT + _TWO_LOCATION_MARKER_COUNT


# --- 7. The typed marker fields: stub_extra, box_x/lead, via_x/via_y (F1 part 5) ---------------

_PORT_UP = 16  # the one N-facing port of a `_pin` sits 2 M = 16 G above its placement origin


def _pair_model(*, first_changes, at=(100, 100)):
    """Two one-port functions on two pages, a marker on each; page 1's marker takes
    `first_changes` (typed `LinkMarker` fields). Returns `(model, sheet, page_1, first)`.
    """
    drawing_set = _drawing_set("t7")
    sheet = _sheet_format("t7")
    page_1 = _page("t7-1", drawing_set=drawing_set, number=1, sheet_format=sheet)
    page_2 = _page("t7-2", drawing_set=drawing_set, number=2, sheet_format=sheet)
    pin_1, pin_2 = _pin("t7-1", "K1"), _pin("t7-2", "K2")
    x, y = at
    placements = [
        _placement("t7-1", function=pin_1[1], page=page_1, x=x, y=y),
        _placement("t7-2", function=pin_2[1], page=page_2, x=x, y=y),
    ]
    first = dataclasses.replace(
        _marker("t7-1", page=page_1, port=pin_1[2], at=(x, y - _PORT_UP), partner_key_part="t7-2"),
        **first_changes,
    )
    second = _marker(
        "t7-2", page=page_2, port=pin_2[2], at=(x, y - _PORT_UP), partner_key_part="t7-1"
    )
    records = [*pin_1, *pin_2, *placements, first, second]
    return _model(drawing_set, sheet, page_1, page_2, *records), sheet, page_1, first


def _mm_x(sheet, grid):
    return format_decimal(grid_to_mm(sheet.content_x_mm, grid, sheet.module_mm))


def _mm_y(sheet, grid):
    return format_decimal(grid_to_mm(sheet.content_y_mm, grid, sheet.module_mm))


def test_stub_extra_moves_stub_end_and_box_origin_out_by_that_many_g():
    _, _sheet, _page_1, plain = _pair_model(first_changes={})
    longer = dataclasses.replace(plain, stub_extra=3)
    assert plain.stub_extra == 0
    for facing in (Direction.N, Direction.E):
        (px, py), (lx, ly) = stub_end(plain, facing), stub_end(longer, facing)
        assert (lx - px, ly - py) == (3 * facing.dx, 3 * facing.dy)
        (bpx, bpy), (blx, bly) = box_origin(plain, facing), box_origin(longer, facing)
        assert (blx - bpx, bly - bpy) == (3 * facing.dx, 3 * facing.dy)
    # the arrow's tip is the stub's far end, so the tip moves with it
    assert arrow_polygon(longer, Direction.N)[0] == stub_end(longer, Direction.N)


def test_shared_box_draws_only_at_its_lead():
    # box_x 95: the box (13 G wide) stands over the stub at x=100, one G right of the port-centred
    # place (94), so it is a plain rectangle, no lead (a box beside its stub is the test below)
    model, sheet, page, follower = _pair_model(first_changes={"box_x": 95, "lead": False})
    assert (follower.box_x, follower.lead) == (95, False)
    stub = (
        f'<line class="marker" x1="{_mm_x(sheet, follower.x)}" y1="{_mm_y(sheet, follower.y)}" '
        f'x2="{_mm_x(sheet, follower.x)}" y2="{_mm_y(sheet, follower.y - 8)}"/>'
    )
    assert markers_group(model, page) == stub  # no box, no text

    lead_model, _sheet, _page_1, lead = _pair_model(first_changes={"box_x": 95, "lead": True})
    drawn = markers_group(lead_model, page)
    assert drawn.startswith(stub)
    assert drawn.count("<polyline") == 1
    assert drawn.count("<text") == 1
    box_x, box_y = box_origin(lead, Direction.N)
    assert box_x == 95  # the shared box's own left edge, not the port-centred one
    corner = f"{_mm_x(sheet, box_x)},{_mm_y(sheet, box_y)}"
    assert f'<polyline class="marker" points="{corner} ' in drawn


def test_a_shared_box_beside_its_stub_draws_a_lead_along_its_near_edge():
    """D14 (layout-0054): a box beyond a sibling lane has its stub outside its span. Its outline
    starts at the stub's far end, runs along the near edge to the box's near corner and goes
    round the rectangle (one polyline); a box over its stub is the plain rectangle.

    UNDO: in `_shared_box_glyph` change `if facing.dy and not x <= end_x <= x + w:` to `if False:`.
    """
    model, sheet, page, beside = _pair_model(first_changes={"box_x": 40, "lead": True})
    end_y = beside.y - 8  # the stub's far end, one grid out (N)
    assert beside.x > 40 + beside.width  # the premise: the stub is right of the box
    top, bottom = _mm_y(sheet, end_y - beside.height), _mm_y(sheet, end_y)
    right, left = _mm_x(sheet, 40 + beside.width), _mm_x(sheet, 40)
    outline = [(_mm_x(sheet, beside.x), bottom), (right, bottom), (left, bottom), (left, top)]
    outline += [(right, top), (right, bottom)]  # the near corner nearest the stub, twice
    points = " ".join(f"{px},{py}" for px, py in outline)
    drawn = markers_group(model, page)
    assert f'<polyline class="marker" points="{points}"/>' in drawn
    assert drawn.count("<polyline") == 1  # the lead is part of the box outline
    over_model, _sheet, over_page, _over = _pair_model(first_changes={"box_x": 95, "lead": True})
    assert f'points="{_mm_x(sheet, 95)},' in markers_group(over_model, over_page)  # plain box


def test_via_draws_a_one_grid_east_stub_from_the_via_point():
    # S20 M7: the branch runs to the stub under the box's centre (`box_x` + width // 2 = 208),
    # then a one-grid stub N (via lies above the port) and the box
    model, sheet, page, turned = _pair_model(
        first_changes={"via_x": 200, "via_y": 70, "box_x": 202}
    )
    east_stub = (
        f'<line class="marker" x1="{_mm_x(sheet, 200)}" y1="{_mm_y(sheet, 70)}" '
        f'x2="{_mm_x(sheet, 208)}" y2="{_mm_y(sheet, 70)}"/>'
    )
    up_stub = (
        f'<line class="marker" x1="{_mm_x(sheet, 208)}" y1="{_mm_y(sheet, 70)}" '
        f'x2="{_mm_x(sheet, 208)}" y2="{_mm_y(sheet, 62)}"/>'
    )
    drawn = markers_group(model, page)
    assert drawn.startswith(east_stub + up_stub)
    assert drawn.count("<line") == 2
    assert _marker_stub(model, turned) == ((200, 70), (208, 70))
    # the box is the N-facing one at the branch's end: its tip is the up stub's far end
    assert f'<polyline class="marker" points="{_mm_x(sheet, 208)},{_mm_y(sheet, 62)} ' in drawn
    # without via the stub runs from the port along its facing
    plain_model, _sheet, _page_1, plain = _pair_model(first_changes={})
    assert _marker_stub(plain_model, plain) == ((plain.x, plain.y), (plain.x, plain.y - 8))


# --- 8. The typed placement fields: view, ports, sides (F1 part 5) ------------------------------


def _box_placement(**changes):
    drawing_set = _drawing_set("t8")
    page = _page("t8", drawing_set=drawing_set)
    item, fn, port = _pin("t8", "K1")
    placement = dataclasses.replace(_placement("t8", function=fn, page=page, x=0, y=0), **changes)
    return _model(drawing_set, page, item, fn, port, placement), placement


def test_item_view_ports_and_sides_give_a_generic_box_with_exactly_those_ports():
    model, placement = _box_placement(
        view=PlacementView.ITEM, ports=("f.1", "f.2", "f.3"), sides=(Side.S, Side.N, Side.S)
    )
    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    # generic_box: north ports at y = -2 M, south at +2 M, each side left to right at 2 M
    assert {port.id: (port.position.x, port.position.y) for port in symbol.ports} == {
        "f.1": (0.0, 2.0),
        "f.2": (0.0, -2.0),
        "f.3": (2.0, 2.0),
    }


def test_placement_without_ports_keeps_the_derived_ports():
    model, placement = _box_placement()
    assert placement.view is PlacementView.FUNCTION
    assert placement.ports == ()
    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    assert [port.id for port in symbol.ports] == ["1"]  # the function's own model port


def test_item_view_without_ports_lists_every_port_of_the_items_functions():
    model, placement = _box_placement(view=PlacementView.ITEM)
    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    assert [port.id for port in symbol.ports] == ["f.1"]  # `<function name>.<port name>`


# --- 9. An off stub draws along its stored facing, not the placement's geometry (F1 part 3c) ----


def test_off_stub_draws_west_of_its_port_though_the_geometry_faces_north():
    model, _sheet, _page_1, plain = _pair_model(first_changes={})
    off = dataclasses.replace(plain, star=StarKind.OFF, far=plain.port, facing=Side.W)
    model = evolve(model, remove=[plain.id], put=[off], origin=_ORIGIN)
    assert geometry_facing(model, off) is Direction.N  # the port leaves its box upward
    assert marker_facing(model, off) is Direction.W  # the stored fact wins
    assert stub_end(off, marker_facing(model, off)) == (off.x - 8, off.y)
    assert _marker_stub(model, off) == ((off.x, off.y), (off.x - 8, off.y))
    # the box hangs off the far end, west of the port
    assert box_origin(off, Direction.W)[0] + off.width == off.x - 8


# --- 10. A vertical marker's text reads along its wire, turned -90 degrees (render-0005) -------


_TURNED_TEXT = re.compile(
    r'<text [^>]*transform="rotate\(-90 ([\d.]+) ([\d.]+)\)" x="([\d.]+)" y="([\d.]+)"'
)


def _vertical_markers_group(**changes):
    model, sheet, page, marker = _pair_model(
        first_changes={"vertical": True, "width": 12, "height": 45, **changes}
    )
    return markers_group(model, page), sheet, marker


def test_a_vertical_marker_draws_its_text_turned_about_its_anchor_and_centred_on_the_length():
    """UNDO: in `_text_element` drop the `rotate=True` (no transform: the regex finds nothing),
    or use `box_y + marker.height` for the centre (the Y equality fails), or `box_x` for the
    anchor (X leaves the box's x-range only if the pad is dropped too: the x-range check fails).
    """
    drawn, sheet, marker = _vertical_markers_group()
    box_x, box_y = box_origin(marker, Direction.N)
    (turned,) = _TURNED_TEXT.findall(drawn)
    anchor_x, anchor_y, x, y = (Decimal(v) for v in turned)
    assert (anchor_x, anchor_y) == (x, y)  # rotated about its own anchor point
    assert Decimal(_mm_x(sheet, box_x)) < x < Decimal(_mm_x(sheet, box_x + 12))
    assert y == Decimal(_mm_y(sheet, box_y + 45 // 2))
    assert drawn.count("<text") == 1


def test_a_horizontal_twin_has_no_transform_and_the_unchanged_text_position():
    """UNDO: make `text_glyph` always emit the transform (the `not in` fails), or branch on
    `marker.vertical` the wrong way round (the horizontal x/y equalities fail).
    """
    model, sheet, page, marker = _pair_model(first_changes={"width": 12, "height": 45})
    assert marker.vertical is False
    drawn = markers_group(model, page)
    assert "transform" not in drawn
    box_x, box_y = box_origin(marker, Direction.N)
    text = re.search(r'<text [^>]*x="([\d.]+)" y="([\d.]+)"', drawn)
    assert text is not None
    assert text.group(1) == _mm_x(sheet, box_x + 12 // 2)  # centred on the width
    top = grid_to_mm(sheet.content_y_mm, box_y + (45 - 8) // 2, sheet.module_mm)
    assert Decimal(text.group(2)) == top + grid_to_mm(0, 8, sheet.module_mm) * ASCENT_RATIO


def test_a_two_line_vertical_marker_stands_its_lines_side_by_side_first_leftmost(monkeypatch):
    """The two lines are forced through `marker_text` (a star reference's wrap needs a star
    layout this file has no fixture for).

    UNDO: in `_text_element` drop `index *` from the cell's x (both texts share one X, the
    `<` fails) or negate it (the first lands rightmost).
    """
    monkeypatch.setattr(_markers, "marker_text", lambda _model, _marker: "/1.1\n/2.2")
    drawn, sheet, _marker_record = _vertical_markers_group()
    first, second = _TURNED_TEXT.findall(drawn)
    assert Decimal(first[2]) < Decimal(second[2])
    assert Decimal(second[2]) - Decimal(first[2]) == grid_to_mm(0, 8, sheet.module_mm)
    assert first[3] == second[3]  # both centred on the same length


def test_a_turned_marker_at_a_junction_draws_its_vertical_box_with_its_text_turned():
    """S20 M7 (33483ee6, 6e06ac8c) replaced the horizontal box at a junction: a dot, a branch and
    a vertical box, whose text reads along its stub like any vertical marker's.

    UNDO: in `_turned_glyphs` add `vertical=False` to `at_end`'s `replace` (no transform: FAILED
    this test alone).
    """
    model, _sheet, page, _turned = _pair_model(
        first_changes={"via_x": 200, "via_y": 70, "box_x": 202, "vertical": True}
    )
    assert "transform" in markers_group(model, page)


def test_a_marker_without_a_stored_facing_keeps_the_geometry_facing():
    model, _sheet, _page, plain = _pair_model(first_changes={})
    assert plain.facing is None
    assert marker_facing(model, plain) is geometry_facing(model, plain) is Direction.N


# --- 10. `_owning_placement` reads the (page, function) index; its `!= 1` assertion stays ------


def _own_placements(model, marker):
    return tuple(p for p in layout_of(model, SymbolPlacement).values() if p.page == marker.page)


def test_owning_placement_with_one_candidate_is_that_placement():
    model, _sheet, _page_1, first = _pair_model(first_changes={})
    (only,) = _own_placements(model, first)
    assert _markers._owning_placement(model, first) == only


def test_owning_placement_picks_the_candidate_whose_port_is_at_the_marker():
    model, _sheet, _page_1, first = _pair_model(first_changes={})
    (here,) = _own_placements(model, first)
    key = (*here.key, "elsewhere")
    elsewhere = dataclasses.replace(here, id=make_id(SymbolPlacement, key), key=key, x=here.x + 400)
    model = evolve(model, put=[elsewhere], origin=_ORIGIN)
    assert len(_own_placements(model, first)) == 2
    assert _markers._owning_placement(model, first) == here


def test_owning_placement_with_no_candidate_is_an_assertion_error():
    model, _sheet, _page_1, first = _pair_model(first_changes={})
    (here,) = _own_placements(model, first)
    model = evolve(model, remove=[here.id], origin=_ORIGIN)
    with pytest.raises(AssertionError, match="has 0 owning placements"):
        _markers._owning_placement(model, first)
