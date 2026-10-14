"""Layout-0158: a page's line labels, and the line and fan-out records drawn from its pieces."""

from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import pad
from fransys_layout.geometry.units import TEXT_GAP
from fransys_layout.stages.content import content_box
from fransys_layout.stages.harness_route import line_text, text_centre
from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLine, slant_boxes
from fransys_layout.stages.space import Shape, Space, span
from fransys_layout.stages.texts.place_texts import place_texts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.line_draw import Pieces
    from fransys_model.kernel import Finding, Id

    from ._lines import LineScene, _Page
    from .read.harness_lines import LineRead
    from .read.line_texts import LineTexts


def _label_boxes(
    paths: Sequence[tuple[Id[Any], int, tuple[Any, ...]]],
    legs: Sequence[tuple[Any, ...]],
    texts: LineTexts,
    shapes: Sequence[Shape],
    scene: LineScene,
) -> tuple[dict[tuple[Id[Any], int], Any], tuple[Finding, ...]]:
    """Each path's designation at the first free candidate along its longest run.

    Every run keeps every label the house text gap off (layout-0158); a fan-out leg is kept clear
    along its slant, sampled every `WIRING_GRID // 2`.
    """
    runs = [
        Shape(owner=None, box=pad(span(first, second), TEXT_GAP))
        for _, _, points in paths
        for first, second in pairwise(points)
    ]
    runs += [Shape(owner=None, box=box) for leg in legs for box in slant_boxes(leg)]
    to_place = tuple(
        line_text(owner, branch, points, texts.size(owner, branch, scene.profile))
        for owner, branch, points in paths
    )
    space = Space(shapes=(*shapes, *runs), content=content_box(scene.sheet))
    placed, unplaced = place_texts(to_place, space, scene.profile.texts)
    return {(one.handle, int(one.slot)): one for one in placed}, unplaced


def _drawn_lines(
    paths: Sequence[tuple[Id[Any], int, tuple[Any, ...]]],
    centres: Mapping[tuple[Id[Any], int], Any],
    page: _Page,
) -> tuple[DrawnLine, ...]:
    """Each path as a `DrawnLine` on `page`, its label at the centre placed for it."""
    return tuple(
        DrawnLine(
            harness=owner,
            branch=branch,
            drawing_set=page[0],
            page=page[1],
            points=points,
            text=text_centre(centres[owner, branch]),
            label=centres[owner, branch].box,
        )
        for owner, branch, points in paths
    )


def _drawn_fans(pieces: Sequence[tuple[LineRead, Pieces]], page: _Page) -> tuple[DrawnFanOut, ...]:
    """Each fan-out of the pieces as a `DrawnFanOut` on `page`."""
    return tuple(
        DrawnFanOut(
            harness=line.owner,
            branch=fan.branch,
            drawing_set=page[0],
            page=page[1],
            at=fan.at,
            legs=fan.legs,
        )
        for line, one in pieces
        for fan in one.fans
    )
