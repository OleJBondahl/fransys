"""Checks over a laid-out page's harness ink: cores, bundle lines, fan outlines and texts.

Rules of the side fan (layout-0172, rounds 3 and 4), each a pure function over `StageResults`:
no ink of a core or a bundle line runs along a symbol's body outline, no split stands on a
foreign keep-out, no tag or line label stands inside a fan's outline, no bundle line runs over
a core, and each fanned branch has one bundle line that ends at its apex.
"""

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, Point, through, translate

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from fransys_layout.engines.schematic.engine import StageResults

type Page = tuple[int, int]


def _page_boxes(results: StageResults) -> dict[Page, list[tuple[object, Box, Box]]]:
    """Each page's placed functions: the function, its body box and its keep-out box."""
    found: dict[Page, list[tuple[object, Box, Box]]] = {}
    for one in results.layout.placed:
        at = one.at
        body = translate(one.geometry.body, dx=at.x, dy=at.y)
        keepout = translate(one.geometry.keepout, dx=at.x, dy=at.y)
        found.setdefault((one.drawing_set, one.page), []).append((one.function, body, keepout))
    return found


def _ink(results: StageResults) -> Iterator[tuple[Page, str, tuple[Point, ...]]]:
    """Every polyline of harness ink on a page that has a side fan: a leg or a bundle line.

    A side fan is a fan of two or more legs; a page without one is not these rules' business.
    """
    side = {(fan.drawing_set, fan.page) for fan in results.lines.fan_outs if fan.legs[1:]}
    for fan in results.lines.fan_outs:
        for leg in fan.legs:
            yield (fan.drawing_set, fan.page), f"{fan.harness} fan {fan.branch}", leg.points
    for line in results.lines.lines:
        if (line.drawing_set, line.page) in side:
            yield (line.drawing_set, line.page), f"{line.harness} line {line.branch}", line.points


def _edges(box: Box) -> list[tuple[Point, Point]]:
    right, bottom = box.x + box.width, box.y + box.height
    corners = [Point(x=box.x, y=box.y), Point(x=right, y=box.y)]
    corners += [Point(x=right, y=bottom), Point(x=box.x, y=bottom), corners[0]]
    return list(pairwise(corners))


def _along(first: tuple[Point, Point], second: tuple[Point, Point]) -> bool:
    """Whether two axis-parallel segments lie on one line and share a stretch of it."""
    (a, b), (c, d) = first, second
    if a.x == b.x == c.x == d.x:
        return min(max(a.y, b.y), max(c.y, d.y)) > max(min(a.y, b.y), min(c.y, d.y))
    if a.y == b.y == c.y == d.y:
        return min(max(a.x, b.x), max(c.x, d.x)) > max(min(a.x, b.x), min(c.x, d.x))
    return False


def ink_along_outlines(results: StageResults) -> list[str]:
    """Each piece of harness ink with a segment along a symbol's body outline."""
    boxes = _page_boxes(results)
    found = []
    for page, name, points in _ink(results):
        edges = [edge for _, body, _ in boxes.get(page, ()) for edge in _edges(body)]
        found += [
            f"{name} on page {page}: {one} to {two}"
            for one, two in pairwise(points)
            if any(_along((one, two), edge) for edge in edges)
        ]
    return found


def _all_ink(results: StageResults) -> Iterator[tuple[Page, str, tuple[Point, ...]]]:
    """Every polyline of harness ink on every page: each leg and each bundle line."""
    for fan in results.lines.fan_outs:
        for leg in fan.legs:
            yield (fan.drawing_set, fan.page), f"{fan.harness} fan {fan.branch}", leg.points
    for line in results.lines.lines:
        yield (line.drawing_set, line.page), f"{line.harness} line {line.branch}", line.points


def ink_over_symbols(results: StageResults) -> list[str]:
    """Each piece of harness ink, on any page, with a segment over a symbol's body ink.

    Over: along a body outline's edge or through its inside; a bold bundle over a symbol reads as
    bridging its contact (layout-0172, round 5). A core ends on its pin, a point on the outline.
    """
    boxes = _page_boxes(results)
    found = []
    for page, name, points in _all_ink(results):
        bodies = [body for _, body, _ in boxes.get(page, ())]
        edges = [edge for body in bodies for edge in _edges(body)]
        found += [
            f"{name} on page {page}: {one} to {two}"
            for one, two in pairwise(points)
            if any(_along((one, two), edge) for edge in edges)
            or any(through((one, two), body) for body in bodies)
        ]
    return found


