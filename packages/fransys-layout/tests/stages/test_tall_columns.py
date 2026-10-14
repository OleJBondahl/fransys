"""LC1 (layout-0215): the row extents and the held row pairs that a cut of a tall column reads.

`row_extents` gives each placed row its top and bottom over its cells' keep-outs; `held_rows`
gives the row pairs a cut must not part: an attachment's row and its host's.
"""

from dataclasses import replace

from samples import column, hid

from fransys_layout.geometry import Box
from fransys_layout.stages.tall_columns import held_rows, row_extents
from fransys_layout.stages.types import Cell


def test_row_extents_spans_each_row_over_its_cells() -> None:
    tall = column("tall", (1, 2, 3, 4))
    tall = replace(
        tall,
        cells=(
            Cell(function=hid("function", 1), index=0),
            Cell(function=hid("function", 2), index=0),
            Cell(function=hid("function", 3), index=1),
            Cell(function=hid("function", 4), index=2),
        ),
    )
    boxes = {
        (tall.key, hid("function", 1)): [Box(x=0, y=10, width=5, height=20)],
        (tall.key, hid("function", 2)): [Box(x=6, y=5, width=5, height=10)],
        (tall.key, hid("function", 3)): [Box(x=0, y=40, width=5, height=8)],
        (("invented", "other"), hid("function", 4)): [Box(x=0, y=0, width=5, height=99)],
    }
    # Row 0 spans both of its cells (top 5, bottom 30); row 2 has no box, so it is absent.
    assert row_extents(tall, boxes) == {0: (5, 30), 1: (40, 48)}


def test_held_rows_pairs_an_attachment_with_its_host_on_another_row() -> None:
    tall = column("tall", (1, 2, 3, 4, 5))
    tall = replace(
        tall,
        cells=(
            Cell(function=hid("function", 1), index=0),
            Cell(function=hid("function", 2), index=1, host=hid("function", 1)),
            Cell(function=hid("function", 3), index=0, host=hid("function", 1)),
            Cell(function=hid("function", 4), index=2, host=hid("function", 9)),
            Cell(function=hid("function", 5), index=2),
        ),
    )
    # Function 3 shares its host's row, and function 4's host is not in this column.
    assert held_rows(tall) == ((0, 1),)
