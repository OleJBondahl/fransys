"""render-0001, the empirical proof the orchestrator's correction (2026-09-22) demanded:
does `_style.py`'s `.not-installed` descendant/attribute CSS actually override the
toolkit's inline presentation attributes on Typst's own compiled SVG output (usvg/resvg),
not just on a browser? Root tests are the one place `fransys_render`, `fransys_pdf`
and `fransys_model` may all be imported (spec section 5's boundary table holds none of
these to import each other; mirrors `tests/test_marker_text_compiles_inside_box.py`'s
render/pdf compiled-pixel pattern and
`packages/fransys-pdf/tests/test_frame_compiled.py`'s PNG route).

Two `fuse` placements (`electrical-symbols/symbols/fuse.toml`) on one schematic page, far
apart: one installed, one not. `fuse` has both a stroke-only element (the centre line) and
a genuinely filled element (the small solid rectangle, `fill = "solid"`), so one symbol
proves both halves of the CSS (`.not-installed *` for stroke, `.not-installed [fill]` for
fill) in a single compile.

Result: both selectors DO override the toolkit's presentation attributes on Typst's
compiled output -- confirmed by the exact pixel colours asserted below. No wrapper-
attribute or string-rewrite fallback was needed.

The model here is built directly (not by importing `packages/fransys-pdf/tests/_build.py`
as a bare module): that file is reachable at runtime only through a `sys.path` insert,
which `ty` cannot see statically (root `pyproject.toml`'s own comment on its `extra-paths`
list), and `pyproject.toml` is not this work order's to edit. `_png.py`'s PNG decoder is
reused, not duplicated, loaded by file path with `importlib` for the same reason -- a
dynamic load, not a static `import`, so `ty` has nothing to fail to resolve.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import typst
from fransys_pdf import source
from fransys_render import pages

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Orientation,
    Page,
    PageRole,
    SymbolPlacement,
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
_PNG_SPEC = importlib.util.spec_from_file_location("_render_worktree_png_probe", _PNG_PATH)
assert _PNG_SPEC is not None
assert _PNG_SPEC.loader is not None
_png = importlib.util.module_from_spec(_PNG_SPEC)
_PNG_SPEC.loader.exec_module(_png)

K = PageKind
PPI = 144.0
_ORIGIN = Origin(file="tests/test_symbol_not_installed_compiles_grey.py", line=1, note="invented")

# Placement grid coordinates chosen as whole multiples of 8 (one module) so the absolute mm
# position is an exact number, no long decimals to carry through this test's own hand-math.
_MODULE_MM = 2.5  # the house sheet's own module_mm (`default_sheet_format()`)
_CONTENT_ORIGIN_MM = 5  # the house sheet's own content_x_mm == content_y_mm (R11.1)
_A_X_G, _A_Y_G = 80, 80  # -> (30, 30) mm
_B_X_G, _B_Y_G = 240, 80  # -> (80, 30) mm -- 50 mm from A, far clear of its symbol


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _grid_to_mm(g: int) -> float:
    return _CONTENT_ORIGIN_MM + g * _MODULE_MM / 8


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


def _location() -> AspectNode:
    key = ("location", "c1")
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="Demo cabinet",
    )


def _project() -> Project:
    return Project(
        id=make_id(Project, ("project",)),
        key=("project",),
        title="Demo cabinet",
        number="DEMO-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )


def _project_revision() -> Revision:
    return Revision(
        id=make_id(Revision, ("revision", "r1")),
        key=("revision", "r1"),
        release=None,
        version=1,
        revision=1,
        date="2026-09-22",
        text="First issue",
        created="XX",
    )


def _pin(key_part: str, *, installed: bool) -> tuple[Item, Function, Port]:
    item_key = ("item", key_part)
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag=key_part.upper(),
        description="Invented",
        installed=installed,
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
        symbol="fuse",
        library_version="test",
        produced_by="test",
    )


def _document_and_page():
    """One COVER + one SCHEMATIC page (`remove` drops CABINET_SCHEMATIC's other pages, same
    tuple `packages/fransys-pdf/tests/test_frame_compiled.py` uses for the same reason).
    """
    location = _location()
    project = _project()
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, ("drawing_set", "ds1")),
        key=("drawing_set", "ds1"),
        location=location.id,
        number=1,
        produced_by="test",
    )
    page = Page(
        id=make_id(Page, ("page", "p1")),
        key=("page", "p1"),
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=None,  # the house sheet
        groups=(),
        produced_by="test",
    )

    item_on, fn_on, port_on = _pin("on", installed=True)
    placement_on = _placement("on", function=fn_on, page=page, x=_A_X_G, y=_A_Y_G)
    item_off, fn_off, port_off = _pin("off", installed=False)
    placement_off = _placement("off", function=fn_off, page=page, x=_B_X_G, y=_B_Y_G)

    doc = Document(
        id=make_id(Document, ("document", "d1")),
        key=("document", "d1"),
        preset=DocumentPreset.CABINET_SCHEMATIC,
        location=location.id,
        item=None,
        add=(),
        remove=(K.PLC_LIST, K.TERMINAL_LIST, K.BOM),
        cover="# Cover\n\nSome cover text.",
        notes=None,
    )
    m = _model(
        location,
        project,
        _project_revision(),
        drawing_set,
        page,
        doc,
        item_on,
        fn_on,
        port_on,
        placement_on,
        item_off,
        fn_off,
        port_off,
        placement_off,
    )
    return m, doc, page


def _compiled_schematic_page():
    m, doc, _page = _document_and_page()
    svgs = pages(m)
    assert len(svgs) == 1  # one layout page -> one rendered SVG
    text = source(m, doc.id, svgs)
    assert text.count("#pagebreak()") == 1  # COVER | SCHEMATIC
    pngs = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=PPI)
    assert isinstance(pngs, list)
    assert len(pngs) == 2
    _cover, schematic = pngs  # (COVER, SCHEMATIC, in that order)
    del pngs, _cover  # drop the cover page's PNG bytes before the schematic is decoded
    return _png.decode_png(schematic)


def _darkest_pixel(raster, box) -> tuple[int, int, int]:
    """The least-bright pixel in `box` (closest to pure ink, least diluted by antialiasing)."""
    best = (255, 255, 255)
    for y in range(box.y0, box.y1):
        for x in range(box.x0, box.x1):
            i = (y * raster.width + x) * 4
            rgb = (raster.pixels[i], raster.pixels[i + 1], raster.pixels[i + 2])
            if sum(rgb) < sum(best):
                best = rgb
    return best


def test_not_installed_symbol_stroke_and_fill_are_grey_on_compiled_output():
    """The real proof (render-0001): compiled Typst output, not the raw SVG source.

    `fuse`'s centre line (stroke only, local x=0, y in [-3, 3]) and its small solid
    rectangle (local x in [-0.5, 0.5], y in [-1.5, -1], `fill = "solid"`) are both sampled,
    for both placements. Presence of ink is asserted first (non-zero pixel counts) so
    neither check can pass by having drawn nothing.
    """
    raster = _compiled_schematic_page()

    for x_g, y_g, label in ((_A_X_G, _A_Y_G, "installed"), (_B_X_G, _B_Y_G, "not-installed")):
        cx_mm, cy_mm = _grid_to_mm(x_g), _grid_to_mm(y_g)

        # The stroke-only centre line, away from the outer rectangle's own border (local
        # y in [2.6, 7.4]/2.5 = [1.04, 2.96] is outside the outer rectangle's y in
        # [-1.5, 1.5]). Wide enough (a few mm) to span more than one period of the
        # not-installed dash pattern (0.25mm on, 0.25mm off), so the darkest pixel found
        # lands on a fully covered "on" segment rather than an antialiased dash edge.
        stroke_box = _png.Box(
            x0=_px(cx_mm - 2.0), x1=_px(cx_mm + 2.0), y0=_px(cy_mm + 2.6), y1=_px(cy_mm + 7.4)
        )
        stroke_bbox = _png.ink_bbox(raster, stroke_box, threshold=245)
        assert stroke_bbox is not None, (label, "no stroke ink found at all")
        stroke_rgb = _darkest_pixel(raster, stroke_box)

        # The small solid-filled rectangle: local x in [-0.5, 0.5] -> mm [-1.25, 1.25],
        # local y in [-1.5, -1] -> mm [-3.75, -2.5], both around the placement centre.
        fill_box = _png.Box(
            x0=_px(cx_mm - 1.0),
            x1=_px(cx_mm + 1.0),
            y0=_px(cy_mm - 3.5),
            y1=_px(cy_mm - 2.75),
        )
        fill_bbox = _png.ink_bbox(raster, fill_box, threshold=245)
        assert fill_bbox is not None, (label, "no fill ink found at all")
        fill_rgb = _darkest_pixel(raster, fill_box)

        if label == "installed":
            # Untouched by any `not-installed` rule: pure black, exactly (`_stroke`'s own
            # `#000`/inherited `stroke="#000"`, no CSS override applies to this placement).
            assert stroke_rgb == (0, 0, 0), (label, "stroke", stroke_rgb)
            assert fill_rgb == (0, 0, 0), (label, "fill", fill_rgb)
        else:
            # CSS `grey` decodes to exactly (128, 128, 128): both `.not-installed *`
            # (stroke) and `.not-installed [fill]` (fill) resolve to that exact value on
            # Typst's compiled output -- the render-0001 proof.
            assert stroke_rgb == (128, 128, 128), (label, "stroke", stroke_rgb)
            assert fill_rgb == (128, 128, 128), (label, "fill", fill_rgb)


# --- PART C: `.not-installed *`'s dash period, on compiled pixels, at a sheet's own scale ------

_DASH_PPI = 600.0  # high enough to tell a 0.25 mm dash from the pre-fix ~0.625 mm one apart
_EXPECTED_DASH_MM = 0.25  # D10/D11: `_constants.STROKE_WIDTH_MM`, the same value as a solid line
_DASH_TOLERANCE_MM = 3 * (25.4 / _DASH_PPI)  # +/-1 px (antialiasing) per edge, one extra px slack


def _compiled_schematic_page_at(ppi: float):
    m, doc, _page = _document_and_page()
    svgs = pages(m)
    assert len(svgs) == 1
    text = source(m, doc.id, svgs)
    assert text.count("#pagebreak()") == 1
    pngs = typst.Compiler(text.encode("utf-8")).compile(format="png", ppi=ppi)
    assert isinstance(pngs, list)
    assert len(pngs) == 2
    _cover, schematic = pngs
    del pngs, _cover  # drop the cover page's PNG bytes before the schematic is decoded
    return _png.decode_png(schematic)


def test_not_installed_dash_period_is_the_sheets_own_025mm_not_the_scaled_one():
    """`.not-installed *`'s dasharray renders at 0.25 mm, not `0.25 * module_mm` (PART C).

    `.not-installed *` is a descendant-combinator rule: it matches the toolkit's own
    elements directly, inside `_symbols.py`'s `<g transform="... scale(module_mm)">`, so a
    page-space bare number there would be stretched by that ancestor transform -- found
    while building PART C's stroke-width fix, a dash/gap measuring about 0.6 mm on the
    house sheet (`module_mm=2.5`), not the intended 0.25 mm. `_style.style_block` now
    divides by `module_mm` for this one rule. Presence of ink is asserted first (each
    scanned pixel is either dark or not; the run-length list itself is asserted non-empty)
    before any period is checked -- so this cannot pass by having measured nothing.
    """

    def px(mm: float) -> int:
        return round(mm * _DASH_PPI / 25.4)

    raster = _compiled_schematic_page_at(_DASH_PPI)
    cx_mm, cy_mm = _grid_to_mm(_B_X_G), _grid_to_mm(_B_Y_G)
    x = px(cx_mm)
    y0, y1 = px(cy_mm + 2.6), px(cy_mm + 7.4)  # the same stroke-only band the test above scans

    runs_mm = []
    cur = raster.is_dark(x, y0, threshold=200)
    length = 1
    for y in range(y0 + 1, y1):
        dark = raster.is_dark(x, y, threshold=200)
        if dark == cur:
            length += 1
        else:
            runs_mm.append(length * 25.4 / _DASH_PPI)
            cur, length = dark, 1
    runs_mm.append(length * 25.4 / _DASH_PPI)

    assert runs_mm, "no dash pattern found at all"
    # The first and last runs are partial (the scan window starts/ends mid-run, so they
    # measure whatever fraction of a dash or gap happened to be left -- one of those
    # fractions can itself be short enough to need dropping too, e.g. the window opening
    # one pixel before a gap ends); every run at least half the expected period is a full
    # dash or gap, so this cannot pass by coincidence of one lucky edge measurement.
    full_runs = [r for r in runs_mm[1:-1] if r >= _EXPECTED_DASH_MM / 2]
    assert len(full_runs) >= 3, (runs_mm, "too few full runs to prove a period, not one edge")
    for run_mm in full_runs:
        assert abs(run_mm - _EXPECTED_DASH_MM) <= _DASH_TOLERANCE_MM, (
            run_mm,
            _EXPECTED_DASH_MM,
            _DASH_TOLERANCE_MM,
            runs_mm,
        )
