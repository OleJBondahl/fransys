"""Laid-out cable blocks to SVG, one per `fransys_layout.PlacedBlock`."""

from decimal import Decimal
from typing import TYPE_CHECKING

from electrical_symbols import WIRING_GRID
from fransys_layout.symbols import text_room_on
from fransys_model.derive import printed_designation
from fransys_model.derive.cable_drawing import (
    block_brackets,
    block_cables,
    cable_heading,
    core_texts,
    drawn_pins,
    end_label,
    pair_room,
    row_links,
)
from fransys_model.layout import sheet_format_of, tuning_of

from ._cable_ink import Ink
from ._cable_pen import Pen
from ._library import smallest_height_mm

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout import CableLayout, PlacedBlock, PlacedEnd, PlacedWire
    from fransys_model.derive import HarnessCable
    from fransys_model.kernel import Model


def _boxes(model: Model, ink: Ink, block: PlacedBlock, cables: tuple[HarnessCable, ...]) -> None:
    """The harness box first (dashed, its label), then each cable box (solid, its heading)."""
    by_cable = {cable.cable: cable for cable in cables}
    pen = ink.pen
    if block.harness is not None:
        box = block.harness
        ink.shape(pen.rect("harness-box", (box.x, box.y, box.width, box.height), dashed=True))
        label = printed_designation(model, block.subject, unit=block.unit)
        ink.text("heading", (box.x + pen.pad_g, box.y + pen.pad_g), label)
    for placed in block.boxes:
        box = placed.box
        ink.shape(pen.rect("cable-box", (box.x, box.y, box.width, box.height), dashed=False))
        text = cable_heading(model, by_cable[placed.cable])
        ink.text("heading", (box.x + pen.pad_g, box.y + pen.pad_g), text)


def _cells(model: Model, ink: Ink, block: PlacedBlock, end: PlacedEnd) -> None:
    """One marking per pin cell, centred on the cell, and a divider on each cell's left edge.

    The cell's width is layout's (layout-0152), so its edge is half that from x.
    """
    pen = ink.pen
    pins = {pin.port: pin for pin in drawn_pins(model, block.subject, end.item, block.unit)}
    top = end.y + Decimal(end.height - pen.font_g) / 2
    for n, cell in enumerate(end.cells):
        pin = pins[cell.port]
        if n:
            edge = cell.x - Decimal(cell.width) / 2
            ink.shape(pen.line("pin-cell", (edge, end.y), (edge, end.y + end.height), dashed=end.dashed))
        ink.text("pin", (cell.x, top), pin.marking, middle=True)


def _end(model: Model, ink: Ink, block: PlacedBlock, end: PlacedEnd) -> None:
    """One end box, its label (above a top box, below a bottom one) and pin cells; none if blank."""
    if end.blank:
        return
    pen = ink.pen
    label = end_label(model, end.item, block.unit, block.subject)
    below = end.y + end.height + pen.pad_g
    above = end.y - pen.pad_g - pen.font_g
    ink.shape(pen.outline("end-box", (end.x, end.y, end.width, end.height), dashed=end.dashed))
    if label:
        centre = end.x + Decimal(end.width) / 2
        at = (centre, above if end.top else below)
        ink.text("end-label", at, label, middle=True)
    _cells(model, ink, block, end)


def _wire(ink: Ink, wire: PlacedWire, text: str, *, link: bool) -> None:
    """One core or single wire: its two runs and its text, from layout's points.

    The text reads upward along the wire; a row link's reads level, centred on the point.
    """
    pen = ink.pen
    for run in (wire.run_a, wire.run_b):
        ink.shape(pen.wire("core", tuple((point.x, point.y) for point in run)))
    if link:
        top = Decimal(wire.text_y) - Decimal(pen.font_g) / 2
        ink.text("core", (wire.text_x, top), text, middle=True)
    else:
        ink.upward_text("core", (wire.text_x, wire.text_y), text)


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
    subject, unit = block.subject, block.unit
    pen = Pen(library, sheet.module_mm, smallest_height_mm(library), tuning_of(model).marker_padding, text_room_on(model, sheet, library))
    cables = block_cables(model, subject, unit)
    texts = core_texts(model, subject, unit)
    links = set(row_links(model, subject, unit))
    ink = Ink(pen)
    _boxes(model, ink, block, cables)
    for end in block.ends:
        _end(model, ink, block, end)
    for wire in block.wires:
        _wire(ink, wire, texts[wire.conductor], link=wire.conductor in links)
    _brackets(model, ink, block)
    return pen.svg(block.width, block.height, ink.body())


def cable_blocks(model: Model, cables: CableLayout, library: Library) -> frozendict[str, str]:
    """Render every cable block of `cables` to SVG, keyed as `cables.blocks` is.

    Each is sized to its block in mm on the block's own sheet (`sheet_format_of`), with the grid
    origin at the block's top-left. A block draws only what its values hold: boxes, end boxes
    with their pin cells, core wires; every text is a `derive.cable_drawing` function's. Pure.
    """
    return frozendict({key: _render_block(model, library, b) for key, b in cables.blocks.items()})
