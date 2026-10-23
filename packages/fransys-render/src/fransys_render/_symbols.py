"""The placement's real symbol body, drawn by the toolkit; a placeholder for an unknown key."""

from typing import TYPE_CHECKING

from symdef import Weight, to_fragment_mm

from fransys_model.derive.print_sizes import (
    LINE_THICK_MM,
    LINE_THIN_MM,
    SYMBOL_DASH_GAP_MM,
    SYMBOL_DASH_MM,
)

from ._library import CAPITAL_RATIO
from ._style import FONT_NAME

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from decimal import Decimal

    from symdef import Symbol


CAP_RATIO = float(CAPITAL_RATIO)  # the capital height per font size every drawn text uses

# The placeholder rectangle is 8x8 G, centred on the placement's origin (last
# paragraph): from (x-4, y-4) to (x+4, y+4). This mirrors how a real symbol's ports sit
# symmetrically around its own origin (e.g. `make-contact.toml`'s ports at y=-2/y=2
# around a centred body) -- centred, not top-left-anchored, so the placeholder reads the
# same way a real symbol would once PART 4 replaces it.
_HALF_SIZE_G = 4


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
