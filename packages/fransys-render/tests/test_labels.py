"""Label text and position (D7), and the `not-installed` class (D10)."""

import xml.etree.ElementTree as ET
from decimal import Decimal

from fransys_render import pages
from fransys_render._constants import ASCENT_RATIO
from fransys_render._numbers import format_decimal, grid_to_mm

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    Page,
    PageRole,
    Profile,
    SheetFormat,
    default_profile,
    layout_of,
    profile_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole

_ORIGIN = Origin(file="packages/fransys-render/tests/test_labels.py", line=1, note="invented label")

_SVG_NS = "{http://www.w3.org/2000/svg}"

# `pages()` returns one SVG per `layout.page`; every model here has exactly one page.
_ONE_PAGE = 1


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


def _pin(key_part, designation, *, installed=True, port_name="1"):
    """A bare item/function/port, one pin (mirrors `test_routes_junctions.py:_pin`)."""
    item_key = ("item", key_part)
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag=designation,
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
        name=port_name,
        role=PortRole.GENERIC,
    )
    return item, fn, port


def _label(  # noqa: PLR0913 -- one keyword per field
    key_part, *, page, kind, x, y, function=None, port=None, conductor=None, slot=""
):
    key = ("label", key_part)
    return Label(
        id=make_id(Label, key),
        key=key,
        page=page.id,
        function=None if function is None else function.id,
        port=None if port is None else port.id,
        conductor=None if conductor is None else conductor.id,
        kind=kind,
        slot=slot,
        x=x,
        y=y,
        width=4,
        height=2,
        produced_by="test",
    )


def _authored_profile(key_part, *, sheet_format, text_height):
    key = ("profile", key_part)
    default = default_profile()
    return Profile(
        id=make_id(Profile, key),
        key=key,
        sheet_format=sheet_format.id,
        column_gap=default.column_gap,
        row_gap=default.row_gap,
        route_margin=default.route_margin,
        text_height=text_height,
        marker_padding=default.marker_padding,
        route_turn_penalty=default.route_turn_penalty,
        route_crossing_penalty=default.route_crossing_penalty,
        band_ranks=default.band_ranks,
        group_ranks=default.group_ranks,
    )


def _one_svg(model):
    svgs = pages(model)
    assert len(svgs) == _ONE_PAGE
    return next(iter(svgs.values()))


def _baseline_mm(sheet, y, text_height):
    top_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    font_size_mm = grid_to_mm(0, text_height, sheet.module_mm)
    return top_mm + font_size_mm * ASCENT_RATIO


def _font_size_mm(sheet, text_height):
    return format_decimal(grid_to_mm(0, text_height, sheet.module_mm))


# --- 1. TAG label text and position (D2, D7): hand-computed, not via the package's own code ----


