"""What harness lines draw, for the geometric lint (HL6, HL15 to HL18, layout-0158).

Lines, fan-out legs, line labels, line stubs and connector boxes are drawn after routing and are
no `Route`, label or marker, so the geometric checks read them from `HarnessInk`. A run here may
be oblique (a fan-out leg), so it crosses a box through `through`, not the router's `Run`.
"""

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import Box, Point, contains, port_page_at
from fransys_layout.stages.slices import by_key
from fransys_model.kernel import Finding, Severity

from .codes import LINE_ON_OUTLINE, OUT_OF_CONTENT_BOX, WIRE_OVER_LABEL, WIRE_THROUGH_SYMBOL

if TYPE_CHECKING:
    from fransys_layout.stages import PlacedFunction
    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.line_shapes import DrawnFanOut, DrawnLine, LineStub
    from fransys_layout.stages.types import PlacedOutline
    from fransys_model.kernel import Id

type Segment = tuple[Point, Point]


@dataclass(frozen=True, slots=True)
class HarnessInk:
    """Every harness line's drawn pieces and every connector box.

    `hidden` holds each boxed pin view (function, drawing set, page) that draws nothing (HL6).
    """

    boxes: tuple[PlacedConnectorBox, ...] = ()
    lines: tuple[DrawnLine, ...] = ()
    fan_outs: tuple[DrawnFanOut, ...] = ()
    stubs: tuple[LineStub, ...] = ()
    hidden: frozenset[tuple[Id[Any], int, int]] = frozenset()


NO_INK = HarnessInk()


@dataclass(frozen=True, slots=True)
class PageInk:
    """One page's share of `HarnessInk`: texts as `(subject, box)` and runs as `(owner, segment)`.

    `ends` holds each leg's pin point, so a leg may enter its own pin's symbol.
    """

    texts: tuple[tuple[Id[Any], Box], ...] = ()
    runs: tuple[tuple[Id[Any], Segment], ...] = ()
    ends: frozenset[Point] = frozenset()


def inks_by_page(ink: HarnessInk) -> dict[tuple[int, int], PageInk]:
    """Each `(drawing set, page)`'s share of `ink`, grouped in one pass (layout-0086)."""
    lines, fans = by_key(ink.lines, _page), by_key(ink.fan_outs, _page)
    stubs, boxes = by_key(ink.stubs, _page), by_key(ink.boxes, _page)
    found: dict[tuple[int, int], PageInk] = {}
    for page in {*lines, *fans, *stubs, *boxes}:
        texts = (
            *((one.harness, one.label) for one in lines.get(page, ())),
            *((one.harness, one.box) for one in stubs.get(page, ())),
            *((one.function, one.box) for one in boxes.get(page, ())),
        )
        runs = (
            *((one.harness, seg) for one in lines.get(page, ()) for seg in pairwise(one.points)),
            *((fan.harness, seg) for fan in fans.get(page, ()) for seg in _leg_runs(fan)),
        )
        ends = frozenset(leg.points[-1] for fan in fans.get(page, ()) for leg in fan.legs)
        found[page] = PageInk(texts, runs, ends)
    return found


def _page(one: DrawnLine | DrawnFanOut | LineStub | PlacedConnectorBox) -> tuple[int, int]:
    return one.drawing_set, one.page


def _leg_runs(fan: DrawnFanOut) -> list[Segment]:
    return [seg for leg in fan.legs for seg in pairwise(leg.points)]


def through(segment: Segment, box: Box) -> bool:
    """Whether `segment` passes through `box`'s interior; touching an edge does not count."""
    (a, b), low, high = segment, 0.0, 1.0
    for start, delta, lo, hi in (
        (a.x, b.x - a.x, box.x, box.x + box.width),
        (a.y, b.y - a.y, box.y, box.y + box.height),
    ):
        if delta == 0:
            if not lo < start < hi:
                return False
            continue
        one, two = (lo - start) / delta, (hi - start) / delta
        low, high = max(low, min(one, two)), min(high, max(one, two))
    return low < high


def _warn(code: str, subjects: tuple[Id[Any], ...], message: str) -> Finding:
    return Finding(code=code, severity=Severity.WARNING, subjects=subjects, message=message)


def runs_over_texts(ink: PageInk, texts: tuple[tuple[Id[Any], Box], ...]) -> list[Finding]:
    """`WIRE_OVER_LABEL`: a line or leg through a text, a marker box, a stub or a connector box."""
    hit = {
        (owner, subject)
        for owner, seg in ink.runs
        for subject, box in (*texts, *ink.texts)
        if through(seg, box)
    }
    return [
        _warn(WIRE_OVER_LABEL, pair, "a harness line runs through a label box")
        for pair in sorted(hit)
    ]


def runs_through_symbols(
    ink: PageInk, bodies: tuple[tuple[PlacedFunction, Box], ...]
) -> list[Finding]:
    """`WIRE_THROUGH_SYMBOL`: a line or leg through a drawn symbol it does not end on."""
    hit = set()
    for owner, seg in ink.runs:
        for one, body in bodies:
            if not through(seg, body):
                continue
            if not _ends_on(seg, one, ink.ends):
                hit.add((owner, one.function))
    return [
        _warn(WIRE_THROUGH_SYMBOL, pair, "a harness line runs through a symbol it does not end on")
        for pair in sorted(hit)
    ]


def _ends_on(seg: Segment, one: PlacedFunction, ends: frozenset[Point]) -> bool:
    """Whether `seg` ends on a port of `one` that is a leg's pin."""
    ports = {port_page_at(one.at, port) for port in one.geometry.ports}
    return any(point in ends and point in ports for point in seg)


def runs_on_outlines(ink: PageInk, outlines: tuple[PlacedOutline, ...]) -> list[Finding]:
    """`LINE_ON_OUTLINE`: a line or leg drawn along a unit outline's edge."""
    hit = {
        (owner, outline.unit)
        for owner, seg in ink.runs
        for outline in outlines
        if _along(seg, outline.box)
    }
    return [
        _warn(LINE_ON_OUTLINE, pair, "a harness line runs along a unit outline's edge")
        for pair in sorted(hit)
    ]


def _along(seg: Segment, box: Box) -> bool:
    a, b = seg
    if a.y == b.y and a.y in (box.y, box.y + box.height):
        return max(a.x, b.x) > box.x and min(a.x, b.x) < box.x + box.width
    if a.x == b.x and a.x in (box.x, box.x + box.width):
        return max(a.y, b.y) > box.y and min(a.y, b.y) < box.y + box.height
    return False


def ink_outside(ink: PageInk, content: Box) -> list[Finding]:
    """`OUT_OF_CONTENT_BOX`: a line point, a stub, a line label or a connector box outside it."""
    hit = {subject for subject, box in ink.texts if not contains(content, box)}
    hit |= {
        owner
        for owner, seg in ink.runs
        for point in seg
        if not contains(content, Box(x=point.x, y=point.y, width=0, height=0))
    }
    return [
        _warn(OUT_OF_CONTENT_BOX, (subject,), "a harness line's ink leaves the content box")
        for subject in sorted(hit)
    ]
