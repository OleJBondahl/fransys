"""LC2 (layout-0215): a device chain's boxes, pins facing their neighbours, hop wires straight down.

Each box takes the pins wired to the device above on its top edge and those wired to the one below
on its bottom edge, both in hop order, one pitch apart from the same left offset: a hop's pins
stand at one x on both boxes, so its wires run straight down the column.
"""

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import G_PER_MODULE, PORT_PITCH_G, generic_box_geometry

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .types import BoxFeed, DeviceChain, DrawnFunction, Handle


def chain_boxes(
    drawn: tuple[DrawnFunction, ...], chains: Sequence[DeviceChain]
) -> tuple[DrawnFunction, ...]:
    """`drawn` with each chain member redrawn as its chain's box; the rest as is."""
    by_function = {one.function: one for one in drawn}
    changed: dict[Handle, DrawnFunction] = {}
    for chain in chains:
        boxes = [by_function[member] for member in chain.members]
        step = max(_step(one) for one in boxes)
        hops = (*chain.hops, *((chain.closing,) if chain.closing else ()))
        changed.update((one.function, _boxed(one, hops, step)) for one in boxes)
    return tuple(changed.get(one.function, one) for one in drawn)


def _step(one: DrawnFunction) -> int:
    """The box's own pin pitch: the smallest gap between two of its pin columns."""
    xs = sorted({g.at.x for g in one.geometry.ports})
    return min((b - a for a, b in pairwise(xs)), default=PORT_PITCH_G)


def _boxed(one: DrawnFunction, hops: Sequence[BoxFeed], step: int) -> DrawnFunction:
    """`one` with its upper hop's pins on top and its lower hop's beneath, `step` apart.

    A pin on no hop is not drawn (owner 2026-10-13); the unit's table lists it.
    """
    symbol = {p.port: p.symbol_port for p in one.ports}
    top = [symbol[pin.fed] for hop in hops if hop.fed == one.function for pin in hop.ports]
    below = [symbol[pin.feeder] for hop in hops if hop.feeder == one.function for pin in hop.ports]
    names = (*top, *below)
    offsets = tuple(at * step / G_PER_MODULE for at in (*range(len(top)), *range(len(below))))
    geometry = generic_box_geometry(names, ("n",) * len(top) + ("s",) * len(below), offsets=offsets)
    return replace(
        one,
        geometry=geometry,
        primary_in=top[0] if top else None,
        primary_out=below[0] if below else None,
        chained=True,
    )
