"""TABLE-T2 step 0: the fitted contact table is today's drawn table (Ruling 30.2, T2-2).

Today's engine draws one table per coil, `table_geometry(rows).height` high (titles, rule, rows,
closing pad). The layer's `symdef.fitted_table` must give that height and the old width, at R0
and the half turn. The accepted differences (an NC column starting after the widest NO text, an
empty NC column 2 G wide) move a column inside the table, never its height.
"""

import pytest
from conventions_fixtures import house
from placement_fixtures import demo_model, kit_for, planted_model
from symdef_layer_equivalence import pairs, tables

from electrical_symbols import LIBRARY
from fransys_model.derive.contact_rows import table_geometry

STEP, PAD = 8, 2


@pytest.mark.parametrize("make", [demo_model, planted_model])
def test_the_fitted_table_is_as_high_as_todays_table_at_every_view(make) -> None:
    model = make()
    held = tables(model, kit_for(model))
    found = [(old, new) for old, new in pairs(model, kit_for(model)) if new.id in held]
    assert found
    base = table_geometry(0, STEP, PAD, headed=False).height
    for old, new in found:
        table = held[new.id]
        rows, left = divmod(table.h - base, STEP)
        assert left == 0
        assert rows >= 1
        assert table.h == table_geometry(rows, STEP, PAD, headed=False).height
        assert old.table is not None
        assert old.table.h == table.h


def test_the_library_body_text_is_the_house_text_room() -> None:
    """The layer sets the table at `Conventions.text_height` G; that is the library's `body`."""
    grid, font = LIBRARY.grid, LIBRARY.font
    assert font is not None
    body_g = font.heights["body"] / grid.module_mm * grid.divisions_per_module
    assert body_g == house().text_height == STEP


def test_a_coil_with_a_table_is_offered_no_quarter_turn_and_one_without_has_no_table() -> None:
    model = planted_model()
    found = pairs(model, kit_for(model))
    held = tables(model, kit_for(model))
    tabled = [new for _, new in found if new.id in held]
    plain = [new for _, new in found if new.id not in held]
    assert tabled
    assert plain
    assert all(set(new.views) <= {"R0", "R180", "MR180"} for new in tabled)
