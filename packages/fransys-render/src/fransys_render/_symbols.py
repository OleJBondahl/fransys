"""The placement's real symbol body, drawn by the toolkit; a placeholder for an unknown key."""

from typing import TYPE_CHECKING

from symdef import Weight, to_fragment_mm

from fransys_model.derive import item_installed
from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.order import drawn_on_page
from fransys_model.derive.print_sizes import (
    ASCENT_RATIO,
    CAPITAL_RATIO,
    LINE_THICK_MM,
    LINE_THIN_MM,
    SYMBOL_DASH_GAP_MM,
    SYMBOL_DASH_MM,
    TextRole,
    role_height_mm,
)
from fransys_model.layout import (
    PowerSymbol,
    SymbolPlacement,
    profile_of_page,
    sheet_format_of,
)
from fransys_model.vocab import functions

from ._leads import visible_symbol
from ._markers import text_glyph
from ._numbers import format_decimal, printed_font_mm
from ._style import FONT_NAME
from ._symbol_geometry import oriented_power_symbol, oriented_symbol, to_grid

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from decimal import Decimal

    from symdef import Symbol

    from fransys_model.kernel import Model
    from fransys_model.layout import Page, Profile, SheetFormat

CAP_RATIO = float(CAPITAL_RATIO)  # the capital height per font size every drawn text uses

# The placeholder rectangle is 8x8 G, centred on the placement's origin (last
# paragraph): from (x-4, y-4) to (x+4, y+4). This mirrors how a real symbol's ports sit
# symmetrically around its own origin (e.g. `make-contact.toml`'s ports at y=-2/y=2
# around a centred body) -- centred, not top-left-anchored, so the placeholder reads the
# same way a real symbol would once PART 4 replaces it.
_HALF_SIZE_G = 4


def symbols_on_page(model: Model, page: Page) -> tuple[SymbolPlacement, ...]:
    """Every `layout.symbol_placement` on `page`, top-down, left to right."""
    return drawn_on_page(model, SymbolPlacement, page)


def _rect_glyph(sheet: SheetFormat, placement: SymbolPlacement) -> str:
    """The 8x8 G placeholder rectangle, centred on `(placement.x, placement.y)`."""
    x1_mm = grid_to_mm(sheet.content_x_mm, placement.x - _HALF_SIZE_G, sheet.module_mm)
    y1_mm = grid_to_mm(sheet.content_y_mm, placement.y - _HALF_SIZE_G, sheet.module_mm)
    x2_mm = grid_to_mm(sheet.content_x_mm, placement.x + _HALF_SIZE_G, sheet.module_mm)
    y2_mm = grid_to_mm(sheet.content_y_mm, placement.y + _HALF_SIZE_G, sheet.module_mm)
    return (
        f'<rect class="symbol" x="{format_decimal(x1_mm)}" y="{format_decimal(y1_mm)}" '
        f'width="{format_decimal(x2_mm - x1_mm)}" height="{format_decimal(y2_mm - y1_mm)}"/>'
    )


def _text_glyph(sheet: SheetFormat, profile: Profile, placement: SymbolPlacement) -> str:
    """The placement's `symbol` key, centred in the rectangle: baseline mirrors `_markers.py`."""
    top_mm = grid_to_mm(sheet.content_y_mm, placement.y - _HALF_SIZE_G, sheet.module_mm)
    font = printed_font_mm(profile.text_height_mm)
    baseline_mm = top_mm + font * ASCENT_RATIO
    x_mm = grid_to_mm(sheet.content_x_mm, placement.x, sheet.module_mm)
    return text_glyph(placement.symbol, x_mm, baseline_mm, font)


def power_symbols_on_page(model: Model, page: Page) -> tuple[PowerSymbol, ...]:
    """Every `layout.power_symbol` on `page`, top-down, left to right (`by_place`)."""
    return drawn_on_page(model, PowerSymbol, page)


