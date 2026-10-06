"""S13 (decision layout-0090): `_stack_attachments` stacks a changeover's two throws as two rows.

Hand-made cells and attachments, no model and no engine. Functions 1 and 2 are the poles of one
host row; each pole's break throw hangs a terminal in the attachment row nearest it (row 0 of
its `_Attachment`) and its make throw one in the second (row 1), all below the poles (S). The
break throw's port stands left of the make throw's, as on the change-over-contact symbol.

Can-fail probe (one Edit, run, undone): `_attached_rows` putting every attachment in one row
(today's shared row, one lane each) fails the first two tests.
"""

from typing import TYPE_CHECKING

from samples import hid

from fransys_layout.stages.chains import _stack_attachments
from fransys_layout.stages.types import Cell

if TYPE_CHECKING:
    from fransys_layout.stages.chains import _Attachment
    from fransys_layout.stages.types import Handle

_BREAK_X, _MAKE_X = -16, 0


def _throws(pole: int) -> list[_Attachment]:
    """Pole `pole`'s throw attachments: break terminal `10 + pole`, make terminal `20 + pole`."""
    return [
        (0, _BREAK_X, ("x02", str(pole)), hid("function", 10 + pole), "nc", False),
        (1, _MAKE_X, ("x01", str(pole)), hid("function", 20 + pole), "no", False),
    ]


def test_the_two_throws_of_one_pole_stand_in_two_rows() -> None:
    """The break throw's terminal is row 1 under the pole, the make throw's row 2, one lane each."""
    pole = hid("function", 1)
    cells = _stack_attachments([Cell(function=pole, index=0)], {(pole, "s"): _throws(1)})
    assert cells == [
        Cell(function=pole, index=0),
        Cell(function=hid("function", 11), index=1, lane=0, host=pole, port="nc"),
        Cell(function=hid("function", 21), index=2, lane=0, host=pole, port="no"),
    ]


def test_two_poles_throws_share_their_rows_each_in_its_poles_lane() -> None:
    """Both break throws form row 1 and both make throws row 2, each in its pole's lane."""
    one, two = hid("function", 1), hid("function", 2)
    host_row = [Cell(function=one, index=0), Cell(function=two, index=0, lane=1)]
    found: dict[tuple[Handle, str], list[_Attachment]] = {
        (one, "s"): _throws(1),
        (two, "s"): _throws(2),
    }
    rows = {}
    for cell in _stack_attachments(host_row, found):
        rows.setdefault(cell.index, []).append((cell.function, cell.lane))
    assert rows == {
        0: [(one, 0), (two, 1)],
        1: [(hid("function", 11), 0), (hid("function", 12), 1)],
        2: [(hid("function", 21), 0), (hid("function", 22), 1)],
    }


def test_attachments_in_one_row_share_it_one_lane_each_in_port_x_order() -> None:
    """R7.1 unchanged: two attachments that are not a changeover's detached throw share a row."""
    host = hid("function", 1)
    found: dict[tuple[Handle, str], list[_Attachment]] = {
        (host, "s"): [
            (0, 8, ("x", "2"), hid("function", 32), "b", False),
            (0, -8, ("x", "1"), hid("function", 31), "a", True),
        ]
    }
    cells = _stack_attachments([Cell(function=host, index=0)], found)
    assert cells == [
        Cell(function=host, index=0),
        Cell(function=hid("function", 31), index=1, lane=0, flip=True, host=host, port="a"),
        Cell(function=hid("function", 32), index=1, lane=1, host=host, port="b"),
    ]
