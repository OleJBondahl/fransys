"""The designation of each symbol as a core `Annex`: a corner of its body, top left first.

Owner 2026-10-18: a designation stands in a corner of its symbol, "top left by default". The
corners come from `Options.corner_order`, each moved out by `Options.slack`; the text stage takes
the first one free of every body, wire and earlier annex. A corner box keeps `label_gap` plus its
slack beside the wire of the pins on its body edge (`Spot.clear`, R353), so a slack step also
clears a reference marker that stands on that wire.
"""

from typing import TYPE_CHECKING, Literal

from fransys_layout.core import Annex, Size, Spot

from .placement_kit import ProblemError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core import Options, Orientation, Sym

__all__ = ["label_annexes"]

Corner = Literal["TL", "TR", "BL", "BR"]

#: corner -> (below the body?, box's left edge on the body's left edge?)
CORNERS: dict[Corner, tuple[bool, bool]] = {
    "BL": (True, True),
    "TL": (False, True),
    "BR": (True, False),
    "TR": (False, False),
}


def corner_spot(corner: str, slack: int, size: Size, gap: int) -> Spot:
    """The spot at a body corner, `slack` out from it, `gap` clear of the pin wire."""
    known = next((k for k in CORNERS if k == corner), None)
    if known is None:
        fix = f"Options.corner_order names one of {list(CORNERS)}"
        msg = f"unknown label corner {corner!r}"
        raise ProblemError(msg, fix)
    below, left = CORNERS[known]
    dx = slack if left else -slack - size.w
    dy = slack if below else -size.h - slack
    return Spot(corner, known, dx, dy, "down", gap)


def label_annexes(syms: Sequence[Sym], options: Options) -> tuple[Annex, ...]:
    """One `Annex` per symbol, sized by its measured tag slot, in the order of `syms`."""
    found = []
    for sym in syms:
        spots = tuple(
            corner_spot(c, s, sym.label, options.label_gap + s)
            for c in options.corner_order
            for s in options.slack
        )
        turns: dict[Orientation, tuple[Spot, ...]] = dict.fromkeys(sym.views, spots)
        found.append(Annex(sym.id, sym.label, None, turns))
    return tuple(found)
