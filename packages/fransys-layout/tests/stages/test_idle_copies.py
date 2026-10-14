"""`without_idle_copies` (layout-0216): a copy no wire needs on its page goes.

Function 5 is the terminal; its wire runs to function 1. Columns are the samples' `column`.
"""

from dataclasses import replace

from samples import column, hid, page_plan

from fransys_layout.stages.idle_copies import without_idle_copies

f1, f5, f9 = hid("function", 1), hid("function", 5), hid("function", 9)


def test_a_copy_whose_wire_is_drawn_on_another_page_goes_with_its_page() -> None:
    """Terminal 5 alone on page 1, its wire drawn on page 2 beside device 1: page 1 empties."""
    home, there = column("t", (5,)), column("d", (1, 5))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    new_plans, columns = without_idle_copies(plans, (home, there), [(f5, f1)])

    assert columns == (there,)
    assert [(plan.number, plan.columns) for plan in new_plans] == [(1, plans[1].columns)]


def test_a_copy_whose_wire_is_drawn_nowhere_stays() -> None:
    """Device 1 stands on page 2 with no copy of 5: the wire still needs page 1's copy."""
    home, there = column("t", (5,)), column("d", (1,))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    assert without_idle_copies(plans, (home, there), [(f5, f1)]) == (plans, (home, there))


def test_a_copy_beside_a_far_end_stays() -> None:
    """Terminal 5 on page 1 beside device 9 it wires keeps that copy, though wire 5-1 is drawn
    on page 2."""
    home, there = column("t", (5, 9)), column("d", (1, 5))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    result = without_idle_copies(plans, (home, there), [(f5, f1), (f5, f9)])

    assert result == (plans, (home, there))


def test_a_function_outside_links_is_never_dropped() -> None:
    """Terminal 5 with no links (the caller keeps it whole) stays on its idle page."""
    home, there = column("t", (5,)), column("d", (1, 5))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    assert without_idle_copies(plans, (home, there), []) == (plans, (home, there))


def test_a_column_that_keeps_a_cell_stays_on_its_page() -> None:
    """Terminal 5 leaves page 1, device 9 beside it stays: the column and page keep their place."""
    home, there = column("t", (5, 9)), column("d", (1, 5))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    new_plans, columns = without_idle_copies(plans, (home, there), [(f5, f1)])

    assert columns == (replace(home, cells=home.cells[1:]), there)
    assert new_plans == plans


def test_a_copy_a_cell_is_attached_to_stays() -> None:
    """Device 9 hangs at idle terminal 5 on page 1: the copy it is attached to stays."""
    home, there = column("t", (5, 9)), column("d", (1, 5))
    home = replace(home, cells=(home.cells[0], replace(home.cells[1], host=f5)))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    assert without_idle_copies(plans, (home, there), [(f5, f1)]) == (plans, (home, there))


def test_a_wire_drawn_only_in_another_set_keeps_the_copy() -> None:
    """Wire 5-1 has both ends only on a page of set 2: set 1's lone copy of 5 stays."""
    home, there = column("t", (5,)), column("d", (1, 5))
    plans = (page_plan(("t",), number=1), replace(page_plan(("d",), number=1), drawing_set=2))

    assert without_idle_copies(plans, (home, there), [(f5, f1)]) == (plans, (home, there))
