"""Rotation, footprints and lane stacking: the geometry every stage shares."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .sides import CLOCKWISE, opposite
from .values import Box, Cell, Lane, Options, Orientation, Pin, Side, Sym

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .outputs import Marker


# Orientation to (mirror in x first, clockwise quarter turns), as symdef's `orient` reads it.
_TURNS: Mapping[str, tuple[bool, int]] = frozendict(
    {
        "R0": (False, 0),
        "R90": (False, 1),
        "R180": (False, 2),
        "R270": (False, 3),
        "MR0": (True, 0),
        "MR90": (True, 1),
        "MR180": (True, 2),
        "MR270": (True, 3),
    }
)


def _turns(func: str, orient: str) -> tuple[bool, int]:
    """The mirror flag and quarter turns of orient; any other string is a ValueError."""
    if orient not in _TURNS:
        msg = f"{func}: orientation {orient} is not one of the eight"
        raise ValueError(msg)
    return _TURNS[orient]


def rotate_xy(dx: int, dy: int, orient: str) -> tuple[int, int]:
    """Offsets at orient: x negated first for an MR, then turned clockwise (y grows down)."""
    mirror, turns = _turns("rotate_xy", orient)
    if mirror:
        dx = -dx
    for _ in range(turns):
        dx, dy = -dy, dx
    return dx, dy


def rotate_box(box: Box, orient: str) -> Box:
    """The box turned about the symbol origin as symdef's `orient` does; w and h swap on R90."""
    _turns("rotate_box", orient)
    x0, y0 = rotate_xy(box.x, box.y, orient)
    x1, y1 = rotate_xy(box.x + box.w, box.y + box.h, orient)
    return Box(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))


def rotate_side(side: Side, orient: Orientation) -> Side:
    """The side a pin faces after the cell is mirrored (E and W swap) and turned clockwise."""
    mirror, turns = _turns("rotate_side", orient)
    if mirror and side in ("E", "W"):
        side = opposite(side)
    return CLOCKWISE[(CLOCKWISE.index(side) + turns) % 4]


def shift(box: Box, x: int, y: int) -> Box:
    """The box moved by (x, y)."""
    return Box(box.x + x, box.y + y, box.w, box.h)


def marker_box_at(x: int, y: int, options: Options, orient: Orientation = "R0") -> Box:
    """A marker's footprint: `Options.marker`, turned to orient, moved to the symbol origin (x, y).

    The origin is the point the drawing hands symdef (layout-0305); no anchor rule is added here.
    `rotate_box` turns the box about the origin as symdef's `orient` does (layout-0306).
    """
    if options.marker is None:
        msg = "Options.marker is unset; fransys_el passes the reference-marker symbol's keepout box"
        raise ValueError(msg)
    return shift(rotate_box(options.marker, orient), x, y)


def marker_box(marker: Marker, options: Options) -> Box:
    """The one home of a marker's footprint: `marker_box_at` its origin and orientation."""
    return marker_box_at(marker.x, marker.y, options, marker.orient)


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
