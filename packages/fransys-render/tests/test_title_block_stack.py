"""The title-block stack grows with the band: a label clears its value at the need (TS1)."""

from decimal import Decimal

import pytest
from fransys_render._symbols import CAP_RATIO

from electrical_symbols import title_block
from fransys_model.derive.print_sizes import (
    DESCENDER_RATIO,
    TextRole,
    font_size_mm,
    role_height_mm,
)
from fransys_model.derive.title_band import title_band_need

_FIELDS = ("title", "number", "revision", "revision_date", "customer", "author", "page_title")
_FIELDS += ("scope", "sheet", "page")
# the authored label and value centres of the 20 mm symbol, read off the unstretched toml
_HOUSE = {
    "title": (3.25, 6.375),
    "number": (3.25, 6.375),
    "revision": (3.25, 6.375),
    "revision_date": (3.25, 6.375),
    "customer": (13.25, 16.375),
    "author": (13.25, 16.375),
    "page_title": (13.25, 16.375),
    "scope": (13.25, 16.375),
    "sheet": (13.25, 16.375),
    "page": (13.25, 16.375),
}


def _fonts(text_height: str) -> tuple[float, float]:
    def font(role):
        return float(font_size_mm(role_height_mm(role, Decimal(text_height))))

    return font(TextRole.LABEL), font(TextRole.BODY)


def _centres(band: float, *, notice: bool) -> dict[str, tuple[float, float]]:
    block = title_block((0, 0), 200, band, notice=notice)
    y = {s.id: s.position.y for part in (block.lines, block.bold, block.labels) for s in part.slots}
    return {f: (y[f"label.{f}"], y[f]) for f in _FIELDS}


@pytest.mark.parametrize("notice", [False, True])
@pytest.mark.parametrize("text_height", ["3.5", "4", "5"])
def test_label_and_value_clear_each_other_at_the_need(text_height, notice):
    label, body = _fonts(text_height)
    half_caps = (label + body) * CAP_RATIO / 2
    for field, (low, high) in _centres(title_band_need(label, body), notice=notice).items():
        assert high - low >= half_caps - 1e-9, field


@pytest.mark.parametrize("notice", [False, True])
def test_the_house_band_keeps_every_slot_where_the_symbol_authored_it(notice):
    assert _centres(20, notice=notice) == pytest.approx(_HOUSE)


@pytest.mark.parametrize("notice", [False, True])
@pytest.mark.parametrize("text_height", ["2.5", "3.5", "4", "5"])
def test_a_label_descender_stays_above_its_value_capitals_at_the_need(text_height, notice):
    """Label centre + half its caps + its descender is above the value's cap top (y grows down)."""
    label, body = _fonts(text_height)
    band = title_band_need(label, body)
    for field, (low, high) in _centres(band, notice=notice).items():
        descender_line = low + label * CAP_RATIO / 2 + label * float(DESCENDER_RATIO)
        assert descender_line <= high - body * CAP_RATIO / 2 + 1e-9, field


@pytest.mark.parametrize("text_height", ["3.5", "4", "5"])
def test_the_need_equals_the_gap_the_symbol_gives(text_height):
    """derive's centre gap (the house 3.125 scaled by the font sizes) is what the cuts give."""
    label, body = _fonts(text_height)
    house = sum(_fonts("1.8"))
    low, high = _centres(title_band_need(label, body), notice=False)["title"]
    assert high - low == pytest.approx(3.125 * (label + body) / house)
