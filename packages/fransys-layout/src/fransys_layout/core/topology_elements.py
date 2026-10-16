"""Stage 1, part 1: elements of a symbol and the ends of a net, read from pins and nodes only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Set as AbstractSet

from .keys import natural_key
from .values import Net, Pin, PinRef, PlacementProblem, Sym

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

STAND_POWERS = frozenset({"SUPPLY", "GROUND", "PE"})


@dataclass(frozen=True, slots=True)
class Elem:
    """One placeable thing in a lane: a pole (n and s pin), a free-sided symbol, or a single pin."""

    key: str
    sym: str
    form: str
    n_pin: str | None
    s_pin: str | None


@dataclass(frozen=True, slots=True)
class NetEnd:
    """How a net meets an element: top (its n pin), bottom (its s pin), side, through, or boxpin."""

    net: str
    elem: str | None
    pin: PinRef
    site: str


def is_wiring(net: Net) -> bool:
    return net.rail is None or net.rail.power not in STAND_POWERS


def is_free_sided(sym: Sym) -> bool:
    """T2: all pins one node, so a wire may leave from any of them."""
    return len(sym.nodes) == 1 and len(sym.pins) > 1


def wired_pins(problem: PlacementProblem) -> dict[PinRef, str]:
    """Pin to wiring net, for nets that join two or more symbols."""
    out: dict[PinRef, str] = {}
    for net in problem.nets:
        if is_wiring(net) and len({r.sym for r in net.pins}) > 1:
            for ref in net.pins:
                out[ref] = net.id
    return out


def connected(sym: Sym, wired: Mapping[PinRef, str]) -> list[Pin]:
    return [p for p in sym.pins if p.stand is not None or PinRef(sym.id, p.id) in wired]


def drawn_symbols(problem: PlacementProblem, wired: Mapping[PinRef, str]) -> tuple[Sym, ...]:
    """A symbol draws when a wire or a stand touches it (no loose symbols)."""
    return tuple(s for s in problem.symbols if connected(s, wired))


def elements(sym: Sym, wired: Mapping[PinRef, str]) -> tuple[Elem, ...]:
    """Poles pair a connected N pin with a connected S pin at one dx; the rest are singles."""
    if sym.box is not None:
        return ()
    pins = connected(sym, wired)
    if is_free_sided(sym):
        n = next((p.id for p in sym.pins if p.side == "N"), None)
        s = next((p.id for p in sym.pins if p.side == "S"), None)
        return (Elem(f"{sym.id}#0", sym.id, "free", n, s),)
    return _poles_and_singles(sym, pins)


def _poles_and_singles(sym: Sym, pins: Sequence[Pin]) -> tuple[Elem, ...]:
    norths = {p.dx: p for p in pins if p.side == "N"}
    souths = {p.dx: p for p in pins if p.side == "S"}
    out: list[Elem] = []
    used: set[str] = set()
    for i, dx in enumerate(sorted(set(norths) & set(souths))):
        out.append(Elem(f"{sym.id}#{i}", sym.id, "pole", norths[dx].id, souths[dx].id))
        used.update((norths[dx].id, souths[dx].id))
    for p in sorted(pins, key=lambda p: natural_key(p.id)):
        if p.id not in used:
            n, s = (p.id, None) if p.side == "N" else (None, p.id)
            out.append(Elem(f"{sym.id}@{p.id}", sym.id, "single", n, s))
    return tuple(out)


def net_ends(
    net: Net, elem_of_pin: Mapping[PinRef, Elem], syms: Mapping[str, Sym]
) -> tuple[NetEnd, ...]:
    """The ends of one wiring net; an element with both pins on it is one through end."""
    seen: set[str] = set()
    out: list[NetEnd] = []
    on_net = {r for r in net.pins if r.sym in syms}
    for ref in sorted(on_net, key=lambda r: (natural_key(r.sym), natural_key(r.pin))):
        if syms[ref.sym].box is not None:
            out.append(NetEnd(net.id, None, ref, "boxpin"))
            continue
        elem = elem_of_pin.get(ref)
        if elem is None or elem.key in seen:
            continue
        seen.add(elem.key)
        out.append(NetEnd(net.id, elem.key, ref, _role(elem, ref, on_net, syms[ref.sym])))
    return tuple(out)


def _role(elem: Elem, ref: PinRef, on_net: AbstractSet[PinRef], sym: Sym) -> str:
    pair = (elem.n_pin, elem.s_pin)
    if elem.form == "free" or all(p is not None and PinRef(ref.sym, p) in on_net for p in pair):
        return "through"
    side = next(p.side for p in sym.pins if p.id == ref.pin)
    if side == "N":
        return "top"
    if side == "S":
        return "bottom"
    return "side"
