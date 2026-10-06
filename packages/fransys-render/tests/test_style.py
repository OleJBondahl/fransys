"""Pins `style_block`'s full literal CSS text, killing survivors substring checks miss."""

from decimal import Decimal

from fransys_render._constants import OUTLINE_DASH_GAP_MM, OUTLINE_DASH_LONG_MM, STROKE_WIDTH_MM
from fransys_render._numbers import format_decimal
from fransys_render._style import style_block

_STROKE_WIDTH_MM = format_decimal(STROKE_WIDTH_MM)
_FONT_FAMILY = 'Liberation Serif, "Times New Roman", serif'
_OUTLINE_DASH_ARRAY = (
    f"{format_decimal(OUTLINE_DASH_LONG_MM)},{format_decimal(OUTLINE_DASH_GAP_MM)},"
    f"{_STROKE_WIDTH_MM},{format_decimal(OUTLINE_DASH_GAP_MM)}"
)


def _expected(module_mm: Decimal) -> str:
    descendant_dash = format_decimal(STROKE_WIDTH_MM / module_mm)
    return (
        "<style>"
        f".symbol, .wire, .marker, .unit-boundary {{ stroke: black; fill: none; "
        f"stroke-width: {_STROKE_WIDTH_MM}; }}"
        ".junction { stroke: none; fill: black; }"
        f".label {{ font-family: {_FONT_FAMILY}; fill: black; }}"
        f".not-installed {{ stroke: grey; fill: none; "
        f"stroke-dasharray: {_STROKE_WIDTH_MM}; }}"
        "text.not-installed { fill: grey; stroke: none; }"
        f".not-installed * {{ stroke: grey; stroke-dasharray: {descendant_dash}; }}"
        ".not-installed [fill] { fill: grey; }"
        f".unit-boundary {{ stroke-dasharray: {_OUTLINE_DASH_ARRAY}; }}"
        "</style>"
    )


def test_style_block_matches_exact_literal_text_for_house_sheet_module() -> None:
    module_mm = Decimal("2.5")
    assert style_block(module_mm) == _expected(module_mm)


def test_style_block_descendant_dash_scales_with_module_mm() -> None:
    house = style_block(Decimal("2.5"))
    other = style_block(Decimal(5))
    assert house != other
    assert style_block(Decimal(5)) == _expected(Decimal(5))
    assert "stroke-dasharray: 0.1;" in house
    assert "stroke-dasharray: 0.05;" in other
