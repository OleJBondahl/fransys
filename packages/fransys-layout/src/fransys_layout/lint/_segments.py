"""Runs of a route and the port ends they leave along, private to the geometric lint (lint.md 6.8).

The closed test the router uses (6.5), which `REDUNDANT_JOG` asks, is `stages.space.run_admitted`,
given the chain's own ends as `own_ends_at` finds them. The interior test `WIRE_THROUGH_SYMBOL`
and `WIRE_OVER_LABEL` read is `stages.space.crosses_unless_leaving`, given the lanes of the box:
`Space.obstacles` makes them from `own_ends_at` for a function's box (gated by the route's end
points), and `own_ends_at` gives a marker's own end for the jog check. `WIRE_OVER_LABEL` exempts no
run from a marker's box: a box never stands on a drawn wire, its own pin's wire included.
"""

from typing import TYPE_CHECKING

from fransys_layout.geometry import legs, port_page_at
from fransys_layout.stages.space import End, Run, run_of

if TYPE_CHECKING:
    from fransys_layout.geometry import Facing, Point
    from fransys_layout.stages import Handle, LinkMarker, PlacedFunction, Route


def runs_of(route: Route) -> tuple[Run, ...]:
    """The orthogonal runs of positive length; a diagonal or a repeated point is not one."""
    return tuple(
        run_of(first.at, second.at)
        for first, second in legs(route.points, at=lambda point: point.at, merge="none")
        if (first.at.x == second.at.x) != (first.at.y == second.at.y)
    )


def _facing_at(at: Point, placed: tuple[PlacedFunction, ...]) -> Facing | None:
    """The facing of the first placed port that sits exactly on `at`, or `None`."""
    return next(
        (
            port.facing
            for one in placed
            for port in one.geometry.ports
            if port_page_at(one.at, port) == at
        ),
        None,
    )


def marker_ends(marker: LinkMarker, placed: tuple[PlacedFunction, ...]) -> tuple[End, ...]:
    """The own end of `marker`'s port, or none when no placed port sits on `marker.at`."""
    facing = _facing_at(marker.at, placed)
    return () if facing is None else (End(at=marker.at, facing=facing),)


def own_ends_at(
    ends: tuple[Point, ...], placed: tuple[PlacedFunction, ...], markers: tuple[LinkMarker, ...]
) -> dict[Handle, tuple[End, ...]]:
    """The own ends of a chain's end points by owner, as `Space.obstacles` takes them."""
    own: dict[Handle, tuple[End, ...]] = {}
    for one in placed:
        for port in one.geometry.ports:
            at = port_page_at(one.at, port)
            if at in ends:
                own[one.function] = (*own.get(one.function, ()), End(at=at, facing=port.facing))
    for marker in markers:
        found = marker_ends(marker, placed)
        if marker.at in ends and found:
            own[marker.port] = (*own.get(marker.port, ()), *found)
    return own
