"""Junction points (layout-0335): where three or more things of one net meet on a page."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .score_wiring import _heading
from .values import PinRef

if TYPE_CHECKING:
    from .outputs import CoreLayout
    from .values import XY

__all__ = ("Junction", "junctions")

#: A point is a junction when this many wire directions and pins of one net meet there.
_MEETING = 3

type _Key = tuple[int, str]
type _Segment = tuple[XY, XY]


@dataclass(frozen=True, slots=True)
class Junction:
    """One junction point on `page`, in G, and the net it joins."""

    net: str
    page: int
    x: int
    y: int


def _leaves(point: XY, segment: _Segment) -> set[XY]:
    """The unit directions in which `segment` leaves `point`, if the point lies on it."""
    (x1, y1), (x2, y2) = segment
    x, y = point
    inside = min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
    straight = (x1 == x2 == x) or (y1 == y2 == y)  # the wires are rectilinear
    if not (inside and straight):
        return set()
    return {d for d in (_heading(point, segment[0]), _heading(point, segment[1])) if d != (0, 0)}


def _segments(layout: CoreLayout) -> dict[_Key, list[_Segment]]:
    """Every wire segment of each (page, net)."""
    found: dict[_Key, list[_Segment]] = {}
    for page in layout.routes.pages:
        for wire in page.wires:
            found.setdefault((page.page, wire.net), []).extend(
                zip(wire.points, wire.points[1:], strict=False)
            )
    return found


def _pins(layout: CoreLayout) -> dict[tuple[_Key, XY], set[PinRef]]:
    """The wired pins standing at each (page, net) point."""
    net_of = dict(layout.wired)
    found: dict[tuple[_Key, XY], set[PinRef]] = {}
    for sheet in layout.placement.pages:
        for placed in sheet.placed:
            for pin in placed.pin_xy:
                ref = PinRef(placed.sym, pin.pin)
                if ref in net_of:
                    found.setdefault(((sheet.page, net_of[ref]), (pin.x, pin.y)), set()).add(ref)
    return found


def junctions(layout: CoreLayout) -> tuple[Junction, ...]:
    """Each point where three or more wire directions and pins of one net meet.

    A direction counts once however many wires overlap on it; a pin counts once. A wire that runs
    straight past a point is two directions there. Order: first appearance in the wires, then pins.
    """
    segments, pins = _segments(layout), _pins(layout)
    keyed = dict.fromkeys(
        [(key, point) for key, segs in segments.items() for seg in segs for point in seg]
        + list(pins)
    )
    found = []
    for key, point in keyed:
        directions: set[XY] = set()
        for seg in segments.get(key, ()):
            directions |= _leaves(point, seg)
        if len(directions) + len(pins.get((key, point), ())) >= _MEETING:
            found.append(Junction(key[1], key[0], *point))
    return tuple(found)
