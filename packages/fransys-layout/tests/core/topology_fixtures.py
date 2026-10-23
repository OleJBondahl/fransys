"""Hand-built stage 1 inputs: the elements, net ends and pin to net map of a small problem."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from fransys_layout.core.topology_chains import Facts
from fransys_layout.core.topology_elements import (
    Elem,
    NetEnd,
    elements,
    net_ends,
    wired_pins,
)
from fransys_layout.core.values import BoxSpec, PinRef

from .flow_builders import OPTIONS, elem, problem

if TYPE_CHECKING:
    from fransys_layout.core.sym_values import Sym
    from fransys_layout.core.values import Net


@dataclass(frozen=True, slots=True)
class Read:
    """What stage 1 reads from a problem before it links, chains or fans."""

    elems: dict[str, Elem]
    ends_by_net: dict[str, tuple[NetEnd, ...]]
    syms: dict[str, Sym]
    net_of: dict[PinRef, str]

    @property
    def facts(self) -> Facts:
        return Facts(
            self.elems,
            self.syms,
            self.ends_by_net,
            self.net_of,
            OPTIONS.end_bias_weight,
            OPTIONS.flip_turn,
        )


def read(syms: list[Sym], nets: list[Net]) -> Read:
    """Elements by key, ends of every wiring net, symbols by id, and pin to net."""
    prob = problem(syms, nets)
    wired = wired_pins(prob)
    elems = {e.key: e for s in prob.symbols for e in elements(s, wired)}
    elem_of_pin = {
        PinRef(e.sym, pin): e for e in elems.values() for pin in (e.n_pin, e.s_pin) if pin
    }
    by_id = {s.id: s for s in prob.symbols}
    ends = {n.id: net_ends(n, elem_of_pin, by_id) for n in prob.nets}
    return Read(elems, ends, by_id, wired)


def box(sym_id: str) -> Sym:
    """A box symbol with pins n (N side) and s (S side)."""
    return replace(elem(sym_id), box=BoxSpec(("n", "s"), "S", 16, 16))
