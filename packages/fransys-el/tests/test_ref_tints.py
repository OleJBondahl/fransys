"""`fransys_el.REF_TINTS`: eight distinct light tints that keep black text legible (el-0001)."""

import re

from fransys_el import REF_TINTS

from fransys_model.derive.marker_text import REF_SLOTS

_HEX = re.compile(r"#[0-9a-f]{6}")
_MIN_LIGHTNESS = 0.85  # OKLab L; the ruled values sit at 0.86


def _rgb(tint: str) -> tuple[int, ...]:
    return tuple(int(tint[i : i + 2], 16) for i in (1, 3, 5))


def _lin(c: int) -> float:
    v = c / 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _contrast_with_black(tint: str) -> float:
    r, g, b = (_lin(c) for c in _rgb(tint))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b + 0.05) / 0.05


def _oklab_lightness(tint: str) -> float:
    r, g, b = (_lin(c) for c in _rgb(tint))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_


def test_there_are_eight_tints():
    assert len(REF_TINTS) == 8


def test_every_tint_is_a_lowercase_hex_colour():
    assert all(_HEX.fullmatch(t) for t in REF_TINTS)


def test_no_two_tints_are_the_same():
    assert len(set(REF_TINTS)) == len(REF_TINTS)


def test_every_tint_keeps_black_text_at_seven_to_one():
    assert min(_contrast_with_black(t) for t in REF_TINTS) >= 7


def test_contrast_check_sees_a_black_tint():
    assert _contrast_with_black("#000000") < 7


def test_every_tint_is_light_enough():
    assert min(_oklab_lightness(t) for t in REF_TINTS) >= _MIN_LIGHTNESS


def test_lightness_check_sees_a_dark_tint():
    assert _oklab_lightness("#000000") < _MIN_LIGHTNESS


def test_the_count_equals_the_slot_count():
    assert len(REF_TINTS) == REF_SLOTS
