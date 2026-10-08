"""TALL-PAGE (layout-0167): which groups the engine cuts, and what a folded page reports.

`tall_groups` names the units to cut from the first placing and `recut` flags them for the second
planning pass (C21), where partition makes two packing units of each. `folded_page` is the page's
fold and its `PAGE_OVERFULL` after it (T6).
"""

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey, Id

    from .middle import MiddleGroup
    from .middle_fold import GroupShape
    from .pagerun import PageRun


class Cut(NamedTuple):
    """How a tall group cuts: the outline's left edge from the lower columns', and the edge (A1)."""

    frame_dx: int
    below: bool


def tall_groups(
    pages: Sequence[tuple[Any, Any]],
    content_height: int,
    middle: Mapping[AuthoringKey, tuple[MiddleGroup, ...]],
) -> dict[Id[Any], Cut]:
    """T1: the units whose one folded shape reaches below the page and may be cut.

    Each maps to its shape's `frame_dx`, the value the cut page repeats, and its edge. A held
    shape, a unit split over pages (T7) and a group `recut` holds (`_cuttable`) stay as they are.
    """
    cuttable = _cuttable(middle)
    shapes: list[GroupShape] = [shape for _, call in pages for shape in call.shapes]
    count = Counter(shape.unit for shape in shapes)
    return {
        shape.unit: Cut(shape.frame_dx, shape.below)
        for shape in shapes
        if shape.bottom > content_height
        and not shape.held
        and count[shape.unit] == 1
        and shape.unit in cuttable
    }


def recut(run: PageRun, tall: Mapping[Id[Any], Cut]) -> PageRun:
    """T2: `run` with each tall group flagged `cut`, unless it shares a column with another."""
    if not tall:
        return run
    middle = run.inputs.middle
    cut = {
        key: tuple(
            replace(g, cut=True, **tall[g.unit.unit]._asdict()) if g.unit.unit in tall else g
            for g in found
        )
        for key, found in middle.items()
    }
    return replace(run, inputs=replace(run.inputs, middle=cut))


def _cuttable(middle: Mapping[AuthoringKey, tuple[MiddleGroup, ...]]) -> set[Id[Any]]:
    """The units that may be cut: no column shared, and a lower band to carry the outline."""
    unique = {group.unit.unit: group for found in middle.values() for group in found}.values()
    seen = Counter(key for group in unique for key in group.upper | group.lower)
    return {
        group.unit.unit
        for group in unique
        if group.lower and all(seen[key] == 1 for key in group.upper | group.lower)
    }
