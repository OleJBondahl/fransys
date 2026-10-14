"""Laid-out cable blocks to SVG, one per `layout.cable_block`."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from symdef import Orientation, orient

from electrical_symbols import LIBRARY, WIRING_GRID
from fransys_model.derive import printed_designation
from fransys_model.derive.cable_drawing import (
    block_brackets,
    block_cables,
    cable_block_key,
    cable_heading,
    core_texts,
    drawn_pins,
    end_label,
    pair_room,
    row_links,
)
from fransys_model.layout import (
    BlockRow,
    BoxKind,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    OpenCoreWire,
    layout_of,
    profile_of,
    sheet_format_of,
)

from ._cable_ink import Ink
from ._cable_pen import Pen
from ._numbers import format_decimal
from ._style import style_block
from ._symbols import symbol_body

if TYPE_CHECKING:
    from fransys_model.derive import HarnessCable
    from fransys_model.kernel import Id, Model


def _of_block[R: (CableBox, EndBox, CoreWire, OpenCoreWire)](
    model: Model, kind: type[R], block: CableBlock
) -> tuple[R, ...]:
    """Every `kind` record of `block`, ordered by `id`."""
    records = layout_of(model, kind).values()
    return tuple(sorted((r for r in records if r.block == block.id), key=lambda r: r.id))


def _boxes(model: Model, ink: Ink, block: CableBlock, cables: tuple[HarnessCable, ...]) -> None:
    """The harness box first (dashed, its label), then each cable box (solid, its heading)."""
    by_cable = {cable.cable: cable for cable in cables}
    pen = ink.pen
    for box in sorted(_of_block(model, CableBox, block), key=lambda b: b.kind is BoxKind.CABLE):
        harness = box.kind is BoxKind.HARNESS
        text = (
            printed_designation(model, box.item, unit=block.unit)
            if harness
            else cable_heading(model, by_cable[box.item], block.unit)
        )
        css = "harness-box" if harness else "cable-box"
        ink.shape(pen.rect(css, (box.x, box.y, box.width, box.height), dashed=harness))
        ink.text("heading", (box.x + pen.pad_g, box.y + pen.pad_g), text)


_DASHED_BY_STYLE = {EndStyle.SOLID: False, EndStyle.DASHED: True}  # a blank end draws no box
_LABEL_BELOW = {BlockRow.TOP: False, BlockRow.BOTTOM: True}


def _cells(model: Model, ink: Ink, block: CableBlock, end: EndBox, *, dashed: bool) -> None:
    """One marking per pin cell, centred on the cell, and a divider on each cell's left edge.

    The cell's width is layout's (layout-0152), so its edge is half that from x.
    """
    pen = ink.pen
    pins = {pin.port: pin for pin in drawn_pins(model, block.subject, end.item, block.unit)}
    top = end.y + Decimal(end.height - pen.font_g) / 2
    for n, cell in enumerate(end.pins):
        pin = pins[cell.port]
        if n:
            edge = cell.x - Decimal(cell.width) / 2
            ink.shape(
                pen.line("pin-cell", (edge, end.y), (edge, end.y + end.height), dashed=dashed)
            )
        ink.text("pin", (cell.x, top), pin.marking, middle=True)


_EARTH_PORT_G = 2 * WIRING_GRID  # the symbol's port lies two modules from its origin
_EARTH_TURN = {BlockRow.TOP: Orientation.R180, BlockRow.BOTTOM: Orientation.R0}


def _earth(ink: Ink, end: EndBox) -> None:
    """A bar's end: a PE symbol at each landed cell, its port on the core's end; no box, no text.

    A top end's core starts at the box's bottom edge and a bottom end's ends at its top edge.
    """
    pen = ink.pen
    top = end.row is BlockRow.TOP
    symbol = orient(LIBRARY.get("protective-earth"), _EARTH_TURN[end.row])
    port_y = end.y + end.height if top else end.y
    y = Decimal(pen.mm(port_y - _EARTH_PORT_G if top else port_y + _EARTH_PORT_G))
    for cell in (cell for cell in end.pins if cell.landed):
        body = symbol_body(symbol, pen.module_mm, pen.font_mm)
        move = f"translate({pen.mm(cell.x)},{format_decimal(y)})"
        ink.shape(f'<g class="symbol earth" transform="{move}">{body}</g>')


def _end(model: Model, ink: Ink, block: CableBlock, end: EndBox) -> None:
    """One end box, its label (above a top box, below a bottom one) and pin cells; none if blank."""
    if end.style is EndStyle.BLANK:
        return
    if end.style is EndStyle.EARTH:
        _earth(ink, end)
        return
    pen = ink.pen
    dashed = _DASHED_BY_STYLE[end.style]
    label = end_label(model, end.item, block.unit, block.subject)
    below = end.y + end.height + pen.pad_g
    above = end.y - pen.pad_g - pen.font_g
    ink.shape(pen.outline("end-box", (end.x, end.y, end.width, end.height), dashed=dashed))
    if label:
        centre = end.x + Decimal(end.width) / 2
        at = (centre, below if _LABEL_BELOW[end.row] else above)
        ink.text("end-label", at, label, middle=True)
    _cells(model, ink, block, end, dashed=dashed)


def _wire(ink: Ink, wire: CoreWire | OpenCoreWire, text: str, *, link: bool) -> None:
    """One core or single wire: its two runs and its text, from layout's points.

    The text reads upward along the wire; a row link's reads level, centred on the point.
    """
    pen = ink.pen
    for run in (wire.run_a, wire.run_b):
        ink.shape(pen.polyline("core", tuple((point.x, point.y) for point in run)))
    if link:
        top = Decimal(wire.text_y) - Decimal(pen.font_g) / 2
        ink.text("core", (wire.text_x, top), text, middle=True)
    else:
        ink.upward_text("core", (wire.text_x, wire.text_y), text)


def _core_of(wire: CoreWire | OpenCoreWire) -> Id[Any]:
    return wire.core if isinstance(wire, OpenCoreWire) else wire.conductor


def _brackets(
    model: Model, ink: Ink, block: CableBlock, wires: tuple[CoreWire | OpenCoreWire, ...]
) -> None:
    """Each pair bracket: a line over its two cores' texts with a tick down each, and its label.

    It stands in the pair room under the cable box's heading (`pair_room`, layout's own).
    """
    pen = ink.pen
    room = pair_room(pen.font_g, pen.pad_g, WIRING_GRID)
    boxes = {box.item: box for box in _of_block(model, CableBox, block)}
    xs = {_core_of(wire): wire.text_x for wire in wires}
    for bracket in block_brackets(model, block.subject, block.unit):
        top = boxes[bracket.cable].y
        a, b = xs[bracket.core_a], xs[bracket.core_b]
        line, tick = top + room.line, top + room.tick
        ink.shape(pen.polyline("core", ((a, tick), (a, line), (b, line), (b, tick))))
        ink.text("core", (Decimal(a + b) / 2, top + room.label), bracket.label, middle=True)


def _render_block(model: Model, block: CableBlock) -> str:
    """One block's SVG, sized to the block in mm on its sheet's module."""
    sheet = sheet_format_of(model, block.sheet_format)
    profile = profile_of(model)
    pen = Pen(sheet.module_mm, profile.text_height_mm, profile.marker_padding)
    cables = block_cables(model, block.subject, block.unit)
    texts = core_texts(model, block.subject, block.unit)
    links = set(row_links(model, block.subject, block.unit))
    ink = Ink(pen)
    _boxes(model, ink, block, cables)
    for end in _of_block(model, EndBox, block):
        _end(model, ink, block, end)
    wires = (*_of_block(model, CoreWire, block), *_of_block(model, OpenCoreWire, block))
    for wire in wires:
        _wire(ink, wire, texts[_core_of(wire)], link=_core_of(wire) in links)
    _brackets(model, ink, block, wires)
    return pen.svg(block.width, block.height, style_block() + ink.body())


def cable_blocks(model: Model) -> frozendict[str, str]:
    """Render every cable block of a laid-out model to SVG.

    One SVG per `layout.cable_block`, keyed by `cable_block_key(block.unit, block.subject)`. Each
    is sized to its block in mm on the block's own sheet (`sheet_format_of`), with the grid
    origin at the block's top-left. A block draws only what its records hold: boxes, end boxes
    with their pin cells, core wires; every text is a `derive.cable_drawing` function's. Pure.
    """
    blocks = layout_of(model, CableBlock).values()
    return frozendict(
        {
            cable_block_key(block.unit, block.subject): _render_block(model, block)
            for block in sorted(blocks, key=lambda b: b.id)
        }
    )
