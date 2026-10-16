"""Tests for core/geometry.py: rotation, footprints, anchors and lane stacking."""

from typing import Any, cast

import pytest
from symdef import Box as SBox
from symdef import Direction, Line, Port, Reference, Status, Symbol, SymbolKind, body_box
from symdef import Orientation as LibraryOrientation
from symdef import Point as SPoint
from symdef import orient as orient_symbol

from fransys_layout.core.geometry import (
    cell_anchor,
    cell_footprint,
    column_extent,
    lane_extent,
    pin_xy,
    rotate_box,
    rotate_side,
    rotate_xy,
    shape_key,
    stack_lane,
)
from fransys_layout.core.values import Box, Cell, Lane, Options, Orientation, Pin, Size, Sym
from fransys_layout.geometry.units import to_grid

R0_TO_R270 = ("R0", "R90", "R180", "R270")
EIGHT = (*R0_TO_R270, "MR0", "MR90", "MR180", "MR270")


FOOTPRINT = Box(-8, -16, 16, 32)


def make_sym(
    sym_id: str = "U1",
    *,
    footprint: Box = FOOTPRINT,
    row_footprint: Box | None = None,
    pins: tuple[Pin, ...] = (),
) -> Sym:
    """A symbol with the given footprint and pins; the other fields are inert."""
    return Sym(
        id=sym_id,
        group=None,
        unit="u",
        label=Size(0, 0),
        body=Box(-8, -8, 16, 16),
        keepout=Box(-8, -16, 16, 32),
        footprint=footprint,
        pins=pins,
        nodes=(),
        orientations=frozenset(R0_TO_R270),
        row_footprint=row_footprint,
    )


def make_cell(
    sym_id: str = "U1",
    orient: Orientation = "R0",
    top: str | None = None,
    bottom: str | None = None,
) -> Cell:
    """A cell of sym_id at orient with the given lane pins."""
    return Cell(sym=sym_id, orient=orient, top_pin=top, bottom_pin=bottom)


def test_rotate_xy_r180() -> None:
    """R180 negates both offsets; R90 and R270 turn a quarter in each direction."""
    assert rotate_xy(16, -8, "R180") == (-16, 8)
    assert rotate_xy(16, -8, "R90") == (8, 16)
    assert rotate_xy(16, -8, "R270") == (-8, -16)


def _oracle_symbol() -> Symbol:
    """A non-square symbol whose body (4 by 3 modules) lies off the origin."""
    top = Line(start=SPoint(-1, -2), end=SPoint(3, -2))
    side = Line(start=SPoint(3, -2), end=SPoint(3, 1))
    return Symbol(
        name="oracle",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference(standard="test", number="0"),
        elements=(top, side),
        ports=tuple(
            Port(id=d.name, position=SPoint(2 * d.dx, 3 * d.dy), direction=d) for d in Direction
        ),
    )


def _grid_box(box: SBox) -> Box:
    """A symdef box in modules as a core box in grid units; the one conversion (SB3 follow-up)."""
    return Box(to_grid(box.min.x), to_grid(box.min.y), to_grid(box.width), to_grid(box.height))


@pytest.mark.parametrize("orient", EIGHT)
def test_rotate_box_equals_symdef_orient_body_box(orient: str) -> None:
    """The oracle: turning the core box equals the body box of the symbol symdef turns."""
    sym = _oracle_symbol()
    want = _grid_box(body_box(orient_symbol(sym, LibraryOrientation[orient])))
    assert rotate_box(_grid_box(body_box(sym)), orient) == want
    assert {want.w, want.h} == {32, 24}


@pytest.mark.parametrize("orient", EIGHT)
def test_rotate_side_and_xy_equal_the_ports_of_symdef_orient(orient: Orientation) -> None:
    """The oracle for sides and offsets: each port of the turned symbol is where we say."""
    base = _oracle_symbol()
    turned = orient_symbol(base, LibraryOrientation[orient])
    for was, now in zip(base.ports, turned.ports, strict=True):
        assert rotate_side(was.direction.name, orient) == now.direction.name
        x, y = to_grid(was.position.x), to_grid(was.position.y)
        assert rotate_xy(x, y, orient) == (to_grid(now.position.x), to_grid(now.position.y))


