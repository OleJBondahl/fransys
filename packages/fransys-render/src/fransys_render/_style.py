"""The page `<style>` block: D11's fixed classes, black on white, deterministic."""

from decimal import Decimal

from graphical_symbols.geometry import Weight

from ._constants import OUTLINE_DASH_GAP_MM, OUTLINE_DASH_LONG_MM, STROKE_WIDTH_MM
from ._numbers import format_decimal

_STROKE_WIDTH_MM = format_decimal(STROKE_WIDTH_MM)
_FONT_FAMILY = 'Liberation Serif, "Times New Roman", serif'  # D7
_OUTLINE_DASH_ARRAY = (
    f"{format_decimal(OUTLINE_DASH_LONG_MM)},{format_decimal(OUTLINE_DASH_GAP_MM)},"
    f"{_STROKE_WIDTH_MM},{format_decimal(OUTLINE_DASH_GAP_MM)}"
)


def _harness_width(module_mm: Decimal) -> str:
    """The harness line's stroke width in mm: the thick weight times the module (0.5 at 2.5)."""
    return format_decimal(Decimal(str(Weight.THICK.value)) * module_mm)


def style_block(module_mm: Decimal) -> str:
    """The one `<style>` element every page carries (D11); the rules are in the README."""
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
        f".harness-line {{ stroke: black; fill: none; stroke-width: {_harness_width(module_mm)}; }}"
        f".connector-box, .connector-cell {{ stroke: black; fill: none; "
        f"stroke-width: {_STROKE_WIDTH_MM}; }}"
        "</style>"
    )
