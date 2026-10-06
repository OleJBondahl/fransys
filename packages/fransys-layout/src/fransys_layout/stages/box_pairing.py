"""layout-0107: a box's pins stand where its feeder's pins stand, pin under pin (V06 V1).

Set at resolve, after the feeders: the fed group's pins copy the feeder's pin offsets, a slot per
feeder as wide as its keep-out plus the column gap; the feeder's paired pins follow the fed order.
"""

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import G_PER_MODULE, generic_box_geometry, snap_up

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .types import BoxFeed, DrawnFunction, Profile

_PIN_ORIGIN = 16  # a generic box's first pin, one port pitch right of its body's left edge
_NORTH, _SOUTH = "n", "s"


def paired_boxes(
    drawn: tuple[DrawnFunction, ...], feeds: Sequence[BoxFeed], profile: Profile
) -> tuple[DrawnFunction, ...]:
    """Each fed box redrawn over its feeders, each feeder redrawn in the fed order; others as is."""
    by_function = {one.function: one for one in drawn}
    changed: dict[object, DrawnFunction] = {}
    for fed_id in sorted({feed.fed for feed in feeds}):
        mine = [feed for feed in feeds if feed.fed == fed_id]
        result = _pair_one(by_function[fed_id], [(f, by_function[f.feeder]) for f in mine], profile)
        if result is not None:
            changed.update((one.function, one) for one in result)
    return tuple(changed.get(one.function, one) for one in drawn)


def _facing(one: DrawnFunction) -> dict[str, str]:
    """Each symbol port's side of `one`."""
    return {g.name: g.facing.value for g in one.geometry.ports}


def _pair_one(
    fed: DrawnFunction, feeders: Sequence[tuple[BoxFeed, DrawnFunction]], profile: Profile
) -> tuple[DrawnFunction, ...] | None:
    """The fed box and its feeders redrawn, or `None` when a pin is not on its facing side."""
    symbol = {p.port: p.symbol_port for p in fed.ports}
    fed_face = _facing(fed)
    blocks = []
    for feed, feeder in feeders:
        mine = {p.port: p.symbol_port for p in feeder.ports}
        names = [(symbol[a], mine[b]) for a, b in ((p.fed, p.feeder) for p in feed.ports)]
        face = _facing(feeder)
        if any(fed_face[a] != _NORTH or face[b] != _SOUTH for a, b in names):
            return None
        blocks.append((feed, feeder, names))
    order = _fed_order(fed, [frozenset(a for a, _ in names) for *_, names in blocks])
    blocks = [
        (feed, _feeder_order(feeder, names, order, fed), names) for feed, feeder, names in blocks
    ]
    return (_fed_over(fed, blocks, order, profile), *(feeder for _, feeder, _ in blocks))


def _fed_order(fed: DrawnFunction, groups: Sequence[frozenset[str]]) -> list[str]:
    """The fed box's top pins left to right, each feeder's pins one block (stable)."""
    top = sorted((g for g in fed.geometry.ports if g.facing.value == _NORTH), key=lambda g: g.at.x)
    names = [g.name for g in top]
    first = {name: next((i for i, g in enumerate(groups) if name in g), None) for name in names}
    start = {i: min(at for at, n in enumerate(names) if first[n] == i) for i in set(first.values())}
    key = {n: start.get(first[n], at) if first[n] is not None else at for at, n in enumerate(names)}
    return sorted(names, key=lambda n: key[n])


def _feeder_order(
    feeder: DrawnFunction,
    names: Sequence[tuple[str, str]],
    order: Sequence[str],
    fed: DrawnFunction,
) -> DrawnFunction:
    """`feeder` redrawn with its paired bottom pins first, in the fed order, the rest after."""
    block = [b for a in order for x, b in names if x == a]
    face = _facing(feeder)
    every = [g.name for g in feeder.geometry.ports]
    ordered = [*block, *(n for n in every if n not in block)]
    geometry = generic_box_geometry(tuple(ordered), tuple(face[n] for n in ordered), feeder.reach)
    return replace(
        feeder, geometry=geometry, primary_in=None, primary_out=block[0], feeds=fed.function
    )


def _fed_over(
    fed: DrawnFunction,
    blocks: Sequence[tuple[BoxFeed, DrawnFunction, Sequence[tuple[str, str]]]],
    order: Sequence[str],
    profile: Profile,
) -> DrawnFunction:
    """`fed` with each feeder's pins' x for its group's pins, a slot a feeder's width apart."""
    own = {g.name: g for g in fed.geometry.ports}
    xs = [g.at.x for g in own.values()]
    step = next((b - a for a, b in pairwise(sorted(xs)) if b > a), _PIN_ORIGIN)
    at: dict[str, int] = {g.name: g.at.x for g in fed.geometry.ports if g.facing.value != _NORTH}
    slot_of = {a: (feeder, b) for _, feeder, names in blocks for a, b in names}
    cursor = 0
    start: dict[object, int] = {}
    for name in order:
        if name not in slot_of:
            at[name] = cursor
            cursor += step
            continue
        feeder, mate = slot_of[name]
        body, keep = feeder.geometry.body, feeder.geometry.keepout
        if feeder.function not in start:
            lead = max(0, body.x - keep.x)
            start[feeder.function] = cursor - _PIN_ORIGIN + lead
            reach = keep.x + keep.width - body.x
            cursor = int(snap_up(start[feeder.function] + reach + profile.column_gap)) + _PIN_ORIGIN
        pin = next(g.at.x for g in feeder.geometry.ports if g.name == mate)
        at[name] = start[feeder.function] + pin - body.x
    names = [*order, *(n for n in own if n not in order)]
    face = _facing(fed)
    offsets = tuple(at[n] / G_PER_MODULE for n in names)
    geometry = generic_box_geometry(tuple(names), tuple(face[n] for n in names), offsets=offsets)
    return replace(fed, geometry=geometry, fed_by=tuple(b[0] for b in blocks))
