"""A beside wire's ends: which pin keeps its way and which one leaves sideways (layout-0174)."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import OPPOSITE, WIRING_GRID, Facing

from ._sides import located

if TYPE_CHECKING:
    from ._sides import Edge, Ends


def sideways_ends(edge: Edge, ends: Ends, *, above: bool = True) -> Ends:
    """`ends` with a level edge's ends facing each other along x: a beside wire leaves sideways.

    `above` enters an up pin from above (JOIN-VERTICAL); off, the shallower pin keeps its way.
    """
    start, goal = ends[located(edge.a)], ends[located(edge.b)]
    if start.at.x == goal.at.x:
        return ends
    if start.at.y == goal.at.y:
        way = Facing.E if goal.at.x > start.at.x else Facing.W
        both = {**ends, located(edge.a): replace(start, facing=way)}
        return {**both, located(edge.b): replace(goal, facing=OPPOSITE[way])}
    # A deeper pin that points up keeps its way and is entered from above (JOIN-VERTICAL), else
    # the shallower one when it leaves down; the other end is entered sideways. Two grids or more
    # between a down pin and an up pin leave both their ways, a jog between them.
    high, low = (edge.a, edge.b) if start.at.y < goal.at.y else (edge.b, edge.a)
    top, bottom = ends[located(high)], ends[located(low)]
    if (
        above
        and bottom.facing is Facing.N
        and not (top.facing is Facing.S and bottom.at.y - top.at.y > WIRING_GRID)
    ):
        keeper, tail, key = bottom, top, located(high)
    elif top.facing is Facing.S and (bottom.facing is not Facing.N or not above):
        keeper, tail, key = top, bottom, located(low)
    else:
        return ends
    way = Facing.W if keeper.at.x < tail.at.x else Facing.E
    return {**ends, key: replace(tail, facing=way)}
