"""EF-A2 part 3: roles may share a page (deep-dive D4), at the stage level.

Inside one drawing set the groups are ordered role first and then packed continuously, so a
group of another role joins the page when it fits. A page's role is its first unit's role.
"""

import dataclasses

import pytest
from samples import NO_HINTS, PROFILE, SHEET, column, hid

from fransys_layout.geometry import HintError
from fransys_layout.stages import (
    ColumnWidth,
    GroupInfo,
    GroupSet,
    LocationInfo,
    OrderHint,
    PageHints,
    Role,
    partition,
)
from fransys_layout.stages.partition import (
    GROUP_SPLIT,
    KEEP_TOGETHER_UNMET,
    ORDER_HINT_UNMET,
    ColumnTables,
)

_LOCATIONS = (
    LocationInfo(location=hid("aspect_node", 100), label="C1"),
    LocationInfo(location=hid("aspect_node", 101), label="C2"),
)


def _group(number: int) -> GroupInfo:
    return GroupInfo(
        group=hid("aspect_node", number),
        key=("invented", f"group{number}"),
        label=f"G{number}",
        description=f"Invented group {number}",
    )


def _col(name, number, *, group=1, role=Role.CONTROL, location=100):
    """Column `name` over function `number`, in `group`, of `role`, at `location`."""
    return dataclasses.replace(
        column(name, (number,), group=group), role=role, location=hid("aspect_node", location)
    )


def _plan(columns, widths, hints=NO_HINTS):
    """Partition `columns` (name -> width in `widths`) with one invented group per number used."""
    numbers = sorted({c.group.value for c in columns if c.group is not None})
    groups = tuple(_group(int(value, 16)) for value in numbers)
    return partition(
        columns,
        ColumnTables(
            widths=tuple(ColumnWidth(column=("invented", n), width=w) for n, w in widths.items()),
            groups=groups,
            locations=_LOCATIONS,
            units=(),
        ),
        hints=hints,
        profile=PROFILE,
        sheet=SHEET,
    )


def _shape(pages):
    """The column names of every page, left to right."""
    return [[c.column[1] for c in p.columns] for p in pages]


def _order(before, after):
    return PageHints(
        keep_together=(),
        break_before=(),
        order=(OrderHint(before=hid("aspect_node", before), after=hid("aspect_node", after)),),
    )


def _together(*numbers):
    return PageHints(
        keep_together=(GroupSet(groups=tuple(hid("aspect_node", n) for n in numbers)),),
        break_before=(),
        order=(),
    )


def test_two_roles_share_one_page_when_they_fit() -> None:
    """A power group and a control group of 300 each are one page: role no longer splits pages."""
    columns = (_col("a", 1, group=1, role=Role.POWER), _col("b", 2, group=2))
    pages, findings = _plan(columns, {"a": 300, "b": 300})
    assert _shape(pages) == [["a", "b"]]
    assert [p.role for p in pages] == [Role.POWER]
    assert [g.group for g in pages[0].groups] == [hid("aspect_node", 1), hid("aspect_node", 2)]
    assert findings == ()


def test_a_page_takes_the_role_of_its_first_group_and_the_role_order_still_orders_groups() -> None:
    """Control group 1 is listed before power group 2 in the input, but power goes first."""
    columns = (_col("a", 1, group=1), _col("b", 2, group=2, role=Role.POWER))
    pages, _ = _plan(columns, {"a": 300, "b": 300})
    assert _shape(pages) == [["b", "a"]]
    assert pages[0].role is Role.POWER


def test_roles_share_the_remainder_of_a_page_and_a_group_that_does_not_fit_starts_the_next() -> (
    None
):
    """The control group joins the power page while it fits; the signal group does not fit."""
    columns = (
        _col("a", 1, group=1, role=Role.POWER),
        _col("b", 2, group=2),
        _col("c", 3, group=3, role=Role.SIGNAL),
    )
    pages, _ = _plan(columns, {"a": 600, "b": 600, "c": 600})
    assert _shape(pages) == [["a", "b"], ["c"]]
    assert [p.role for p in pages] == [Role.POWER, Role.SIGNAL]


def test_an_order_hint_against_the_role_order_is_honoured() -> None:
    """Signal group 2 before power group 1: no finding, and the page's role is the signal's."""
    columns = (_col("a", 1, group=1, role=Role.POWER), _col("b", 2, group=2, role=Role.SIGNAL))
    pages, findings = _plan(columns, {"a": 300, "b": 300}, _order(2, 1))
    assert _shape(pages) == [["b", "a"]]
    assert pages[0].role is Role.SIGNAL
    assert findings == ()


def test_the_same_pair_without_the_hint_keeps_the_role_order() -> None:
    """The near-identical input: no hint, so power first."""
    columns = (_col("a", 1, group=1, role=Role.POWER), _col("b", 2, group=2, role=Role.SIGNAL))
    pages, _ = _plan(columns, {"a": 300, "b": 300})
    assert _shape(pages) == [["a", "b"]]
    assert pages[0].role is Role.POWER


