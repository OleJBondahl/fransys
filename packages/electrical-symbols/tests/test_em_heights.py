"""`em_heights` is `symdef.em_height` of each capital height asked for (es-0089, es-0090)."""

from dataclasses import replace

from symdef import em_height

from electrical_symbols import LIBRARY, em_heights


def test_each_capital_height_asked_for_is_its_em():
    font = LIBRARY.font
    assert font is not None
    got = em_heights(LIBRARY, [1.8, 2.2, 5.0])
    assert set(got) == {1.8, 2.2, 5.0}
    assert got[2.2] == em_height(font, 2.2)
    assert got[1.8] > 1.8  # an em is taller than its capital


def test_a_library_without_a_font_gives_no_em():
    assert em_heights(replace(LIBRARY, font=None), [1.8]) == {}
