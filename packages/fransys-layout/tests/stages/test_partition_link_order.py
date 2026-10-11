"""A group's columns stand in key order, but a pole-linked column follows its partner.

A column pole-linked to an earlier column of the same unit stands right after it, behind the
columns already attached to that partner. The order holds whatever the page
width, so every column here is narrow and one page holds them all.
"""

import dataclasses

from samples import NO_HINTS, PROFILE, SHEET, column, hid

from fransys_layout.stages import ColumnWidth, GroupInfo, LocationInfo, Role, partition
from fransys_layout.stages.partition import ColumnTables


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


def test_a_cycle_of_links_ends_and_orders_by_the_rule() -> None:
    assert _plan(_abcde(), [("a", "b"), ("b", "c"), ("a", "c")])[0] == [["a", "b", "c", "d", "e"]]
    assert _plan(_abcde(), [("a", "c"), ("c", "e"), ("a", "e")])[0] == [["a", "c", "e", "b", "d"]]


def test_columns_with_no_group_are_never_reordered() -> None:
    """`x`, `y`, `z` are three units: a link between them moves none, the group's own link does."""
    columns = [_col("a", 1), _col("b", 2), _col("c", 3)]
    loose = [_col("x", 4, group=None), _col("y", 5, group=None), _col("z", 6, group=None)]
    assert _plan(columns + loose, [("a", "c"), ("x", "z")])[0] == [["a", "c", "b", "x", "y", "z"]]


def test_a_column_stands_right_after_its_earlier_partner() -> None:
    assert _plan(_abcde(), [("a", "d")])[0] == [["a", "d", "b", "c", "e"]]
