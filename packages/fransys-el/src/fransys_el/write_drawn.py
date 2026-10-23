"""The pin offsets, sides and leads of a placed symbol, for its page Drawing symbol."""

from typing import TYPE_CHECKING

from fransys_layout.core import PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core import Placed, Sym


__all__ = ["_leads", "_offsets", "_sides"]


def _offsets(placed: Placed, sym: Sym) -> dict[str, int]:
    """A box's pin offsets from its origin, one per pin; empty for another symbol.

    The box is built at them (`electrical_symbols.drawn_symbol`), so its length is not carried.
    """
    if sym.box is None:
        return {}
    return {p.pin: p.x - placed.x for p in placed.pin_xy}


def _sides(sym: Sym) -> dict[str, str]:
    """A box's pin sides (`n` or `s`), one per pin; empty for another symbol."""
    return {} if sym.box is None else {p.id: p.side.lower() for p in sym.pins}


def _leads(sym: Sym, wired: Mapping[PinRef, str]) -> tuple[str, ...]:
    """The pins of `sym` that a wire reaches, in the symbol's pin order."""
    return tuple(p.id for p in sym.pins if PinRef(sym.id, p.id) in wired)