def splits_on_foreign_keepouts(results: StageResults) -> list[str]:
    """Each fan split on or inside the keep-out of a function none of the fan's pins belong to."""
    boxes = _page_boxes(results)
    found = []
    for fan in results.lines.fan_outs:
        page = (fan.drawing_set, fan.page)
        pins = [leg.points[-1] for leg in fan.legs]
        for _, body, keepout in boxes.get(page, ()):
            own = any(_inside(body, pin) or _inside(keepout, pin) for pin in pins)
            if not own and _inside(keepout, fan.at):
                found.append(f"{fan.harness} fan {fan.branch} on page {page}: split {fan.at}")
    return found


def _inside(box: Box, point: Point) -> bool:
    """Whether `point` is in `box`, its edges included."""
    return box.x <= point.x <= box.x + box.width and box.y <= point.y <= box.y + box.height


def _hull(points: Sequence[Point]) -> list[Point]:
    """The convex hull of `points`, counter-clockwise (monotone chain)."""
    pts = sorted(set(points), key=lambda p: (p.x, p.y))

    def half(seq: Sequence[Point]) -> list[Point]:
        out: list[Point] = []
        for p in seq:
            while len(out) > 1 and _cross(out[-2], out[-1], p) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]

    return [*half(pts), *half(pts[::-1])] if len(pts) > 2 else pts


def _cross(o: Point, a: Point, b: Point) -> int:
    return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)


def _hits(box: Box, polygon: Sequence[Point]) -> bool:
    """Whether `box` shares interior area with the convex `polygon` (strips of half a grid)."""
    if len(polygon) < 3:
        return False
    ys = [p.y for p in polygon]
    for y in range(max(box.y, min(ys)), min(box.y + box.height, max(ys)), 1):
        xs = _span(polygon, y + 0.5)
        if xs and min(xs[1], box.x + box.width) > max(xs[0], box.x):
            return True
    return False


def _span(polygon: Sequence[Point], y: float) -> tuple[float, float] | None:
    """The x extent of the convex `polygon` along the horizontal line at `y`."""
    cuts = [
        a.x + (b.x - a.x) * (y - a.y) / (b.y - a.y)
        for a, b in pairwise([*polygon, polygon[0]])
        if a.y != b.y and min(a.y, b.y) < y < max(a.y, b.y)
    ]
    return (min(cuts), max(cuts)) if cuts else None


def texts_in_fan_outlines(results: StageResults) -> list[str]:
    """Each tag or line label whose box shares area with a fan's outline (its legs' hull)."""
    found = []
    labels = [
        ((one.drawing_set, one.page), f"tag {one.subject}", one.box)
        for one in results.layout.labels
        if one.kind.value == "tag"
    ]
    labels += [
        ((one.drawing_set, one.page), f"{one.harness} label {one.branch}", one.label)
        for one in results.lines.lines
    ]
    for fan in results.lines.fan_outs:
        page = (fan.drawing_set, fan.page)
        outline = _hull([fan.at, *(p for leg in fan.legs for p in leg.points)])
        found += [
            f"{name} on page {page} inside fan {fan.harness} {fan.branch}"
            for where, name, box in labels
            if where == page and _hits(box, outline)
        ]
    return found


def bundle_over_cores(results: StageResults) -> list[str]:
    """Each bundle line with a segment that shares a stretch with a fan's core: bold ink hides it.

    Bold ink lies only from a fan's apex to the far end, never along a thin core (layout-0172).
    """
    found = []
    for line in results.lines.lines:
        page = (line.drawing_set, line.page)
        for fan in results.lines.fan_outs:
            if (fan.drawing_set, fan.page) != page:
                continue
            found += [
                f"{line.harness} line {line.branch} on page {page}: {one} to {two} over a core"
                for one, two in pairwise(line.points)
                for leg in fan.legs
                if any(_along((one, two), seg) for seg in pairwise(leg.points))
            ]
    return found


def bundle_lines_off_their_apex(results: StageResults) -> list[str]:
    """Each fanned branch whose bundle lines on the page are not exactly one, ending at the apex."""
    found = []
    for fan in results.lines.fan_outs:
        page = (fan.drawing_set, fan.page)
        mine = [
            line
            for line in results.lines.lines
            if (line.drawing_set, line.page) == page
            and line.harness == fan.harness
            and line.branch == fan.branch
        ]
        ok = len(mine) == 1 and fan.at in (mine[0].points[0], mine[0].points[-1])
        if not ok:
            found.append(f"{fan.harness} fan {fan.branch} on page {page}: {len(mine)} lines")
    return found