def test_an_order_hint_between_two_drawing_sets_is_still_unmet() -> None:
    """Only a drawing set separates two groups now, and no page order crosses it."""
    columns = (_col("a", 1, group=1, role=Role.POWER), _col("b", 2, group=2, location=101))
    pages, findings = _plan(columns, {"a": 300, "b": 300}, _order(2, 1))
    assert [p.drawing_set for p in pages] == [1, 2]
    assert [(f.code, f.subjects) for f in findings] == [
        (ORDER_HINT_UNMET, (hid("aspect_node", 1), hid("aspect_node", 2)))
    ]


def test_order_hints_that_contradict_across_roles_are_a_cycle() -> None:
    """Both groups are in one bucket now, so the two hints form a cycle and raise."""
    columns = (_col("a", 1, group=1, role=Role.POWER), _col("b", 2, group=2))
    one, two = hid("aspect_node", 1), hid("aspect_node", 2)
    hints = PageHints(
        keep_together=(),
        break_before=(),
        order=(OrderHint(before=one, after=two), OrderHint(before=two, after=one)),
    )
    with pytest.raises(HintError) as raised:
        _plan(columns, {"a": 300, "b": 300}, hints)
    assert raised.value.subjects == (one, two)


def test_a_keep_together_of_two_roles_is_merged_at_its_first_members_place() -> None:
    """Power 1 and control 2 are met together, and pull 2 ahead of power group 3."""
    columns = (
        _col("a", 1, group=1, role=Role.POWER),
        _col("c", 3, group=3, role=Role.POWER),
        _col("b", 2, group=2),
    )
    widths = {"a": 600, "b": 600, "c": 600}
    apart, _ = _plan(columns, widths)
    pages, findings = _plan(columns, widths, _together(1, 2))
    assert _shape(apart) == [["a", "c"], ["b"]]
    assert _shape(pages) == [["a", "b"], ["c"]]
    assert findings == ()


def test_a_keep_together_of_two_roles_that_does_not_fit_is_still_reported() -> None:
    """The reason left is width: 800 and 800 are more than the 1280 content width."""
    columns = (_col("a", 1, group=1, role=Role.POWER), _col("b", 2, group=2))
    pages, findings = _plan(columns, {"a": 800, "b": 800}, _together(1, 2))
    assert _shape(pages) == [["a"], ["b"]]
    assert [f.code for f in findings] == [KEEP_TOGETHER_UNMET]


def test_a_group_wider_than_a_page_still_splits_and_the_next_role_joins_its_last_page() -> None:
    """Power group 1 is 1800 wide: it splits with GROUP_SPLIT, and control group 2 joins page 2."""
    columns = (
        _col("a", 1, group=1, role=Role.POWER),
        _col("b", 2, group=1, role=Role.POWER),
        _col("c", 3, group=1, role=Role.POWER),
        _col("d", 4, group=2),
    )
    pages, findings = _plan(columns, {"a": 600, "b": 600, "c": 600, "d": 300})
    assert _shape(pages) == [["a", "b"], ["c", "d"]]
    assert [(f.code, f.subjects) for f in findings] == [(GROUP_SPLIT, (hid("aspect_node", 1),))]
    assert [p.role for p in pages] == [Role.POWER, Role.POWER]


def test_a_group_of_two_roles_is_listed_once_on_a_page_that_holds_both_of_its_units() -> None:
    """Its power column and its control column fit one page, where the group is named once."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2))
    pages, findings = _plan(columns, {"a": 300, "b": 300})
    assert _shape(pages) == [["a", "b"]]
    assert [g.group for g in pages[0].groups] == [hid("aspect_node", 1)]
    assert pages[0].title == "Invented group 1"
    assert findings == ()


def test_a_group_of_two_roles_is_listed_on_each_page_that_holds_one_of_its_units() -> None:
    """The near-identical input at 800 each: two pages, the group on both."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2))
    pages, findings = _plan(columns, {"a": 800, "b": 800})
    assert _shape(pages) == [["a"], ["b"]]
    assert [g.group for p in pages for g in p.groups] == [hid("aspect_node", 1)] * 2
    assert findings == ()


def test_a_break_before_names_only_the_first_unit_of_a_group_of_two_roles() -> None:
    """Break before group 1 breaks before its power unit; its control unit follows on that page."""
    columns = (_col("z", 9, group=0, role=Role.POWER), _col("a", 1, role=Role.POWER), _col("b", 2))
    hints = PageHints(keep_together=(), break_before=(hid("aspect_node", 1),), order=())
    pages, findings = _plan(columns, {"a": 300, "b": 300, "z": 300}, hints)
    assert _shape(pages) == [["z"], ["a", "b"]]
    assert findings == ()
