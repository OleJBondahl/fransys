"""D6: a placement's real symbol body; the last-paragraph placeholder for an unknown key."""

import re
from decimal import Decimal

from fransys_render import pages
from fransys_render._numbers import format_decimal, grid_to_mm
from fransys_render._symbol_geometry import oriented_symbol
from fransys_render._symbols import _rect_glyph, _text_glyph, symbols_group, symbols_on_page
from graphical_symbols import to_fragment
from graphical_symbols.geometry import Line

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    Orientation,
    Page,
    PageRole,
    SheetFormat,
    SymbolPlacement,
    layout_of,
    profile_of,
)
from fransys_model.vocab import Function, FunctionKind, Item, Port, PortRole

_ORIGIN = Origin(file="packages/fransys-render/tests/test_symbols.py", line=1, note="invented")

_BOGUS_KEY = "no-such-symbol-key"
_REAL_KEY = "make-contact"


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part, *, number=1):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=number, produced_by="test"
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


def _pin(key_part, designation, *, installed=True):
    """A bare item/function/port, one pin (mirrors `test_markers.py:_pin`)."""
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
        name="1",
        role=PortRole.GENERIC,
    )
    return item, fn, port


def _placement(key_part, *, function, page, symbol, x, y):  # noqa: PLR0913 -- one keyword per field
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
        symbol=symbol,
        library_version="test",
        produced_by="test",
    )


