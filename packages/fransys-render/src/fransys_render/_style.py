"""The page `<style>` block: the fixed classes, black on white, deterministic."""

from fransys_model.derive.print_sizes import (
    DASH_GAP_MM,
    DASH_LONG_MM,
    LINE_THICK_MM,
    LINE_THIN_MM,
    OUTLINE_DASHES_MM,
)

from ._numbers import format_decimal

_THIN = format_decimal(LINE_THIN_MM)
_THICK = format_decimal(LINE_THICK_MM)
FONT_NAME = "DejaVu Sans"
_FONT_FAMILY = f"{FONT_NAME}, sans-serif"
_OUTLINE_DASH_ARRAY = ",".join(format_decimal(dash) for dash in OUTLINE_DASHES_MM)
# The by-others dash, the same long dash and gap `_cable_pen.Pen` draws its dashed boxes with.
_DASHED_ARRAY = ",".join(format_decimal(dash) for dash in (DASH_LONG_MM, DASH_GAP_MM))


def style_block() -> str:
    """The one `<style>` element every page carries; the rules are in the README."""
    return (
        "<style>"
        f".symbol, .wire, .marker, .unit-boundary, .external-outline {{ stroke: black; fill: none; "
        f"stroke-width: {_THIN}; }}"
        ".junction { stroke: none; fill: black; }"
        f".label {{ font-family: {_FONT_FAMILY}; fill: black; }}"
        f".not-installed {{ stroke: grey; fill: none; "
        f"stroke-dasharray: {_THIN}; }}"
        "text.not-installed { fill: grey; stroke: none; }"
        f".not-installed * {{ stroke: grey; stroke-dasharray: {_THIN}; }}"
        ".not-installed [fill] { fill: grey; }"
        f".unit-boundary {{ stroke-dasharray: {_OUTLINE_DASH_ARRAY}; }}"
        f".external-outline {{ stroke-dasharray: {_DASHED_ARRAY}; }}"
        f".harness-line {{ stroke: black; fill: none; stroke-width: {_THICK}; }}"
        f".connector-box, .connector-cell {{ stroke: black; fill: none; "
        f"stroke-width: {_THIN}; }}"
        "</style>"
    )
