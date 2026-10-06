"""UNIT-ID acceptance 7: the board set's child designations and KiCad netlist do not move.

UNIT-ID only stops the board's own root tag from printing on the board's own set (I4); it changes
neither `item_designation` nor `printed_designation`, and `board_netlist` keeps its path. Proven on
the units worked example (the same board the units spec built): the children print unit-relative
exactly as at v0.3.0 (`-X1`, `-K1`; the values below are the v0.3.0 ones, measured by
building `_build_system()` at base commit `73fd159`, before UNIT-ID, and equal on this branch),
the root still prints `-U1`
everywhere but the board's own BOM and designation rows, and the board's KiCad netlist is the text
`test_units_worked_example.py::test_step_4b_the_kicad_netlist_of_the_board_is_board_relative`
already pins verbatim.
"""

import sys
from pathlib import Path

# `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _build_system

from fransys_model.derive import (
    bom_lines,
    designation_list,
    is_own_unit_root,
    printed_designation,
)
from fransys_model.vocab.tables import items as items_of


def _board_unit(model):
    by_key = {item.key: item for item in items_of(model).values()}
    board = by_key[("pump1", "io", "board")]
    assert board.unit is not None
    return board, board.unit, by_key


def test_the_boards_children_print_as_before_and_only_the_root_rows_move():
    model = _build_system()[0].model
    board, unit, by_key = _board_unit(model)
    k1 = by_key[("pump1", "io", "k1")]
    x1 = by_key[("pump1", "io", "X1")]

    # Unchanged text functions: children unit-relative, the root still `-U1` (v0.3.0 values).
    assert printed_designation(model, k1.id, unit=unit) == "-K1"
    assert printed_designation(model, x1.id, unit=unit) == "-X1"
    assert printed_designation(model, board.id) == "-U1"
    assert printed_designation(model, board.id, unit=unit) == "-U1"

    # The new rule sits only in the list sites: the board's own designation rows keep its
    # children and drop the root; the whole-model rows keep the root.
    own_rows = {row.designation for row in designation_list(model, unit=unit)}
    assert own_rows == {"-K1", "-X1"}
    assert "-U1" in {row.designation for row in designation_list(model)}

    # The predicate holds for the root of this unit and for nothing else of it.
    assert is_own_unit_root(model, board.id, unit)
    assert not is_own_unit_root(model, k1.id, unit)
    assert not is_own_unit_root(model, board.id, None)

    # Its own BOM keeps the relay line with the child's unit-relative cell.
    cells = {line.mpn: line.designations for line in bom_lines(model, unit)}
    assert cells["DEMO-RLY-2CO-24"] == ("-K1",)
