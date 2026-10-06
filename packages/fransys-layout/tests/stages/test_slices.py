"""D10: the page slices: which functions a page draws, and one pass that cuts a run into pages."""

from operator import attrgetter, itemgetter

from samples import column, drawn, hid, page_plan, placed

from fransys_layout.stages.slices import (
    by_ends,
    by_key,
    by_page,
    by_plan,
    page_columns,
    page_of,
    pages_of,
    rooms_by_page,
)

_FUNCTION = attrgetter("function")


def _f(number: int):
    return hid("function", number)


def test_a_slice_keeps_the_original_order_of_its_items() -> None:
    """The items 3, 1, 2 come out 3, 1, 2 (handle order would be 1, 2, 3)."""
    # UNDO: stages/slices.py:_per_page, `grouped.get(page, ())`
    #     -> `sorted(grouped.get(page, ()), key=lambda pair: pair[1].function)`
    #     (a slice is sorted by function)
    items = (drawn(3), drawn(1), drawn(2))
    pages = {_f(1): (0,), _f(2): (0,), _f(3): (0,)}

    (only,) = by_page(items, _FUNCTION, pages, 1)

    assert [one.function for one in only] == [_f(3), _f(1), _f(2)]


def test_a_function_on_two_pages_is_in_both_slices_and_a_function_on_none_in_no_slice() -> None:
    """Function 2 stands on pages 0 and 1; 5 is in a column no page names, 6 in no column."""
    # UNDO: stages/slices.py:by_page, `pages.get(key(item), ())` -> `pages.get(key(item), ())[:1]`
    #     (an item goes into its first page only)
    plans = (page_plan(("a",), number=1), page_plan(("b",), number=2))
    columns = (column("a", (3, 1, 2)), column("b", (2, 4)), column("c", (5,)))
    items = tuple(drawn(n) for n in (3, 1, 2, 4, 5, 6))

    on_page = pages_of(page_columns(plans, columns))
    first, second = by_page(items, _FUNCTION, on_page, len(plans))

    assert [one.function for one in first] == [_f(3), _f(1), _f(2)]
    assert [one.function for one in second] == [_f(2), _f(4)]


def test_pages_of_follows_the_plans_columns_not_a_functions_home_page() -> None:
    """A column no plan names (the replica drop removed it) puts its functions on no page."""
    # UNDO: stages/slices.py:page_columns, the return -> `tuple(columns for _ in plans)`
    #     (every page takes every column)
    plans = (page_plan(("a",), number=1), page_plan(("b",), number=2))
    columns = (column("a", (1,)), column("b", (2,)), column("dropped", (1, 3)))

    on_page = pages_of(page_columns(plans, columns))

    assert on_page == {_f(1): (0,), _f(2): (1,)}


def test_page_columns_are_in_the_plans_order_and_skip_a_key_no_column_carries() -> None:
    # UNDO 1: stages/slices.py:page_columns, drop ` if one.column in by_key` (a missing key raises)
    # UNDO 2: stages/slices.py:page_columns, `for one in plan.columns`
    #     -> `for one in sorted(plan.columns, key=lambda one: one.column)` (the plan's order lost)
    plans = (page_plan(("b", "missing", "a")),)
    columns = (column("a", (1,)), column("b", (2,)))

    (only,) = page_columns(plans, columns)

    assert [one.key for one in only] == [("invented", "b"), ("invented", "a")]


def test_a_page_gets_the_rooms_of_the_columns_its_plan_names_only() -> None:
    """Room keys are `(column key, function)`: a column on two pages gives its rooms to both."""
    # UNDO: stages/slices.py:rooms_by_page, `key[0]` -> `key[1]` (the function for the column)
    plans = (page_plan(("a", "b"), number=1), page_plan(("b",), number=2))
    a, b, c = ("invented", "a"), ("invented", "b"), ("invented", "c")
    rooms = {(a, _f(1)): (8, 0), (b, _f(2)): (0, 4), (c, _f(3)): (1, 1)}

    first, second = rooms_by_page(rooms, plans)

    assert first == {(a, _f(1)): (8, 0), (b, _f(2)): (0, 4)}
    assert second == {(b, _f(2)): (0, 4)}


