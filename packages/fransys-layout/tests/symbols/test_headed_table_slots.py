"""The headed fitted table keeps today's heading and title lines (es-0075).

The old engine's `table_geometry(rows, 8, 2, headed=True)` puts the heading centre 4 G below the
table top and the NO/NC titles' centre 14 G below it, whatever the row count.
"""

import pytest
from symdef import from_divisions, keepout_box

from electrical_symbols import LIBRARY
from fransys_layout.symbols import TableAsk, library_symbol
from fransys_layout.symbols.table import placed_table

CELLS = {"no": "13 /1.1", "nc": "21 /1.1"}


def _g(value: float) -> float:
    return value / from_divisions(LIBRARY.grid, 1)


def _lines(rows: int) -> dict[str, float]:
    ask = TableAsk(
        library_symbol(LIBRARY, "contact-row"),
        library_symbol(LIBRARY, "contact-head-headed"),
        [CELLS] * rows,
        (0, 0),
        "-K1",
    )
    made = placed_table(ask, LIBRARY, 8)
    top = keepout_box(made).min.y
    return {s.id: _g(s.position.y - top) for s in made.slots}


@pytest.mark.parametrize("rows", range(1, 8))
def test_the_heading_and_the_titles_sit_where_todays_headed_table_has_them(rows: int) -> None:
    slots = _lines(rows)
    assert slots["heading"] == 4
    assert slots["no"] == slots["nc"] == 14
