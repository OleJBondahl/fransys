"""The title-block stack grows with the band: a label clears its value at the need (TS1)."""

import dataclasses
from decimal import Decimal

import pytest
from fransys_render._library import capital_ratio
from library_records import drawing_library, freeze

from electrical_symbols import LIBRARY, title_block
from fransys_model.derive.print_sizes import TextRole, font_size_mm, role_height_mm
from fransys_model.derive.title_band import title_band_need
from fransys_model.kernel import Draft, Origin, evolve

_MODEL = freeze(Draft())
_ORIGIN = Origin(file="test_title_block_stack.py", line=1, note="test library")
_DESCENDER_RATIO = Decimal(426) / Decimal(2048)  # the bundled font's descender over its em
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


def _model_at(text_height: str):
    """`_MODEL` whose library prints the label at `text_height` mm capitals and the body at the larger of that and 2.5."""
    label = Decimal(text_height)
    library = drawing_library()
    bigger = {"smallest": label, "body": max(label, Decimal("2.5"))}
    swapped = dataclasses.replace(library, heights=frozendict({**library.heights, **bigger}))
    return evolve(evolve(_MODEL, remove=(library.id,)), put=(swapped,), origin=_ORIGIN)


def _fonts_of(model) -> tuple[float, float]:
    """The label and body font sizes in mm that `model`'s library prints at."""
    sizes = {role: float(font_size_mm(model, role_height_mm(model, role))) for role in TextRole}
    return sizes[TextRole.LABEL], sizes[TextRole.BODY]


def _centres(band: float, *, notice: bool) -> dict[str, tuple[float, float]]:
    block = title_block((0, 0), 200, band, notice=notice)
    y = {s.id: s.position.y for part in (block.lines, block.bold, block.labels) for s in part.slots}
    return {f: (y[f"label.{f}"], y[f]) for f in _FIELDS}


@pytest.mark.parametrize("notice", [False, True])
@pytest.mark.parametrize("text_height", ["3.5", "4", "5"])
def test_label_and_value_clear_each_other_at_the_need(text_height, notice):
    model = _model_at(text_height)
    label, body = _fonts_of(model)
    half_caps = (label + body) * float(capital_ratio(LIBRARY)) / 2
    for field, (low, high) in _centres(title_band_need(model), notice=notice).items():
        assert high - low >= half_caps - 1e-9, field


@pytest.mark.parametrize("notice", [False, True])
def test_the_house_band_keeps_every_slot_where_the_symbol_authored_it(notice):
    assert list(_centres(20, notice=notice).items()) == [(k, pytest.approx(v)) for k, v in _HOUSE.items()]


@pytest.mark.parametrize("notice", [False, True])
@pytest.mark.parametrize("text_height", ["2.5", "3.5", "4", "5"])
def test_a_label_descender_stays_above_its_value_capitals_at_the_need(text_height, notice):
    """Label centre + half its caps + its descender is above the value's cap top (y grows down)."""
    model = _model_at(text_height)
    label, body = _fonts_of(model)
    band = title_band_need(model)
    for field, (low, high) in _centres(band, notice=notice).items():
        descender_line = low + label * float(capital_ratio(LIBRARY)) / 2 + label * float(_DESCENDER_RATIO)
        assert descender_line <= high - body * float(capital_ratio(LIBRARY)) / 2 + 1e-9, field


@pytest.mark.parametrize("text_height", ["3.5", "4", "5"])
def test_the_need_equals_the_gap_the_symbol_gives(text_height):
    """derive's centre gap (the house 3.125 scaled by the font sizes) is what the cuts give."""
    model = _model_at(text_height)
    label, body = _fonts_of(model)
    house = sum(_fonts_of(_model_at("1.8")))
    low, high = _centres(title_band_need(model), notice=False)["title"]
    assert high - low == pytest.approx(3.125 * (label + body) / house)