def test_a_connection_is_on_the_pages_that_hold_both_its_ends_in_original_order() -> None:
    """Function 2 stands on both pages: a conductor from 2 to 2 is on both, 1 to 3 on none."""
    # UNDO: stages/slices.py:_pages_with, `set.intersection(*found) if every else set.union(*found)`
    #     -> `set.union(*found)` (a connection with one end on the page is on it)
    plans = (page_plan(("a",), number=1), page_plan(("b",), number=2))
    columns = (column("a", (1, 2)), column("b", (2, 3)))
    on_page = pages_of(page_columns(plans, columns))
    ends = {"x": (_f(1), _f(2)), "y": (_f(2), _f(3)), "z": (_f(2), _f(2)), "w": (_f(1), _f(3))}

    first, second = by_ends(("y", "w", "x", "z"), ends.__getitem__, on_page, count=2, every=True)

    assert first == ("x", "z")
    assert second == ("y", "z")


def test_a_net_group_is_on_every_page_that_holds_one_of_its_ports() -> None:
    """Ends 4 and 1: function 1 is on page 0 only, 4 on page 1 only, so the group is on both."""
    # UNDO: stages/slices.py:_pages_with, `set.intersection(*found) if every else set.union(*found)`
    #     -> `set.intersection(*found)` (a net group needs all its ports on the page)
    plans = (page_plan(("a",), number=1), page_plan(("b",), number=2))
    columns = (column("a", (1, 3)), column("b", (2, 4)))
    on_page = pages_of(page_columns(plans, columns))
    groups = {"g": (_f(4), _f(1)), "h": (_f(3),), "none": (_f(9),), "empty": ()}

    first, second = by_ends(groups, groups.__getitem__, on_page, count=2, every=False)

    assert first == ("g", "h")
    assert second == ("g",)


def test_a_marker_is_in_the_slice_of_the_plan_with_its_drawing_set_and_number() -> None:
    """A key no plan has is in no slice; a slice keeps the original order."""
    # UNDO: stages/slices.py:by_plan, `(plan.drawing_set, plan.number)` -> `(plan.drawing_set, 1)`
    #     (every page of the set is page 1)
    plans = (page_plan(("a",), number=1), page_plan(("b",), number=2))
    items = ((1, 2), (1, 1), (7, 1), (1, 2))

    first, second = by_plan(items, itemgetter(0, 1), plans)

    assert first == ((1, 1),)
    assert second == ((1, 2), (1, 2))


def test_the_one_grouping_keeps_each_groups_order_and_page_of_names_the_drawing_set_and_page() -> (
    None
):
    """Items 3, 1, 2 grouped by parity come out 3, 1 and 2; `page_of` reads set and page."""
    # UNDO: stages/slices.py:by_key, `tuple(group)` -> `tuple(sorted(group))`
    #     (a group is sorted)
    grouped = by_key((3, 1, 2), lambda number: number % 2)

    assert grouped == {1: (3, 1), 0: (2,)}
    assert page_of(placed(1, x=0, y=0, page=5)) == (1, 5)


def test_a_function_in_two_columns_of_one_page_is_on_that_page_once() -> None:
    # UNDO: stages/slices.py:pages_of, `if not pages or pages[-1] != page:` -> `if True:`
    #     (the page is appended once per cell)
    plans = (page_plan(("a", "b")),)
    columns = (column("a", (1, 2)), column("b", (2, 3)))
    items = (drawn(2),)

    on_page = pages_of(page_columns(plans, columns))
    (only,) = by_page(items, _FUNCTION, on_page, 1)

    assert on_page[_f(2)] == (0,)
    assert [one.function for one in only] == [_f(2)]
