"""Pure reads of a `Drawing`: counts a reader's eye would make, in G (R218).

Each takes the drawn values and returns an int or a tuple. Only orthogonal segments count;
a diagonal one is ignored. Imports the standard library and the core's plain values only: the
parameters are structural protocols that `fransys_layout.drawing`'s values satisfy.
"""

from itertools import pairwise
from typing import Protocol
lazy from collections.abc import Sequence

lazy from .core.values import XY, Box, Size

__all__ = (
    "fill_percent",
    "page_texts",
    "struck_texts",
    "text_overlaps",
    "wire_bends",
    "wire_crossings",
    "wire_length",
)


class DrawnText(Protocol):
    """What a read needs of a text: its box."""

    @property
    def box(self) -> Box: ...


class DrawnWire(Protocol):
    """What a read needs of a wire: id, points, label."""

    @property
    def id(self) -> str: ...
    @property
    def points(self) -> Sequence[XY]: ...
    @property
    def label(self) -> DrawnText | None: ...


class DrawnSymbol(Protocol):
    """What a read needs of a symbol: its placed body box, if the producer knew one."""

    @property
    def outline(self) -> Box | None: ...


class DrawnOutline(Protocol):
    """What a read needs of an outline: its points and its label."""

    @property
    def points(self) -> Sequence[XY]: ...
    @property
    def label(self) -> DrawnText | None: ...


class Drawing(Protocol):
    """What a read needs of a drawing: its area, symbols, texts, wires, outlines."""

    @property
    def area(self) -> Size: ...
    @property
    def symbols(self) -> Sequence[DrawnSymbol]: ...
    @property
    def texts(self) -> tuple[DrawnText, ...]: ...
    @property
    def wires(self) -> Sequence[DrawnWire]: ...
    @property
    def outlines(self) -> Sequence[DrawnOutline]: ...


def _segments(points: Sequence[XY]) -> list[tuple[XY, XY]]:
    return [(a, b) for a, b in pairwise(points) if a != b]


def _crosses(one: tuple[XY, XY], other: tuple[XY, XY]) -> bool:
    (ax, ay), (bx, by) = one
    (cx, cy), (dx, dy) = other
    if ay == by and cx == dx:
        return min(ax, bx) < cx < max(ax, bx) and min(cy, dy) < ay < max(cy, dy)
    if ax == bx and cy == dy:
        return min(ay, by) < cy < max(ay, by) and min(cx, dx) < ax < max(cx, dx)
    return False


def wire_crossings(wires: Sequence[DrawnWire]) -> int:
    """Pairs of segments of two different wires that cross strictly inside both (one each way)."""
    found = 0
    for i, first in enumerate(wires):
        for second in wires[i + 1 :]:
            if first.id == second.id:
                continue
            for one in _segments(first.points):
                found += sum(_crosses(one, other) for other in _segments(second.points))
    return found


def _turns(a: XY, b: XY, c: XY) -> bool:
    before = (b[0] - a[0], b[1] - a[1])
    after = (c[0] - b[0], c[1] - b[1])
    cross = before[0] * after[1] - before[1] * after[0]
    return cross != 0 or before[0] * after[0] + before[1] * after[1] < 0


def wire_bends(wires: Sequence[DrawnWire]) -> int:
    """Interior vertices where the direction changes; a straight continuation is no bend."""
    found = 0
    for wire in wires:
        segs = _segments(wire.points)
        found += sum(_turns(a, b, c) for (a, b), (_, c) in pairwise(segs))
    return found


def wire_length(wires: Sequence[DrawnWire]) -> int:
    """The summed length of all segments in G (abs dx plus abs dy)."""
    return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for w in wires for a, b in _segments(w.points))


def _overlap(one: DrawnText, other: DrawnText) -> bool:
    p, q = one.box, other.box
    return p.x < q.x + q.w and q.x < p.x + p.w and p.y < q.y + q.h and q.y < p.y + p.h


def text_overlaps(texts: Sequence[DrawnText]) -> int:
    """Unordered pairs of texts whose boxes overlap with positive area; touching edges do not."""
    return sum(_overlap(a, b) for i, a in enumerate(texts) for b in texts[i + 1 :])


def _passes(seg: tuple[XY, XY], text: DrawnText) -> bool:
    (ax, ay), (bx, by) = seg
    box = text.box
    if ay == by:
        spans = min(ax, bx) < box.x + box.w and max(ax, bx) > box.x
        return box.y < ay < box.y + box.h and spans
    if ax == bx:
        spans = min(ay, by) < box.y + box.h and max(ay, by) > box.y
        return box.x < ax < box.x + box.w and spans
    return False


def struck_texts(wires: Sequence[DrawnWire], texts: Sequence[DrawnText]) -> int:
    """Texts that an orthogonal wire segment passes through the interior of.

    A wire whose `label is` the text never strikes it; any other wire does.
    """
    found = 0
    for text in texts:
        others = [w for w in wires if w.label is not text]
        found += any(_passes(seg, text) for w in others for seg in _segments(w.points))
    return found


def page_texts(drawing: Drawing) -> tuple[DrawnText, ...]:
    """Every text a drawing carries: its texts, then each wire label, then each outline label."""
    labels = [w.label for w in drawing.wires] + [o.label for o in drawing.outlines]
    return drawing.texts + tuple(t for t in labels if t is not None)


def _ink(drawing: Drawing) -> list[tuple[int, int, int, int]]:
    """The (x0, y0, x1, y1) of every placed body, text, wire and outline of a drawing."""
    boxes = [s.outline for s in drawing.symbols if s.outline is not None]
    boxes += [t.box for t in page_texts(drawing)]
    found = [(b.x, b.y, b.x + b.w, b.y + b.h) for b in boxes]
    for points in [w.points for w in drawing.wires] + [o.points for o in drawing.outlines]:
        if points:
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            found.append((min(xs), min(ys), max(xs), max(ys)))
    return found


def fill_percent(drawing: Drawing) -> int:
    """The share of the page's content box (`area`) that its placed ink spans, 0 to 100.

    The ink is one extent: the box around every symbol body, text, wire and outline, clipped to
    the area. A page with no ink, or no area, reads 0. Whole percent, rounded down.
    """
    ink = _ink(drawing)
    width, height = drawing.area.w, drawing.area.h
    if not ink or width <= 0 or height <= 0:
        return 0
    x0, y0 = max(0, min(i[0] for i in ink)), max(0, min(i[1] for i in ink))
    x1, y1 = min(width, max(i[2] for i in ink)), min(height, max(i[3] for i in ink))
    return max(0, x1 - x0) * max(0, y1 - y0) * 100 // (width * height)
