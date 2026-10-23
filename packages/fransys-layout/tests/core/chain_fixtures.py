"""Facing box chains for the CHAIN plants (layout-0289)."""

from __future__ import annotations

from turn_fixtures import views_of

from fransys_layout.core.sym_values import Sym
from fransys_layout.core.values import Box, BoxSpec, Pin, PlacementProblem, Size

from .flow_builders import net, problem


def link_box(sid: str, wires: int, *, first: bool = False, last: bool = False) -> Sym:
    """A box with `wires` inputs on its north side and `wires` outputs on its south side."""
    pins: list[Pin] = []
    for k in range(1, wires + 1):
        dx = 32 * (k - 1)
        if not first:
            pins.append(Pin(f"i{k}", "N", dx, -16, len(pins)))
        if not last:
            pins.append(Pin(f"o{k}", "S", dx, 16, len(pins)))
    body = Box(-16, -16, 32 * wires + 16, 32)
    return Sym(
        id=sid,
        group=None,
        unit="",
        label=Size(16, 8),
        pins=tuple(pins),
        nodes=tuple((p.id,) for p in pins),
        views=views_of(body, body, body, pins, ("R0",)),
        box=BoxSpec(tuple(p.id for p in pins), "S", 16, 16),
    )


def facing_chain(n: int, wires: int = 2) -> PlacementProblem:
    """n boxes B1..Bn, each wired to the next by `wires` nets from its outputs to its inputs."""
    boxes = [link_box(f"B{i}", wires, first=i == 1, last=i == n) for i in range(1, n + 1)]
    nets = [
        net(f"h{h}k{k}", f"B{h}.o{k}", f"B{h + 1}.i{k}")
        for h in range(1, n)
        for k in range(1, wires + 1)
    ]
    return problem(boxes, nets)


def tall_chain(n: int = 24) -> PlacementProblem:
    """A chain taller than the page, so the cut has to fold it."""
    return facing_chain(n)
