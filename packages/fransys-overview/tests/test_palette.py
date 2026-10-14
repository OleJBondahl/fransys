"""A6: every palette colour passes 3:1 against its theme's background (WCAG 1.4.11)."""

import pytest
from fransys_overview._palette import ALERT, BACKGROUND, HUES, NEUTRAL, palette_data

_THEMES = {"light": 1, "dark": 2}
_ALL = (*HUES, ALERT, NEUTRAL)


def _luminance(colour: str) -> float:
    rgb = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("theme", _THEMES)
@pytest.mark.parametrize("entry", _ALL, ids=[e[0] for e in _ALL])
def test_every_colour_has_3_to_1_against_its_background(entry, theme):
    colour = entry[_THEMES[theme]]
    assert _contrast(colour, BACKGROUND[theme]) >= 3.0, (entry[0], theme, colour)


def test_the_data_the_page_reads_is_the_table():
    data = palette_data()
    assert [h["dark"] for h in data["hues"]] == [h[2] for h in HUES]
    assert data["neutral"]["light"] == NEUTRAL[1]


def test_the_contrast_check_can_fail():
    assert _contrast("#0077BB", BACKGROUND["dark"]) < 3.0
