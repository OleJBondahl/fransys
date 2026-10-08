"""TALL-PAGE (layout-0167): what the fold does with a cut group, and how far down it reaches.

Private to `middle_fold`. A cut group draws its outline only on the page of its lower band (T2,
T3). T4 (the lower columns that pass the bottom standing beside the outline) is held out of 0.13.5
(designer R3); the fallback's own order rebuilds it.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, snap_up
from fransys_model.kernel import Finding, Severity

from .lookups import placed_keepout
from .place import PAGE_OVERFULL

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .middle import MiddleGroup
    from .middle_fold import GroupShape, _Page
    from .types import PlacedFunction


def stack_lower(
    lower: Sequence[AuthoringKey],
    hulls: Mapping[AuthoringKey, Box],
    moves: Mapping[AuthoringKey, tuple[int, int]],
    deepest: int,
) -> dict[AuthoringKey, tuple[int, int]]:
    """HL20: the lower columns move down together until the highest is at `deepest`."""
    dy = snap_up(deepest - min((hulls[key].y for key in lower), default=deepest))
    return {key: (dx, dy) for key, (dx, _) in moves.items()}


def measured(
    shape: GroupShape,
    group: MiddleGroup,
    page: _Page,
    lower_moves: tuple[Sequence[AuthoringKey], Mapping[AuthoringKey, tuple[int, int]]],
) -> GroupShape:
    """T1: `shape` with how far down the fold reaches, and whether the group is held.

    The reach is the lowest of the outline, its boxes and the moved lower columns. Replicas in the
    upper band send the cut below (A1); with bottom replicas too, the group is held.
    """
    lower, moves = lower_moves
    hulls = page.hulls
    ends = [shape.outline.y + shape.outline.height]
    ends += [one.box.y + one.box.height for one in shape.boxes]
    ends += [hulls[key].y + moves[key][1] + hulls[key].height for key in lower]
    top, bottom = page.reps[group.unit.unit]
    upper = any(one.column in group.upper for one in (*top, *bottom))
    return replace(shape, bottom=max(ends), held=upper and bool(bottom), below=upper and not bottom)


_MESSAGE = "page content is taller than the content box: nothing is scaled"


def fold_overfull(
    placed: Sequence[PlacedFunction],
    shapes: Sequence[GroupShape],
    floor: int,
    found: tuple[Finding, ...],
) -> tuple[Finding, ...]:
    """T6: a folded group still below the page adds its cells to the page's `PAGE_OVERFULL`.

    `found` is what `place` reported before the fold; one finding names both sets of cells.
    """
    if not any(shape.bottom > floor for shape in shapes):
        return found
    below = {one.function for one in placed if _reach(one) > floor}
    below |= {shape.lead for shape in shapes if shape.bottom > floor}
    named = [one for one in found if one.code == PAGE_OVERFULL]
    below |= {subject for one in named for subject in one.subjects}
    rest = tuple(one for one in found if one.code != PAGE_OVERFULL)
    return (
        *rest,
        Finding(
            code=PAGE_OVERFULL,
            severity=Severity.WARNING,
            subjects=tuple(sorted(below)),
            message=_MESSAGE,
        ),
    )


def _reach(one: PlacedFunction) -> int:
    keepout = placed_keepout(one)
    return keepout.y + keepout.height
