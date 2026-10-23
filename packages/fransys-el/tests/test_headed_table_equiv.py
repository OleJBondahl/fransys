"""CONTACT-HEAD-HEADED step 0: the headed fitted table is today's headed table (es-0075).

Today's engine draws a table that shares its foot with a heading line over the NO/NC titles,
`table_geometry(rows, step, pad, headed=True)`. The layer's `placed_table` with a heading must give
that total height, that heading line and those titles, at every row count the models' coils have.
The width is the fitted rule; a heading wider than the NO column widens it (Q3, accepted).
"""

import pytest
from conventions_fixtures import house
from fransys_el.placement_env import make_env
from fransys_el.placement_syms import heading_of
from placement_fixtures import demo_model, kit_for, leads, planted_model
from symdef_layer_equivalence import tables

from electrical_symbols import LIBRARY
from fransys_layout.symbols import Ask, TableAsk, library_symbol, symbol_shape, symbol_views
from fransys_model.derive import function_item, item_unit
from fransys_model.derive.contact_rows import table_geometry
from fransys_model.derive.drawing_text import coil_heading

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


def test_the_heading_of_a_coil_is_the_derive_heading_in_its_own_unit() -> None:
    """A coil in a unit reads `coil_heading` in that unit, never the bare tag (model-0238)."""
    model = planted_model()
    env = make_env(model, kit_for(model), house(), LIBRARY)
    seen = set()
    for lead in leads(env.kit):
        item = function_item(model, lead)
        unit = item_unit(model, item)
        assert heading_of(env, lead) == coil_heading(model, item, unit=unit)
        seen.add(unit is not None and coil_heading(model, item) != heading_of(env, lead))
    assert True in seen