def power_lead_ends(power: PowerSymbol, symbol: Symbol) -> tuple[tuple[int, int], tuple[int, int]]:
    """The lead's two ends in grid units: the symbol's own port, and the record's pin point."""
    port = symbol.ports[0]
    return (power.x + to_grid(port.position.x), power.y + to_grid(port.position.y)), (
        power.pin_x,
        power.pin_y,
    )


def _power_lead(sheet: SheetFormat, power: PowerSymbol, symbol: Symbol) -> str:
    """The power symbol's lead: one straight `<line>` in the wire style."""
    (x1, y1), (x2, y2) = (
        (
            grid_to_mm(sheet.content_x_mm, x, sheet.module_mm),
            grid_to_mm(sheet.content_y_mm, y, sheet.module_mm),
        )
        for x, y in power_lead_ends(power, symbol)
    )
    return (
        f'<line class="wire" x1="{format_decimal(x1)}" y1="{format_decimal(y1)}" '
        f'x2="{format_decimal(x2)}" y2="{format_decimal(y2)}"/>'
    )


def symbol_body(  # noqa: PLR0913 -- the toolkit's keywords, forwarded
    symbol: Symbol,
    module_mm: Decimal,
    font_mm: Decimal,
    tint: str | None = None,
    *,
    texts: Mapping[str, str] | None = None,
    required_slots: Sequence[str] = (),
    weights_mm: Mapping[Weight, float] | None = None,
) -> str:
    """`symbol` drawn by the toolkit in mm at its own origin, with the drawing's pens and font.

    `texts` (slot id to string) and `required_slots` go to symdef, which draws and checks them;
    `weights_mm` replaces the symbol pens (the Bridge marks draw with the table rule).
    """
    return to_fragment_mm(
        symbol,
        module_mm=float(module_mm),
        weights_mm=weights_mm
        or {Weight.NORMAL: float(LINE_THIN_MM), Weight.THICK: float(LINE_THICK_MM)},
        dash_mm=(float(SYMBOL_DASH_MM), float(SYMBOL_DASH_GAP_MM)),
        font_family=FONT_NAME,
        font_mm=float(font_mm),
        cap_ratio=CAP_RATIO,
        tint=tint,
        texts=texts,
        required_slots=required_slots,
    )


def _symbol_fragment(
    sheet: SheetFormat,
    profile: Profile,
    placement: SymbolPlacement | PowerSymbol,
    symbol: Symbol,
    *,
    not_installed: bool = False,
) -> str:
    """`symbol`'s body in absolute mm, translated to `placement`'s page position."""
    x_mm = grid_to_mm(sheet.content_x_mm, placement.x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, placement.y, sheet.module_mm)
    css_class = "symbol not-installed" if not_installed else "symbol"
    font_mm = printed_font_mm(role_height_mm(TextRole.LABEL, profile.text_height_mm))
    body = symbol_body(symbol, sheet.module_mm, font_mm)
    transform = f"translate({format_decimal(x_mm)},{format_decimal(y_mm)})"
    return f'<g class="{css_class}" transform="{transform}">{body}</g>'


def symbols_group(model: Model, page: Page) -> str:
    """Every placement on `page`: its real symbol body, or the 8x8 G placeholder (unknown key)."""
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of_page(model, page)
    parts = []
    for placement in symbols_on_page(model, page):
        symbol = oriented_symbol(model, placement)
        if symbol is None:
            parts.append(_rect_glyph(sheet, placement))
            parts.append(_text_glyph(sheet, profile, placement))
        else:
            symbol = visible_symbol(model, page, placement, symbol)
            not_installed = not item_installed(model, functions(model)[placement.function].item)
            parts.append(
                _symbol_fragment(sheet, profile, placement, symbol, not_installed=not_installed)
            )
    for power in power_symbols_on_page(model, page):
        symbol = oriented_power_symbol(power)
        parts.append(_symbol_fragment(sheet, profile, power, symbol))
        parts.append(_power_lead(sheet, power, symbol))
    return "".join(parts)
