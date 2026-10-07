"""A link marker's stub as runs, and which other functions it runs through (layout-0093 M9).

The one home of "a stub runs through a foreign symbol": placement refuses a place by it and the
lint reports it. A foreign symbol is a function with no port at the marker's point; the stub
runs through it when it crosses the body's interior or passes over one of its ports.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_layout.geometry import Box, Point, meets

from .cell_index import CellIndex
from .space import Run, crosses, run_of

if TYPE_CHECKING:
    from fransys_layout.stages import Handle, LinkMarker


def stub_runs(marker: LinkMarker) -> tuple[Run, ...]:
    """The marker's stub as one run, port to box or `turn` to box; a box beyond a lane has two."""
    start = marker.at if marker.turn is None else marker.turn
    box = marker.box
    if marker.turn is not None:  # M7: the branch, then the stub up to the box
        end = Point(x=box.x + box.width // 2, y=start.y)
        near = Point(x=end.x, y=box.y + box.height if box.y < start.y else box.y)
        return (run_of(start, end), run_of(end, near))
    run = _run_to_box(start, box)
    if run is not None:
        return (run,)
    right, bottom = box.x + box.width, box.y + box.height
    if box.x <= start.x <= right or box.y <= start.y <= bottom:
        return ()  # no box beside its stub: a start beside the box is `_run_to_box`'s
    near = Point(x=start.x, y=box.y if start.y < box.y else bottom)
    runs = (run_of(start, near),)
    if marker.lead:
        corner = Point(x=box.x if start.x < box.x else right, y=near.y)
        runs += (run_of(near, corner),)
    return runs


def _run_to_box(start: Point, box: Box) -> Run | None:
    """The axis-aligned run from `start` to the nearest edge of `box`, if `start` faces it."""
    right = box.x + box.width
    bottom = box.y + box.height
    if box.x <= start.x <= right and not box.y < start.y < bottom:
        end = Point(x=start.x, y=bottom if start.y >= bottom else box.y)
    elif box.y <= start.y <= bottom and not box.x < start.x < right:
        end = Point(x=right if start.x >= right else box.x, y=start.y)
    else:
        return None
    return None if end == start else run_of(start, end)


@dataclass(frozen=True, slots=True)
class Solids:
    """A page's bodies and port points keyed by wiring-grid cell, each with its body-order rank."""

    bodies: CellIndex[tuple[int, Handle, Box]]
    ports: CellIndex[tuple[int, Handle, Point]]


def solids(bodies: Mapping[Handle, Box], ports: Mapping[Handle, tuple[Point, ...]]) -> Solids:
    """The index `functions_through` reads; a port of a function with no body is no candidate."""
    rank = {function: place for place, function in enumerate(bodies)}
    return Solids(
        bodies=CellIndex(
            (box, (rank[function], function, box)) for function, box in bodies.items()
        ),
        ports=CellIndex(
            (Box(x=point.x, y=point.y, width=0, height=0), (rank[function], function, point))
            for function, points in ports.items()
            if function in rank
            for point in points
        ),
    )


def functions_through(marker: LinkMarker, solids: Solids) -> tuple[Handle, ...]:
    """The foreign functions the marker's stub runs through or over, in body order."""
    at = marker.at
    own = {
        function
        for _, function, point in solids.ports.meeting(at.x, at.y, at.x, at.y)
        if point == at
    }
    hit: set[tuple[int, Handle]] = set()
    for run in stub_runs(marker):
        corners = (run.x, run.y, run.to_x, run.to_y)
        hit.update((r, f) for r, f, body in solids.bodies.meeting(*corners) if crosses(body, run))
        hit.update((r, f) for r, f, p in solids.ports.meeting(*corners) if _on(p, at, (run,)))
    return tuple(function for _, function in sorted(hit) if function not in own)


def _on(point: Point, own: Point, runs: tuple[Run, ...]) -> bool:
    """Whether a port point other than `own` lies on one of the runs, ends included."""
    return point != own and any(
        meets((run.x, run.to_x), (point.x, point.x))
        and meets((run.y, run.to_y), (point.y, point.y))
        for run in runs
    )
