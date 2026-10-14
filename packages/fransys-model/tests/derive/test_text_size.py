"""model-0203: the layout's text room in G for a capital height, and the floor it is held to."""

from dataclasses import replace
from decimal import Decimal

import pytest

from fransys_model.derive import text_room_g, text_under_floor
from fransys_model.derive.print_sizes import CAPITAL_RATIO, TextRole, role_height_mm
from fransys_model.layout import default_profile

_MODULE = Decimal("2.5")
_LABEL_MM = role_height_mm(TextRole.LABEL, default_profile().text_height_mm)


def test_the_house_capital_height_is_eight_g_on_the_house_sheet() -> None:
    assert text_room_g(_LABEL_MM, _MODULE) == 8


def test_the_house_profile_holds_the_label_role() -> None:
    profile = default_profile()
    assert profile.text_height_mm == _LABEL_MM
    assert profile.min_text_height_mm == _LABEL_MM


def test_the_room_rounds_the_font_size_up_to_a_whole_g() -> None:
    """A font size of exactly one module is 8 G; a hair over it is 9 G (one G is 0.3125 mm)."""
    assert text_room_g(_MODULE * CAPITAL_RATIO, _MODULE) == 8
    assert text_room_g(_MODULE * CAPITAL_RATIO + Decimal("0.001"), _MODULE) == 9


def test_a_smaller_module_gives_more_g() -> None:
    assert text_room_g(_LABEL_MM, Decimal("1.25")) == 16


@pytest.mark.parametrize(
    ("height", "floor", "under"),
    [("1.8", "1.8", None), ("1.79", "1.8", "1.79"), ("1.0", "0.5", None), ("2.5", "2.5", None)],
)
def test_the_floor_fires_under_it_and_not_at_it(height: str, floor: str, under: str | None) -> None:
    profile = replace(
        default_profile(), text_height_mm=Decimal(height), min_text_height_mm=Decimal(floor)
    )
    assert text_under_floor(profile) == (None if under is None else Decimal(under))