def test_tag_label_text_and_position():
    drawing_set = _drawing_set("t1")
    sheet = _sheet_format("t1")
    page = _page("t1", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("t1", "K1")
    label = _label("t1", page=page, kind=LabelKind.TAG, x=4, y=8, function=fn)

    model = _model(drawing_set, sheet, page, item, fn, port, label)
    svg = _one_svg(model)

    # grid_to_mm(10, 4, 2.5) = 11.25 ; baseline = grid_to_mm(10, 8, 2.5)
    # + grid_to_mm(0, 8, 2.5) * ASCENT_RATIO = 12.5 + 2.5 * 0.693359375 = 14.2333984375.
    # font_size_mm = grid_to_mm(0, 8, 2.5) = 2.5.
    # An item with no `=`/`+` placement renders `-<designation>` (reference_designation).
    x_mm = format_decimal(grid_to_mm(sheet.content_x_mm, 4, sheet.module_mm))
    y_mm = format_decimal(_baseline_mm(sheet, 8, default_profile().text_height))
    font_size_mm = _font_size_mm(sheet, default_profile().text_height)
    expected = f'<text class="label" x="{x_mm}" y="{y_mm}" font-size="{font_size_mm}">-K1</text>'
    assert expected in svg


# --- 2. MARKING label text (D2): a port's name appears verbatim, no dash prefix ----------------


def test_marking_label_text_is_the_port_name_verbatim():
    drawing_set = _drawing_set("t2")
    sheet = _sheet_format("t2")
    page = _page("t2", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("t2", "K2", port_name="A1")
    label = _label("t2", page=page, kind=LabelKind.MARKING, x=0, y=0, port=port)

    model = _model(drawing_set, sheet, page, item, fn, port, label)
    svg = _one_svg(model)

    x_mm = format_decimal(grid_to_mm(sheet.content_x_mm, 0, sheet.module_mm))
    y_mm = format_decimal(_baseline_mm(sheet, 0, default_profile().text_height))
    font_size_mm = _font_size_mm(sheet, default_profile().text_height)
    expected = f'<text class="label" x="{x_mm}" y="{y_mm}" font-size="{font_size_mm}">A1</text>'
    assert expected in svg


# --- 3. XML-escaping round-trip: `<`, `&`, `"` together, parsed back with ElementTree ----------


def test_label_text_escaping_round_trips_through_xml_parsing():
    raw_text = 'A&<B>"C"'
    drawing_set = _drawing_set("t3")
    sheet = _sheet_format("t3")
    page = _page("t3", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("t3", raw_text)
    label = _label("t3", page=page, kind=LabelKind.TAG, x=0, y=0, function=fn)

    model = _model(drawing_set, sheet, page, item, fn, port, label)
    svg = _one_svg(model)

    root = ET.fromstring(svg)  # noqa: S314 -- parsing our own generated SVG, not untrusted input
    text_elements = root.findall(f".//{_SVG_NS}text")
    assert len(text_elements) == 1
    assert text_elements[0].text == f"-{raw_text}"


# --- 4. `not-installed` propagation (D10): via `function` directly -----------------------------


def test_not_installed_propagates_from_function_item():
    drawing_set = _drawing_set("t4")
    sheet = _sheet_format("t4")
    page = _page("t4", drawing_set=drawing_set, sheet_format=sheet)

    item_off, fn_off, port_off = _pin("t4-off", "K1", installed=False)
    label_off = _label("t4-off", page=page, kind=LabelKind.TAG, x=0, y=0, function=fn_off)

    item_on, fn_on, port_on = _pin("t4-on", "K2", installed=True)
    label_on = _label("t4-on", page=page, kind=LabelKind.TAG, x=20, y=0, function=fn_on)

    model = _model(
        drawing_set,
        sheet,
        page,
        item_off,
        fn_off,
        port_off,
        label_off,
        item_on,
        fn_on,
        port_on,
        label_on,
    )
    svg = _one_svg(model)

    y_mm = format_decimal(_baseline_mm(sheet, 0, default_profile().text_height))
    x_off = format_decimal(grid_to_mm(sheet.content_x_mm, 0, sheet.module_mm))
    x_on = format_decimal(grid_to_mm(sheet.content_x_mm, 20, sheet.module_mm))
    font_size_mm = _font_size_mm(sheet, default_profile().text_height)
    assert (
        f'<text class="label not-installed" x="{x_off}" y="{y_mm}" '
        f'font-size="{font_size_mm}">-K1</text>' in svg
    )
    assert f'<text class="label" x="{x_on}" y="{y_mm}" font-size="{font_size_mm}">-K2</text>' in svg


def test_not_installed_text_is_solid_grey_not_dashed_outline():
    """`.not-installed` alone is stroke-only (D10, for symbols/wires); text needs its own rule.

    `<text class="label not-installed">` would otherwise inherit `.not-installed`'s
    `fill: none` from the plain class rule (later in source order than `.label`, so it
    wins the cascade), leaving only a thin dashed glyph outline. The element-qualified
    `text.not-installed` rule overrides that for text specifically: solid grey fill, no
    stroke, no dash.
    """
    from fransys_render._style import style_block

    # `module_mm` doesn't affect this particular rule (`text.not-installed`'s fill/stroke,
    # not `.not-installed *`'s descendant dasharray) -- any sheet's own value proves it.
    assert "text.not-installed { fill: grey; stroke: none; }" in style_block(Decimal("2.5"))


# --- 5. `not-installed` propagation (D10): via `port` -> `function` -> `item`, the two-hop path -


def test_not_installed_propagates_from_port_through_function_to_item():
    drawing_set = _drawing_set("t5")
    sheet = _sheet_format("t5")
    page = _page("t5", drawing_set=drawing_set, sheet_format=sheet)

    item_off, fn_off, port_off = _pin("t5-off", "K1", installed=False, port_name="A1")
    label_off = _label("t5-off", page=page, kind=LabelKind.MARKING, x=0, y=0, port=port_off)

    item_on, fn_on, port_on = _pin("t5-on", "K2", installed=True, port_name="A2")
    label_on = _label("t5-on", page=page, kind=LabelKind.MARKING, x=20, y=0, port=port_on)

    model = _model(
        drawing_set,
        sheet,
        page,
        item_off,
        fn_off,
        port_off,
        label_off,
        item_on,
        fn_on,
        port_on,
        label_on,
    )
    svg = _one_svg(model)

    y_mm = format_decimal(_baseline_mm(sheet, 0, default_profile().text_height))
    x_off = format_decimal(grid_to_mm(sheet.content_x_mm, 0, sheet.module_mm))
    x_on = format_decimal(grid_to_mm(sheet.content_x_mm, 20, sheet.module_mm))
    font_size_mm = _font_size_mm(sheet, default_profile().text_height)
    assert (
        f'<text class="label not-installed" x="{x_off}" y="{y_mm}" '
        f'font-size="{font_size_mm}">A1</text>' in svg
    )
    assert f'<text class="label" x="{x_on}" y="{y_mm}" font-size="{font_size_mm}">A2</text>' in svg


# --- 6. Ordering: labels come out in `id` order (D11) -------------------------------------------


def test_labels_are_ordered_by_id():
    drawing_set = _drawing_set("t6")
    sheet = _sheet_format("t6")
    page = _page("t6", drawing_set=drawing_set, sheet_format=sheet)

    pins = [_pin(f"t6-{n}", f"K{n}") for n in range(5)]
    labels = [
        _label(f"t6-{n}", page=page, kind=LabelKind.TAG, x=n, y=0, function=fn)
        for n, (_item, fn, _port) in enumerate(pins)
    ]
    records = [record for triple in pins for record in triple] + labels
    model = _model(drawing_set, sheet, page, *records)
    svg = _one_svg(model)

    ordered_labels = sorted(layout_of(model, Label).values(), key=lambda label: label.id)
    expected_count = 5
    assert len(ordered_labels) == expected_count

    def _marker(label):
        x_mm = format_decimal(grid_to_mm(sheet.content_x_mm, label.x, sheet.module_mm))
        y_mm = format_decimal(_baseline_mm(sheet, label.y, default_profile().text_height))
        font_size_mm = _font_size_mm(sheet, default_profile().text_height)
        return f'x="{x_mm}" y="{y_mm}" font-size="{font_size_mm}">'

    positions = [svg.index(_marker(label)) for label in ordered_labels]
    assert positions == sorted(positions)


# --- 7. `profile_of` (D7): the house default, or the authored one, with different font sizes ---


def test_profile_of_default_and_authored_give_different_font_sizes():
    drawing_set = _drawing_set("t7")
    sheet = _sheet_format("t7")
    page = _page("t7", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("t7", "K1")
    label = _label("t7", page=page, kind=LabelKind.TAG, x=0, y=0, function=fn)

    default_model = _model(drawing_set, sheet, page, item, fn, port, label)
    assert profile_of(default_model) == default_profile()

    authored = _authored_profile("t7", sheet_format=sheet, text_height=16)
    authored_model = _model(drawing_set, sheet, page, item, fn, port, label, authored)
    assert profile_of(authored_model) == authored
    assert authored.text_height != default_profile().text_height

    default_svg = _one_svg(default_model)
    authored_svg = _one_svg(authored_model)

    default_y = format_decimal(_baseline_mm(sheet, 0, default_profile().text_height))
    authored_y = format_decimal(_baseline_mm(sheet, 0, authored.text_height))
    default_font_size = _font_size_mm(sheet, default_profile().text_height)
    authored_font_size = _font_size_mm(sheet, authored.text_height)
    assert default_y != authored_y
    assert default_font_size != authored_font_size
    assert f'y="{default_y}" font-size="{default_font_size}">-K1</text>' in default_svg
    assert f'y="{authored_y}" font-size="{authored_font_size}">-K1</text>' in authored_svg
