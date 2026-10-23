"""A cell's hold is extra G above it: stacking, column height, placement, cuts and the edge flip."""

from options_fixtures import core_options

from fransys_layout.core.cut_tall import Tall, _cuts
from fransys_layout.core.geometry import stack_lane
from fransys_layout.core.pack import PlacedColumn, flip_column
from fransys_layout.core.pack_sep import placed_cells
from fransys_layout.core.topology import build_column
from fransys_layout.core.values import Cell, Column, Lane, Options

from .pack_fixtures import elem


def _options() -> Options:
    return core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )


def _cell(sym: str = "U1", hold: int = 0) -> Cell:
    return Cell(sym, "R0", None, None, hold=hold)


def test_a_hold_moves_its_cell_and_the_cells_below_by_the_hold() -> None:
    """Three 32 G cells, wire_min 8: the hold on the second adds 24 to its gap and to the rest."""
    syms = {"U1": elem("U1")}
    plain = (_cell(), _cell(), _cell())
    held = (_cell(), _cell(hold=24), _cell())
    ys, height = stack_lane(syms, plain, _options(), frozenset())
    assert ys == (16, 56, 96)
    assert height == 112
    held_ys, held_height = stack_lane(syms, held, _options(), frozenset())
    assert held_ys == (16, 80, 120)
    assert held_ys[1] - ys[1] == 24
    assert held_ys[2] - ys[2] == 24
    assert held_height - height == 24


def test_a_hold_on_the_first_cell_changes_nothing() -> None:
    """Nothing stands above the first cell, so its hold is ignored."""
    syms = {"U1": elem("U1")}
    ys, height = stack_lane(syms, (_cell(hold=24), _cell(), _cell()), _options(), frozenset())
    assert ys == (16, 56, 96)
    assert height == 112


def test_build_column_height_grows_by_the_hold() -> None:
    """A column's height is its tallest lane's stack, so a hold in that lane adds to it."""
    syms = {"U1": elem("U1")}
    lane = Lane((_cell(), _cell(hold=24), _cell()), 0)
    column = build_column("c", (lane,), ((), ()), syms, _options())
    assert column.height == 136


def test_placed_cells_moves_a_cell_below_a_hold_by_the_hold() -> None:
    """The cell under the hold stands 24 lower than with no hold: its top goes from 40 to 64."""
    syms = {"U1": elem("U1")}
    options = _options()
    plain = PlacedColumn("c", ((_cell(), _cell()),), (0,), 0, flipped=False)
    held = PlacedColumn("c", ((_cell(), _cell(hold=24)),), (0,), 0, flipped=False)
    assert [c.top for c in placed_cells(plain, syms, frozenset(), options)] == [0, 40]
    assert [c.top for c in placed_cells(held, syms, frozenset(), options)] == [0, 64]


def test_a_cut_moves_up_to_the_held_cell_when_the_hold_pushes_it_past_room() -> None:
    """With room 80, the plain lane cuts at cell 2 (pieces 0 and 2); the hold on cell 1 pushes
    cell 1 past room, so the cut comes at cell 1 and the lane has one more piece."""
    syms = {"U1": elem("U1")}
    env = Tall(syms, _options(), 0, {}, frozenset(), {}, {}, {})
    plain = (_cell(), _cell(), _cell())
    held = (_cell(), _cell(hold=24), _cell())
    assert _cuts(plain, env, 80) == (0, 2, 3)
    assert _cuts(held, env, 80) == (0, 1, 3)


def test_flip_moves_each_hold_to_the_cell_above_it_and_the_first_cell_gets_none() -> None:
    """Holds [0, 24, 0] flip to [0, 0, 24]: the 24 G gap now sits above the cell that was top."""
    column = Column("c", (Lane((_cell(), _cell(hold=24), _cell()), 0),), (), (), 0, 0)
    flipped = flip_column(column, flip=True)
    assert flipped.flipped
    assert [c.hold for c in flipped.lanes[0]] == [0, 0, 24]
    assert [c.sym for c in flipped.lanes[0]] == ["U1", "U1", "U1"]
    assert flip_column(column, flip=False).lanes[0][1].hold == 24
