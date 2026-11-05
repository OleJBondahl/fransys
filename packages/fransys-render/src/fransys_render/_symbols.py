"""The placement's real symbol body, drawn by the toolkit; a placeholder for an unknown key."""

from typing import TYPE_CHECKING

from symdef import Weight, to_fragment_mm

from ._library import capital_ratio, font_family

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal

    from symdef import Symbol

    from electrical_symbols import Library

# The placeholder rectangle is 8x8 G, centred on the placement's origin (last
# paragraph): from (x-4, y-4) to (x+4, y+4). This mirrors how a real symbol's ports sit
# symmetrically around its own origin (e.g. `make-contact.toml`'s ports at y=-2/y=2
# around a centred body) -- centred, not top-left-anchored, so the placeholder reads the
# same way a real symbol would once PART 4 replaces it.
_HALF_SIZE_G = 4


def symbol_body(  # noqa: PLR0913 -- the toolkit's keywords, forwarded [internal builder of a public call, kept by decision 0414, KI-044]
    library: Library,
    symbol: Symbol,
    module_mm: Decimal,
    font_mm: Decimal,
    *,
    texts: Mapping[str, str] | None = None,
    weights_mm: Mapping[Weight, float] | None = None,
) -> str:
    """`symbol` drawn by the toolkit in mm at its own origin, in the drawing's pens and font.

    `texts` (slot id to string) goes to symdef, which draws and checks it;
    `weights_mm` replaces the symbol pens (the Bridge marks draw with the table rule).
    """
    return to_fragment_mm(
        symbol,
        module_mm=float(module_mm),
        weights_mm=weights_mm or {Weight.NORMAL: float(library.lines[Weight.NORMAL]), Weight.THICK: float(library.lines[Weight.THICK])},
        dash_mm=(float(library.dash["dashed"][0]), float(library.dash["dashed"][1])),
        font_family=font_family(library),
        font_mm=float(font_mm),
        cap_ratio=float(capital_ratio(library)),
        texts=texts,
    )
