"""A link marker's stub as runs, and which other functions it runs through (layout-0093 M9).

The one home of "a stub runs through a foreign symbol": placement refuses a place by it and the
lint reports it. A foreign symbol is a function with no port at the marker's point; the stub
runs through it when it crosses the body's interior or passes over one of its ports.
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_layout.geometry import Box, Point, meets

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


def functions_through(
    marker: LinkMarker,
    bodies: Mapping[Handle, Box],
    ports: Mapping[Handle, tuple[Point, ...]],
) -> tuple[Handle, ...]:
    """The foreign functions the marker's stub runs through or over, in `bodies` order."""
    own = {function for function, points in ports.items() if marker.at in points}
    runs = stub_runs(marker)
    return tuple(
        function
        for function, body in bodies.items()
        if function not in own
        and (
            any(crosses(body, run) for run in runs)
            or any(_on(point, marker.at, runs) for point in ports[function])
        )
    )


def _on(point: Point, own: Point, runs: tuple[Run, ...]) -> bool:
    """Whether a port point other than `own` lies on one of the runs, ends included."""
    return point != own and any(
        meets((run.x, run.to_x), (point.x, point.x))
        and meets((run.y, run.to_y), (point.y, point.y))
        for run in runs
    )
