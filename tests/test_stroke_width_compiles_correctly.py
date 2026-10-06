"""PART C: `.wire`'s compiled stroke thickness matches D11's 0.25 mm, on REAL compiled pixels.

`_style.py`'s CSS `stroke-width: 0.25mm` compiled to about 0.93 mm on this Typst/resvg
pipeline (roughly 96/25.4, CSS's own 96-px-per-inch default resolving the `mm` unit into
user units, not this SVG's own `viewBox` scale) -- the same class of unit trap PART 7 found
for `font-size`. The fix is the same shape: a bare, unitless number in the `<style>` block
(`_style.style_block`), since this package's `viewBox` already makes 1 user unit equal 1 mm
(D5). This test compiles a real page with one real wire, decodes the PNG Typst emits, and
measures the wire's own ink thickness perpendicular to its run, in millimetres.

Root tests are the one place `fransys_render` and `fransys_pdf` may both be imported
(spec section 5's boundary table holds neither to import the other; mirrors
`tests/test_marker_text_compiles_inside_box.py`'s cross-package pattern). `_png.py`'s PNG
decoder is loaded the same dynamic-`importlib` way the other compiled tests already do it
(`ty` cannot see a `sys.path` insert statically, and root `pyproject.toml` is not this work
order's to edit).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import typst
from fransys_pdf import font_dir, source
from fransys_render import pages

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import DrawingSet, Page, PageRole, Route, RoutePoint
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    Conductor,
    ConductorKind,
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
_PNG_SPEC = importlib.util.spec_from_file_location("_render_worktree_png_probe_stroke", _PNG_PATH)
assert _PNG_SPEC is not None
assert _PNG_SPEC.loader is not None
_png = importlib.util.module_from_spec(_PNG_SPEC)
_PNG_SPEC.loader.exec_module(_png)

K = PageKind
PPI = 600.0  # high enough that 0.25 mm is several pixels wide (0.25 * 600 / 25.4 =~ 5.9 px)
_ORIGIN = Origin(file="tests/test_stroke_width_compiles_correctly.py", line=1, note="invented")

# The house sheet's own constants (`default_sheet_format()`), the same numbers the other
# compiled root tests hand-compute from -- content origin R11.1's 5 mm house margin, not the
# old 10 mm one.
_MODULE_MM = 2.5
_CONTENT_ORIGIN_MM = 5

# A straight horizontal wire, well clear of the title block and any label text: grid x in
# [100, 250] at y=150 -> mm x in [41.25, 88.125] at y=56.875, all whole multiples of 8 G
# (one module) except the scan column below, chosen mid-span.
_WIRE_X0_G, _WIRE_X1_G, _WIRE_Y_G = 100, 250, 150
_SCAN_X_G = 175  # mid-span: clear of both endpoints' own line-cap antialiasing

_EXPECTED_STROKE_WIDTH_MM = 0.25  # D11, `_constants.STROKE_WIDTH_MM`

# Tolerance derived from the scan resolution, not guessed: a stroke edge can land anywhere
# within one pixel (antialiasing spreads it over that pixel, and the `is_dark` threshold
# either counts it or not), so each of the stroke's two edges carries +/-1 px of
# uncertainty -- +/-2 px total on the measured width. One px at this PPI is 25.4/600 mm.
_PX_MM = 25.4 / PPI
_TOLERANCE_MM = 2 * _PX_MM


def _grid_to_mm(g: int) -> float:
    return _CONTENT_ORIGIN_MM + g * _MODULE_MM / 8


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


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


def _model_and_doc():
    location = AspectNode(
        id=make_id(AspectNode, ("location", "c1")),
        key=("location", "c1"),
        aspect=Aspect.LOCATION,
        parent=None,
        label="C1",
        description="Demo cabinet",
    )
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
        date="2026-09-23",
        text="First issue",
        created="XX",
    )
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

    item1, fn1, port1 = _pin("w1")
    item2, fn2, port2 = _pin("w2")
    a_port, b_port = (port1, port2) if port1.id < port2.id else (port2, port1)
    conductor = Conductor(
        id=make_id(Conductor, ("conductor", "w")),
        key=("conductor", "w"),
        a=a_port.id,
        b=b_port.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )
    points = (
        RoutePoint(index=0, x=_WIRE_X0_G, y=_WIRE_Y_G),
        RoutePoint(index=1, x=_WIRE_X1_G, y=_WIRE_Y_G),
    )
    route = Route(
        id=make_id(Route, ("route", "w")),
        key=("route", "w"),
        page=page.id,
        conductor=conductor.id,
        net=None,
        a=a_port.id,
        b=b_port.id,
        points=points,
        produced_by="test",
    )

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

    draft = Draft()
    draft.extend(
        [
            location,
            project,
            revision,
            drawing_set,
            page,
            item1,
            fn1,
            port1,
            item2,
            fn2,
            port2,
            conductor,
            route,
            doc,
        ],
        origin=_ORIGIN,
    )
    return freeze(draft), doc


def _compiled_schematic_page():
    model, doc = _model_and_doc()
    svgs = pages(model)
    assert len(svgs) == 1  # one layout page -> one rendered SVG
    assert 'class="wire"' in next(iter(svgs.values()))  # the wire is really there to measure
    text = source(model, doc.id, svgs)
    assert text.count("#pagebreak()") == 1  # COVER | SCHEMATIC
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    pngs = compiler.compile(input=text.encode("utf-8"), format="png", ppi=PPI)
    assert isinstance(pngs, list)
    assert len(pngs) == 2
    _cover, schematic = pngs  # (COVER, SCHEMATIC, in that order)
    del pngs, _cover  # drop the cover page's PNG bytes before the schematic is decoded
    return _png.decode_png(schematic)


def _measured_stroke_width_mm(raster) -> float:
    """The wire's own ink thickness (mm), scanned perpendicular to its run at mid-span."""
    x_px = _px(_grid_to_mm(_SCAN_X_G))
    y_mm = _grid_to_mm(_WIRE_Y_G)
    y0_px, y1_px = _px(y_mm - 2.0), _px(y_mm + 2.0)  # a window well clear of anything else
    dark = [y for y in range(y0_px, y1_px) if raster.is_dark(x_px, y, threshold=128)]
    assert dark, "no wire ink found at all"
    return (max(dark) - min(dark) + 1) * _PX_MM


def test_wire_stroke_width_compiles_to_the_intended_mm():
    """The compiled wire's ink thickness is 0.25 mm, within the scan's own pixel tolerance.

    Presence of ink is asserted first (`_measured_stroke_width_mm` itself asserts a
    non-empty scan), before the width is checked -- so this cannot pass by having measured
    nothing. Can-fail: reverting `_style.py`'s bare `stroke-width` to `0.25mm` (a CSS
    absolute length again) makes this fail, quoted in the hand-back, then undone with Edit.
    """
    raster = _compiled_schematic_page()
    measured_mm = _measured_stroke_width_mm(raster)
    assert abs(measured_mm - _EXPECTED_STROKE_WIDTH_MM) <= _TOLERANCE_MM, (
        measured_mm,
        _EXPECTED_STROKE_WIDTH_MM,
        _TOLERANCE_MM,
    )
