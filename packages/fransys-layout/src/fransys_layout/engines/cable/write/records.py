"""Private to `write/`: the records of one placed block, keyed by its reading and subject."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.cable.values import PlacedCable
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import (
    BlockRow,
    BoxKind,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    PinCell,
    RoutePoint,
)

if TYPE_CHECKING:
    from fransys_layout.engines.cable.values import (
        PlacedBlock,
        PlacedEnd,
        PlacedWire,
    )
    from fransys_layout.geometry import Point
    from fransys_model.kernel import AuthoringKey, Id


def _block_key(block: PlacedBlock) -> tuple[str, ...]:
    unit = () if block.unit is None else ("unit", render_id(block.unit))
    return ("layout", "cable", "block", *unit, render_id(block.subject))


def _style(end: PlacedEnd) -> EndStyle:
    if end.blank:
        return EndStyle.BLANK
    return EndStyle.DASHED if end.dashed else EndStyle.SOLID


def _end(end: PlacedEnd, key: AuthoringKey, block: Id[Any], stamp: str) -> EndBox:
    end_key = (*key, "end", render_id(end.item))
    pins = tuple(
        PinCell(index=i, port=cell.port, x=cell.x, landed=cell.landed)
        for i, cell in enumerate(end.cells)
    )
    return EndBox(
        id=make_id(EndBox, end_key),
        key=end_key,
        block=block,
        item=end.item,
        row=BlockRow.TOP if end.top else BlockRow.BOTTOM,
        style=_style(end),
        x=end.x,
        y=end.y,
        width=end.width,
        height=end.height,
        pins=pins,
        produced_by=stamp,
    )


def _points(run: tuple[Point, ...]) -> tuple[RoutePoint, ...]:
    return tuple(RoutePoint(index=i, x=p.x, y=p.y) for i, p in enumerate(run))


def _wire(wire: PlacedWire, key: AuthoringKey, block: Id[Any], stamp: str) -> CoreWire:
    wire_key = (*key, "wire", render_id(wire.conductor))
    return CoreWire(
        id=make_id(CoreWire, wire_key),
        key=wire_key,
        block=block,
        conductor=wire.conductor,
        run_a=_points(wire.run_a),
        run_b=_points(wire.run_b),
        text_x=wire.text_x,
        text_y=wire.text_y,
        stub_a=wire.stub_a,
        stub_b=wire.stub_b,
        produced_by=stamp,
    )


def _box(
    key: AuthoringKey, block_id: Id[Any], stamp: str, kind: BoxKind, placed: PlacedCable
) -> CableBox:
    box_key = (*key, "box", render_id(placed.cable))
    x, y, width, height = placed.box.x, placed.box.y, placed.box.width, placed.box.height
    return CableBox(
        id=make_id(CableBox, box_key),
        key=box_key,
        block=block_id,
        item=placed.cable,
        kind=kind,
        external=placed.external,
        x=x,
        y=y,
        width=width,
        height=height,
        produced_by=stamp,
    )


def block_records(block: PlacedBlock, stamp: str) -> list[Any]:
    """The `CableBlock`, its harness box, its cable boxes, its end boxes and its core wires."""
    key = _block_key(block)
    block_id = make_id(CableBlock, key)
    head = CableBlock(
        id=block_id,
        key=key,
        subject=block.subject,
        unit=block.unit,
        width=block.width,
        height=block.height,
        pitch=block.pitch,
        sheet_format=block.sheet_format,
        produced_by=stamp,
    )
    harness = block.harness
    around = (
        []
        if harness is None
        else [
            _box(
                key,
                block_id,
                stamp,
                BoxKind.HARNESS,
                PlacedCable(cable=block.subject, external=False, box=harness),
            )
        ]
    )
    return [
        head,
        *around,
        *(_box(key, block_id, stamp, BoxKind.CABLE, c) for c in block.boxes),
        *(_end(end, key, block_id, stamp) for end in block.ends),
        *(_wire(wire, key, block_id, stamp) for wire in block.wires),
    ]
