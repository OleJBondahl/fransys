"""Drawn shorts (render-0012): one net's ink that the page shows joined to another net's ink.

A general check over plain strokes and bodies. Two strokes of different owners join where they
run on one line, or where an end of one lies on the other; a marker's stub or rail joins any wire
it crosses. A stroke joins a flag box or a power symbol it meets, edge included, and a symbol body
it runs into. A power symbol joins another owner's power symbol or flag box it touches. Not joins:
a plain crossing of two wires (no dot, IEC 61082), the legs of one fan-out at their own fan point
and a line's own legs and stubs (the one-line cable form), a stub over a symbol body (layout's
`WIRE_THROUGH_SYMBOL`), and a mate's stub into the box it shares.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from fransys_model.kernel import Id

type Point = tuple[int, int]
type Box = tuple[int, int, int, int]  # x0, y0, x1, y1, edges included
type Owner = tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Stroke:
    """One straight piece of drawn wire: `kind` route, stub, rail, lead, leg or line.

    `bundle` is the harness a line, its legs and a stub it carries belong to; `fan` is a leg's fan
    point, its first point, where the legs of one fan-out leave their line (render-0010).
    """

    kind: str
    owner: Owner
    subject: Id[Any]
    a: Point
    b: Point
    bundle: object = None
    fan: Point | None = None


@dataclass(frozen=True, slots=True)
class Body:
    """One drawn body: `kind` flag, power or symbol; a shared flag box's `owners` are its nets."""

    kind: str
    owners: frozenset[Owner]
    subject: Id[Any]
    box: Box
    ports: frozenset[Point] = frozenset()
    bundle: object = None


_MARKER_INK = frozenset({"stub", "rail"})
_JOINS_POWER = frozenset({"power", "flag"})


@dataclass(frozen=True, slots=True)
class Short:
    """Where the page joins two owners' ink: the two subjects, sorted, and one point of it."""

    subjects: tuple[Id[Any], ...]
    at: Point


def drawn_shorts(strokes: Sequence[Stroke], bodies: Sequence[Body]) -> tuple[Short, ...]:
    """One `Short` per pair of subjects whose ink the page joins, by subjects."""
    items: list[Stroke | Body] = [*strokes, *bodies]
    found: dict[tuple[Id[Any], ...], Point] = {}
    for one, other in _near(items):
        at = _join(one, other)
        if at is not None:
            found.setdefault(tuple(sorted((one.subject, other.subject))), at)
    return tuple(Short(subjects, at) for subjects, at in sorted(found.items()))


def _near(items: Sequence[Stroke | Body]) -> Iterator[tuple[Stroke | Body, Stroke | Body]]:
    """Every pair of items whose bounding boxes meet, by a sweep along x."""
    boxes = [_extent(one) for one in items]
    order = sorted(range(len(items)), key=lambda index: boxes[index][0])
    for rank, index in enumerate(order):
        box = boxes[index]
        for other in order[rank + 1 :]:
            if boxes[other][0] > box[2]:
                break
            if boxes[other][1] <= box[3] and box[1] <= boxes[other][3]:
                yield items[index], items[other]


def _extent(one: Stroke | Body) -> Box:
    if isinstance(one, Body):
        return one.box
    (ax, ay), (bx, by) = one.a, one.b
    return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))


def _join(one: Stroke | Body, other: Stroke | Body) -> Point | None:
    """Where `one` and `other` join on the page, or `None`."""
    if isinstance(one, Stroke) and isinstance(other, Stroke):
        return _strokes_join(one, other)
    if isinstance(one, Body) and isinstance(other, Body):
        return _bodies_join(one, other)
    if isinstance(one, Stroke) and isinstance(other, Body):
        return _stroke_meets(one, other)
    if isinstance(one, Body) and isinstance(other, Stroke):
        return _stroke_meets(other, one)
    return None


