"""Junction points (layout-0335): where three or more things of one net meet on a page.

`route_page` writes them as `PageRoutes.dots` (layout-0395, R535 H10).
"""

from typing import TYPE_CHECKING

from .outputs import Junction
from .score_wiring import heading
from .values import PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .outputs import Wire
    from .route_env import RouteEnv
    from .values import XY

__all__ = ("page_junctions",)

#: A point is a junction when this many wire directions and pins of one net meet there.
_MEETING = 3

type _Key = tuple[int, str]
type _Segment = tuple[XY, XY]


def _leaves(point: XY, segment: _Segment) -> set[XY]:
    """The unit directions in which `segment` leaves `point`, if the point lies on it."""
    (x1, y1), (x2, y2) = segment
    x, y = point
    inside = min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
    straight = (x1 == x2 == x) or (y1 == y2 == y)  # the wires are rectilinear
    if not (inside and straight):
        return set()
    return {d for d in (heading(point, segment[0]), heading(point, segment[1])) if d != (0, 0)}


def _found(segments: Mapping[_Key, Sequence[_Segment]], pins: Mapping[tuple[_Key, XY], AbstractSet[PinRef]]) -> tuple[Junction, ...]:
    """The junction rule over the segments and pins of each (page, net)."""
    keyed = dict.fromkeys([(key, point) for key, segs in segments.items() for seg in segs for point in seg] + list(pins))
    found = []
    for key, point in keyed:
        directions: set[XY] = set()
        for seg in segments.get(key, ()):
            directions |= _leaves(point, seg)
        if len(directions) + len(pins.get((key, point), ())) >= _MEETING:
            found.append(Junction(key[1], key[0], *point))
    return tuple(found)


def _anchor_leads(env: RouteEnv) -> dict[_Key, list[_Segment]]:
    """The lead from each anchored pin to its symbol's port: a conductor segment of the pin's net (layout-0451)."""
    found: dict[_Key, list[_Segment]] = {}
    for keep in env.obstacles:
        if keep.kind != "anchor" or keep.net is None or keep.port is None or keep.owner not in env.placed:
            continue
        for pin in env.placed[keep.owner].pin_xy:
            if env.net_of.get(PinRef(keep.owner, pin.pin)) == keep.net and (pin.x == keep.port[0] or pin.y == keep.port[1]):
                found.setdefault((env.page, keep.net), []).append(((pin.x, pin.y), keep.port))
                break
    return found


def page_junctions(env: RouteEnv, wires: Sequence[Wire]) -> tuple[Junction, ...]:
    """The junctions of one page's `wires`: three or more directions and pins of one net (R535 H10).

    Anchor leads count as wires. Pins are the page's placed pins that `env.net_of` gives a net; order: wires first, then pins.
    """
    segments = _anchor_leads(env)
    for wire in wires:
        segments.setdefault((env.page, wire.net), []).extend(zip(wire.points, wire.points[1:], strict=False))
    pins: dict[tuple[_Key, XY], set[PinRef]] = {}
    for placed in env.placed.values():
        for pin in placed.pin_xy:
            ref = PinRef(placed.sym, pin.pin)
            if ref in env.net_of:
                pins.setdefault(((env.page, env.net_of[ref]), (pin.x, pin.y)), set()).add(ref)
    return _found(segments, pins)
