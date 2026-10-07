"""Laid-out cable blocks to SVG, one per `layout.cable_block` (CT5, CD7 to CD11)."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.derive import printed_designation
from fransys_model.derive.cable_drawing import (
    block_cables,
    block_wires,
    cable_block_key,
    cable_heading,
    core_text,
    drawn_pins,
    end_label,
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
    layout_of,
    profile_of,
    sheet_format_of,
)

from ._cable_pen import Pen
from ._style import style_block

if TYPE_CHECKING:
    from fransys_model.derive import HarnessCable
    from fransys_model.kernel import Model


def _of_block[R: (CableBox, EndBox, CoreWire)](
    model: Model, kind: type[R], block: CableBlock
) -> tuple[R, ...]:
    """Every `kind` record of `block`, ordered by `id`."""
    records = layout_of(model, kind).values()
    return tuple(sorted((r for r in records if r.block == block.id), key=lambda r: r.id))


def _boxes(model: Model, pen: Pen, block: CableBlock, cables: tuple[HarnessCable, ...]) -> str:
    """The harness box first (dashed, its label), then each cable box (solid, its heading)."""
    by_cable = {cable.cable: cable for cable in cables}
    parts = []
    for box in sorted(_of_block(model, CableBox, block), key=lambda b: b.kind is BoxKind.CABLE):
        harness = box.kind is BoxKind.HARNESS
        text = (
            printed_designation(model, box.item, unit=block.unit)
            if harness
            else cable_heading(model, by_cable[box.item], block.unit)
        )
        css = "harness-box" if harness else "cable-box"
        parts.append(pen.rect(css, (box.x, box.y, box.width, box.height), dashed=harness))
        parts.append(pen.text("heading", (box.x + pen.pad_g, box.y + pen.pad_g), text))
    return "".join(parts)


_DASHED_BY_STYLE = {EndStyle.SOLID: False, EndStyle.DASHED: True}  # a blank end draws no box
_LABEL_BELOW = {BlockRow.TOP: False, BlockRow.BOTTOM: True}


def _cells(model: Model, pen: Pen, block: CableBlock, end: EndBox, *, dashed: bool) -> str:
    """One marking per pin cell, centred on the cell, and a divider on each cell's left edge.

    The cell's width is layout's (layout-0152), so its edge is half that from x.
    """
    pins = {pin.port: pin for pin in drawn_pins(model, block.subject, end.item, block.unit)}
    top = end.y + Decimal(end.height - pen.font_g) / 2
    parts = []
    for n, cell in enumerate(end.pins):
        pin = pins[cell.port]
        if n:
            edge = cell.x - Decimal(cell.width) / 2
            parts.append(
                pen.line("pin-cell", (edge, end.y), (edge, end.y + end.height), dashed=dashed)
            )
        parts.append(pen.text("pin", (cell.x, top), pin.marking, middle=True))
    return "".join(parts)


def _end(model: Model, pen: Pen, block: CableBlock, end: EndBox) -> str:
    """One end box, its label (above a top box, below a bottom one) and pin cells; none if blank."""
    if end.style is EndStyle.BLANK:
        return ""
    dashed = _DASHED_BY_STYLE[end.style]
    label = end_label(model, end.item, block.unit)
    below = end.y + end.height + pen.pad_g
    above = end.y - pen.pad_g - pen.font_g
    parts = [pen.outline("end-box", (end.x, end.y, end.width, end.height), dashed=dashed)]
    if label:
        centre = end.x + Decimal(end.width) / 2
        parts.append(
            pen.text(
                "end-label",
                (centre, below if _LABEL_BELOW[end.row] else above),
                label,
                middle=True,
            )
        )
    return "".join(parts) + _cells(model, pen, block, end, dashed=dashed)


def _wire(pen: Pen, wire: CoreWire, text: str, *, link: bool) -> str:
    """One core or single wire: its two runs and its text, from layout's points (HA-H1 A1).

    The text reads upward along the wire; a row link's reads level, centred on the point (L1).
    """
    runs = "".join(
        pen.polyline("core", tuple((point.x, point.y) for point in run))
        for run in (wire.run_a, wire.run_b)
    )
    if link:
        top = Decimal(wire.text_y) - Decimal(pen.font_g) / 2
        return runs + pen.text("core", (wire.text_x, top), text, middle=True)
    return runs + pen.upward_text("core", (wire.text_x, wire.text_y), text)


def _render_block(model: Model, block: CableBlock) -> str:
    """One block's SVG, sized to the block in mm on its sheet's module (Q5)."""
    sheet = sheet_format_of(model, block.sheet_format)
    profile = profile_of(model)
    pen = Pen(sheet.module_mm, profile.text_height, profile.marker_padding)
    cables = block_cables(model, block.subject, block.unit)
    texts = {core.conductor: core_text(core) for cable in cables for core in cable.cores}
    texts |= {w.conductor: w.text for w in block_wires(model, block.subject, block.unit)}
    links = set(row_links(model, block.subject, block.unit))
    body = _boxes(model, pen, block, cables)
    body += "".join(_end(model, pen, block, end) for end in _of_block(model, EndBox, block))
    body += "".join(
        _wire(pen, wire, texts[wire.conductor], link=wire.conductor in links)
        for wire in _of_block(model, CoreWire, block)
    )
    return pen.svg(block.width, block.height, style_block(sheet.module_mm) + body)


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
