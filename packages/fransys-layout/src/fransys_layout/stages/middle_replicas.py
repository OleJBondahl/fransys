"""HL11: a middle unit's no-line interfaces, today's pin replicas, inside its outline at an edge.

Designer's P3 condition 3: no D11 frame for a middle unit; its replicas stand on the outline's
edges that HL13's step 2 gives them, after that edge's boxes.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, Point

from .lookups import placed_keepout

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id

    from .middle import MiddleGroup
    from .types import PlacedFunction


def replicas(
    group: MiddleGroup, placed: Sequence[PlacedFunction]
) -> tuple[list[PlacedFunction], list[PlacedFunction]]:
    """The no-line interfaces' replica views on the page: the top edge's, the bottom edge's."""
    edge = {
        view: one.edge.function in group.top
        for one in group.unit.interfaces
        if not one.edge.line
        for view in one.views
    }
    mine = [one for one in placed if one.function in edge]
    return [one for one in mine if edge[one.function]], [
        one for one in mine if not edge[one.function]
    ]


def replica_width(edge: Sequence[PlacedFunction], gap: int) -> int:
    """An edge's replicas side by side, a column gap apart, each its keep-out wide."""
    return sum(placed_keepout(one).width + gap for one in edge)


def replica_height(edge: Sequence[PlacedFunction]) -> int:
    """The tallest replica's keep-out height."""
    return max((placed_keepout(one).height for one in edge), default=0)


def replica_places(
    edge: Sequence[PlacedFunction], frame: Box, x: int, gap: int, *, top: bool
) -> dict[Id[Any], Point]:
    """Each replica's new `at`: side by side from `x`, a grid inside the edge of `frame`."""
    found: dict[Id[Any], Point] = {}
    for one in sorted(edge, key=lambda one: (one.at.x, one.function)):
        keepout = placed_keepout(one)
        y = frame.y + WIRING_GRID if top else frame.y + frame.height - WIRING_GRID - keepout.height
        found[one.function] = Point(x=one.at.x + x - keepout.x, y=one.at.y + y - keepout.y)
        x += keepout.width + gap
    return found
