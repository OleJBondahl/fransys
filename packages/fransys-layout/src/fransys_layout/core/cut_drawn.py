"""Stage 4: for each pin with a drawn and an undrawn conductor, where its marker stands (MARKER-FREE-SIDE, M1).

The drawn pairs are `cut_ledger.account`'s ink; the stubs are its references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .sides import VERTICAL
from .topology_elements import is_free_sided
from .values import PinRef

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from .flow_values import CutResult, Fan
    from .sym_values import Sym
    from .values import Orientation, PlacementProblem

__all__ = ("cut_stands", "stand_pins")


type Pair = tuple[PinRef, PinRef]


def stand_pins(
    far_ends: Collection[Pair], wired: tuple[Collection[Pair], Collection[Fan], Collection[PinRef]], symbols: Sequence[Sym]
) -> dict[PinRef, dict[Orientation, PinRef | None]]:
    """For each pin with a drawn and an undrawn conductor, the pin its marker stands at, by orientation.

    `wired`: drawn pairs, fans, stub pins. Free-sided symbol: the first pin with no drawn conductor on a vertical side (R829); else none.
    A one-sided pin has none (None): its marker stands on a leg (ONE-SIDED-PIN).
    """
    pairs, fans, stubbed = wired
    fan_pins = {a.pin for f in fans for a in (*f.drivers, *f.legs)}
    paired = {a for a, _ in pairs}
    used = paired | fan_pins
    mixed = (paired & {a for a, b in far_ends if (a, b) not in pairs}) | (fan_pins & set(stubbed))
    syms = {s.id: s for s in symbols}
    out: dict[PinRef, dict[Orientation, PinRef | None]] = {}
    for pin in mixed:
        if (sym := syms.get(pin.sym)) is None:
            continue
        free = (
            [i for i, p in enumerate(sym.pins) if PinRef(pin.sym, p.id) not in (paired if pin in paired else used | set(stubbed))]
            if is_free_sided(sym)
            else []
        )
        out[pin] = {o: next((PinRef(pin.sym, sym.pins[i].id) for i in free if view.pins[i].side in VERTICAL), None) for o, view in sym.views.items()}
    return out


def cut_stands(problem: PlacementProblem, cut: CutResult) -> dict[PinRef, dict[Orientation, PinRef | None]]:
    """`stand_pins` of a finished cut, on the one `stubbed` fact `stubs` settled."""
    return stand_pins(problem.facts.far_ends, (cut.spec.drawn, cut.flow.fans, cut.spec.stubbed), problem.symbols)