def _strokes_join(one: Stroke, other: Stroke) -> Point | None:
    if one.owner == other.owner or _same_bundle(one, other):
        return None
    run = _overlap(one, other)
    if run is not None:
        return run
    at = _end_on(one, other) or _end_on(other, one)
    if at is not None:
        return None if _fan_joint(one, other, at) else at
    if _MARKER_INK & {one.kind, other.kind}:
        return _crossing(one, other)
    return None


def _fan_joint(one: Stroke, other: Stroke, at: Point) -> bool:
    """Two legs of one fan-out touching at the point where both leave their line, and only there."""
    return one.bundle == other.bundle and one.fan is not None and one.fan == other.fan == at


def _same_bundle(one: Stroke, other: Stroke) -> bool:
    """A line with its own legs or carried stubs: the one-line cable form."""
    return (
        one.bundle is not None and one.bundle == other.bundle and "line" in {one.kind, other.kind}
    )


def _stroke_meets(stroke: Stroke, body: Body) -> Point | None:
    if stroke.owner in body.owners or (body.bundle is not None and body.bundle == stroke.bundle):
        return None
    if body.kind == "symbol":
        if stroke.kind in _MARKER_INK or {stroke.a, stroke.b} & body.ports:
            return None
        return stroke.a if _meets(stroke.a, stroke.b, body.box, closed=False) else None
    return stroke.a if _meets(stroke.a, stroke.b, body.box, closed=True) else None


def _bodies_join(one: Body, other: Body) -> Point | None:
    kinds = {one.kind, other.kind}
    if "power" not in kinds or not kinds <= _JOINS_POWER or one.owners & other.owners:
        return None
    a, b = one.box, other.box
    if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
        return (max(a[0], b[0]), max(a[1], b[1]))
    return None


def _side(o: Point, a: Point, b: Point) -> int:
    """The sign of the turn from `o`->`a` to `o`->`b`: 0 when the three points are on one line."""
    turn = (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (turn > 0) - (turn < 0)


def _on(point: Point, a: Point, b: Point) -> bool:
    """Whether `point` lies on the closed segment `a`-`b`."""
    return (
        _side(a, b, point) == 0
        and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _end_on(one: Stroke, other: Stroke) -> Point | None:
    """An end of `one` that lies on `other`."""
    return next((end for end in (one.a, one.b) if _on(end, other.a, other.b)), None)


def _overlap(one: Stroke, other: Stroke) -> Point | None:
    """The start of a run the two strokes share on one line, of positive length."""
    if _side(one.a, one.b, other.a) or _side(one.a, one.b, other.b):
        return None
    axis = 0 if one.a[0] != one.b[0] else 1
    first = max(
        min(one.a, one.b, key=lambda p: p[axis]),
        min(other.a, other.b, key=lambda p: p[axis]),
        key=lambda p: p[axis],
    )
    last = min(
        max(one.a, one.b, key=lambda p: p[axis]),
        max(other.a, other.b, key=lambda p: p[axis]),
        key=lambda p: p[axis],
    )
    return first if first[axis] < last[axis] else None


def _crossing(one: Stroke, other: Stroke) -> Point | None:
    """Where the two strokes cross inside both, or `None`."""
    if _side(one.a, one.b, other.a) * _side(one.a, one.b, other.b) >= 0:
        return None
    if _side(other.a, other.b, one.a) * _side(other.a, other.b, one.b) >= 0:
        return None
    upright = one if one.a[0] == one.b[0] else other
    level = other if upright is one else one
    return (upright.a[0], level.a[1])


def _meets(a: Point, b: Point, box: Box, *, closed: bool) -> bool:
    """Whether the segment `a`-`b` meets `box`: its edges included when `closed`, else inside it."""
    low, high = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for step, room in (
        (-dx, a[0] - box[0]),
        (dx, box[2] - a[0]),
        (-dy, a[1] - box[1]),
        (dy, box[3] - a[1]),
    ):
        if step == 0:
            if room < 0 or (room == 0 and not closed):
                return False
            continue
        ratio = room / step
        if step < 0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
    return low <= high if closed else low < high
