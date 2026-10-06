"""`REDUNDANT_JOG`: joining the routes of one net end to end and finding its U-turns (lint.md 6.8).

Private to the geometric lint. Every input here is already one page and one physical net.
"""

from typing import TYPE_CHECKING

from fransys_layout.geometry import follow, legs
from fransys_layout.stages.space import run_admitted, span

from ._segments import own_ends_at

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import Point
    from fransys_layout.stages import Handle, LinkMarker, PlacedFunction, Route
    from fransys_layout.stages.space import Cell, End, Space

# One end of one route: its index and 0 for its first point or 1 for its last.
type _End = tuple[int, int]
# A route of a chain and the end it is entered at: 1 means it is walked backwards.
type _Link = tuple[Route, int]
type _Leg = tuple[Point, Point]

_JOINED = 2  # a point where exactly this many route ends meet joins them


def routes_with_a_jog(
    routes: tuple[Route, ...],
    space: Space,
    placed: tuple[PlacedFunction, ...],
    markers: tuple[LinkMarker, ...],
) -> tuple[tuple[Route, ...], ...]:
    """The joined polylines of `routes` that hold a redundant jog, each as its routes."""
    found = []
    for chain, ring in _chains(routes):
        points = tuple(route.points[side].at for route, _ in chain for side in (0, -1))
        own = own_ends_at(points, placed, markers)
        cells = frozenset((at.x, at.y) for at in points)
        legs = _legs(chain, ring=ring)
        if any(
            _is_jog(one, middle, other) and _admitted(one[0], other[1], space, own, cells)
            for one, middle, other in zip(legs, legs[1:], legs[2:], strict=False)
        ):
            found.append(tuple(route for route, _ in chain))
    return tuple(found)


def _admitted(
    first: Point,
    second: Point,
    space: Space,
    own: Mapping[Handle, tuple[End, ...]],
    cells: frozenset[Cell],
) -> bool:
    """Whether the router could have drawn the straight run: `run_admitted` inside its span."""
    obstacles = space.obstacles(own, span(first, second))
    return run_admitted((first.x, first.y), (second.x, second.y), obstacles, cells)


def _chains(routes: tuple[Route, ...]) -> list[tuple[list[_Link], bool]]:
    """Routes joined end to end where exactly two ends of two routes meet at one point."""
    meeting: dict[tuple[int, int], list[_End]] = {}
    for index, route in enumerate(routes):
        for side, at in enumerate((route.points[0].at, route.points[-1].at)):
            meeting.setdefault((at.x, at.y), []).append((index, side))
    partner: dict[_End, _End] = {}
    for ends in meeting.values():
        if len(ends) == _JOINED:
            partner[ends[0]] = ends[1]
            partner[ends[1]] = ends[0]
    taken: set[int] = set()
    chains = []
    for first in range(len(routes)):
        if first in taken:
            continue
        chain: list[_Link] = []
        state: _End | None = _head(first, partner)
        while state is not None and state[0] not in taken:
            taken.add(state[0])
            chain.append((routes[state[0]], state[1]))
            state = partner.get((state[0], 1 - state[1]))
        chains.append((chain, state is not None))
    return chains


def _head(first: int, partner: Mapping[_End, _End]) -> _End:
    """The route a chain through `first` starts at, with the end it is entered at."""
    return follow(
        (first, 0), lambda state: _flipped(partner.get(state)), key=lambda state: state[0]
    )[-1]


def _flipped(end: _End | None) -> _End | None:
    """The same route entered at its other end, or `None` for no end."""
    return None if end is None else (end[0], 1 - end[1])


def _legs(chain: Sequence[_Link], *, ring: bool) -> list[_Leg]:
    """The polyline of a chain as straight legs."""
    points = (
        point
        for route, entered in chain
        for point in (reversed(route.points) if entered else route.points)
    )
    found = [
        (first.at, second.at)
        for first, second in legs(points, at=lambda point: point.at, ring=ring)
    ]
    return [*found, *found[:2]] if ring else found


def _is_jog(one: _Leg, middle: _Leg, other: _Leg) -> bool:
    """Whether three legs leave a line and re-enter it: equal, opposite arms, a middle across."""
    return (
        _across(one, middle)
        and other[1].x - other[0].x == one[0].x - one[1].x
        and other[1].y - other[0].y == one[0].y - one[1].y
    )


def _across(one: _Leg, other: _Leg) -> bool:
    """Whether two orthogonal legs are perpendicular; a diagonal is across nothing."""
    return (one[0].y == one[1].y and other[0].x == other[1].x) or (
        one[0].x == one[1].x and other[0].y == other[1].y
    )
