"""The marker box work package's own proof, on REAL compiled pixels: a location-prefixed
marker text (`+C1/1.2`, D2) -- THE DEFECT's own example (designer's ruling, 2026-09-23: "on
'+C1/1.2' the ink touches the outline") and the longest form a marker text ever takes, the
exact case a render-side constant box could never have fit (render-0001's named limitation,
closed by model-0037/layout-0043/this PART B) -- draws its ink inside the box render drew
for it, clear of the outline on every edge, not merely unclipped past it (decision
layout-0043's amendment, this work order). LD3/LD5 (spec 2026-09-25) later gave the position
text a `#n-` reference number and a row letter: the designer's ruling's own text is now printed
as `#1-+C1p1:2A`, still the same box-sizing defect, quoted verbatim above as the ruling wrote it.

Root tests are the one place `fransys_render` and `fransys_pdf` may
both be imported (spec section 5's boundary table holds neither to import
the other; mirrors `tests/test_marker_fit.py`'s and
`tests/test_symbol_not_installed_compiles_grey.py`'s cross-package
pattern). This file also imports `fransys_layout.geometry.text_width`,
the one place outside `tests/test_marker_fit.py` a render test may: not to
duplicate layout's sizing rule in render (D8 forbids that), but to give
this marker a width the same way
`fransys_layout.stages.references.marker_boxes.reference_size` really
would -- a generous guessed constant would prove nothing about the real
defect (a fixed box too narrow for a longer text).
`_png.py`'s PNG decoder is loaded the same dynamic-`importlib` way the other two compiled
tests already do it (`ty` cannot see a `sys.path` insert statically, and root
`pyproject.toml` is not this work order's to edit).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
import typst
from fransys_pdf import font_dir, source
from fransys_render import pages
from fransys_render._constants import MARKER_ARROW_DEPTH_G

from electrical_symbols import GENERIC_BOX_KEY
from fransys_layout.geometry import text_width
from fransys_model.derive.drawing_text import frame_column, frame_row, marker_text, position_text
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.kernel.ids import render_id
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Orientation,
    Page,
    PageRole,
    SymbolPlacement,
    default_profile,
    layout_of,
)
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Document,
    DocumentPreset,
    Function,
    FunctionKind,
    Item,
    PageKind,
    Port,
    PortRole,
    Project,
    Revision,
)

_PNG_PATH = (
    Path(__file__).resolve().parent.parent / "packages" / "fransys-pdf" / "tests" / "_png.py"
)
_PNG_SPEC = importlib.util.spec_from_file_location("_render_worktree_png_probe_marker", _PNG_PATH)
assert _PNG_SPEC is not None
assert _PNG_SPEC.loader is not None
_png = importlib.util.module_from_spec(_PNG_SPEC)
_PNG_SPEC.loader.exec_module(_png)

K = PageKind
PPI = 144.0
_ORIGIN = Origin(file="tests/test_marker_text_compiles_inside_box.py", line=1, note="invented")

# The house sheet's own constants (`default_sheet_format()`), the same numbers the other two
# compiled root tests hand-compute from -- content origin R11.1's 5 mm house margin, not the
# old 10 mm one.
_MODULE_MM = 2.5
_CONTENT_ORIGIN_MM = 5
_CONTENT_WIDTH_G = 1312  # 410 mm content width, in G (410 * 8 / 2.5)
_FRAME_COLUMNS = 8
_CONTENT_HEIGHT_G = 854  # 267 mm content height, in G (267 * 8 / 2.5, floored)
_FRAME_ROWS = 6

# Placement grid coordinates, whole multiples of 8 (one module), so the absolute mm position
# is exact -- the same convention `test_symbol_not_installed_compiles_grey.py` and
# `test_label_font_size_compiles_correctly.py` use.
_OWNER_X_G, _OWNER_Y_G = 80, 80  # the un-prefixed drawing set's placement -> the printed page
_PARTNER_X_G, _PARTNER_Y_G = 240, 80  # +C1's placement -- never printed, only cited by the text
_PARTNER_PAGE_NUMBER = 1  # together with the column and row below, the owner marker's text is
# #1-+C1p1:2A: the same defect example the designer named (2026-09-23 ruling, THE DEFECT,
# against the then-current text format, "+C1/1.2"): "the ink touches the outline".
# `_PARTNER_X_G = 240` already gives frame column 2, `_PARTNER_Y_G - 16 = 64` gives row A
# (`frame_column`/`frame_row`'s own arithmetic, unchanged by this rename); the model's one
# severed pair is always reference number 1 (`reference_number`, LD3/LD5's `#n-` prefix).

_TEXT_HEIGHT_G = default_profile().text_height  # 8 G: the house profile's own marker box height
_MARKER_PADDING_G = default_profile().marker_padding  # 2 G: decision layout-0043's amendment


def _grid_to_mm(g: int) -> float:
    return _CONTENT_ORIGIN_MM + g * _MODULE_MM / 8


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


def _mm(px: float) -> float:
    return px * 25.4 / PPI


def _location(key_part: str, label: str) -> AspectNode:
    key = ("location", key_part)
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=Aspect.LOCATION,
        parent=None,
        label=label,
        description=f"Demo cabinet {label}",
    )


def _pin(key_part: str) -> tuple[Item, Function, Port]:
    item_key = ("item", key_part)
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag=key_part.upper(),
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


def _placement(key_part: str, *, function: Function, page: Page, x: int, y: int) -> SymbolPlacement:
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


def _model_and_owner_marker_id():
    """Two drawing sets, two locations, a marker severed across them (location-prefixed text).

    `generic_box`'s one port per function sits at module offset (0, -2.0) -> grid (0, -16),
    N-facing (the same fixed geometry `packages/fransys-render/tests/test_markers.py`'s
    own `_pin`/`_placement` helpers rely on) -- so each marker sits 16 G above its owning
    placement, with no symbol-geometry lookup needed here to predict it.
    """
    # `location_c1` (drawing set 1, printed) is labelled "C0" and `location_c2` (drawing set 2,
    # never printed, only cited) is labelled "C1": the owner marker's text names the partner's
    # label, so this is what makes the printed page's own marker text read "#1-+C1p1:2A".
    location_c1 = _location("c1", "C0")
    location_c2 = _location("c2", "C1")
    project = Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title="Demo cabinet",
        number="DEMO-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    revision = Revision(
        id=make_id(Revision, ("revision", "r1")),
        key=("revision", "r1"),
        release=None,
        version=1,
        revision=1,
        date="2026-09-22",
        text="First issue",
        created="XX",
    )
    drawing_set_1 = DrawingSet(
        id=make_id(DrawingSet, ("drawing_set", "ds1")),
        key=("drawing_set", "ds1"),
        location=location_c1.id,
        number=1,
        produced_by="test",
    )
    drawing_set_2 = DrawingSet(
        id=make_id(DrawingSet, ("drawing_set", "ds2")),
        key=("drawing_set", "ds2"),
        location=location_c2.id,
        number=2,
        produced_by="test",
    )
    page_owner = Page(
        id=make_id(Page, ("page", "owner")),
        key=("page", "owner"),
        drawing_set=drawing_set_1.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=None,  # the house sheet
        groups=(),
        produced_by="test",
    )
    page_partner = Page(
        id=make_id(Page, ("page", "partner")),
        key=("page", "partner"),
        drawing_set=drawing_set_2.id,
        number=_PARTNER_PAGE_NUMBER,
        role=PageRole.CONTROL,
        sheet_format=None,  # the house sheet
        groups=(),
        produced_by="test",
    )

    item_owner, fn_owner, port_owner = _pin("owner")
    item_partner, fn_partner, port_partner = _pin("partner")
    placement_owner = _placement(
        "owner", function=fn_owner, page=page_owner, x=_OWNER_X_G, y=_OWNER_Y_G
    )
    placement_partner = _placement(
        "partner", function=fn_partner, page=page_partner, x=_PARTNER_X_G, y=_PARTNER_Y_G
    )

    owner_id = make_id(LinkMarker, ("link_marker", "owner"))
    partner_id = make_id(LinkMarker, ("link_marker", "partner"))

    # The text `marker_text` will read for the owner marker, predicted the
    # same way `fransys_model.derive.drawing_text.marker_text` itself
    # computes it (the partner's page number, frame column and frame row,
    # location-prefixed since the two pages are in different, both-labelled
    # drawing sets, and `#n-` prefixed by its reference number) -- so the
    # width given below is sized for the real text, not a guess. `marker_box`
    # (`fransys_layout.stages.references.marker_boxes`) pads both
    # dimensions by `2 * marker_padding` (decision layout-0043's amendment):
    # the width/height given here are what the real engine would have written
    # for this profile, not the pre-amendment unpadded box render-0001's own
    # limitation was proven against.
    column = frame_column(_CONTENT_WIDTH_G, _FRAME_COLUMNS, _PARTNER_X_G)
    row = frame_row(_CONTENT_HEIGHT_G, _FRAME_ROWS, _PARTNER_Y_G - 16)
    position = position_text(_PARTNER_PAGE_NUMBER, column, row, ("C1",))
    # This model holds exactly one severed pair, so it is the model's only reference group and
    # always reference number 1 (`reference_number`); the model isn't built yet to call it on.
    predicted_text = f"#1-{position}"
    assert predicted_text == "#1-+C1p1:2A", "THE DEFECT's own example (owner ruling, 2026-09-23)"
    width = text_width(predicted_text, height=_TEXT_HEIGHT_G) + 2 * _MARKER_PADDING_G

    marker_owner = LinkMarker(
        id=owner_id,
        key=("link_marker", "owner"),
        page=page_owner.id,
        port=port_owner.id,
        side=MarkerSide.OWNER,
        partner=partner_id,
        x=_OWNER_X_G,
        y=_OWNER_Y_G - 16,
        width=width,
        height=_TEXT_HEIGHT_G + 2 * _MARKER_PADDING_G,
        produced_by="test",
    )
    marker_partner = LinkMarker(
        id=partner_id,
        key=("link_marker", "partner"),
        page=page_partner.id,
        port=port_partner.id,
        side=MarkerSide.USER,
        partner=owner_id,
        x=_PARTNER_X_G,
        y=_PARTNER_Y_G - 16,
        width=13 + 2 * _MARKER_PADDING_G,
        height=_TEXT_HEIGHT_G + 2 * _MARKER_PADDING_G,
        produced_by="test",
    )

    doc = Document(
        id=make_id(Document, ("document", "d1")),
        key=("document", "d1"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=location_c1.id,
        item=None,
        add=(),
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
        cover="# Cover\n\nSome cover text.",
        notes=None,
    )

    draft = Draft()
    draft.extend(
        [
            location_c1,
            location_c2,
            project,
            revision,
            drawing_set_1,
            drawing_set_2,
            page_owner,
            page_partner,
            item_owner,
            fn_owner,
            port_owner,
            item_partner,
            fn_partner,
            port_partner,
            placement_owner,
            placement_partner,
            marker_owner,
            marker_partner,
            doc,
        ],
        origin=_ORIGIN,
    )
    return freeze(draft), doc, owner_id


@pytest.fixture(scope="module")
def compiled_page():
    """One compile, shared by both tests below (typst compilation is not free)."""
    model, doc, owner_id = _model_and_owner_marker_id()
    svgs = pages(model)
    assert len(svgs) == 2  # both real layout pages render, even though only C1's is printed
    text = source(model, doc.id, svgs)
    assert text.count("#pagebreak()") == 1  # COVER | SCHEMATIC: only C1's page, never C2's
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    pngs = compiler.compile(input=text.encode("utf-8"), format="png", ppi=PPI)
    assert isinstance(pngs, list)
    assert len(pngs) == 2
    raster = _png.decode_png(pngs[1])  # index 1: SCHEMATIC (COVER, SCHEMATIC, in that order)
    return model, raster, owner_id, svgs


_EXPECTED_OWNER_PAGE_MARKER_COUNT = 1  # one marker glyph -- the owner's -- on the printed page


def _real_box_bounds_mm(svg: str) -> tuple[float, float, float, float]:
    """The drawn box's real mm bounds, parsed from the rendered SVG's own `<polyline>`.

    Reads the coordinates render actually emitted (the same numbers `_box_glyph` turned
    into a `<polyline points="...">` string), not a second call to `box_origin`/
    `arrow_polygon` -- the size equality between that computation and `marker.width`/
    `height` is `test_markers.py::test_drawn_box_size_equals_the_records_stored_size`'s
    job, proven there; this file's job is the compiled *pixels*, so it reads the compiled
    *source*.
    """
    polylines = re.findall(r'<polyline class="marker"[^>]*points="([^"]*)"', svg)
    assert len(polylines) == _EXPECTED_OWNER_PAGE_MARKER_COUNT
    points = [tuple(float(v) for v in pair.split(",")) for pair in polylines[0].split(" ")]
    xs = [x for x, _y in points]
    ys = [y for _x, y in points]
    return min(xs), max(xs), min(ys), max(ys)


# Strips just outside the drawn box's own edge, scanned for ink that should not be there --
# the direct test of "no overflowing text" (owner ruling F5), immune to the box outline's
# own stroke width (unlike a tolerance band added to the box's own coordinates, which
# cannot tell overflowing text ink apart from the outline's own stroke bleeding outward).
#
# `_OUTER_OFFSET_MM` clears that bleed: a direct probe of this box's own `<polyline
# class="marker">` outline (`stroke-width: 0.25mm`, `_constants.STROKE_WIDTH_MM`) measured
# about 0.93 mm of total rendered width on this Typst/resvg pipeline, roughly 3.7x
# (~96/25.4) the intended 0.25 mm -- the same class of unit surprise PART 7 found for a
# `<text>`'s `font-size`, this time in `_style.py`'s CSS `stroke-width`. A `<line
# class="wire">` measured the identical ~0.93 mm, so this is not specific to the marker
# glyph's own path; not proven here for `.symbol`/`.junction` (a different shape, a
# different rule -- `.junction` has no stroke at all), and not something PART B introduced
# or fixes -- reported in the hand-back, not touched here. 0.75 mm clears the outline's own
# ~0.47 mm half-stroke with margin; `_STRIP_WIDTH_MM` only needs to be wide enough that a
# real overflow (several mm, proven by `test_the_containment_check_can_fail` below) lands
# inside it. `_Y_INSET_MM` keeps the vertical scan off the box's own top/bottom edges.
_OUTER_OFFSET_MM = 0.75
_STRIP_WIDTH_MM = 1.5
_Y_INSET_MM = 0.3


def _outer_strips_mm(
    box_x0_mm: float, box_x1_mm: float, box_y0_mm: float, box_y1_mm: float
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """The (left, right) strips just outside the box, each `(x0_mm, x1_mm, y0_mm, y1_mm)`."""
    y0_mm, y1_mm = box_y0_mm + _Y_INSET_MM, box_y1_mm - _Y_INSET_MM
    left_x1_mm = box_x0_mm - _OUTER_OFFSET_MM
    left_x0_mm = left_x1_mm - _STRIP_WIDTH_MM
    right_x0_mm = box_x1_mm + _OUTER_OFFSET_MM
    right_x1_mm = right_x0_mm + _STRIP_WIDTH_MM
    return (left_x0_mm, left_x1_mm, y0_mm, y1_mm), (right_x0_mm, right_x1_mm, y0_mm, y1_mm)


def _strip_ink(raster, x0_mm: float, x1_mm: float, y0_mm: float, y1_mm: float):
    box = _png.Box(x0=_px(x0_mm), x1=_px(x1_mm), y0=_px(y0_mm), y1=_px(y1_mm))
    return _png.ink_bbox(raster, box, threshold=245)


# THE DEFECT's own root cause (owner ruling, 2026-09-23): the box's outline is drawn ON the
# box edge, so its own stroke has an inward half and an outward half -- the outline's *inner*
# edge (what the text must clear) is the box edge minus half the stroke's real rendered
# width, not the box edge itself. Measured on the compiled raster, not assumed from
# `_constants.STROKE_WIDTH_MM` (0.25 mm): the box's own top edge (`box_y0_mm`) is a plain
# horizontal stroke for an N-facing marker (the arrow's pulled-in corners are on the bottom,
# near the stub, docs/design/links.md 6.6), scanned a little in from the box's left corner,
# clear of both the arrow tip and the text.
_STROKE_PROBE_INSET_MM = 0.3
_STROKE_PROBE_WIDTH_MM = 0.4
_STROKE_PROBE_BAND_MM = 1.0  # generous: only the true stroke is dark in this band


def _measured_stroke_width_mm(raster, box_x0_mm: float, box_y0_mm: float) -> float:
    """The `.marker` outline's own rendered stroke width, read off the box's plain top edge."""
    x0_mm = box_x0_mm + _STROKE_PROBE_INSET_MM
    x1_mm = x0_mm + _STROKE_PROBE_WIDTH_MM
    y0_mm = box_y0_mm - _STROKE_PROBE_BAND_MM
    y1_mm = box_y0_mm + _STROKE_PROBE_BAND_MM
    bbox = _strip_ink(raster, x0_mm, x1_mm, y0_mm, y1_mm)
    assert bbox is not None, "no ink found on the box's own top edge -- nothing to measure"
    _min_x, min_y, _max_x, max_y = bbox
    return _mm(max_y - min_y + 1)


# The inner check's own margin, stated from the dpi (owner ruling, THE RULE): one rendered
# pixel at 144 ppi (`_mm(1)` = 25.4/144 ~= 0.176 mm), covering anti-aliasing fuzz at the
# stroke's own inner edge. The scanned band itself is deliberately narrow (`_INNER_STRIP_MM`):
# the padding this work package adds is 2 G = 0.625 mm on the house profile, half of it
# already spent clearing the stroke's own half-width (~0.125 mm), so the genuine clear gap
# between the stroke's inner edge and the text's own ink is only a fraction of a millimetre --
# a strip as wide as the outer one (1.5 mm) would reach the text itself and always find ink.
_INNER_MARGIN_MM = _mm(1)
_INNER_STRIP_MM = 0.25


def _inner_strips_mm(
    box_x0_mm: float,
    box_x1_mm: float,
    box_y0_mm: float,
    *,
    half_stroke_mm: float,
    side_y1_mm: float,
) -> tuple[tuple[float, float, float, float], ...]:
    """Left, right, top: thin bands just inside the outline's own inner edge.

    Each band starts `half_stroke_mm + _INNER_MARGIN_MM` in from the box's own edge (clear of
    the stroke's own ink) and is `_INNER_STRIP_MM` wide, going further inward -- the same
    "scan where only overflowing ink could be, not the outline's own" logic
    `_outer_strips_mm` uses, mirrored to the inside. `_Y_INSET_MM` keeps the top band off the
    box's own corners; the left/right bands stop at `side_y1_mm`, short of the box's own near
    edge, because for this N-facing marker only the region from the top down to
    `MARKER_ARROW_DEPTH_G` above the near edge is a plain vertical side (`arrow_polygon`) --
    beyond that the outline itself turns inward toward the arrow's tip, so a rectangular
    strip running the box's full height would pick up the diagonal tip stroke as if it were
    overflowing text. Left, right and top only: the near (bottom, port-side) edge is the
    arrow's tip itself, never a plain line, so its own clearance is checked visually instead
    (the hand-back's rendered PNG).
    """
    inset = half_stroke_mm + _INNER_MARGIN_MM
    left = (
        box_x0_mm + inset,
        box_x0_mm + inset + _INNER_STRIP_MM,
        box_y0_mm + _Y_INSET_MM,
        side_y1_mm,
    )
    right = (
        box_x1_mm - inset - _INNER_STRIP_MM,
        box_x1_mm - inset,
        box_y0_mm + _Y_INSET_MM,
        side_y1_mm,
    )
    top = (
        box_x0_mm + _Y_INSET_MM,
        box_x1_mm - _Y_INSET_MM,
        box_y0_mm + inset,
        box_y0_mm + inset + _INNER_STRIP_MM,
    )
    return left, right, top


def _plain_side_y1_mm(box_y0_mm: float, marker_height_g: int) -> float:
    """How far down the box's left/right edges stay plain before the arrow tip pulls them in.

    `arrow_polygon`'s own N-facing vertices: the plain sides run from the top down to
    `height - MARKER_ARROW_DEPTH_G`; a small further margin keeps the scan off the corner
    where the outline turns.
    """
    plain_g = marker_height_g - MARKER_ARROW_DEPTH_G
    return box_y0_mm + plain_g * _MODULE_MM / 8 - _Y_INSET_MM


def test_location_prefixed_marker_text_ink_lies_inside_its_drawn_box(compiled_page):
    """The compiled glyph of THE DEFECT's own example, `#1-+C1p1:2A`, never touches its own box.

    The box itself is present and non-degenerate first (`_real_box_bounds_mm` asserts
    exactly one drawn polyline, and both its dimensions are asserted positive below) --
    so this cannot pass by having found nothing to check against. Then two things, both
    proven able to fail (not only pass) below: no ink at all in a strip just outside either
    edge (overflow, `test_the_containment_check_can_fail`), and no ink in a strip just
    inside the outline's own inner edge (touching, the padding this work package adds --
    `test_the_containment_check_fails_at_zero_padding`, plus the can-fail probe on the real
    glyph code quoted in the hand-back).
    """
    model, raster, owner_id, svgs = compiled_page
    marker = layout_of(model, LinkMarker)[owner_id]
    text = marker_text(model, marker)
    assert text == "#1-+C1p1:2A"  # THE DEFECT's own example (owner ruling, 2026-09-23)

    owner_svg = svgs[render_id(marker.page)]
    box_x0_mm, box_x1_mm, box_y0_mm, box_y1_mm = _real_box_bounds_mm(owner_svg)
    assert box_x1_mm > box_x0_mm
    assert box_y1_mm > box_y0_mm

    left, right = _outer_strips_mm(box_x0_mm, box_x1_mm, box_y0_mm, box_y1_mm)
    assert _strip_ink(raster, *left) is None, "text ink spills past the box's left edge"
    assert _strip_ink(raster, *right) is None, "text ink spills past the box's right edge"

    half_stroke_mm = _measured_stroke_width_mm(raster, box_x0_mm, box_y0_mm) / 2
    side_y1_mm = _plain_side_y1_mm(box_y0_mm, marker.height)
    inner_left, inner_right, inner_top = _inner_strips_mm(
        box_x0_mm,
        box_x1_mm,
        box_y0_mm,
        half_stroke_mm=half_stroke_mm,
        side_y1_mm=side_y1_mm,
    )
    assert _strip_ink(raster, *inner_left) is None, "ink touches the outline's left inner edge"
    assert _strip_ink(raster, *inner_right) is None, "ink touches the outline's right inner edge"
    assert _strip_ink(raster, *inner_top) is None, "ink touches the outline's top inner edge"


def test_the_containment_check_can_fail(compiled_page):
    """The identical strip check, against render's own retired fixed-width box, finds ink.

    Not a git discard: the same real compiled raster the main test above reads (the
    glyph code is untouched here), checked against a box this work package retired --
    `MARKER_BOX_WIDTH_G = 12`, centred on the marker's own `x`, `box_origin`'s old N-facing
    formula (`marker.x - w // 2`) -- proves the strip check has the power to fail on a
    too-narrow box, not only to pass on the real one. Only the width is retired here (the
    real box's own, now-padded, `y`-bounds still apply): `MARKER_BOX_WIDTH_G` was
    render-0001's own width-only constant, and this probe is about the horizontal overflow
    that decision closed, not the vertical padding this work package adds (that one is
    `test_the_containment_check_fails_at_zero_padding`, below).
    """
    model, raster, owner_id, svgs = compiled_page
    marker = layout_of(model, LinkMarker)[owner_id]
    owner_svg = svgs[render_id(marker.page)]
    _real_x0_mm, _real_x1_mm, box_y0_mm, box_y1_mm = _real_box_bounds_mm(owner_svg)

    old_width_g = 12  # render's retired MARKER_BOX_WIDTH_G constant (render-0001)
    old_x0_g = marker.x - old_width_g // 2
    old_x1_g = old_x0_g + old_width_g
    old_x0_mm, old_x1_mm = _grid_to_mm(old_x0_g), _grid_to_mm(old_x1_g)

    left, right = _outer_strips_mm(old_x0_mm, old_x1_mm, box_y0_mm, box_y1_mm)
    left_ink = _strip_ink(raster, *left)
    right_ink = _strip_ink(raster, *right)
    assert left_ink is not None, "the check should have caught the old box's overflow, on the left"
    assert right_ink is not None, "and on the right"


def test_the_containment_check_fails_at_zero_padding(compiled_page):
    """The inner-edge check, against a box built with `marker_padding=0`, finds ink.

    Not a git discard: the same real compiled raster the main test above reads (the glyph
    code is untouched here) is re-checked against the box a `marker_padding=0` profile
    would have produced -- narrower and shorter by `2 * _MARKER_PADDING_G` than the real,
    padded box this page was actually compiled with. Shrinking the box after the fact
    (rather than recompiling at padding 0) keeps this test independent of the actual
    can-fail probe on the source (quoted in the hand-back), while still proving the inner
    strip check has the power to fail on THE DEFECT's own example: `#1-+C1p1:2A` ink right at
    the edge of a zero-padding box.
    """
    model, raster, owner_id, svgs = compiled_page
    marker = layout_of(model, LinkMarker)[owner_id]
    text = marker_text(model, marker)
    assert text == "#1-+C1p1:2A"
    owner_svg = svgs[render_id(marker.page)]
    box_x0_mm, box_x1_mm, box_y0_mm, _box_y1_mm = _real_box_bounds_mm(owner_svg)

    # The real box, shrunk back to what `marker_padding=0` would have reserved.
    # `marker_box` centres the width on the port (E/W) or, here, on the port's `x` (N):
    # each side loses one `pad_mm`. The height is not centred -- the near (bottom) edge is
    # anchored to the stub's own touch point regardless of padding (the invariant
    # `test_stub_touches_box_near_edge_exactly` proves), so all `2 * pad_mm` of the height
    # difference comes off the far (top) edge alone.
    pad_mm = _MARKER_PADDING_G * _MODULE_MM / 8
    zero_x0_mm, zero_x1_mm = box_x0_mm + pad_mm, box_x1_mm - pad_mm
    zero_y0_mm = box_y0_mm + 2 * pad_mm

    half_stroke_mm = _measured_stroke_width_mm(raster, box_x0_mm, box_y0_mm) / 2
    zero_height_g = marker.height - 2 * _MARKER_PADDING_G
    side_y1_mm = _plain_side_y1_mm(zero_y0_mm, zero_height_g)
    inner_left, inner_right, inner_top = _inner_strips_mm(
        zero_x0_mm,
        zero_x1_mm,
        zero_y0_mm,
        half_stroke_mm=half_stroke_mm,
        side_y1_mm=side_y1_mm,
    )
    found = [_strip_ink(raster, *strip) for strip in (inner_left, inner_right, inner_top)]
    assert any(ink is not None for ink in found), (
        f"the inner check should have caught {text!r}'s ink touching a zero-padding box"
    )
