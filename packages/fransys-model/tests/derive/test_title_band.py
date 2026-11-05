"""The title-block band a text size needs (TS2): 20 mm at the house sizes, more for larger text."""

import dataclasses
from decimal import Decimal

import pytest
from derive_helpers import drawing_library, frozen_with_library

from fransys_model.derive.print_sizes import TextRole, font_size_mm, role_height_mm
from fransys_model.derive.title_band import title_band_need
from fransys_model.kernel import Draft, Origin, evolve

MODEL = frozen_with_library(Draft())
_ORIGIN = Origin(file="test_title_band.py", line=1, note="test library")


def _model_at(text_height: str):
    """`MODEL` with a library whose label capitals are `text_height` and body the larger of it and the body height."""
    library = drawing_library()
    label = Decimal(text_height)
    heights = frozendict({**library.heights, "smallest": label, "body": max(label, library.heights["body"])})
    return evolve(evolve(MODEL, remove=(library.id,)), put=(dataclasses.replace(library, heights=heights),), origin=_ORIGIN)


def _fonts_of(model) -> tuple[float, float]:
    label, body = (float(font_size_mm(model, role_height_mm(model, role))) for role in (TextRole.LABEL, TextRole.BODY))
    return label, body


def _fonts(text_height: str) -> tuple[float, float]:
    return _fonts_of(_model_at(text_height))


def _need(text_height: str) -> float:
    return title_band_need(_model_at(text_height))


def test_title_band_at_the_house_sizes_is_20():
    assert _need("1.8") == 20


def test_title_band_never_falls_under_the_authored_20_below_the_house_height():
    assert _need("1.0") == 20


def test_title_band_grows_with_the_text_height():
    assert 20 < _need("2.5") < _need("3.2") < _need("3.5") < _need("4") < _need("5")


def test_title_band_scales_the_house_gap_with_the_font_sizes():
    """The gap grows with label + body from the house 3.125; a third of the band's growth."""
    house = sum(_fonts("1.8"))
    for text_height in ("2.5", "3.5", "4", "5"):
        gap = 3.125 * sum(_fonts(text_height)) / house
        assert _need(text_height) == pytest.approx(20 + 3 * (gap - 3.125))
