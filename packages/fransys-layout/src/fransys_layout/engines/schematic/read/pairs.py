"""layout-0107: which item box stands over the pin group it feeds, read from V1's sides.

The model says which functions are wired pin to pin (`derive.box_pairs`, model-0130); V1's side
split (`item_sides`, via `pin_sides`) says which end is fed: its group on top, the feeder's below.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages import BoxFeed, FedPin
from fransys_model.derive import box_pairs

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_layout.stages import FunctionSpec
    from fransys_model.kernel import Id, Model


def box_feeds(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    north: Collection[Id[Any]],
    south: Collection[Id[Any]],
) -> tuple[BoxFeed, ...]:
    """Each pairing whose fed group is on its box's top and feeder group on its box's bottom."""
    box_of = {port.port: spec.function for spec in specs for port in spec.ports}
    found: dict[tuple[Id[Any], Id[Any]], list[FedPin]] = {}
    for pair in box_pairs(model).values():
        own, far = zip(*pair.port_pairs, strict=True)
        if not all(p in box_of for p in (*own, *far)):
            continue
        if all(p in north for p in own) and all(p in south for p in far):
            fed, feeder = box_of[own[0]], box_of[far[0]]
            if fed != feeder:
                found.setdefault((fed, feeder), []).extend(
                    FedPin(fed=a, feeder=b) for a, b in pair.port_pairs
                )
    feeds = tuple(
        BoxFeed(fed=fed, feeder=feeder, ports=tuple(pins))
        for (fed, feeder), pins in sorted(found.items())
    )
    # layout-0107: the upper link of a chain wins, so a pair whose feeder is itself fed is no
    # pairing; a feeder of two groups draws as today
    fed_boxes = {f.fed for f in feeds}
    feeders = [f.feeder for f in feeds]
    return tuple(f for f in feeds if f.feeder not in fed_boxes and feeders.count(f.feeder) == 1)
