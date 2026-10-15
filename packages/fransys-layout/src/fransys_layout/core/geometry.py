"""Rotation, footprints and lane stacking: the geometry every stage shares."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .values import Box, Cell, Lane, Options, Pin, Sym

if TYPE_CHECKING:
    from collections.abc import Mapping


def rotate_xy(dx: int, dy: int, orient: str) -> tuple[int, int]:
    """Pin offsets at orient; R180 turns both signs, R90 and R270 turn a quarter."""
    if orient == "R180":
        return -dx, -dy
    if orient == "R90":
        return -dy, dx
    if orient == "R270":
        return dy, -dx
    return dx, dy


def rotate_box(box: Box, orient: str) -> Box:
    """The box at orient; width and height are kept, corners are mapped."""
    if orient == "R180":
        return Box(-box.x - box.w, -box.y - box.h, box.w, box.h)
    if orient in ("R90", "R270"):
        x0, y0 = rotate_xy(box.x, box.y, orient)
        x1, y1 = rotate_xy(box.x + box.w, box.y + box.h, orient)
        return Box(min(x0, x1), min(y0, y1), box.w, box.h)
    return box


def rotate_side(side: str, orient: str) -> str:
    """The side a pin faces after the cell turns to orient (N E S W clockwise)."""
    turns = {"R0": 0, "R90": 1, "R180": 2, "R270": 3}[orient]
    order = "NESW"
    return order[(order.index(side) + turns) % 4]


def shift(box: Box, x: int, y: int) -> Box:
    """The box moved by (x, y)."""
    return Box(box.x + x, box.y + y, box.w, box.h)


def union(a: Box, b: Box) -> Box:
    """The smallest box holding both a and b."""
    x0, y0 = min(a.x, b.x), min(a.y, b.y)
    x1, y1 = max(a.x + a.w, b.x + b.w), max(a.y + a.h, b.y + b.h)
    return Box(x0, y0, x1 - x0, y1 - y0)


def overlaps(a: Box, b: Box) -> bool:
    """True when the two boxes share interior area; touching edges do not count."""
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def pin_of(sym: Sym, pin_id: str) -> Pin:
    """The pin of sym with pin_id; a missing id is a KeyError."""
    for p in sym.pins:
        if p.id == pin_id:
            return p
    msg = f"{sym.id} has no pin {pin_id}"
    raise KeyError(msg)


def cell_footprint(sym: Sym, cell: Cell, *, in_row: bool) -> Box:
    """The footprint at the cell's orient; the row variant when the cell stands in a row group."""
    base = sym.row_footprint if in_row and sym.row_footprint is not None else sym.footprint
    return rotate_box(base, cell.orient)


def cell_anchor(sym: Sym, cell: Cell) -> tuple[int, int]:
    """Offset of the lane pin (top, else bottom) from the symbol origin at the cell's orient."""
    pin_id = cell.top_pin if cell.top_pin is not None else cell.bottom_pin
    if pin_id is None:
        return 0, 0
    p = pin_of(sym, pin_id)
    return rotate_xy(p.dx, p.dy, cell.orient)


def pin_xy(sym: Sym, cell: Cell, pin_id: str) -> tuple[int, int]:
    """Offset of pin_id from the symbol origin, at the cell's orient."""
    p = pin_of(sym, pin_id)
    return rotate_xy(p.dx, p.dy, cell.orient)


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
