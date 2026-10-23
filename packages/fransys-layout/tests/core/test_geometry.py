"""Tests for core/geometry.py: rotation, footprints, anchors and lane stacking."""

from options_fixtures import core_options
from turn_fixtures import views_of

from fransys_layout.core.geometry import (
    cell_anchor,
    cell_footprint,
    column_extent,
    lane_extent,
    pin_xy,
    shape_key,
    stack_lane,
    stair_room,
)
from fransys_layout.core.sym_values import Sym
from fransys_layout.core.values import Box, Cell, Lane, Orientation, Pin, Size

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
    body = Box(-8, -8, 16, 16)
    keepout = Box(-8, -16, 16, 32)
    return Sym(
        id=sym_id,
        group=None,
        unit="u",
        label=Size(0, 0),
        pins=pins,
        nodes=(),
        views=views_of(body, keepout, footprint, pins, R0_TO_R270, row_footprint=row_footprint),
    )


def make_cell(
    sym_id: str = "U1",
    orient: Orientation = "R0",
    top: str | None = None,
    bottom: str | None = None,
) -> Cell:
    """A cell of sym_id at orient with the given lane pins."""
    return Cell(sym=sym_id, orient=orient, top_pin=top, bottom_pin=bottom)


def test_stack_lane_puts_cells_a_wire_min_apart() -> None:
    """Two 32 G footprints with wire_min 8 stack 40 apart, leaving an 8 G gap."""
    syms = {"U1": make_sym()}
    cells = (make_cell(), make_cell())
    ys, height = stack_lane(
        syms,
        cells,
        core_options(
            wire_min=8,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
        frozenset(),
    )
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


def test_stair_room_is_whole_grids_apart_minus_one() -> None:
    """A stair has one turn row per whole grid between its ends, less the one it starts from."""
    assert stair_room(0, 20, 10) == 1
    assert stair_room(0, 10, 10) == 0
    assert stair_room(0, 19, 10) == 0
    assert stair_room(0, 30, 10) == 2
