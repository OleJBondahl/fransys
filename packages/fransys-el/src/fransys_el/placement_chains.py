"""The box-drawn end that a series is anchored at, from the drawn wires (layout-0181, 0396)."""

from typing import TYPE_CHECKING

from electrical_symbols import is_generic_box
from fransys_layout.core import Series
from fransys_model.derive import physical_nets

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from fransys_layout.core import PinRef, Sym

    from .placement_env import Env

_NORTH, _SOUTH = "N", "S"  # the sides a box pin faces, its circuit above or below the box (BOX-SIDES)

__all__ = ["anchored"]


def _boxes(env: Env) -> set[str]:
    """The symbol ids of the box-drawn functions (a PLC channel or an item box)."""
    return {env.ids[k] for k, p in env.kit.items() if is_generic_box(p.key) and k in env.ids}


def anchored(env: Env, syms: Sequence[Sym], far_ends: Iterable[tuple[PinRef, PinRef]]) -> tuple[Series, ...]:
    """A "tail" `Series` per symbol wired to a box's N pins (layout-0181, R927).

    Candidates are by direct wire, vetoed by net: a symbol whose nets reach a box's S pin has a box at both ends
    and a through pole spreads no candidacy (R932, R941).
    """
    boxes = _boxes(env)
    side = {(s.id, p.id): p.side for s in syms if s.id in boxes for p in s.pins}
    nets = [[env.pins[p] for p in n.ports if p in env.pins and p not in env.undrawn] for n in physical_nets(env.model)]
    south = {p.sym for pins in nets if any(side.get((p.sym, p.pin)) == _SOUTH for p in pins) for p in pins}
    derived = (a.sym for a, b in (*far_ends, *((b, a) for a, b in far_ends)) if side.get((b.sym, b.pin)) == _NORTH and a.sym not in boxes | south)
    return tuple(Series((sym,), "tail") for sym in dict.fromkeys(derived))
