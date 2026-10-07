"""One reading's `DiagramFacts`: boxes in text order, lines in line order, the A2 sheet in G."""

from typing import Any

from fransys_layout.engines.diagram.values import BoxFacts, DiagramFacts, LineFacts
from fransys_layout.geometry import text_width
from fransys_model.derive.block_diagram import box_dashed, box_lines, box_order, diagram_lines
from fransys_model.derive.drawing_text import content_extent
from fransys_model.layout.tables import profile_of, sheet_for
from fransys_model.vocab.enums import PageKind
lazy from fransys_model.derive.block_diagram import DiagramLine
lazy from fransys_model.kernel import Id, Model


def _width(text: str | None, height: int) -> int | None:
    """The text width of a tab, or `None` for no tab."""
    return None if text is None else text_width(text, height=height)


def _line(line: DiagramLine, height: int) -> LineFacts:
    """A line's label width and the width of each tab it has."""
    return LineFacts(
        cable=line.cable,
        a=line.a,
        b=line.b,
        label_width=text_width(line.designation, height=height),
        tab_a=_width(line.tab_a, height),
        tab_b=_width(line.tab_b, height),
    )


def _box(model: Model, box: Id[Any], unit: Id[Any] | None, height: int) -> BoxFacts:
    """A box's text widths and its dash."""
    return BoxFacts(
        box=box,
        text_widths=tuple(text_width(t, height=height) for t in box_lines(model, box, unit)),
        dashed=box_dashed(model, box, unit),
    )


def diagram_reading(model: Model, unit: Id[Any] | None) -> DiagramFacts | None:
    """The facts of `unit`'s diagram, or `None` when the reading has no line (no page)."""
    lines = diagram_lines(model, unit)
    if not lines:
        return None
    profile, sheet = profile_of(model), sheet_for(model, PageKind.BLOCK_DIAGRAM)
    height = profile.text_height
    reached = {box for line in lines for box in (line.a, line.b)}
    boxes = sorted(reached, key=lambda box: box_order(model, box, unit))
    return DiagramFacts(
        unit=unit,
        boxes=tuple(_box(model, box, unit, height) for box in boxes),
        lines=tuple(_line(line, height) for line in lines),
        text_height=height,
        turn_penalty=profile.route_turn_penalty,
        crossing_penalty=profile.route_crossing_penalty,
        width=content_extent(sheet.content_width_mm, sheet.module_mm),
        height=content_extent(sheet.content_height_mm, sheet.module_mm),
    )
