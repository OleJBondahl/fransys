"""One reading's `DiagramFacts`: boxes in text order, lines in line order, the A2 sheet in G."""

from typing import Any

from fransys_layout.engines.overview.sheet_values import DiagramFacts
from fransys_layout.engines.overview.sizes import measured_box, measured_line
from fransys_layout.symbols import frame_extent, text_room_on
from fransys_model.derive.block_diagram import box_dashed, box_lines, box_order, diagram_lines
from fransys_model.layout.tables import sheet_for, tuning_of
from fransys_model.vocab.enums import PageKind
lazy from fransys_layout.symbols import SymbolLibrary
lazy from fransys_model.kernel import Id, Model


def diagram_reading(model: Model, unit: Id[Any] | None, library: SymbolLibrary) -> DiagramFacts | None:
    """The facts of `unit`'s diagram, or `None` when the reading has no line (no page)."""
    lines = diagram_lines(model, unit)
    if not lines:
        return None
    tuning, sheet = tuning_of(model), sheet_for(model, PageKind.BLOCK_DIAGRAM)
    height = text_room_on(model, sheet, library)
    width, depth = frame_extent(library, sheet)
    reached = {box for line in lines for box in (line.a, line.b)}
    boxes = sorted(reached, key=lambda box: box_order(model, box, unit))
    return DiagramFacts(
        unit=unit,
        boxes=tuple(measured_box(box, box_lines(model, box, unit), height, dashed=box_dashed(model, box)) for box in boxes),
        lines=tuple(measured_line((ln.cable, ln.a, ln.b), ln.designation, (ln.tab_a, ln.tab_b), height) for ln in lines),
        text_height=height,
        turn_penalty=tuning.route_turn_penalty,
        crossing_penalty=tuning.route_crossing_penalty,
        width=width,
        height=depth,
        nest_same=True,
    )
