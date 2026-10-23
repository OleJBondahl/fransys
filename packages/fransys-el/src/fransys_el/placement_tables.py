"""The core `Annex` of each coil's contact table: bottom-right first, top-right second (R339).

The table is no part of the coil's footprint. The core's one annex stage (R345) takes the first spot
that fits; el passes plain values (TABLE POSITION T1 for x, T2 for the padding) and the coil order.
"""

from typing import TYPE_CHECKING

from fransys_layout.core import Annex, Box, Size, Spot

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core import Orientation, Sym

__all__ = ["is_table_spot", "table_annexes"]

PREFIX = "table-"  # a table spot's name starts so; a label corner is BL, TL, BR or TR


def is_table_spot(name: str) -> bool:
    """True for the spot name of a table annex, false for a designation corner."""
    return name.startswith(PREFIX)


def _right(sym: Sym, orient: Orientation) -> int:
    """T1: the x of the rightmost pin facing south at `orient`, else of all pins."""
    pins = sym.views[orient].pins
    xs = [p.dx for p in pins if p.side == "S"] or [p.dx for p in pins]
    return max(xs)


def _spots(
    sym: Sym, orient: Orientation, size: Size, gaps: tuple[int, int, int]
) -> tuple[Spot, ...]:
    """Bottom-right then top-right of the coil: offsets from its body's right edge, wire-clear.

    The stage keeps `clear` (`label_gap`) beside the wire, so T1's half pitch is the least gap.
    """
    half_pitch, padding, clear = gaps
    view = sym.views[orient]
    body = view.body
    dx = _right(sym, orient) + half_pitch - (body.x + body.w)
    low = view.keepout.y + view.keepout.h + padding - (body.y + body.h)
    high = view.keepout.y - padding - size.h - body.y
    return (
        Spot(f"{PREFIX}BR", "BR", dx, low, "down", clear),
        Spot(f"{PREFIX}TR", "TR", dx, high, "up", clear),
    )


def table_annexes(
    syms: tuple[Sym, ...], tables: Mapping[str, Box], gaps: tuple[int, int, int]
) -> tuple[Annex, ...]:
    """One `Annex` per coil with a table, in the order given; the stack is the coil's id.

    `gaps` are half a wire pitch (T1), the padding (T2) and the wire clearance (R346: the stack
    is the coil's own id).
    """
    sizes = {i: Size(b.w, b.h) for i, b in tables.items()}
    return tuple(
        Annex(s.id, sizes[s.id], s.id, {o: _spots(s, o, sizes[s.id], gaps) for o in s.views})
        for s in syms
        if s.id in sizes
    )
