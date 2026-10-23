"""`STYLE` holds every constant render reads from the model and the symbols today (el-0004)."""

from fransys_el import REF_TINTS, style

from electrical_symbols import G_PER_MODULE, LIBRARY, WIRING_GRID
from fransys_model.derive import print_sizes as sizes

STYLE = style(LIBRARY)


def _dash(name: str) -> tuple[float, ...]:
    return dict(STYLE.dashes)[name]


def test_the_pens_and_dashes_equal_the_print_sizes():
    assert STYLE.line_thin_mm == float(sizes.LINE_THIN_MM)
    assert STYLE.line_thick_mm == float(sizes.LINE_THICK_MM)
    assert STYLE.line_rule_mm == float(sizes.LINE_RULE_MM)
    assert STYLE.junction_dot_mm == float(sizes.JUNCTION_DOT_MM)
    assert _dash("long") == (float(sizes.DASH_LONG_MM), float(sizes.DASH_GAP_MM))
    assert _dash("outline") == tuple(float(d) for d in sizes.OUTLINE_DASHES_MM)
    assert _dash("symbol") == (float(sizes.SYMBOL_DASH_MM), float(sizes.SYMBOL_DASH_GAP_MM))


def test_the_grid_the_tints_and_the_font_equal_their_homes():
    assert STYLE.tints == REF_TINTS
    assert STYLE.wiring_grid == WIRING_GRID
    assert STYLE.g_per_module == G_PER_MODULE
    assert STYLE.module_mm == 2.5
    assert LIBRARY.font is not None
    label = dict(STYLE.texts)["label"]
    assert (label.height_mm, label.family) == (
        float(LIBRARY.font.heights["smallest"]),
        LIBRARY.font.family,
    )


def test_every_library_wire_style_has_a_pen():
    wires = dict(STYLE.wires)
    assert set(wires) == {wire.id for wire in LIBRARY.wires}
    assert wires["trunk"].width_mm == STYLE.line_thick_mm
    assert wires["wire"].width_mm == STYLE.line_thin_mm
    assert wires["wire"].dash_mm == ()
    assert wires["link"].dash_mm == _dash("symbol")
