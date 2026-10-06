"""layout-0107: `attach_feeders`, a feeder box takes the row above its fed box (hand values).

Box 1 is the fed one, boxes 2 and 3 its feeders, built by `test_box_pairing._pair`.
"""

from dataclasses import replace

from pairing_fixture import pair
from samples import column, hid

from fransys_layout.stages.attach import attach_feeders
from fransys_layout.stages.types import Cell, Column


def _fits(_: Column) -> bool:
    return True


def _cell(number: int, index: int, lane: int = 0, **hosted) -> Cell:
    return Cell(function=hid("function", number), index=index, lane=lane, **hosted)


def test_attach_feeders_puts_each_feeder_above_its_fed_box_and_drops_its_column() -> None:
    """Feeders 2 and 3 take row 0 of box 1's column, left to right by the fed pin they sit over."""
    # UNDO: stages/attach.py:attach_feeders, `drop.update(keys[e[3]] for e in entries)` -> `drop`
    #     (the feeders' own columns stay)
    boxes = pair()
    home = column("fed", (1,))
    result = attach_feeders((home, column("t2", (2,)), column("t3", (3,))), boxes, _fits)
    hosted = {"host": hid("function", 1), "replica": False}
    assert result == (
        replace(
            home,
            cells=(
                _cell(2, 0, 0, port="a1", **hosted),
                _cell(3, 0, 1, port="b1", **hosted),
                _cell(1, 1),
            ),
        ),
    )


def test_a_feeder_in_another_group_is_not_attached() -> None:
    """Box 2's column belongs to another group: it keeps its own column."""
    boxes = pair()
    home, other = column("fed", (1,)), column("t2", (2,), group=9)
    assert attach_feeders((home, other), boxes, _fits) == (home, other)


def test_a_feeder_at_the_bottom_of_its_column_takes_its_column_along() -> None:
    """layout-0122: chains of different height stand above their feeders, bottom-aligned.

    Feeder 2 has cells 7 and 8 above it, feeder 3 has cell 9: row 0 holds 7 alone, row 1 holds 8
    and 9 side by side, the feeders follow in row 2 and the fed box in row 3.
    """
    # UNDO: stages/attach.py:attach_feeders, `chain_of(column.cells)` -> `()` (the chain is left
    #     behind and its column dropped with it)
    boxes = pair()
    home = column("fed", (1,))
    result = attach_feeders((home, column("t2", (7, 8, 2)), column("t3", (9, 3))), boxes, _fits)
    hosted = {"host": hid("function", 1), "replica": False}
    assert result == (
        replace(
            home,
            cells=(
                _cell(7, 0, 0),
                _cell(8, 1, 0),
                _cell(9, 1, 1),
                _cell(2, 2, 0, port="a1", **hosted),
                _cell(3, 2, 1, port="b1", **hosted),
                _cell(1, 3),
            ),
        ),
    )


def test_a_feeder_with_another_cell_in_its_row_keeps_its_own_column() -> None:
    """layout-0122: the feeder must be alone in the last row of its column to attach."""
    # UNDO: stages/feeder_chains.py:chain_of, `len(bottom) == 1` -> `True`
    boxes = pair()
    home = column("fed", (1,))
    held = replace(
        column("t2", (7, 8, 2)),
        cells=(_cell(7, 0), _cell(8, 1, 0), _cell(2, 1, 1)),
    )
    assert attach_feeders((home, held), boxes, _fits) == (home, held)


def test_a_chained_feeder_whose_column_does_not_fit_the_page_keeps_its_own_column() -> None:
    """layout-0122: markers stay where the stacked column would pass the page height."""
    # UNDO: stages/attach.py:attach_feeders, `if not fits(attached):` -> `if False:`
    boxes = pair()
    home, chained, plain = column("fed", (1,)), column("t2", (7, 2)), column("t3", (3,))
    result = attach_feeders(
        (home, chained, plain), boxes, lambda c: len({x.index for x in c.cells}) < 3
    )
    hosted = {"host": hid("function", 1), "replica": False}
    assert result == (
        replace(home, cells=(_cell(3, 0, 0, port="b1", **hosted), _cell(1, 1))),
        chained,
    )
