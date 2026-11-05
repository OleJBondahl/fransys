"""The boxes and tabs of a diagram sheet: drawn from the placed values, texts from derive."""

from typing import TYPE_CHECKING, Any

from fransys_layout import Facing

from ._constants import DIAGRAM_TAB_PAD_G, DIAGRAM_TEXT_LEAD_G, DIAGRAM_TEXT_PAD_G

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout import DiagramBox, DiagramLine, DiagramTab
    from fransys_model.kernel import Id

    from ._cable_pen import Pen


def tab_outer(edge: int, tab: DiagramTab, lines: Iterable[DiagramLine]) -> int | None:
    """Where the tab's own cable touches it: the nearest line point at the tab's `y` past `edge`."""
    east = tab.side is Facing.E
    xs = [p.x for line in lines if line.cable == tab.cable for p in line.points if p.y == tab.y and (p.x > edge if east else p.x < edge)]
    if not xs:
        return None
    return min(xs) if east else max(xs)


def _tab(pen: Pen, box: DiagramBox, tab: DiagramTab, lines: Iterable[DiagramLine], text: str) -> str:
    """One tab: a rectangle on the box edge reaching to its line, the text a pad inside."""
    east = tab.side is Facing.E
    edge = box.x + box.width if east else box.x
    outer = tab_outer(edge, tab, lines)
    if outer is None:
        reach = tab.text_width + 2 * DIAGRAM_TAB_PAD_G
        outer = edge + reach if east else edge - reach
    left = min(edge, outer)
    height = pen.font_g + 2 * DIAGRAM_TAB_PAD_G
    rect = pen.rect("diagram-tab", (left, tab.y - height // 2, abs(outer - edge), height), dashed=False)
    if not text:
        return rect
    return rect + pen.text("tab", (left + DIAGRAM_TAB_PAD_G, tab.y - pen.font_g // 2), text)


def box_parts(
    pen: Pen,
    box: DiagramBox,
    texts: tuple[str, ...],
    lines: tuple[DiagramLine, ...],
    tab_texts: Mapping[tuple[Id[Any], Id[Any]], str | None],
) -> str:
    """A box's outline, its `texts` and its tabs; `tab_texts` maps (cable, box id) to a text."""
    line_step = pen.font_g + DIAGRAM_TEXT_LEAD_G
    shape = (box.x, box.y, box.width, box.height)
    parts = [pen.outline("diagram-box", shape, dashed=box.dashed)]
    for k, text in enumerate(texts):
        at = (box.x + DIAGRAM_TEXT_PAD_G, box.y + DIAGRAM_TEXT_PAD_G + k * line_step)
        parts.append(pen.text("box", at, text))
    parts.extend(_tab(pen, box, tab, lines, tab_texts.get((tab.cable, box.box)) or "") for tab in box.tabs)
    return "".join(parts)
