"""Cable engine, routing: the lower band's cores through the shared grid search (CT5-3, CD8).

Geometry only. A core is two runs and the cable box is closed, so the upper run is a straight
drop and every bend falls in the lower band. `channel` assigns each bending core, or each half
of a jogged one, a track; `grid_path` then draws that track's horizontal under the crossing rule.
"""

from dataclasses import dataclass
from itertools import pairwise
lazy from collections.abc import Mapping, Sequence

from fransys_layout.engines.cable.channel import Net, Plan, rise
from fransys_layout.geometry import WIRING_GRID, Box, Facing, Point
from fransys_layout.stages.grid_path import Field, axes_of, grid_path
from fransys_layout.stages.space import Cell, End, Obstacle

G = WIRING_GRID


@dataclass(frozen=True, slots=True)
class Band:
    """The lower band: its top edge, the boxes that close it, and the search's penalties."""

    top: int
    obstacles: tuple[Obstacle, ...]
    turn_penalty: int
    crossing_penalty: int
    head: int = 0  # the room a link track has above it for its text (CD8 at L1)


type Pair = tuple[Point, Point]


def _nets_of(plan: Plan, core: int) -> list[tuple[Net, int]]:
    return sorted(
        ((n, t) for n, t in zip(plan.nets, plan.tracks, strict=True) if n.core == core),
        key=lambda p: p[0].part,
    )


def _planned(
    pair: Pair, found: Sequence[tuple[Net, int]], band: Band, plan: Plan
) -> tuple[Point, ...]:
    """The corners of one core: down its column, along each track, down to its pin."""
    start, goal = pair
    if not found:
        return (start, goal)
    points: list[Point] = [start]
    for net, track in found:
        y = band.top + rise(plan, track, band.head)
        points += [Point(x=net.top, y=y), Point(x=net.bottom, y=y)]
    points.append(goal)
    return tuple(points)


def _foreign(core: int, planned: Sequence[tuple[Point, ...]]) -> dict[Cell, frozenset[str]]:
    axes: dict[Cell, frozenset[str]] = {}
    for i, points in enumerate(planned):
        if i != core:
            for cell, found in axes_of(points).items():
                axes[cell] = axes.get(cell, frozenset()) | found
    return axes


def _along(
    start: Point, goal: Point, band: Band, axes: Mapping[Cell, frozenset[str]]
) -> tuple[Point, ...] | None:
    """One track piece from `start` to `goal`, drawn by `grid_path` among the foreign wires."""
    east = goal.x > start.x
    field = Field(
        region=Box(x=min(start.x, goal.x), y=start.y, width=abs(goal.x - start.x), height=0),
        obstacles=band.obstacles,
        free=frozenset(),
        busy=frozenset(),
        turn_penalty=band.turn_penalty,
        crossing_penalty=band.crossing_penalty,
        axes=dict(axes),
    )
    return grid_path(
        End(at=start, facing=Facing.E if east else Facing.W),
        End(at=goal, facing=Facing.W if east else Facing.E),
        field,
    )


def route_lower(
    pairs: Sequence[Pair], keys: Sequence[int], plan: Plan, band: Band
) -> tuple[tuple[Point, ...], ...] | None:
    """The lower run of each core (`keys` one per pair), or None if one is stuck.

    Straight cores drop; the others follow `plan`, each track piece drawn by `grid_path` (C22).
    """
    planned = [
        _planned(pair, _nets_of(plan, key), band, plan)
        for key, pair in zip(keys, pairs, strict=True)
    ]
    for i, points in enumerate(planned):
        axes = _foreign(i, planned)
        for first, second in pairwise(points):
            if first.y == second.y and _along(first, second, band, axes) is None:
                return None
    return tuple(planned)
