"""The diagram placer's labels: a line's text sits above the middle of its longest run."""

from itertools import pairwise
lazy from collections.abc import Sequence

from fransys_layout.engines.diagram.sizes import TEXT_LEAD
from fransys_layout.geometry import WIRING_GRID as G
from fransys_layout.geometry import Box, overlaps
from fransys_layout.stages.space import crosses, run_of
lazy from fransys_layout.engines.diagram.values import LineFacts, PlacedBox, PlacedLine
lazy from fransys_layout.geometry import Point
lazy from fransys_layout.stages.space import Run


def label_at(points: tuple[Point, ...], text_height: int) -> tuple[int, int]:
    """The label's centre: above the longest horizontal run (the first on a tie), on the grid."""
    runs = [(a, b) for a, b in pairwise(points) if a.y == b.y]
    a, b = max(runs, key=lambda r: abs(r[1].x - r[0].x), default=(points[0], points[0]))
    return (a.x + b.x) // 2 // G * G, (a.y - text_height // 2 - TEXT_LEAD) // G * G


def label_box(x: int, y: int, width: int, text_height: int) -> Box:
    """The box a label of `width` takes when its centre is `(x, y)`."""
    return Box(x=x - width // 2, y=y - text_height // 2, width=width, height=text_height)


def _spots(points: tuple[Point, ...], text_height: int, width: int) -> list[tuple[int, int, int]]:
    """Each place a label may stand, as `(x, y, reach)`: above, then below, each horizontal run.

    Runs go longest first. `reach` is how far the centre may move either side with the label's
    width still over the run, 0 when the run is the narrower.
    """
    runs = sorted(
        (r for r in pairwise(points) if r[0].y == r[1].y), key=lambda r: -abs(r[1].x - r[0].x)
    )
    gap = text_height // 2 + TEXT_LEAD
    return [
        (
            (a.x + b.x) // 2 // G * G,
            (a.y - gap) // G * G if above else -(-(a.y + gap) // G) * G,
            max(0, (abs(b.x - a.x) - width) // 2) // G * G,
        )
        for above in (True, False)
        for a, b in runs
    ]


def label_clear(
    points: tuple[Point, ...],
    text_height: int,
    width: int,
    blocked: Sequence[Run],
    taken: Sequence[Box],
) -> tuple[int, int]:
    """The label's centre: `label_at`'s, or the nearest place along a run that is free of ink.

    Free means no run of `blocked` passes through the label's box and no box of `taken` overlaps
    it. Runs are tried longest first, above before below; none free gives `label_at`'s place.
    """
    for x, y, reach in _spots(points, text_height, width):
        for step in range(0, reach + 1, G):
            for cx in dict.fromkeys((x - step, x + step)):
                box = label_box(cx, y, width, text_height)
                if not any(crosses(box, r) for r in blocked) and not any(
                    overlaps(box, t) for t in taken
                ):
                    return cx, y
    return label_at(points, text_height)


def label_lines(
    here: Sequence[tuple[LineFacts, tuple[Point, ...]]],
    boxes: Sequence[PlacedBox],
    text_height: int,
) -> tuple[PlacedLine, ...]:
    """The lines of one sheet, each label clear of every line run and of the boxes and labels."""
    runs = [run_of(a, b) for _, pts in here for a, b in pairwise(pts)]
    taken = [Box(x=b.x, y=b.y, width=b.width, height=b.height) for b in boxes]
    lines = []
    for ln, pts in here:
        x, y = label_clear(pts, text_height, ln.label_width, runs, taken)
        taken.append(label_box(x, y, ln.label_width, text_height))
        lines.append(PlacedLine(cable=ln.cable, a=ln.a, b=ln.b, points=pts, text_x=x, text_y=y))
    return tuple(lines)
