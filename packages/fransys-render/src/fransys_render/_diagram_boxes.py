"""The boxes and tabs of a diagram sheet (BD4, BD7): drawn from the records, texts from derive."""

from typing import TYPE_CHECKING, cast

from fransys_model.layout import Side

from ._constants import DIAGRAM_TAB_PAD_G, DIAGRAM_TEXT_LEAD_G, DIAGRAM_TEXT_PAD_G

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.derive.block_diagram import BoxKey
    from fransys_model.kernel import Id
    from fransys_model.layout import BoxRef, DiagramBox, DiagramLine, TabCell
    from fransys_model.vocab import Item

    from ._cable_pen import Pen


def ref_id(ref: BoxRef) -> BoxKey:
    """The id a `BoxRef` stands for: its unit instance, else its item."""
    return cast("BoxKey", ref.item if ref.unit is None else ref.unit)


def tab_outer(edge: int, tab: TabCell, lines: Iterable[DiagramLine]) -> int | None:
    """Where the tab's own cable touches it: the nearest line point at the tab's `y` past `edge`."""
    east = tab.side is Side.E
    xs = [
        p.x
        for line in lines
        if line.cable == tab.line
        for p in line.points
        if p.y == tab.y and (p.x > edge if east else p.x < edge)
    ]
    if not xs:
        return None
    return min(xs) if east else max(xs)


def _tab(pen: Pen, box: DiagramBox, tab: TabCell, lines: Iterable[DiagramLine], text: str) -> str:
    """One tab: a rectangle on the box edge reaching to its line, the text a pad inside."""
    east = tab.side is Side.E
    edge = box.x + box.width if east else box.x
    outer = tab_outer(edge, tab, lines)
    if outer is None:
        reach = tab.text_width + 2 * DIAGRAM_TAB_PAD_G
        outer = edge + reach if east else edge - reach
    left = min(edge, outer)
    height = pen.font_g + 2 * DIAGRAM_TAB_PAD_G
    rect = pen.rect(
        "diagram-tab", (left, tab.y - height // 2, abs(outer - edge), height), dashed=False
    )
    if not text:
        return rect
    return rect + pen.text("tab", (left + DIAGRAM_TAB_PAD_G, tab.y - pen.font_g // 2), text)


def box_parts(
    pen: Pen,
    box: DiagramBox,
    texts: tuple[str, ...],
    lines: tuple[DiagramLine, ...],
    tab_texts: Mapping[tuple[Id[Item], BoxKey], str | None],
) -> str:
    """A box's outline, its `texts` and its tabs; `tab_texts` maps (cable, box id) to a text."""
    line_step = pen.font_g + DIAGRAM_TEXT_LEAD_G
    shape = (box.x, box.y, box.width, box.height)
    parts = [pen.outline("diagram-box", shape, dashed=box.dashed)]
    for k, text in enumerate(texts):
        at = (box.x + DIAGRAM_TEXT_PAD_G, box.y + DIAGRAM_TEXT_PAD_G + k * line_step)
        parts.append(pen.text("box", at, text))
    parts.extend(
        _tab(pen, box, tab, lines, tab_texts.get((tab.line, ref_id(box.subject))) or "")
        for tab in box.tabs
    )
    return "".join(parts)
