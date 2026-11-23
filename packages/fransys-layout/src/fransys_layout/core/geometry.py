"""Rotation, footprints and lane stacking: the geometry every stage shares."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Literal

from .errors import CoreError
from .values import Box, MarkerBoxes, Options, Orientation, Pin, Size

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .flow_values import Cell, Lane
    from .outputs import Marker
    from .sym_values import PinTurn, Sym, Turned
    from .values import PinRef


def row_of(bands: Sequence[tuple[int, int]], y: int) -> int:
    """The index of the (top, bottom) band that holds y, else -1."""
    return next((i for i, (top, bottom) in enumerate(bands) if top <= y <= bottom), -1)


def around(box: Box, gap: int) -> Box:
    """The box with `gap` more on every side."""
    return Box(box.x - gap, box.y - gap, box.w + 2 * gap, box.h + 2 * gap)


def shift(box: Box, x: int, y: int) -> Box:
    """The box moved by (x, y)."""
    return Box(box.x + x, box.y + y, box.w, box.h)


def stub_views(
    lines: Mapping[tuple[PinRef, PinRef], tuple[int, ...]],
    table: Mapping[tuple[int, int], Mapping[Orientation, Box]],
    pin: PinRef,
    also: Sequence[PinRef],
    far: Sequence[PinRef],
) -> Mapping[Orientation, Box] | None:
    """The boxes of the stub at `pin` for the conductors its ledger end holds (R1597), or `None` when `lines` names none.

    Each far pin is read at the first of `pin` and its `also` pins that has lines for it; the stub's boxes are
    the `table` entry at the widest of those lines and their count. Layout and the writer both size a stub through here.
    """
    widths: list[int] = []
    for f in far:
        widths += next((ws for near in (pin, *also) if (ws := lines.get((near, f)))), ())
    if not widths:
        return None
    if (max(widths), len(widths)) not in table:
        msg = f"Options.stub_table has no box for {len(widths)} lines of width {max(widths)} at {pin}; pass a row for every count a stub can hold"
        raise CoreError(msg)
    return table[max(widths), len(widths)]


def _boxes(options: Options, key: tuple[PinRef | None, str]) -> MarkerBoxes:
    """The one lookup of `Options.marker_boxes`: the key's own boxes, else the kind's at any pin (SB4)."""
    boxes = options.marker_boxes.get(key) or options.marker_boxes.get((None, key[1]))
    if boxes is None:
        msg = f"Options.marker_boxes has no box for {key}: pass `(None, {key[1]!r})`, the kind's box at any pin"
        raise CoreError(msg)
    return boxes


def _box_at(x: int, y: int, views: Mapping[Orientation, Box], orient: Orientation, key: tuple[PinRef | None, str]) -> Box:
    """The box of `views` at `orient`, moved to the origin (x, y)."""
    if orient not in views:
        msg = f"Options.marker_boxes has no box for {key} at {orient}; the symdef layer measures all eight"
        raise CoreError(msg)
    return shift(views[orient], x, y)


def marker_box_at(x: int, y: int, options: Options, orient: Orientation, key: tuple[PinRef | None, str]) -> Box:
    """A marker's footprint at orient, moved to the symbol origin (x, y): what places and routes it (R350)."""
    return _box_at(x, y, _boxes(options, key).footprint, orient, key)


def marker_drawn_at(x: int, y: int, options: Options, orient: Orientation, key: tuple[PinRef | None, str]) -> Box:
    """The box a marker is drawn in at (x, y), the reserve a wire keeps off: a tag is drawn as wide as its text can be (R543)."""
    return _box_at(x, y, _boxes(options, key).drawn, orient, key)


def sized(options: Options, key: tuple[PinRef, str], also: Sequence[PinRef], far: Sequence[PinRef]) -> Options:
    """`options` with the boxes of the stub at `key` for the lines its ledger end holds, else as they were (R1597)."""
    views = stub_views(options.stub_lines, options.stub_table, key[0], also, far)
    return replace(options, marker_boxes={**options.marker_boxes, key: MarkerBoxes(views, views)}) if views else options


def marker_box(marker: Marker, options: Options, *, drawn: bool = False) -> Box:
    """The one home of a marker's box: `marker_box_at` its origin, orientation and key, sized by its ledger end."""
    key = (marker.end, str(marker.kind))
    box = (marker_drawn_at if drawn else marker_box_at)(marker.x, marker.y, sized(options, key, marker.also, marker.far), marker.orient, key)
    return replace(box, h=box.h + marker.span)


