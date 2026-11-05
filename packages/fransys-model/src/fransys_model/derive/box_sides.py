"""The sides a generic box's power pins keep: supply N and ground S, AC N, a potential rank on N.

One home for the rule (layout-0102, model-0344): the old engine and `fransys_el` both call it.
"""

from itertools import repeat
lazy from collections.abc import Sequence

from fransys_model.derive.potential import port_potential_current, port_potential_rank
from fransys_model.derive.power import port_power_kind
from fransys_model.elecdef import Current
from fransys_model.vocab.enums import PowerKind
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port

__all__ = ["pinned_box_sides"]

_POTENTIALS = 2  # a box on this many declared potentials or more has them all on top


def _by_kind(dc: dict[Id[Port], PowerKind], *, shut: bool, bare: bool) -> dict[Id[Port], str]:
    """Supply N, ground or earth S (the symbol hangs below); all S when `shut`, all N if `bare`."""
    return {p: "n" if (k is PowerKind.SUPPLY or bare) and not shut else "s" for p, k in dc.items()}


def pinned_box_sides(model: Model, ports: Sequence[Id[Port]]) -> dict[Id[Port], str | None]:
    """The side ("n" or "s") the power of a box decides for each of its `ports`, else `None`.

    A box with a pin on a supply, ground or earth net, drawn as a symbol: a supply pin N and the
    rest of those S, but when it has an AC pin too (a port on no such net that carries AC), every
    AC pin N and all those S. A box whose pins are all on such nets has every pin N
    (CROSS-HALF-TAGS: a straight riser for the return). Without such a pin, a box on two or more
    declared potentials has every pin that carries one on N, so a supply whose + and - are
    wired stands both on N.
    Ports the power does not decide are `None`.
    """
    sides: dict[Id[Port], str | None] = dict(zip(ports, repeat(None), strict=False))
    kinds = {p: port_power_kind(model, p) for p in ports}
    dc = {p: kind for p, kind in kinds.items() if kind is not PowerKind.NONE}
    if dc:
        ac = [p for p in ports if p not in dc and port_potential_current(model, p) is Current.AC]
        sides.update(_by_kind(dc, shut=bool(ac), bare=len(dc) == len(ports)))
        sides.update(dict.fromkeys(ac, "n"))
        return sides
    ranked = {p: r for p in ports if (r := port_potential_rank(model, p)) is not None}
    if len(set(ranked.values())) >= _POTENTIALS:
        sides.update(dict.fromkeys(ranked, "n"))
    return sides
