"""The diagram placer's routes (BD5): a line's points from its first end to its second, in G.

A line between adjacent columns follows its planned tracks. A same-column line leaves the east
edges to track count+1+k of the channel right of its column (k its index in `same`), or to the
cut's zone; those tracks are reserved clear of boxes, so no `grid_path` search is needed.
"""

from fransys_layout.engines.diagram.sizes import TRACK_PITCH
from fransys_layout.geometry import Point
from fransys_model.kernel import value
lazy from fransys_layout.engines.diagram.frame_values import (
    Frame,
    FrameBox,
    FrameChannel,
    FrameEnd,
    FrameSheet,
)

type Where = tuple[int, FrameBox, FrameEnd]  # a line end: its sheet number, box and end


@value
class Half:
    """A line's run on one sheet; `other` is the sheet a cut sends it to (a marker ends it)."""

    sheet: int
    points: tuple[Point, ...]
    other: int | None


def _straight(a: Point, b: Point, c: Point) -> bool:
    """Whether `c` continues the straight run from `a` through `b`."""
    return a.x == b.x == c.x or a.y == b.y == c.y


def tidy(points: tuple[Point, ...]) -> tuple[Point, ...]:
    """The points without repeats and without a middle point on a straight run."""
    out: list[Point] = []
    for p in points:
        if out and out[-1] == p:
            continue
        if len(out) > 1 and _straight(out[-2], out[-1], p):
            out[-1] = p
        else:
            out.append(p)
    return tuple(out)


def touch(where: Where) -> Point:
    """Where the line meets its end: the box edge or the outer edge of the end's tab."""
    _, box, end = where
    return Point(x=box.touch_x(end), y=end.y)


def between(channel: FrameChannel, line: int, left: Point, right: Point) -> tuple[Point, ...]:
    """The line from `left` to `right` through its tracks; a jogged core's halves are joined."""
    runs = sorted((t for t in channel.tracks if t.line == line), key=lambda t: t.part)
    middle: list[Point] = []
    for run in runs:
        x = channel.track_x(run.track)
        middle += [Point(x=x, y=run.left_y), Point(x=x, y=run.right_y)]
    return tidy((left, *middle, right))


def _same_x(frame: Frame, sheet: FrameSheet, box: FrameBox, line: int) -> int:
    """The x of a same-column line's track, in the channel or the cut right of its column."""
    column = next(c for c in sheet.columns if c.x == box.x)
    for ch in sheet.channels:
        if ch.left == column.index and line in ch.same:
            return ch.track_x(ch.count + 1 + ch.same.index(line))
    cut = next(c for c in frame.cuts if c.left == column.index and line in c.same)
    room = cut.tab_l + cut.label + (cut.same.index(line) + 1) * TRACK_PITCH
    return column.x + column.width + room


def route(frame: Frame, line: int, first: Where, second: Where) -> tuple[Point, ...]:
    """The points of a line whose ends lie on one sheet, from `first` to `second`."""
    start, stop = touch(first), touch(second)
    sheet = frame.sheets[first[0] - 1]
    if first[2].side is second[2].side:
        x = _same_x(frame, sheet, first[1], line)
        return tidy((start, Point(x=x, y=start.y), Point(x=x, y=stop.y), stop))
    channel = next(c for c in sheet.channels if line in c.lines)
    return between(channel, line, start, stop)