def union(a: Box, b: Box) -> Box:
    """The smallest box holding both a and b."""
    x0, y0 = min(a.x, b.x), min(a.y, b.y)
    x1, y1 = max(a.x + a.w, b.x + b.w), max(a.y + a.h, b.y + b.h)
    return Box(x0, y0, x1 - x0, y1 - y0)


def inset(box: Box, by: int = 1) -> Box:
    """The box less `by` on each side: a closed test of it is an open test of `box`."""
    return Box(box.x + by, box.y + by, box.w - 2 * by, box.h - 2 * by)


def overlaps(a: Box, b: Box) -> bool:
    """True when the two boxes share interior area; touching edges do not count."""
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def inside(box: Box, area: Size, *, edge: Literal["open", "closed"] = "open") -> bool:
    """True when `box` lies wholly within the page `area`; "open" (OUT_OF_PAGE's predicate, R751) refuses a touched edge, "closed" allows it."""
    room = min(box.x, box.y, area.w - (box.x + box.w), area.h - (box.y + box.h))
    return room >= 0 if edge == "closed" else room > 0


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


def cell_footprint(sym: Sym, cell: Cell) -> Box:
    """The footprint at the cell's orient; the row variant when the cell stands in a row group."""
    view = view_of(sym, cell.orient)
    return view.row_footprint if sym.in_row and view.row_footprint is not None else view.footprint


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


def stack_lane(syms: Mapping[str, Sym], cells: tuple[Cell, ...], options: Options) -> tuple[tuple[int, ...], int]:
    """Origin y of each cell stacked from y 0: wire_min plus its hold above each cell but the first.

    A hold on the first cell is ignored; nothing stands above it. Also returns the lane height.
    """
    ys: list[int] = []
    bottom = 0
    for i, cell in enumerate(cells):
        sym = syms[cell.sym]
        fp = cell_footprint(sym, cell)
        top = bottom + (options.wire_min + cell.hold if i else 0)
        origin = top - fp.y
        ys.append(origin)
        bottom = origin + fp.y + fp.h
    return tuple(ys), bottom


def lane_extent(syms: Mapping[str, Sym], cells: tuple[Cell, ...], *, body: bool = False) -> tuple[int, int]:
    """Left and right reach of a lane's footprints (its bodies when `body`) against the lane's wire x."""
    left, right = 0, 0
    for cell in cells:
        sym = syms[cell.sym]
        fp = view_of(sym, cell.orient).body if body else cell_footprint(sym, cell)
        ax, _ = cell_anchor(sym, cell)
        left = min(left, fp.x - ax)
        right = max(right, fp.x + fp.w - ax)
    return left, right


def column_extent(syms: Mapping[str, Sym], lanes: tuple[Lane, ...]) -> tuple[int, int]:
    """Left and right reach of a column against lane 0's x, over all lanes and their offsets."""
    left, right = 0, 0
    for lane in lanes:
        a, b = lane_extent(syms, lane.cells)
        left = min(left, lane.offset + a)
        right = max(right, lane.offset + b)
    return left, right


def box_reach(sym: Sym) -> tuple[int, int]:
    """How far a box's footprint reaches past its body, left and right (its label); never negative.

    The one home of footprint minus body for a card (layout-0287): stages 2, 4 and 5 read it.
    """
    if sym.box is None:
        msg = f"{sym.id} has no box spec, so it has no card reach"
        raise CoreError(msg)
    fp, body = sym.footprint, sym.body
    left, right = body.x - fp.x, fp.x + fp.w - body.x - body.w
    if left < 0 or right < 0:
        msg = f"{sym.id}: footprint {fp} lies inside body {body}; a card's footprint holds its body"
        raise CoreError(msg)
    return left, right


def offset_to(box: Box, x: int, y: int) -> tuple[int, int]:
    """The move that takes `box`'s top-left corner to (`x`, `y`)."""
    return x - box.x, y - box.y


def stair_room(y0: int, y1: int, grid: int) -> int:
    """Turn rows a stair between y0 and y1 has: whole grids apart, minus one."""
    return (y1 - y0) // grid - 1
