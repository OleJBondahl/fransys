"""The side of each pin of a generic box (BOX-SIDES): one pin over the other.

Rules in order: a `pins_below` hint puts every pin on S; item functions of different V1 rank split
(the first rank on N); a power pin keeps the side `derive.pinned_box_sides` gives; the rest take
the first half in marking order on N, the other half on S. A bundle stays together.
"""

from typing import TYPE_CHECKING, cast

from electrical_symbols import NORTH, SOUTH
from fransys_model.derive import (
    bundle_of,
    connected_ports,
    pinned_box_sides,
    pins_below,
    port_function,
    side_order_key,
)

if TYPE_CHECKING:
    from collections.abc import Hashable, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Port

    from .placement_kit import Pick

__all__ = ["box_sides", "half_split"]


def _by_rank(model: Model, ports: Sequence[Id[Port]]) -> dict[Id[Port], str]:
    """The ports N when their function ranks first, else S; `{}` when every function ties."""
    fn = {p: cast("Id[Function]", port_function(model, p)) for p in ports}  # a box port has one
    rank = {p: side_order_key(model, fn[p]) for p in ports}
    first = min(rank.values())
    if all(r == first for r in rank.values()):
        return {}
    return {p: NORTH if r == first else SOUTH for p, r in rank.items()}


def half_split(wired: Sequence[bool], bundles: Sequence[Hashable | None]) -> tuple[str, ...]:
    """The sides of pins in marking order: N until half of the `wired` ones are placed, by bundles.

    A pin nothing connects to follows the pin before it. A box keeps a loose pin (`None` in
    `bundles`) on each side. The model-free rule, shared by `box_sides` and the corpus dumper.
    """
    north = (sum(wired) + 1) // 2
    sides: list[str] = []
    placed: dict[Hashable, str] = {}
    seen = 0
    for is_wired, bundle in zip(wired, bundles, strict=True):
        side = placed.get(bundle) if bundle is not None else None
        side = side or (NORTH if seen < north else SOUTH)
        if bundle is not None:
            placed[bundle] = side
        sides.append(side)
        seen += is_wired
    loose = [i for i, bundle in enumerate(bundles) if bundle is None]
    if loose and len(sides) > 1 and len(set(sides)) == 1:  # one pin on each side
        other = SOUTH if NORTH in sides else NORTH
        sides[loose[-1] if other == SOUTH else loose[0]] = other
    return tuple(sides)


def _halves(model: Model, ports: Sequence[Id[Port]]) -> dict[Id[Port], str]:
    """`ports` in marking order on the sides `half_split` gives, read off the model."""
    wired = connected_ports(model)
    bundles = [(b[0] if (b := bundle_of(model, p)) else None) for p in ports]
    return dict(zip(ports, half_split([p in wired for p in ports], bundles), strict=True))


def box_sides(model: Model, pick: Pick, names: Sequence[str]) -> tuple[str, ...]:
    """The side of each box port in `names` (marking order): hint, rank split, power, halves."""
    port_of = {name: port for port, name in pick.ports.items()}
    ports = [port_of[name] for name in names]
    if any(pins_below(model, port_function(model, p)) for p in ports):
        return (SOUTH,) * len(ports)
    split = _by_rank(model, ports)
    if split:
        return tuple(split[p] for p in ports)
    pinned = pinned_box_sides(model, ports)
    free = [p for p in ports if pinned[p] is None]
    rest = _halves(model, free) if len(free) == len(ports) else dict.fromkeys(free, SOUTH)
    return tuple(pinned[p] or rest[p] for p in ports)
