"""Unit boundaries: one dash-dot outline per `layout.outline` record (units spec U1, I2a).

Layout owns the rectangle and the title label; render draws the record as it is.
"""

import re
from decimal import Decimal

from fransys_render import pages
from fransys_render._numbers import grid_to_mm
from fransys_render._outlines import _outline_glyph, outlines_group

from electrical_symbols import GENERIC_BOX_KEY
from fransys_model.derive.drawing_text import label_text
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    Orientation,
    Outline,
    Page,
    PageRole,
    SheetFormat,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole, Unit, UnitRelease

_ORIGIN = Origin(file="packages/fransys-render/tests/test_outlines.py", line=1, note="invented")

_POLYLINE_RE = re.compile(r'<polyline class="unit-boundary" points="([^"]*)"/>')
_EXPECTED_TWO_OUTLINE_COUNT = 2  # one per record, never merged


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part, *, number=1, unit=None):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key),
        key=key,
        location=None,
        unit=unit,
        number=number,
        produced_by="test",
    )


def _page(key_part, *, drawing_set, sheet_format, number=1):
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format.id,
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


def _unit(key_part, *, name, revision, parent=None, title=""):
    """The `Unit` and the `UnitRelease` it is an instance of (version 1)."""
    release_key = ("unit_release", name, "1", str(revision))
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name=name,
        version=1,
        revision=revision,
        interface="1",
        title=title,
    )
    key = ("unit", key_part)
    return Unit(id=make_id(Unit, key), key=key, release=release.id, parent=parent), release


def _pin(key_part, designation, *, unit=None):
    """A bare item/function/port, one pin (mirrors `test_markers.py:_pin`); `unit` is the
    item's own unit membership (units spec U1), `None` by default.
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
        unit=unit,
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


def _outline(key_part, *, unit, page, x, y, width, height):  # noqa: PLR0913 -- one per field
    key = ("outline", key_part)
    return Outline(
        id=make_id(Outline, key),
        key=key,
        unit=unit.id,
        page=page.id,
        x=x,
        y=y,
        width=width,
        height=height,
        produced_by="test",
    )


def _box_mm(sheet, box_g):
    min_x, min_y, max_x, max_y = box_g
    return (
        grid_to_mm(sheet.content_x_mm, min_x, sheet.module_mm),
        grid_to_mm(sheet.content_y_mm, min_y, sheet.module_mm),
        grid_to_mm(sheet.content_x_mm, max_x, sheet.module_mm),
        grid_to_mm(sheet.content_y_mm, max_y, sheet.module_mm),
    )


def _parsed_polyline_bounds_mm(points_attr):
    """The `<polyline>`'s own drawn bounds, parsed back from its `points` attribute (mm)."""
    points = [tuple(Decimal(v) for v in pair.split(",")) for pair in points_attr.split(" ")]
    xs = [x for x, _y in points]
    ys = [y for _x, y in points]
    return min(xs), min(ys), max(xs), max(ys)


# --- 1. The record's rectangle is drawn exactly, measured by nothing in render --------------------


def test_an_outline_record_is_drawn_at_its_own_rectangle():
    drawing_set = _drawing_set("t1", unit=None)
    sheet = _sheet_format("t1")
    page = _page("t1", drawing_set=drawing_set, sheet_format=sheet)
    unit, release = _unit("t1", name="io-board", revision=1)
    outline = _outline("t1", unit=unit, page=page, x=-20, y=-8, width=300, height=40)

    model = _model(drawing_set, sheet, page, release, unit, outline)

    (points,) = _POLYLINE_RE.findall(outlines_group(model, page))
    assert _parsed_polyline_bounds_mm(points) == _box_mm(sheet, (-20, -8, 280, 32))


# --- 2. Two records on one page: two outlines; another page's record is not drawn here -----------


def test_two_outline_records_on_one_page_draw_two_outlines_and_no_other_pages():
    drawing_set = _drawing_set("t3", unit=None)
    sheet = _sheet_format("t3")
    page = _page("t3", drawing_set=drawing_set, sheet_format=sheet)
    other_page = _page("t3-other", drawing_set=drawing_set, sheet_format=sheet, number=2)
    unit_a, release_a = _unit("t3a", name="io-board", revision=1)
    unit_b, release_b = _unit("t3b", name="power-board", revision=2)
    a = _outline("t3-a", unit=unit_a, page=page, x=0, y=0, width=80, height=40)
    b = _outline("t3-b", unit=unit_b, page=page, x=1000, y=1000, width=80, height=40)
    elsewhere = _outline("t3-c", unit=unit_b, page=other_page, x=0, y=0, width=8, height=8)

    model = _model(
        drawing_set, sheet, page, other_page, release_a, release_b, unit_a, unit_b, a, b, elsewhere
    )

    matches = _POLYLINE_RE.findall(outlines_group(model, page))
    assert len(matches) == _EXPECTED_TWO_OUTLINE_COUNT
    drawn = {_parsed_polyline_bounds_mm(points) for points in matches}
    assert drawn == {_box_mm(sheet, (0, 0, 80, 40)), _box_mm(sheet, (1000, 1000, 1080, 1040))}


