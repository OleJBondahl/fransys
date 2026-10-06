"""EF-A2 part 7: a group's columns stand in key order, but a pole-linked column follows its partner.

A column pole-linked to an earlier column of the same unit stands right after it, behind the
columns already attached to that partner (deep-dive D2). The order holds whatever the page
width, so every column here is narrow and one page holds them all.
"""

import dataclasses

import pytest
from samples import NO_HINTS, PROFILE, SHEET, column, hid

from fransys_layout.stages import ColumnWidth, GroupInfo, LocationInfo, Role, partition
from fransys_layout.stages.partition import GROUP_SPLIT, ColumnTables


def _col(name, number, *, group=1, role=Role.CONTROL):
    """Column `name` over function `number`, in `group` (None: no group), of `role`."""
    return dataclasses.replace(column(name, (number,), group=group), role=role)


def _plan(columns, links=(), *, width=100, content_width=None):
    """Partition `columns` given `links` (name pairs); returns the column names page by page."""
    sheet = (
        SHEET if content_width is None else dataclasses.replace(SHEET, content_width=content_width)
    )
    numbers = sorted({c.group.value for c in columns if c.group is not None})
    groups = tuple(
        GroupInfo(
            group=hid("aspect_node", int(value, 16)),
            key=("invented", f"group{int(value, 16)}"),
            label=f"G{int(value, 16)}",
            description=f"Invented group {int(value, 16)}",
        )
        for value in numbers
    )
    plans, findings = partition(
        tuple(columns),
        ColumnTables(
            widths=tuple(ColumnWidth(column=c.key, width=width) for c in columns),
            groups=groups,
            locations=(LocationInfo(location=hid("aspect_node", 100), label="C1"),),
            units=(),
            pole_links=tuple((("invented", x), ("invented", y)) for x, y in links),
        ),
        hints=NO_HINTS,
        profile=PROFILE,
        sheet=sheet,
    )
    return [[c.column[1] for c in plan.columns] for plan in plans], findings


def _abcde(**by_name):
    return [_col(name, number, **by_name) for number, name in enumerate("abcde", start=1)]


def test_no_links_keep_the_key_order() -> None:
    assert _plan(_abcde())[0] == [["a", "b", "c", "d", "e"]]


def test_a_column_stands_right_after_its_earlier_partner() -> None:
    assert _plan(_abcde(), [("a", "d")])[0] == [["a", "d", "b", "c", "e"]]


def test_a_column_whose_partner_comes_later_stays_put() -> None:
    """`b` keeps its place; `d`, the later column, moves, whichever way round the pair is."""
    assert _plan(_abcde(), [("b", "d")])[0] == [["a", "b", "d", "c", "e"]]
    assert _plan(_abcde(), [("d", "b")])[0] == [["a", "b", "d", "c", "e"]]


def test_a_second_column_of_one_partner_goes_behind_the_first() -> None:
    """`c` and `d` are both linked to `a`: `c` attaches first and `d` stands behind it."""
    assert _plan(_abcde(), [("a", "c"), ("a", "d")])[0] == [["a", "c", "d", "b", "e"]]


def test_a_column_linked_only_to_an_attached_column_follows_it() -> None:
    """`e` is linked to `c`, which sits after `a`: `e` stands after `c`, before `d` behind `a`."""
    plans = _plan(_abcde(), [("a", "c"), ("a", "d"), ("c", "e")])[0]
    assert plans == [["a", "c", "e", "d", "b"]]


def test_a_column_with_two_placed_partners_follows_the_earliest_placed() -> None:
    """`d` is linked to `b` and to `a`: the earliest placed is `a`, so it stands after `a`."""
    assert _plan(_abcde(), [("b", "d"), ("a", "d")])[0] == [["a", "d", "b", "c", "e"]]


def test_a_cycle_of_links_ends_and_orders_by_the_rule() -> None:
    assert _plan(_abcde(), [("a", "b"), ("b", "c"), ("a", "c")])[0] == [["a", "b", "c", "d", "e"]]
    assert _plan(_abcde(), [("a", "c"), ("c", "e"), ("a", "e")])[0] == [["a", "c", "e", "b", "d"]]


def test_a_link_between_two_groups_reorders_nothing() -> None:
    """Group 1 holds `a`, `b`, `c`; group 2 holds `d`, `e`. Links across them leave both alone."""
    columns = [
        _col("a", 1),
        _col("b", 2),
        _col("c", 3),
        _col("d", 4, group=2),
        _col("e", 5, group=2),
    ]
    assert _plan(columns, [("a", "e"), ("c", "d")])[0] == [["a", "b", "c", "d", "e"]]
    assert _plan(columns, [("a", "c"), ("d", "e")])[0] == [["a", "c", "b", "d", "e"]]


def test_a_link_between_two_roles_of_one_group_reorders_nothing() -> None:
    """The group's `POWER` unit holds `a`, `c`, `d` and its `CONTROL` unit `b`; one unit each."""
    columns = [
        _col("a", 1, role=Role.POWER),
        _col("b", 2),
        _col("c", 3, role=Role.POWER),
        _col("d", 4, role=Role.POWER),
    ]
    assert _plan(columns, [("b", "d")])[0] == [["a", "c", "d", "b"]]
    assert _plan(columns, [("a", "d")])[0] == [["a", "d", "c", "b"]]


def test_columns_with_no_group_are_never_reordered() -> None:
    """`x`, `y`, `z` are three units: a link between them moves none, the group's own link does."""
    columns = [_col("a", 1), _col("b", 2), _col("c", 3)]
    loose = [_col("x", 4, group=None), _col("y", 5, group=None), _col("z", 6, group=None)]
    assert _plan(columns + loose, [("a", "c"), ("x", "z")])[0] == [["a", "c", "b", "x", "y", "z"]]


def test_the_order_does_not_depend_on_the_order_of_the_pairs() -> None:
    links = [("a", "c"), ("a", "d"), ("c", "e"), ("b", "e")]
    expected = _plan(_abcde(), links)[0]
    assert expected == [["a", "c", "e", "d", "b"]]
    assert _plan(_abcde(), links[::-1])[0] == expected
    assert _plan(_abcde(), [links[2], links[0], links[3], links[1]])[0] == expected
    assert _plan(_abcde(), [(y, x) for x, y in links])[0] == expected


def test_the_order_is_the_same_at_every_width_and_a_split_follows_it() -> None:
    """Link `a`-`d` puts `d` after `a` on a wide page, and the narrow page cuts the same order."""
    wide = _plan(_abcde(), [("a", "d")])[0]
    narrow, findings = _plan(_abcde(), [("a", "d")], content_width=350)
    assert wide == [["a", "d", "b", "c", "e"]]
    assert narrow == [["a", "d", "b"], ["c", "e"]]
    assert [f.code for f in findings] == [GROUP_SPLIT]


@pytest.mark.parametrize("links", [[("a", "d")], [("a", "c"), ("c", "e")]])
def test_the_result_is_deterministic(links) -> None:
    assert _plan(_abcde(), links) == _plan(_abcde(), links)
