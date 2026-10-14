"""layout-0167: which groups the engine cuts, and what a folded page reports.

`tall_groups` names the units to cut from the first placing and `recut` flags them for the second
planning pass, where partition makes two packing units of each. `folded_page` is the page's
fold and its `PAGE_OVERFULL` after it.
"""

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING, Any, NamedTuple

from fransys_model.kernel import AuthoringKey

from .lookups import placed_keepout

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id

    from .middle import MiddleGroup
    from .pagerun import PageRun
    from .types import PlacedFunction


class Cut(NamedTuple):
    """How a tall group cuts: the outline's left edge from the lower columns', and the edge.

    `carry` is the upper column a group with no lower band hands down (layout-0234): it stands
    below the outline on the next page and so carries the outline there.
    """

    frame_dx: int
    below: bool
    carry: frozenset[AuthoringKey] = frozenset[AuthoringKey]()


def tall_groups(
    pages: Sequence[tuple[Sequence[PlacedFunction], Any]],
    content_height: int,
    middle: Mapping[AuthoringKey, tuple[MiddleGroup, ...]],
) -> dict[Id[Any], Cut]:
    """The units whose one folded shape reaches below the page and may be cut.

    Each maps to its shape's `frame_dx` (repeated on the cut page) and edge. A held shape, a split
    unit and a group `recut` holds stay; one with no lower band hands a column down (`_carry`).
    """
    cuttable = _cuttable(middle)
    found = [(placed, shape) for placed, call in pages for shape in call.shapes]
    count = Counter(shape.unit for _, shape in found)
    groups = {g.unit.unit: g for gs in middle.values() for g in gs}
    cuts: dict[Id[Any], Cut] = {}
    for placed, shape in found:
        group = groups.get(shape.unit)
        if not (
            shape.bottom > content_height
            and not shape.held
            and count[shape.unit] == 1
            and shape.unit in cuttable
            and group is not None
        ):
            continue
        carry = frozenset[AuthoringKey]() if group.lower else _carry(group, placed)
        if group.lower or (carry and not shape.below):
            cuts[shape.unit] = Cut(shape.frame_dx, shape.below, carry)
    return cuts


def _carry(group: MiddleGroup, placed: Sequence[PlacedFunction]) -> frozenset[AuthoringKey]:
    """The shortest upper column on the page, the last on a tie; none when it would be the only."""
    heights: dict[AuthoringKey, list[int]] = {}
    for one in placed:
        if one.column in group.upper:
            box = placed_keepout(one)
            low, high = heights.setdefault(one.column, [box.y, box.y + box.height])
            heights[one.column] = [min(low, box.y), max(high, box.y + box.height)]
    if len(heights) <= 1:
        return frozenset[AuthoringKey]()
    return frozenset({min(reversed(list(heights)), key=lambda k: heights[k][1] - heights[k][0])})


def recut(run: PageRun, tall: Mapping[Id[Any], Cut]) -> PageRun:
    """`run` with each tall group flagged `cut`, unless it shares a column with another."""
    if not tall:
        return run
    middle = run.inputs.middle
    cut = {
        key: tuple(_flagged(g, tall[g.unit.unit]) if g.unit.unit in tall else g for g in found)
        for key, found in middle.items()
    }
    return replace(run, inputs=replace(run.inputs, middle=cut))


def _flagged(group: MiddleGroup, how: Cut) -> MiddleGroup:
    """`group` cut as `how` says, its carried column moved from the upper band to the lower."""
    return replace(
        group,
        cut=True,
        frame_dx=how.frame_dx,
        below=how.below,
        upper=group.upper - how.carry,
        lower=group.lower | how.carry,
    )


def _cuttable(middle: Mapping[AuthoringKey, tuple[MiddleGroup, ...]]) -> set[Id[Any]]:
    """The units that may be cut: no column shared, and a column to carry the outline.

    A lower band carries it; with none, a second upper column hands one down (layout-0234).
    """
    unique = {group.unit.unit: group for found in middle.values() for group in found}.values()
    seen = Counter(key for group in unique for key in group.upper | group.lower)
    return {
        group.unit.unit
        for group in unique
        if (group.lower or len(group.upper) > 1)
        and all(seen[key] == 1 for key in group.upper | group.lower)
    }
