"""layout-0107: `attach_feeders`, a feeder box takes the row above its fed box (hand values).

Box 1 is the fed one, boxes 2 and 3 its feeders, built by `test_box_pairing._pair`.
"""

from dataclasses import replace

from pairing_fixture import pair
from samples import column, hid

from fransys_layout.stages.attach import attach_feeders
from fransys_layout.stages.types import Cell


def _cell(number: int, index: int, lane: int = 0, **hosted) -> Cell:
    return Cell(function=hid("function", number), index=index, lane=lane, **hosted)


def test_attach_feeders_puts_each_feeder_above_its_fed_box_and_drops_its_column() -> None:
    """Feeders 2 and 3 take row 0 of box 1's column, left to right by the fed pin they sit over."""
    # UNDO: stages/attach.py:attach_feeders, `drop.add(column.key)` -> `drop.add(())`
    #     (the feeders' own columns stay)
    boxes = pair()
    home = column("fed", (1,))
    result = attach_feeders((home, column("t2", (2,)), column("t3", (3,))), boxes)
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
    assert attach_feeders((home, other), boxes) == (home, other)
