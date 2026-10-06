"""D6: the placement's real symbol body, drawn by the toolkit; a placeholder for an unknown key."""

from typing import TYPE_CHECKING

from graphical_symbols import to_fragment

from fransys_model.layout import (
    PowerSymbol,
    SymbolPlacement,
    page_slice,
    profile_of,
    sheet_format_of,
)
from fransys_model.vocab import functions, items

from ._constants import ASCENT_RATIO
from ._leads import visible_symbol
from ._markers import text_glyph
from ._numbers import format_decimal, grid_to_mm
from ._symbol_geometry import oriented_power_symbol, oriented_symbol, to_grid

if TYPE_CHECKING:
    from graphical_symbols.model import Symbol

    from fransys_model.kernel import Model
    from fransys_model.layout import Page, Profile, SheetFormat

# The placeholder rectangle is 8x8 G, centred on the placement's origin (D6 last
# paragraph): from (x-4, y-4) to (x+4, y+4). This mirrors how a real symbol's ports sit
# symmetrically around its own origin (e.g. `make-contact.toml`'s ports at y=-2/y=2
# around a centred body) -- centred, not top-left-anchored, so the placeholder reads the
# same way a real symbol would once PART 4 replaces it.
_HALF_SIZE_G = 4


def symbols_on_page(model: Model, page: Page) -> tuple[SymbolPlacement, ...]:
    """Every `layout.symbol_placement` on `page`, ordered by `id` (D11's placement-id order)."""
    return page_slice(model, SymbolPlacement, page)


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
    font_size_mm = grid_to_mm(0, profile.text_height, sheet.module_mm)
    baseline_mm = top_mm + font_size_mm * ASCENT_RATIO
    x_mm = grid_to_mm(sheet.content_x_mm, placement.x, sheet.module_mm)
    return text_glyph(placement.symbol, x_mm, baseline_mm, font_size_mm)


def _not_installed(model: Model, placement: SymbolPlacement) -> bool:
    """D10: `placement`'s function's item has `installed=False`."""
    function = functions(model)[placement.function]
    return not items(model)[function.item].installed


def power_symbols_on_page(model: Model, page: Page) -> tuple[PowerSymbol, ...]:
    """Every `layout.power_symbol` on `page`, ordered by `id`."""
    return page_slice(model, PowerSymbol, page)


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


def _symbol_fragment(
    sheet: SheetFormat,
    placement: SymbolPlacement | PowerSymbol,
    symbol: Symbol,
    *,
    not_installed: bool = False,
) -> str:
    """`symbol`'s body, wrapped and positioned at `placement`'s absolute page position."""
    x_mm = grid_to_mm(sheet.content_x_mm, placement.x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, placement.y, sheet.module_mm)
    css_class = "symbol not-installed" if not_installed else "symbol"
    transform = (
        f"translate({format_decimal(x_mm)},{format_decimal(y_mm)}) "
        f"scale({format_decimal(sheet.module_mm)})"
    )
    return f'<g class="{css_class}" transform="{transform}">{to_fragment(symbol)}</g>'


def symbols_group(model: Model, page: Page) -> str:
    """Every placement on `page`: its real symbol body, or the 8x8 G placeholder (unknown key)."""
    sheet = sheet_format_of(model, page.sheet_format)
    profile = profile_of(model)
    parts = []
    for placement in symbols_on_page(model, page):
        symbol = oriented_symbol(model, placement)
        if symbol is None:
            parts.append(_rect_glyph(sheet, placement))
            parts.append(_text_glyph(sheet, profile, placement))
        else:
            symbol = visible_symbol(model, page, placement, symbol)
            not_installed = _not_installed(model, placement)
            parts.append(_symbol_fragment(sheet, placement, symbol, not_installed=not_installed))
    for power in power_symbols_on_page(model, page):
        symbol = oriented_power_symbol(power)
        parts.append(_symbol_fragment(sheet, power, symbol))
        parts.append(_power_lead(sheet, power, symbol))
    return "".join(parts)
