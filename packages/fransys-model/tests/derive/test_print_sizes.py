"""The printed-size table and the one capital-height to font-size conversion (E3, E4, E7)."""

from decimal import Decimal

import pytest

from fransys_model.derive import print_sizes as sizes


def test_the_four_text_roles_are_the_iso_capital_heights():
    heights = tuple(sizes.role_height_mm(role, Decimal("1.8")) for role in sizes.TextRole)
    assert heights == (Decimal("1.8"), Decimal("2.5"), Decimal("3.5"), Decimal(5))


@pytest.mark.parametrize(
    ("profile_mm", "expected"),
    [
        ("1.8", ("1.8", "2.5", "3.5", "5")),
        ("2.5", ("2.5", "2.5", "3.5", "5")),
        ("3.0", ("3.0", "3.0", "3.5", "5")),
        ("4", ("4", "4", "4", "5")),
        ("6", ("6", "6", "6", "6")),
    ],
)
def test_text_height_sets_the_label_and_floors_every_larger_role(profile_mm, expected):
    """E10: the label is the profile value; each larger role is its own size or the profile's."""
    heights = tuple(sizes.role_height_mm(role, Decimal(profile_mm)) for role in sizes.TextRole)
    assert heights == tuple(Decimal(one) for one in expected)


def test_the_line_roles_dashes_and_dot_are_the_ruled_mm_values():
    assert (
        Decimal("0.25"),
        Decimal("0.5"),
        Decimal("0.18"),
    ) == (sizes.LINE_THIN_MM, sizes.LINE_THICK_MM, sizes.LINE_RULE_MM)
    assert (sizes.DASH_LONG_MM, sizes.DASH_GAP_MM) == (4, 1)
    assert (4, 1, Decimal("0.25"), 1) == sizes.OUTLINE_DASHES_MM
    assert (Decimal("1.25"), Decimal("0.625")) == (sizes.SYMBOL_DASH_MM, sizes.SYMBOL_DASH_GAP_MM)
    assert sizes.JUNCTION_DOT_MM == 1


def test_the_ratios_are_the_bundled_fonts_exact_fractions():
    assert Decimal(1493) / 2048 == sizes.CAPITAL_RATIO
    assert Decimal(1556) / 2048 == sizes.ASCENT_RATIO


@pytest.mark.parametrize("height", [Decimal("1.8"), Decimal("2.5"), Decimal(5)])
def test_a_font_size_gives_back_its_capital_height(height):
    assert abs(sizes.font_size_mm(height) * sizes.CAPITAL_RATIO - height) < Decimal("1e-20")


def test_the_house_label_font_size_is_about_2_47_mm():
    assert sizes.font_size_mm(Decimal("1.8")).quantize(Decimal("0.001")) == Decimal("2.469")
