"""The printed-size table and the one capital-height to font-size conversion (E3, E4, E7)."""

from decimal import Decimal

import pytest
from derive_helpers import frozen_with_library

from fransys_model.derive import print_sizes as sizes
from fransys_model.kernel import Draft, SchemaError

MODEL = frozen_with_library(Draft())
CAPITAL_RATIO = Decimal(1493) / 2048


def test_the_four_text_roles_are_the_iso_capital_heights():
    heights = tuple(sizes.role_height_mm(MODEL, role) for role in sizes.TextRole)
    assert heights == (Decimal("1.8"), Decimal("2.5"), Decimal("3.5"), Decimal(5))


def test_the_ascent_ratio_is_the_records_exact_fraction():
    assert sizes.ascent_ratio(MODEL) == Decimal(1556) / 2048


@pytest.mark.parametrize("height", ["1.8", "2.5", "3.5", "5.0", "2.0", "3.0", "2.2"])
def test_a_font_size_is_the_old_division_to_four_places(height):
    """The lookup keeps every printed size: the old formula, quantized, is the reference."""
    cap = Decimal(height)
    old = (cap / CAPITAL_RATIO).quantize(Decimal("0.0001"))
    assert sizes.font_size_mm(MODEL, cap).quantize(Decimal("0.0001")) == old


def test_the_house_label_font_size_is_about_2_47_mm():
    assert sizes.font_size_mm(MODEL, Decimal("1.8")).quantize(Decimal("0.001")) == Decimal("2.469")


def test_a_height_the_record_lacks_raises_and_names_what_it_has():
    with pytest.raises(SchemaError, match=r"4\.4 mm.*holds 1, 1\.8"):
        sizes.font_size_mm(MODEL, Decimal("4.4"))


@pytest.mark.parametrize(
    ("height", "key"),
    [("1.80", "1.8"), ("5.0", "5"), ("50", "50"), ("0.125", "0.125")],
)
def test_the_height_key_is_the_canonical_string(height, key):
    assert sizes.height_key(Decimal(height)) == key


def test_the_rule_width_is_the_records_rule_line():
    assert sizes.rule_mm(MODEL) == Decimal("0.18")


_ROLES = {
    "smallest": Decimal("1.8"),
    "body": Decimal("2.5"),
    "heading_2": Decimal("3.5"),
    "heading_1": Decimal(5),
}


def test_the_capital_heights_are_the_library_roles_once_each():
    assert sizes.capital_heights(_ROLES) == (
        Decimal("1.8"),
        Decimal("2.5"),
        Decimal("3.5"),
        Decimal(5),
    )
