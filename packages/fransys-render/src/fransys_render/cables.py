"""Laid-out cable blocks to SVG, one per `fransys_layout.PlacedBlock`."""

from decimal import Decimal
from typing import TYPE_CHECKING

from electrical_symbols import WIRING_GRID
from fransys_layout.symbols import text_room_on
from fransys_model.derive.cable_drawing import block_brackets, pair_room
from fransys_model.layout import sheet_format_of, tuning_of

from ._cable_ink import Ink
from ._cable_pen import Pen
from ._library import smallest_height_mm

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout import CableLayout, PlacedBlock, PlacedEnd, PlacedWire
    from fransys_model.kernel import Model


def _boxes(ink: Ink, block: PlacedBlock) -> None:
    """The harness box first (dashed, its label), then each cable box (solid, its heading)."""
    pen = ink.pen
    if block.harness is not None and block.harness_label is not None:
        box = block.harness
        ink.shape(pen.rect("harness-box", (box.x, box.y, box.width, box.height), dashed=True))
        ink.text("heading", (box.x + pen.pad_g, box.y + pen.pad_g), block.harness_label)
    for placed in block.boxes:
        box = placed.box
        ink.shape(pen.rect("cable-box", (box.x, box.y, box.width, box.height), dashed=False))
        ink.text("heading", (box.x + pen.pad_g, box.y + pen.pad_g), placed.heading)


def _cells(ink: Ink, end: PlacedEnd) -> None:
    """One marking per pin cell, centred on the cell, and a divider on each cell's left edge.

    The cell's width is layout's (layout-0152), so its edge is half that from x.
    """
    pen = ink.pen
    top = end.y + Decimal(end.height - pen.font_g) / 2
    for n, cell in enumerate(end.cells):
        if n:
            edge = cell.x - Decimal(cell.width) / 2
            ink.shape(pen.line("pin-cell", (edge, end.y), (edge, end.y + end.height), dashed=end.dashed))
        ink.text("pin", (cell.x, top), cell.marking, middle=True)


def _end(ink: Ink, end: PlacedEnd) -> None:
    """One end box, its label (above a top box, below a bottom one) and pin cells; none if blank."""
    if end.blank:
        return
    pen = ink.pen
    below = end.y + end.height + pen.pad_g
    above = end.y - pen.pad_g - pen.font_g
    ink.shape(pen.outline("end-box", (end.x, end.y, end.width, end.height), dashed=end.dashed))
    if end.label:
        centre = end.x + Decimal(end.width) / 2
        at = (centre, above if end.top else below)
        ink.text("end-label", at, end.label, middle=True)
    _cells(ink, end)


def _wire(ink: Ink, wire: PlacedWire) -> None:
    """One core or single wire: its two runs and its text, from layout's points.

    The text reads upward along the wire; a row link's reads level, centred on the point.
    """
    pen = ink.pen
    for run in (wire.run_a, wire.run_b):
        ink.shape(pen.wire("core", tuple((point.x, point.y) for point in run)))
    if wire.link:
        top = Decimal(wire.text_y) - Decimal(pen.font_g) / 2
        ink.text("core", (wire.text_x, top), wire.text, middle=True)
    else:
        ink.upward_text("core", (wire.text_x, wire.text_y), wire.text)


def _brackets(model: Model, ink: Ink, block: PlacedBlock) -> None:
    """Each pair bracket: a line over its two cores' texts with a tick down each, and its label.

    It stands in the pair room under the cable box's heading (`pair_room`, layout's own).
    """
    pen = ink.pen
    room = pair_room(pen.font_g, pen.pad_g, WIRING_GRID)
    boxes = {placed.cable: placed.box for placed in block.boxes}
    xs = {wire.conductor: wire.text_x for wire in block.wires}
    for bracket in block_brackets(model, block.subject, block.unit):
        top = boxes[bracket.cable].y
        a, b = xs[bracket.core_a], xs[bracket.core_b]
        line, tick = top + room.line, top + room.tick
        ink.shape(pen.wire("core", ((a, tick), (a, line), (b, line), (b, tick))))
        ink.text("core", (Decimal(a + b) / 2, top + room.label), bracket.label, middle=True)


def _render_block(model: Model, library: Library, block: PlacedBlock) -> str:
    """One block's SVG, sized to the block in mm on its sheet's module."""
    sheet = sheet_format_of(model, None)
    pen = Pen(library, sheet.module_mm, smallest_height_mm(library), tuning_of(model).marker_padding, text_room_on(model, sheet, library))
    ink = Ink(pen)
    _boxes(ink, block)
    for end in block.ends:
        _end(ink, end)
    for wire in block.wires:
        _wire(ink, wire)
    _brackets(model, ink, block)
    return pen.svg(block.width, block.height, ink.body())


def cable_blocks(model: Model, cables: CableLayout, library: Library) -> frozendict[str, str]:
    """Render every cable block of `cables` to SVG, keyed as `cables.blocks` is.

    Each is sized to its block in mm on the block's own sheet (`sheet_format_of`), with the grid
    origin at the block's top-left. A block draws only what its values hold: boxes, end boxes
    with their pin cells, core wires; every text is a value of the block (layout's). Pure.
    """
    return frozendict({key: _render_block(model, library, b) for key, b in cables.blocks.items()})
