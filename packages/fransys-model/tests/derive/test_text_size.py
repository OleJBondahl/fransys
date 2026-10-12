"""model-0195: the one printed font size of `text_height` on a sheet, in millimetres."""

from decimal import Decimal

from fransys_model.derive import text_size_mm


def test_one_module_of_text_height_prints_one_module_of_millimetres() -> None:
    """8 G is one module, so the size is `module_mm`."""
    assert text_size_mm(8, Decimal("2.5")) == Decimal("2.5")


def test_a_smaller_text_height_prints_a_proportionally_smaller_size() -> None:
    """2 G is a quarter of a module."""
    assert text_size_mm(2, Decimal("2.5")) == Decimal("0.625")


def test_a_text_under_the_floor_gives_its_size_and_one_at_or_over_it_gives_none() -> None:
    from dataclasses import replace

    from fransys_model.derive import text_under_floor
    from fransys_model.layout import default_profile

    small = replace(default_profile(), text_height=2)
    assert text_under_floor(small, Decimal("2.5")) == Decimal("0.625")
    assert text_under_floor(replace(small, min_text_mm=Decimal("0.625")), Decimal("2.5")) is None
    assert text_under_floor(default_profile(), Decimal("2.5")) is None
