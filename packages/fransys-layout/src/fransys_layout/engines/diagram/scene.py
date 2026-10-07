"""The diagram engine's lint feed (BD8): a placed sheet to the scene `lint_diagram` checks."""

from fransys_layout.engines.diagram.sizes import (
    TAB_PAD,
    TEXT_LEAD,
    TEXT_PAD,
    tab_height,
    tab_reach,
)
from fransys_layout.geometry import Box, Facing
from fransys_layout.lint._diagram_scene import Scene, SceneBox, SceneLine, SceneText, shapes
lazy from fransys_layout.engines.diagram.values import (
    DiagramFacts,
    PlacedBox,
    PlacedLine,
    PlacedSheet,
    PlacedTab,
)
lazy from fransys_layout.geometry import Point


def _tab_rect(box: PlacedBox, tab: PlacedTab, text_height: int) -> Box:
    """The tab outside its box edge, centred on the tab's `y`."""
    reach = tab_reach(tab.text_width)
    height = tab_height(text_height)
    x = box.x + box.width if tab.side is Facing.E else box.x - reach
    return Box(x=x, y=tab.y - height // 2, width=reach, height=height)


def _scene_box(box: PlacedBox, text_height: int) -> SceneBox:
    rect = Box(x=box.x, y=box.y, width=box.width, height=box.height)
    return SceneBox(
        box=box.box, rect=rect, tabs=tuple(_tab_rect(box, t, text_height) for t in box.tabs)
    )


def _box_texts(box: PlacedBox, widths: tuple[int, ...], text_height: int) -> list[SceneText]:
    pitch = text_height + TEXT_LEAD
    return [
        SceneText(
            owner=box.box,
            rect=Box(
                x=box.x + TEXT_PAD, y=box.y + TEXT_PAD + k * pitch, width=w, height=text_height
            ),
        )
        for k, w in enumerate(widths)
    ]


def _tab_texts(box: PlacedBox, text_height: int) -> list[SceneText]:
    texts = []
    for tab in box.tabs:
        rect = _tab_rect(box, tab, text_height)
        inner = Box(x=rect.x + TAB_PAD, y=rect.y, width=tab.text_width, height=rect.height)
        texts.append(SceneText(owner=tab.cable, rect=inner))
    return texts


def _label_text(line: PlacedLine, facts: DiagramFacts) -> SceneText:
    width = next(
        ln.label_width
        for ln in facts.lines
        if (ln.cable, ln.a, ln.b) == (line.cable, line.a, line.b)
    )
    rect = Box(
        x=line.text_x - width // 2,
        y=line.text_y - facts.text_height // 2,
        width=width,
        height=facts.text_height,
    )
    return SceneText(owner=line.cable, rect=rect)


def _touches(point: Point, box: SceneBox) -> bool:
    return any(
        s.x <= point.x <= s.x + s.width and s.y <= point.y <= s.y + s.height for s in shapes(box)
    )


def _scene_line(
    line: PlacedLine, boxes: tuple[SceneBox, ...], markers: tuple[Point, ...]
) -> SceneLine:
    """The line with `start` the end box (`a` or `b`) its first point touches, `stop` the other."""
    first = next(
        (box for box in boxes if box.box == line.a and _touches(line.points[0], box)), None
    )
    start, other = (line.a, line.b) if first is not None else (line.b, line.a)
    stop = None if line.points[-1] in markers else other
    return SceneLine(
        cable=line.cable, a=line.a, b=line.b, start=start, stop=stop, points=line.points
    )


def scene_of(facts: DiagramFacts, sheet: PlacedSheet) -> Scene:
    """The lint scene of `sheet`: its boxes with tabs, every printed text, lines and markers."""
    widths = {b.box: b.text_widths for b in facts.boxes}
    th = facts.text_height
    markers = tuple(Point(x=m.x, y=m.y) for m in sheet.markers)
    boxes = tuple(_scene_box(b, th) for b in sheet.boxes)
    texts = [
        t for b in sheet.boxes for t in (*_box_texts(b, widths[b.box], th), *_tab_texts(b, th))
    ]
    texts += [_label_text(line, facts) for line in sheet.lines]
    lines = tuple(_scene_line(line, boxes, markers) for line in sheet.lines)
    return Scene(boxes=boxes, texts=tuple(texts), lines=lines, markers=markers)
