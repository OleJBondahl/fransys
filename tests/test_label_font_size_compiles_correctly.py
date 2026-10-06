"""D7 bug fix (part 7), proven on REAL compiled pixels, not just the SVG source string.

Every earlier test in this package proved label POSITION; none proved SIZE. Before this
fix, no `<text>` element this package emitted carried a `font-size` attribute at all, so
Typst's SVG renderer (usvg) fell back to its own default (~16 user units, roughly 6.4x the
intended 2.5mm on the house sheet) -- exactly the bug the owner's visual review caught. This
test compiles a real page with one known label, decodes the PNG Typst emits, and measures
the actual ink height of the label's glyph in millimetres.

Root tests are the one place `fransys_render` and `fransys_pdf` may both be imported
(spec section 5's boundary table holds neither to import the other; mirrors
`tests/test_symbol_not_installed_compiles_grey.py` and
`tests/test_marker_text_compiles_inside_box.py`'s cross-package pattern). `font_paths` and
`ignore_system_fonts` mirror the facade's own compile call (`fransys/pipeline.py`'s
`_compile_pdf`) -- the visual-review script this work order just ran found this necessary
for label glyphs to render correctly at all. `_png.py`'s PNG decoder is loaded the same
dynamic-`importlib` way `test_symbol_not_installed_compiles_grey.py` already does it (`ty`
cannot see a `sys.path` insert statically, and root `pyproject.toml` is not this work
order's to edit).
"""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import typst
from fransys_pdf import font_dir, source
from fransys_render import pages
from fransys_render._constants import ASCENT_RATIO

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import DrawingSet, Label, LabelKind, Page, PageRole
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
_PNG_SPEC = importlib.util.spec_from_file_location(
    "_render_worktree_png_probe_font_size", _PNG_PATH
)
assert _PNG_SPEC is not None
assert _PNG_SPEC.loader is not None
_png = importlib.util.module_from_spec(_PNG_SPEC)
_PNG_SPEC.loader.exec_module(_png)

K = PageKind
PPI = 144.0
_ORIGIN = Origin(
    file="tests/test_label_font_size_compiles_correctly.py", line=1, note="invented label"
)

# The house sheet's own constants (`default_sheet_format()`): content origin and module size,
# chosen the same way `test_symbol_not_installed_compiles_grey.py` picks its grid coordinates
# (whole multiples of 8 = one module, so the absolute mm position is exact, no long decimals).
_MODULE_MM = 2.5
_CONTENT_ORIGIN_MM = 5
_LABEL_X_G, _LABEL_Y_G = 80, 80  # -> (35, 35) mm

# `default_profile().text_height` is 8 G (`_constants.py`'s own docstring cites this for the
# goldens); font_size_mm = grid_to_mm(0, 8, 2.5) = 2.5, the house sheet's intended label size.
_EXPECTED_FONT_SIZE_MM = Decimal("2.5")

# Tolerance on the measured ink HEIGHT of one digit glyph ("1", MARKING kind: the port name
# verbatim, no dash prefix), not the font-size itself -- glyph metrics are never pixel-exact
# (antialiasing, the font's own cap-height-to-em ratio). A direct probe of this exact page
# (recorded here, not re-derived) measured 1.76mm for the digit "1" at font-size 2.5mm, a
# cap-height ratio of about 0.7 -- typical for a serif digit. The band [0.3, 1.0] x
# font-size (0.75mm-2.5mm) comfortably contains that reading while still being tight enough
# to catch the old bug: with the `font-size` attribute missing, Typst's SVG renderer falls
# back to its own default (~16 user units, ~6.4x too large), and the same probe against that
# broken output measured an ink height of 8.11mm for the same glyph -- more than 3x the
# tolerance's own ceiling, decisively outside this band.
_MIN_INK_HEIGHT_MM = 0.3 * float(_EXPECTED_FONT_SIZE_MM)
_MAX_INK_HEIGHT_MM = 1.0 * float(_EXPECTED_FONT_SIZE_MM)


def _model():
    draft = Draft()
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
        date="2026-09-22",
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

    item = Item(
        id=make_id(Item, ("item", "k1")),
        key=("item", "k1"),
        part=None,
        parent=None,
        position=None,
        tag="K1",
        description="Invented",
        installed=True,
    )
    fn = Function(
        id=make_id(Function, ("function", "k1")),
        key=("function", "k1"),
        item=item.id,
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    port_key = ("function", "k1", "1")
    port = Port(
        id=make_id(Port, port_key),
        key=port_key,
        function=fn.id,
        template=None,
        name="1",  # MARKING label text is the port name verbatim: a single digit glyph
        role=PortRole.GENERIC,
    )
    label = Label(
        id=make_id(Label, ("label", "l1")),
        key=("label", "l1"),
        page=page.id,
        function=None,
        port=port.id,
        conductor=None,
        kind=LabelKind.MARKING,
        slot="",
        x=_LABEL_X_G,
        y=_LABEL_Y_G,
        width=4,
        height=2,
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

    draft.extend(
        [location, project, revision, drawing_set, page, item, fn, port, label, doc],
        origin=_ORIGIN,
    )
    return freeze(draft), doc, page


def _grid_to_mm(g: int) -> float:
    return _CONTENT_ORIGIN_MM + g * _MODULE_MM / 8


def _px(mm: float) -> int:
    return round(mm * PPI / 25.4)


def _compiled_schematic_page():
    model, doc, _page = _model()
    svgs = pages(model)
    assert len(svgs) == 1  # one layout page -> one rendered SVG
    text = source(model, doc.id, svgs)
    assert text.count("#pagebreak()") == 1  # COVER | SCHEMATIC
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    pngs = compiler.compile(input=text.encode("utf-8"), format="png", ppi=PPI)
    assert isinstance(pngs, list)
    assert len(pngs) == 2
    return _png.decode_png(pngs[1])  # index 1: SCHEMATIC (COVER, SCHEMATIC, in that order)


def test_label_glyph_ink_height_matches_the_profiles_font_size():
    """The measured ink height of a real compiled label glyph falls inside the tolerance band.

    Presence of ink is asserted first (the box must find something), before the height itself
    is checked against the band -- so this cannot pass by having measured nothing.
    """
    raster = _compiled_schematic_page()

    cx_mm = _grid_to_mm(_LABEL_X_G)
    top_mm = _grid_to_mm(_LABEL_Y_G)
    baseline_mm = top_mm + float(_EXPECTED_FONT_SIZE_MM * ASCENT_RATIO)

    # Generous box, not a tight crop around the correct-size glyph: wide/tall enough to
    # capture the OLD bug's ~6.4x-too-large glyph in full too (not just a box-clipped
    # fragment of it), so the can-fail probe below measures the real broken ink height, not
    # an artifact of a too-small scan window.
    box = _png.Box(
        x0=_px(cx_mm - 5), x1=_px(cx_mm + 10), y0=_px(top_mm - 20), y1=_px(baseline_mm + 3)
    )
    bbox = _png.ink_bbox(raster, box, threshold=245)
    assert bbox is not None, "no label ink found at all"

    _min_x, min_y, _max_x, max_y = bbox
    height_px = max_y - min_y + 1
    height_mm = height_px * 25.4 / PPI

    assert _MIN_INK_HEIGHT_MM <= height_mm <= _MAX_INK_HEIGHT_MM, (
        height_mm,
        _MIN_INK_HEIGHT_MM,
        _MAX_INK_HEIGHT_MM,
    )