def test_rotate_side_r180() -> None:
    """A north pin faces south after R180; an east pin faces south after R90."""
    assert rotate_side("N", "R180") == "S"
    assert rotate_side("E", "R90") == "S"


def test_stack_lane_puts_cells_a_wire_min_apart() -> None:
    """Two 32 G footprints with wire_min 8 stack 40 apart, leaving an 8 G gap."""
    syms = {"U1": make_sym()}
    cells = (make_cell(), make_cell())
    ys, height = stack_lane(syms, cells, Options(wire_min=8), frozenset())
    assert ys == (16, 56)
    assert ys[1] - ys[0] == 40
    assert height == 72


def test_column_extent_spans_both_lanes() -> None:
    """Lanes at offsets 0 and 24 reach from -8 to 32 against lane 0's wire."""
    syms = {"U1": make_sym()}
    lanes = (Lane(cells=(make_cell(),), offset=0), Lane(cells=(make_cell(),), offset=24))
    assert column_extent(syms, lanes, frozenset()) == (-8, 32)


def test_lane_extent_uses_the_footprint_not_the_body() -> None:
    """The lane reach is the full footprint against the lane pin."""
    syms = {"U1": make_sym()}
    assert lane_extent(syms, (make_cell(),), frozenset()) == (-8, 8)


def test_pin_xy_on_an_r180_cell() -> None:
    """A pin at (8, -16) on an R180 cell sits at (-8, 16)."""
    sym = make_sym(pins=(Pin(id="A", side="N", dx=8, dy=-16, node=0),))
    assert pin_xy(sym, make_cell(orient="R180"), "A") == (-8, 16)


def test_cell_footprint_uses_the_row_variant_only_in_a_row_group() -> None:
    """The row footprint applies only to a cell that stands in a row group."""
    sym = make_sym(footprint=Box(0, 0, 10, 10), row_footprint=Box(0, 0, 20, 5))
    cell = make_cell()
    assert cell_footprint(sym, cell, in_row=True) == Box(0, 0, 20, 5)
    assert cell_footprint(sym, cell, in_row=False) == Box(0, 0, 10, 10)


def test_cell_anchor_uses_top_pin_else_bottom_pin() -> None:
    """The lane anchor is the top pin when set, else the bottom pin, else the origin."""
    sym = make_sym(
        pins=(
            Pin(id="A", side="N", dx=4, dy=-8, node=0),
            Pin(id="B", side="S", dx=-4, dy=8, node=0),
        ),
    )
    assert cell_anchor(sym, make_cell(top="A", bottom="B")) == (4, -8)
    assert cell_anchor(sym, make_cell(bottom="B")) == (-4, 8)
    assert cell_anchor(sym, make_cell()) == (0, 0)


def test_shape_key_is_equal_for_equal_shapes_and_differs_on_orientation() -> None:
    """Two lanes of equal body, keepout and orientation share a key; a turned cell does not."""
    syms = {"U1": make_sym("U1"), "U2": make_sym("U2")}
    plain = (Lane((make_cell("U1"),), 0),)
    twin = (Lane((make_cell("U2"),), 8),)
    turned = (Lane((make_cell("U1", "R90"),), 0),)
    assert shape_key(syms, plain) == shape_key(syms, twin)
    assert shape_key(syms, plain) != shape_key(syms, turned)


@pytest.mark.parametrize("func", [rotate_xy, rotate_box, rotate_side])
def test_an_unknown_orientation_raises_and_names_the_function(func) -> None:
    """Only the eight orientations have a rule; a mirrored one no longer raises (layout-0306)."""
    args = {rotate_xy: (16, -8), rotate_box: (Box(2, 4, 10, 6),), rotate_side: ("N",)}[func]
    with pytest.raises(ValueError, match=f"{func.__name__}: orientation R45"):
        func(*args, cast("Any", "R45"))
