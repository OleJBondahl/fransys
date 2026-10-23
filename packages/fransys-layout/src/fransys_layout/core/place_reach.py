"""Stage 5, y: the room an anchored item on a card's pin row asks of a trunk passing it (R510).

A card is no anchor owner (`anchors.reserved`), so rows and trunks would not leave its anchored
items room. The reach of an item is the G it stands from the pin row towards the trunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import pin_of
from .place_trunk import box_at, box_pin_x

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from .place_env import PageEnv
    from .place_levels import Span
    from .values import Anchor

Reaches = dict[tuple[str, str, int, bool], int]


def _pose_reach(anchor: Anchor, *, north: bool) -> int:
    """The G the item's outline reaches for a pin that leaves north (a leg) or south (a driver)."""
    side = "N" if north else "S"
    boxes = [pose.outline for s, pose in anchor.poses if s == side]
    return max((-b.y if north else b.y + b.h for b in boxes), default=0)


def _fans_over(spans: Sequence[Span], row: int, at: int) -> Iterator[str]:
    """The fans whose trunk in `row` runs over the x `at`."""
    return (s.fan for s in spans if s.row == row and s.x0 <= at <= s.x1)


def card_reaches(env: PageEnv, x: Mapping[str, int], spans: Sequence[Span]) -> Reaches:
    """Per (fan, card, pin row's dy, north) the reach of its anchored items under that trunk."""
    out: Reaches = {}
    for anchor in env.problem.anchors:
        sym = anchor.pin.sym
        card = box_at(env, sym)
        if card is None:
            continue
        at = box_pin_x(env, x, sym, anchor.pin.pin)
        dy = pin_of(env.syms[sym], anchor.pin.pin).dy
        for fan in _fans_over(spans, card[1], at):
            for north in (True, False):
                key = (fan, sym, dy, north)
                out[key] = max(out.get(key, 0), _pose_reach(anchor, north=north))
    return out