def test_outlines_group_concatenates_glyphs_with_no_separator():
    """`outlines_group` joins its glyphs with `""` (D8-style join): the exact returned string
    is the concatenation of the two individual `_outline_glyph` calls, in `.id` order, with
    nothing between them.
    """
    drawing_set = _drawing_set("t4", unit=None)
    sheet = _sheet_format("t4")
    page = _page("t4", drawing_set=drawing_set, sheet_format=sheet)
    unit_a, release_a = _unit("t4a", name="io-board", revision=1)
    unit_b, release_b = _unit("t4b", name="power-board", revision=2)
    a = _outline("t4-a", unit=unit_a, page=page, x=0, y=0, width=80, height=40)
    b = _outline("t4-b", unit=unit_b, page=page, x=1000, y=1000, width=80, height=40)

    model = _model(drawing_set, sheet, page, release_a, release_b, unit_a, unit_b, a, b)

    first, second = sorted((a, b), key=lambda outline: outline.id)
    expected = _outline_glyph(sheet, first) + _outline_glyph(sheet, second)
    assert outlines_group(model, page) == expected


def test_outline_glyph_closes_back_to_the_first_vertex_not_the_second():
    """The closed polyline's last point equals its first (`vertices[0]`), not its second
    (`vertices[1]`, the mutant): a non-square box makes the two corners distinct.
    """
    sheet = _sheet_format("t5")
    drawing_set = _drawing_set("t5", unit=None)
    page = _page("t5", drawing_set=drawing_set, sheet_format=sheet)
    unit, _release = _unit("t5", name="io-board", revision=1)
    outline = _outline("t5", unit=unit, page=page, x=0, y=0, width=80, height=40)

    glyph = _outline_glyph(sheet, outline)
    (points,) = _POLYLINE_RE.findall(glyph)
    pairs = points.split(" ")
    assert pairs[1] != pairs[0], "fixture must be non-square for this check to be meaningful"
    assert pairs[-1] == pairs[0]


# --- 3. The title is an ordinary label: "<unit label> rev <revision>" (model-0066) -------------


def test_the_outline_title_label_reads_unit_title_rev_revision():
    _assert_outline_title("t2", title="IO board", expected="IO board rev 1.3")


def test_the_outline_title_label_reads_the_name_when_the_unit_has_no_title():
    _assert_outline_title("t2b", title="", expected="io-board rev 1.3")


def _assert_outline_title(key_part, *, title, expected):
    drawing_set = _drawing_set(key_part, unit=None)
    sheet = _sheet_format(key_part)
    page = _page(key_part, drawing_set=drawing_set, sheet_format=sheet)
    unit, release = _unit(key_part, name="io-board", revision=3, title=title)
    item, fn, port = _pin(key_part, "K1", unit=unit.id)
    key = ("label", key_part)
    label = Label(
        id=make_id(Label, key),
        key=key,
        page=page.id,
        function=fn.id,
        port=None,
        conductor=None,
        kind=LabelKind.TAG,
        slot="outline_title",
        x=0,
        y=0,
        width=4,
        height=2,
        produced_by="test",
    )

    model = _model(drawing_set, sheet, page, release, unit, item, fn, port, label)

    assert label_text(model, label) == expected
    assert f">{expected}</text>" in next(iter(pages(model).values()))


# --- 4. No outline record: `outlines_group` draws nothing, on a fresh model and on every ---------
# --- real golden (none of which has any `unit` record yet) --------------------------------------


def test_pages_with_no_outline_record_render_no_outline():
    drawing_set = _drawing_set("t5", unit=None)
    sheet = _sheet_format("t5")
    page = _page("t5", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("t5", "K1", unit=None)
    placement = _placement("t5", function=fn, page=page, x=0, y=0)
    model = _model(drawing_set, sheet, page, item, fn, port, placement)

    assert outlines_group(model, page) == ""


# Page counts, per golden (`conftest.py`'s own docstrings for the wide/narrow counts;
# the two-location golden's counted directly, `layout_of(model, Page)`).
_WIDE_GOLDEN_PAGE_COUNT = 2
_NARROW_GOLDEN_PAGE_COUNT = 4  # was 5: harness lines (HL15-HL18) merge sup page 1 into page 0
# 2, not 3: the golden's `=P1` and `sup` groups now share drawing set c1's page 1 (deep-dive D4,
# "groups pack onto pages by their measured widths"), and `=P2` (drawing set c2) is the second.
_TWO_LOCATION_GOLDEN_PAGE_COUNT = 2


def test_real_goldens_render_no_outline(
    cabinet_laid_out, cabinet_narrow_laid_out, cabinet_two_location_laid_out
):
    goldens = (
        (cabinet_laid_out, _WIDE_GOLDEN_PAGE_COUNT),
        (cabinet_narrow_laid_out, _NARROW_GOLDEN_PAGE_COUNT),
        (cabinet_two_location_laid_out, _TWO_LOCATION_GOLDEN_PAGE_COUNT),
    )
    checked = 0
    for model, expected_page_count in goldens:
        model_pages = layout_of(model, Page)
        assert len(model_pages) == expected_page_count
        for page in model_pages.values():
            assert outlines_group(model, page) == ""
            checked += 1
    assert checked == _WIDE_GOLDEN_PAGE_COUNT + _NARROW_GOLDEN_PAGE_COUNT + (
        _TWO_LOCATION_GOLDEN_PAGE_COUNT
    )
    for model, _expected_page_count in goldens:
        for svg in pages(model).values():
            assert 'class="unit-boundary"' not in svg
