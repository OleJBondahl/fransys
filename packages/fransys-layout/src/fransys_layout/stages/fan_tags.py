"""A tag a side fan wraps moves to its symbol's mirror side (layout-0172 round 3).

The fan stands to the side of the line's other end; a tag on that side would sit inside its
outline, so it takes the other side of its symbol when that place is free.
"""

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, contains, is_clear, overlaps, translate
from fransys_layout.stages.space import Run, crosses

from .content import content_box
from .types import LabelKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.geometry import Point

    from .line_shapes import DrawnFanOut, DrawnLine
    from .types import PlacedFunction, PlacedLabel, SheetFormat


def _outline(fan: DrawnFanOut) -> Box:
    """The box round a fan: its split and every leg's points."""
    points = [fan.at, *(p for leg in fan.legs for p in leg.points)]
    left, top = min(p.x for p in points), min(p.y for p in points)
    return Box(
        x=left, y=top, width=max(p.x for p in points) - left, height=max(p.y for p in points) - top
    )


def _runs(points: Sequence[Point]) -> list[Run]:
    return [Run(x=a.x, y=a.y, to_x=b.x, to_y=b.y) for a, b in pairwise(points)]


def _ink(
    fans: Sequence[DrawnFanOut], lines: Sequence[DrawnLine], page: tuple[int, int]
) -> list[Run]:
    """The runs of every leg and line on `page`."""
    legs = [leg.points for fan in fans if (fan.drawing_set, fan.page) == page for leg in fan.legs]
    mine = [line.points for line in lines if (line.drawing_set, line.page) == page]
    return [run for points in (*legs, *mine) for run in _runs(points)]


def _mirrored(label: PlacedLabel, owner: PlacedFunction) -> Box:
    """`label`'s box on the other side of its owner's body, across the axis it stands off along."""
    body = translate(owner.geometry.body, dx=owner.at.x, dy=owner.at.y)
    box = label.box
    across_x = abs(2 * box.x + box.width - 2 * body.x - body.width)
    across_y = abs(2 * box.y + box.height - 2 * body.y - body.height)
    if across_y > across_x:  # the tag stands north or south: a fan opening that way wraps it
        return replace(box, y=2 * body.y + body.height - box.y - box.height)
    return replace(box, x=2 * body.x + body.width - box.x - box.width)


def _outlines(fans: Sequence[DrawnFanOut]) -> dict[tuple[int, int], list[Box]]:
    """The outline of each side fan (two or more legs), by page."""
    found: dict[tuple[int, int], list[Box]] = {}
    for fan in fans:
        if fan.legs[1:]:
            found.setdefault((fan.drawing_set, fan.page), []).append(_outline(fan))
    return found


def _blockers(
    page: tuple[int, int],
    labels: Sequence[PlacedLabel],
    placed: Sequence[PlacedFunction],
    lines: Sequence[DrawnLine],
) -> list[Box]:
    """The bodies, labels and line labels on `page` that a moved tag keeps clear of."""
    found = [translate(o.geometry.body, dx=o.at.x, dy=o.at.y) for o in placed]
    return [
        box
        for (where, box) in [
            *(((o.drawing_set, o.page), b) for o, b in zip(placed, found, strict=True)),
            *(((one.drawing_set, one.page), one.box) for one in labels),
            *(((one.drawing_set, one.page), one.label) for one in lines),
        ]
        if where == page
    ]


def tags_out_of_fans(
    labels: Sequence[PlacedLabel],
    placed: Sequence[PlacedFunction],
    fans: Sequence[DrawnFanOut],
    lines: Sequence[DrawnLine],
    sheet: SheetFormat,
) -> tuple[PlacedLabel, ...]:
    """`labels`, each tag that a fan of two or more legs wraps moved to its symbol's far side."""
    content = content_box(sheet)
    where = {(one.function, one.drawing_set, one.page): one for one in placed}
    outlines = _outlines(fans)
    kept = list(labels)
    for index, label in enumerate(labels):
        page = (label.drawing_set, label.page)
        owner = where.get((label.subject, *page))
        wrapped = [
            box
            for box in outlines.get(page, ())
            if label.kind is LabelKind.TAG and overlaps(label.box, box)
        ]
        if owner is None or not wrapped:
            continue
        box = _mirrored(label, owner)
        blockers = _blockers(page, kept[:index] + kept[index + 1 :], placed, lines)
        free = contains(content, box) and is_clear(box, blockers + wrapped)
        if free and not any(crosses(box, run) for run in _ink(fans, lines, page)):
            kept[index] = replace(label, box=box)
    return tuple(kept)
