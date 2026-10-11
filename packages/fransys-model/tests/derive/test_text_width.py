"""The one text width (model-0190): table units, grid width rounded up, unknown = widest."""

from fransys_model.derive.text_width import UNITS_PER_EM, marking_widths, text_units, text_width


def test_units_sum_the_advances():
    assert text_units("") == 0
    assert text_units("ii") == 2 * text_units("i")
    assert text_units("W") > text_units("i")


def test_bold_differs_from_regular():
    assert text_units("Bold text", bold=True) > text_units("Bold text")


def test_unknown_glyph_is_the_widest_advance():
    widest = max(text_units(chr(c)) for c in range(0x20, 0x7F))
    assert text_units("☃") >= widest
    assert text_units("a☃") == text_units("a") + text_units("☃")


def test_grid_width_rounds_up_and_never_under_measures():
    for height in (1, 7, 8, 9, 40):
        width = text_width("-K12 Wii", height=height)
        exact = text_units("-K12 Wii") * height
        assert width * UNITS_PER_EM >= exact
        assert (width - 1) * UNITS_PER_EM < exact


def test_height_zero_and_empty():
    assert text_width("-K1", height=0) == 0
    assert text_width("", height=8) == 0


def test_one_em_at_em_height():
    assert text_width("0", height=UNITS_PER_EM) == text_units("0")


def test_marking_widths_set_each_marking_one_module_high():
    assert marking_widths(["A1", "", "W"]) == tuple(
        text_width(m, height=8) for m in ("A1", "", "W")
    )
    assert marking_widths(["W"])[0] > marking_widths(["i"])[0] > 0
