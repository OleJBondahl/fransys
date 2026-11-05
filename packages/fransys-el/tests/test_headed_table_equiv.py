"""CONTACT-HEAD-HEADED step 0: the headed fitted table is today's headed table (es-0075).

Today's engine draws a table that shares its foot with a heading line over the NO/NC titles,
`table_geometry(rows, step, pad, headed=True)`. The layer's `placed_table` with a heading must give
"""
# NET_POTENTIAL_CONFLICT 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# WIRE_ROW_UNRESOLVED 6 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

import pytest
from placement_fixtures import demo_model, kit_for, planted_model
from symdef_layer_equivalence import tables

from electrical_symbols import LIBRARY
from fransys_layout.symbols import Ask, TableAsk, library_symbol, symbol_shape, symbol_views
from fransys_model.derive.contact_rows import table_geometry

STEP, PAD = 8, 2
CELLS = {"no": "13 /1.1", "nc": "21 /1.1"}


def _height(rows: int, heading: str) -> int:
    """The table's total height in G, read from the views of a coil carrying it."""
    ask = TableAsk(
        library_symbol(LIBRARY, "contact-row"),
        library_symbol(LIBRARY, "contact-head-headed"),
        [CELLS] * rows,
        (0, 0),
        heading,
    )
    coil = library_symbol(LIBRARY, "coil")
    order = list(symbol_shape(coil, LIBRARY).pins)
    views = symbol_views(coil, LIBRARY, Ask(("R0",), order, "tag", "K1", STEP, ask))
    assert views.table is not None
    return views.table.h


@pytest.mark.parametrize("rows", range(1, 8))
def test_the_headed_table_is_as_high_where_todays_table_is(rows: int) -> None:
    """The heading and title lines are checked in the layout package's own tests."""
    assert _height(rows, "-K1") == table_geometry(rows, STEP, PAD, headed=True).height


@pytest.mark.parametrize("make", [demo_model, planted_model])
def test_the_headed_table_matches_at_the_row_count_of_every_coil(make) -> None:
    model = make()
    base = table_geometry(0, STEP, PAD, headed=False).height
    found = {(t.h - base) // STEP for t in tables(model, kit_for(model)).values()}
    assert found
    for rows in found:
        assert _height(rows, "-K1") == table_geometry(rows, STEP, PAD, headed=True).height
