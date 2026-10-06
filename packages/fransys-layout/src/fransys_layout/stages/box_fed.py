"""layout-0124: a fed box's pins, each feeder's group kept pin over pin, the groups spread apart."""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry.box_reach import Reach, spread
from fransys_layout.geometry.symbols import channel_pitch, generic_box_geometry
from fransys_layout.geometry.units import G_PER_MODULE

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.geometry.symbols import SymbolGeometry

    from .types import DrawnFunction


def fed_geometry(
    one: DrawnFunction, names: tuple[str, ...], sides: tuple[str, ...], reach: tuple[Reach, ...]
) -> SymbolGeometry:
    """`one` redrawn: only each group's first pin is spread, the rest keep their offset to it."""
    symbol = {p.port: p.symbol_port for p in one.ports}
    at = {g.name: g.at.x for g in one.geometry.ports}
    follow: dict[str, str] = {}  # a group's other pin -> the group's first pin
    for feed in one.fed_by:
        group = sorted((symbol[p.fed] for p in feed.ports), key=lambda n: at[n])
        follow.update((n, group[0]) for n in group[1:])
    face = dict(zip(names, sides, strict=True))
    spots = {n: (face[n], at[n]) for n in names if n not in follow}
    placed = _no_closer(spots, spread(spots, reach, channel_pitch()))
    placed.update((n, placed[lead] + at[n] - at[lead]) for n, lead in follow.items())
    return generic_box_geometry(
        names, sides, offsets=tuple(placed[n] / G_PER_MODULE for n in names)
    )


def _no_closer(
    spots: Mapping[str, tuple[str, int]], spread_at: Mapping[str, int]
) -> dict[str, int]:
    """`placed`, each pin kept as far from the one before it as it stood (a feeder's slot)."""
    placed = dict(spread_at)
    for side in {side for side, _ in spots.values()}:
        names = sorted((n for n in spots if spots[n][0] == side), key=lambda n: spots[n][1])
        for before, name in pairwise(names):
            gap = spots[name][1] - spots[before][1]
            placed[name] = max(placed[name], placed[before] + gap)
    return placed