def _one_placement_model(symbol, *, key_part="p"):
    drawing_set = _drawing_set(key_part)
    sheet = _sheet_format(key_part)
    page = _page(key_part, drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin(key_part, "K1")
    placement = _placement(key_part, function=fn, page=page, symbol=symbol, x=100, y=100)
    model = _model(drawing_set, sheet, page, item, fn, port, placement)
    return model, page, placement


# --- 1. Exact rectangle coordinates and escaped text, hand-computed -----------------------------


def test_placeholder_rect_and_text_are_exact_for_a_bogus_key():
    model, page, _ = _one_placement_model(_BOGUS_KEY)

    # 8x8 G box centred on (100, 100): (96, 96) to (104, 104) in grid units.
    # content_x_mm=content_y_mm=10, module_mm=2.5:
    # grid_to_mm(10, 96, 2.5) = 10 + 96*2.5/8 = 40 ; grid_to_mm(10, 104, 2.5) = 42.5.
    # width = height = 2.5.
    expected_rect = '<rect class="symbol" x="40" y="40" width="2.5" height="2.5"/>'

    # Text baseline mirrors `_markers.py`'s `_text_element`: top of the box (40) plus
    # font_size_mm * ASCENT_RATIO. font_size_mm = grid_to_mm(0, 8, 2.5) = 2.5.
    # ASCENT_RATIO = 1420/2048 = 355/512 ; 2.5 * 355/512 = 1775/1024 = 1.7333984375.
    # baseline = 40 + 1.7333984375 = 41.7333984375.
    # x_mm (horizontally centred) = grid_to_mm(10, 100, 2.5) = 10 + 100*2.5/8 = 41.25.
    expected_text = (
        '<text class="label" text-anchor="middle" x="41.25" y="41.7333984375" '
        'font-size="2.5">no-such-symbol-key</text>'
    )

    group = symbols_group(model, page)
    assert expected_rect in group
    assert expected_text in group


# --- 2. The transform composition, hand-verified independently of this package's code ----------

_TRANSFORM_RE = re.compile(r"translate\(([^,]+),([^)]+)\)\s*scale\(([^)]+)\)")


def _apply_translate_then_scale(transform: str, x: float, y: float) -> tuple[Decimal, Decimal]:
    """Independently work out where `(x, y)` lands under `transform`, by SVG's own composition
    rule (right-to-left onto a point): `scale` is applied to the point first, `translate` second.
    Parses the transform string with a regex, not by calling any of this package's own code.
    """
    match = _TRANSFORM_RE.fullmatch(transform)
    assert match is not None, transform
    tx, ty, s = (Decimal(g) for g in match.groups())
    return tx + Decimal(x) * s, ty + Decimal(y) * s


def test_transform_composition_is_translate_then_scale_hand_verified():
    """The single most important test in this part (per the work order): a real symbol's
    element sits at a known local module-unit coordinate; the placement/sheet fix a known
    absolute mm position by hand; the transform this package emits, independently
    interpreted by SVG's own composition rule, must land the element exactly there.
    """
    model, page, _placement = _one_placement_model(_REAL_KEY, key_part="xform")

    # By hand, from `_sheet_format`'s fixed constants (content_x_mm=content_y_mm=10,
    # module_mm=2.5) and the placement's (x, y) = (100, 100):
    # x_mm = 10 + 100*2.5/8 = 41.25 ; y_mm = 10 + 100*2.5/8 = 41.25.
    expected_x_mm, expected_y_mm, expected_module_mm = "41.25", "41.25", "2.5"

    group = symbols_group(model, page)
    transform_match = re.search(r'transform="([^"]+)"', group)
    assert transform_match is not None, group
    transform = transform_match.group(1)
    assert transform == f"translate({expected_x_mm},{expected_y_mm}) scale({expected_module_mm})"

    # `make-contact`'s first element is `Line(start=(0, -2), end=(0, -1))` (checked directly
    # against the installed toolkit library, not re-derived): local (0, -2), scaled by 2.5
    # first -> (0, -5), then translated by (41.25, 41.25) -> (41.25, 36.25).
    symbol = LIBRARY.get(_REAL_KEY)
    first = symbol.elements[0]
    assert isinstance(first, Line), first
    start_x, start_y = float(first.start.x), float(first.start.y)
    got_x, got_y = _apply_translate_then_scale(transform, start_x, start_y)
    assert (got_x, got_y) == (Decimal("41.25"), Decimal("36.25"))


# --- 3. A real placement, and generic-box, each draw their own real fragment ---------------------


def test_a_real_placement_draws_its_toolkit_fragment():
    model, page, placement = _one_placement_model(_REAL_KEY, key_part="real")

    # Computed independently by calling the toolkit functions directly, not by re-deriving
    # this package's own logic.
    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    fragment = to_fragment(symbol)
    x_mm = format_decimal(grid_to_mm(10, placement.x, Decimal("2.5")))
    y_mm = format_decimal(grid_to_mm(10, placement.y, Decimal("2.5")))
    expected = f'<g class="symbol" transform="translate({x_mm},{y_mm}) scale(2.5)">{fragment}</g>'

    assert expected in symbols_group(model, page)


def test_generic_box_draws_a_real_fragment_too():
    model, page, placement = _one_placement_model(GENERIC_BOX_KEY, key_part="gb")

    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    fragment = to_fragment(symbol)

    group = symbols_group(model, page)
    assert group != ""
    assert '<g class="symbol"' in group
    assert fragment in group


# --- 4. Ordering: multiple unknown-key placements draw in `id` order (D11) ----------------------


def test_unknown_placements_are_ordered_by_id():
    drawing_set = _drawing_set("t3")
    sheet = _sheet_format("t3")
    page = _page("t3", drawing_set=drawing_set, sheet_format=sheet)

    pins = [_pin(f"t3-{n}", f"K{n}") for n in range(4)]
    placements = [
        _placement(f"t3-{n}", function=fn, page=page, symbol=_BOGUS_KEY, x=n * 100, y=100)
        for n, (_item, fn, _port) in enumerate(pins)
    ]
    records = [rec for triple in pins for rec in triple] + placements
    model = _model(drawing_set, sheet, page, *records)

    ordered = symbols_on_page(model, page)
    expected_count = 4
    assert len(ordered) == expected_count
    assert list(ordered) == sorted(placements, key=lambda p: p.id)

    group = symbols_group(model, page)

    def _rect_x(placement):
        # x1_mm for placement.x - 4, content_x_mm=10, module_mm=2.5 (matches `_rect_glyph`).
        return format_decimal(grid_to_mm(sheet.content_x_mm, placement.x - 4, sheet.module_mm))

    order_positions = [group.index(f'<rect class="symbol" x="{_rect_x(p)}"') for p in ordered]
    assert order_positions == sorted(order_positions)


# --- 5. `pages` never raises for an unknown key; `symbols_on_page` is used by both ---------------


def test_pages_never_raises_for_an_unknown_key():
    model, page, _ = _one_placement_model(_BOGUS_KEY, key_part="p4")
    svgs = pages(model)
    assert len(svgs) == 1
    svg = next(iter(svgs.values()))
    assert 'class="symbol"' in svg
    assert layout_of(model, Page)[page.id] is page


# --- 6. not-installed for a symbol body (D10) -----------------------------------------------------


def test_not_installed_symbol_body_gets_the_extra_class():
    drawing_set = _drawing_set("t6")
    sheet = _sheet_format("t6")
    page = _page("t6", drawing_set=drawing_set, sheet_format=sheet)

    item_off, fn_off, port_off = _pin("t6-off", "K1", installed=False)
    placement_off = _placement("t6-off", function=fn_off, page=page, symbol=_REAL_KEY, x=0, y=0)
    item_on, fn_on, port_on = _pin("t6-on", "K2", installed=True)
    placement_on = _placement("t6-on", function=fn_on, page=page, symbol=_REAL_KEY, x=100, y=0)

    model = _model(
        drawing_set,
        sheet,
        page,
        item_off,
        fn_off,
        port_off,
        placement_off,
        item_on,
        fn_on,
        port_on,
        placement_on,
    )

    group = symbols_group(model, page)
    assert 'class="symbol not-installed"' in group
    # a plain "symbol" class also occurs standalone (the installed placement), not only as a
    # prefix of "symbol not-installed" -- check the exact standalone token is present too.
    assert group.count('class="symbol"') == 1
    assert group.count('class="symbol not-installed"') == 1


def test_not_installed_symbol_css_rules_are_present_in_the_style_block():
    """Mirrors PART 2c's `text.not-installed` rule-presence test: the new descendant and
    attribute selectors this part adds must actually be in `style_block()`'s output.
    """
    from fransys_render._style import style_block

    # `.not-installed *` reaches inside a symbol's own `<g transform="... scale(module_mm)">`
    # (the "marker box" work package's PART C, found while fixing the sibling `mm`-suffix
    # bug): a bare `0.25` there would render as `0.25 * module_mm` mm once that ancestor
    # transform applies, so the rule divides by `module_mm` first -- `0.1` at `module_mm=2.5`
    # renders back to the intended 0.25 mm.
    block = style_block(Decimal("2.5"))
    assert ".not-installed * { stroke: grey; stroke-dasharray: 0.1; }" in block
    assert ".not-installed [fill] { fill: grey; }" in block


# --- 7. A filled element's raw fragment is untouched (the CSS does the work, not a rewrite) ------


def test_filled_element_fragment_is_untouched_by_not_installed():
    """`connection-point`'s one element is a solid-filled circle (`fill="solid"` in its TOML,
    read directly from the installed library, not assumed). The not-installed treatment is a
    CSS rule (`_style.py`'s `.not-installed [fill]`), never a rewrite of the toolkit's own
    fragment text -- so the raw `fill="#000"` attribute must still be there, verbatim, inside
    the `not-installed` wrapper. The rendered *colour* this produces is proved separately, on
    compiled output, by `tests/test_symbol_not_installed_compiles_grey.py` (root tests/,
    render-0001): a raw SVG string has no cascade to resolve `.not-installed [fill]` against.
    """
    drawing_set = _drawing_set("t7")
    sheet = _sheet_format("t7")
    page = _page("t7", drawing_set=drawing_set, sheet_format=sheet)
    item, fn, port = _pin("t7", "K1", installed=False)
    placement = _placement("t7", function=fn, page=page, symbol="connection-point", x=0, y=0)
    model = _model(drawing_set, sheet, page, item, fn, port, placement)

    symbol = LIBRARY.get("connection-point")
    fragment = to_fragment(symbol)
    assert 'fill="#000"' in fragment

    group = symbols_group(model, page)
    assert 'class="symbol not-installed"' in group
    assert fragment in group


# --- 8. Both real goldens render every placement without error -----------------------------------


def test_both_goldens_render_every_symbol_placement(cabinet_laid_out, cabinet_narrow_laid_out):
    for model in (cabinet_laid_out, cabinet_narrow_laid_out):
        placements = layout_of(model, SymbolPlacement)
        assert len(placements) > 0

        svgs = pages(model)
        assert len(svgs) > 0
        for svg in svgs.values():
            assert '<g class="symbol' in svg


# --- 9. `pages()` stays deterministic once it draws real symbol bodies ---------------------------


def test_pages_is_still_deterministic_for_a_real_golden(cabinet_laid_out):
    assert pages(cabinet_laid_out) == pages(cabinet_laid_out)


# --- 10. `symbols_group` joins its parts with `""`, not any separator ---------------------------


def test_symbols_group_concatenates_placement_output_with_no_separator():
    """Two unknown-key placements on one page: the exact returned string is the
    `_rect_glyph`/`_text_glyph` pairs, in `.id` order (`symbols_on_page`), with nothing
    between them -- built from the same private helpers `symbols_group` itself calls, never
    a hand-typed literal.
    """
    drawing_set = _drawing_set("t9")
    sheet = _sheet_format("t9")
    page = _page("t9", drawing_set=drawing_set, sheet_format=sheet)

    pins = [_pin(f"t9-{n}", f"K{n}") for n in range(2)]
    placements = [
        _placement(f"t9-{n}", function=fn, page=page, symbol=_BOGUS_KEY, x=n * 100, y=100)
        for n, (_item, fn, _port) in enumerate(pins)
    ]
    records = [rec for triple in pins for rec in triple] + placements
    model = _model(drawing_set, sheet, page, *records)

    profile = profile_of(model)
    ordered = symbols_on_page(model, page)
    expected_placement_count = 2
    assert len(ordered) == expected_placement_count
    expected = "".join(_rect_glyph(sheet, p) + _text_glyph(sheet, profile, p) for p in ordered)
    assert symbols_group(model, page) == expected
