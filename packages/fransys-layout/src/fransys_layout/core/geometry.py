"""Rotation, footprints and lane stacking: the geometry every stage shares."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import CoreError
from .values import Box, Cell, Lane, Options, Orientation, Pin, RefKind, Size

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .outputs import Marker
    from .sym_values import PinTurn, Sym, Turned
    from .values import PinRef


_LINKS = (RefKind.ARROW,)  # R350: only an arrow is sized by its widest text; its flag is level


def shift(box: Box, x: int, y: int) -> Box:
    """The box moved by (x, y)."""
    return Box(box.x + x, box.y + y, box.w, box.h)


def marker_box_at(
    x: int,
    y: int,
    options: Options,
    orient: Orientation = "R0",
    key: tuple[PinRef, str] | None = None,
) -> Box:
    """A marker's footprint at orient, moved to the symbol origin (x, y).

    The box is `Options.marker_fit[key]` (the marker's pin and kind) when named, else `link_fit`
    for a link kind, else `Options.marker`; the symdef layer measured every orientation (SB4).
    """
    boxes = options.marker_fit.get(key) if key is not None else None
    if boxes is None and key is not None and key[1] in _LINKS:
        boxes = options.link_fit
    boxes = boxes or options.marker
    if boxes is None:
        msg = "Options.marker is unset; the symdef layer sets the marker symbol's keepout boxes"
        raise ValueError(msg)
    if orient not in boxes:
        msg = f"Options.marker has no box for {orient}; the symdef layer measures all eight"
        raise CoreError(msg)
    return shift(boxes[orient], x, y)


def marker_box(marker: Marker, options: Options) -> Box:
    """The one home of a marker's footprint: `marker_box_at` its origin, orientation and key."""
    return marker_box_at(marker.x, marker.y, options, marker.orient, (marker.end, str(marker.kind)))


def corners(box: Box) -> tuple[int, int, int, int]:
    """The box as left, top, right and bottom."""
    return box.x, box.y, box.x + box.w, box.y + box.h


def union(a: Box, b: Box) -> Box:
    """The smallest box holding both a and b."""
    x0, y0 = min(a.x, b.x), min(a.y, b.y)
    x1, y1 = max(a.x + a.w, b.x + b.w), max(a.y + a.h, b.y + b.h)
    return Box(x0, y0, x1 - x0, y1 - y0)


def overlaps(a: Box, b: Box) -> bool:
    """True when the two boxes share interior area; touching edges do not count."""
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def inside(box: Box, area: Size) -> bool:
    """True when `box` lies wholly within the page `area`, edges included."""
    return box.x >= 0 and box.y >= 0 and box.x + box.w <= area.w and box.y + box.h <= area.h


def pin_of(sym: Sym, pin_id: str) -> Pin:
    """The pin of sym with pin_id; a missing id is a KeyError."""
    for p in sym.pins:
        if p.id == pin_id:
            return p
    msg = f"{sym.id} has no pin {pin_id}"
    raise CoreError(msg)


def view_of(sym: Sym, orient: Orientation) -> Turned:
    """The symbol at orient, as the symdef layer measured it; a missing view is a ValueError."""
    view = sym.views.get(orient)
    if view is None:
        msg = (
            f"symbol {sym.id} has no view at {orient}: its views are {list(sym.views)}; "
            "the symdef layer measures every orientation the symbol is allowed"
        )
        raise CoreError(msg)
    return view


def pin_turn(sym: Sym, orient: Orientation, pin_id: str) -> PinTurn:
    """Pin_id's offset and side at orient: the view's entry at the pin's place in Sym.pins."""
    for p, turn in zip(sym.pins, view_of(sym, orient).pins, strict=True):
        if p.id == pin_id:
            return turn
    msg = f"{sym.id} has no pin {pin_id}"
    raise CoreError(msg)


def cell_footprint(sym: Sym, cell: Cell, *, in_row: bool) -> Box:
    """The footprint at the cell's orient; the row variant when the cell stands in a row group."""
    view = view_of(sym, cell.orient)
    return view.row_footprint if in_row and view.row_footprint is not None else view.footprint


def cell_anchor(sym: Sym, cell: Cell) -> tuple[int, int]:
    """Offset of the lane pin (top, else bottom) from the symbol origin at the cell's orient."""
    pin_id = cell.top_pin if cell.top_pin is not None else cell.bottom_pin
    if pin_id is None:
        return 0, 0
    return pin_xy(sym, cell, pin_id)


def pin_xy(sym: Sym, cell: Cell, pin_id: str) -> tuple[int, int]:
    """Offset of pin_id from the symbol origin, at the cell's orient."""
    turn = pin_turn(sym, cell.orient, pin_id)
    return turn.dx, turn.dy


def stack_lane(
    syms: Mapping[str, Sym], cells: tuple[Cell, ...], options: Options, in_row: frozenset[str]
) -> tuple[tuple[int, ...], int]:
    """Origin y of each cell stacked from y 0 with wire_min gaps; and the lane height."""
    ys: list[int] = []
    bottom = 0
    for i, cell in enumerate(cells):
        sym = syms[cell.sym]
        fp = cell_footprint(sym, cell, in_row=cell.sym in in_row)
        top = bottom + (options.wire_min if i else 0)
        origin = top - fp.y
        ys.append(origin)
        bottom = origin + fp.y + fp.h
    return tuple(ys), bottom


def lane_extent(
    syms: Mapping[str, Sym], cells: tuple[Cell, ...], in_row: frozenset[str]
) -> tuple[int, int]:
    """Left and right reach of a lane's footprints against the lane's wire x."""
    left, right = 0, 0
    for cell in cells:
        sym = syms[cell.sym]
        fp = cell_footprint(sym, cell, in_row=cell.sym in in_row)
        ax, _ = cell_anchor(sym, cell)
        left = min(left, fp.x - ax)
        right = max(right, fp.x + fp.w - ax)
    return left, right


def column_extent(
    syms: Mapping[str, Sym], lanes: tuple[Lane, ...], in_row: frozenset[str]
) -> tuple[int, int]:
    """Left and right reach of a column against lane 0's x, over all lanes and their offsets."""
    left, right = 0, 0
    for lane in lanes:
        a, b = lane_extent(syms, lane.cells, in_row)
        left = min(left, lane.offset + a)
        right = max(right, lane.offset + b)
    return left, right


def shape_key(syms: Mapping[str, Sym], lanes: tuple[Lane, ...]) -> str:
    """Columns with equal shapes are like: the stagger rule applies between them.

    A documented exception to "P1.2 is done"; topology's port reads it from here.
    """
    return "|".join(
        ",".join(f"{syms[c.sym].body}{syms[c.sym].keepout}{c.orient}" for c in lane.cells)
        for lane in lanes
    )


def box_reach(sym: Sym) -> tuple[int, int]:
    """How far a box's footprint reaches past its body, left and right (its label); never negative.

    The one home of footprint minus body for a card (layout-0287): stages 2, 4 and 5 read it.
    """
    if sym.box is None:
        msg = f"{sym.id} has no box spec, so it has no card reach"
        raise ValueError(msg)
    fp, body = sym.footprint, sym.body
    left, right = body.x - fp.x, fp.x + fp.w - body.x - body.w
    if left < 0 or right < 0:
        msg = f"{sym.id}: footprint {fp} lies inside body {body}; a card's footprint holds its body"
        raise ValueError(msg)
    return left, right


def offset_to(box: Box, x: int, y: int) -> tuple[int, int]:
    """The move that takes `box`'s top-left corner to (`x`, `y`)."""
    return x - box.x, y - box.y


def stair_room(y0: int, y1: int, grid: int) -> int:
    """Turn rows a stair between y0 and y1 has: whole grids apart, minus one."""
    return (y1 - y0) // grid - 1
