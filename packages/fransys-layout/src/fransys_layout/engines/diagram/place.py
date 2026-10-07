"""The diagram placer (BD5): a reading's facts to its placed sheets, boxes, tabs, lines, markers."""

lazy from collections.abc import Sequence

from fransys_layout.engines.diagram.cutting import stubs
from fransys_layout.engines.diagram.frame import build_frame
from fransys_layout.engines.diagram.labels import label_at
from fransys_layout.engines.diagram.route import Half, route
from fransys_layout.engines.diagram.values import (
    PlacedBox,
    PlacedDiagram,
    PlacedLine,
    PlacedMarker,
    PlacedSheet,
    PlacedTab,
)
lazy from fransys_layout.engines.diagram.frame_values import Frame, FrameBox
lazy from fransys_layout.engines.diagram.values import DiagramFacts, LineFacts


def _halves(frame: Frame, facts: DiagramFacts, i: int) -> tuple[Half, ...]:
    """The runs of line `i`, one per sheet, each from the box on it (a to b on a single sheet)."""
    first, second = frame.ends_of(i)
    if first[0] != second[0]:
        cut = next(c for c in frame.cuts if i in c.lines)
        return stubs(first, second, cut)
    points = route(frame, i, first, second)
    if first[1].box != facts.lines[i].a:
        points = points[::-1]
    return (Half(sheet=first[0], points=points, other=None),)


def _box(box: FrameBox, facts: DiagramFacts) -> PlacedBox:
    tabs = tuple(
        PlacedTab(cable=facts.lines[e.line].cable, side=e.side, y=e.y, text_width=e.tab)
        for e in box.ends
        if e.tab is not None
    )
    return PlacedBox(
        box=box.box,
        dashed=box.dashed,
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        tabs=tabs,
    )


def _line(ln: LineFacts, half: Half, text_height: int) -> PlacedLine:
    x, y = label_at(half.points, text_height)
    return PlacedLine(cable=ln.cable, a=ln.a, b=ln.b, points=half.points, text_x=x, text_y=y)


def _sheet(
    number: int, frame: Frame, facts: DiagramFacts, halves: Sequence[tuple[Half, ...]]
) -> PlacedSheet:
    """Sheet `number` with its boxes and the lines and markers of the halves lying on it."""
    boxes = tuple(_box(b, facts) for c in frame.sheets[number - 1].columns for b in c.boxes)
    here = [(facts.lines[i], h) for i, hs in enumerate(halves) for h in hs if h.sheet == number]
    lines = tuple(_line(ln, h, facts.text_height) for ln, h in here)
    markers = tuple(
        PlacedMarker(
            cable=ln.cable, a=ln.a, b=ln.b, at_sheet=h.other, x=h.points[-1].x, y=h.points[-1].y
        )
        for ln, h in here
        if h.other is not None
    )
    return PlacedSheet(number=number, boxes=boxes, lines=lines, markers=markers)


def place_diagram(facts: DiagramFacts) -> PlacedDiagram | None:
    """The placed diagram of `facts`, or None when it cannot be placed on its sheet."""
    frame = build_frame(facts)
    if frame is None:
        return None
    halves = [_halves(frame, facts, i) for i in range(len(facts.lines))]
    sheets = tuple(_sheet(s.number, frame, facts, halves) for s in frame.sheets)
    return PlacedDiagram(unit=facts.unit, sheets=sheets)
