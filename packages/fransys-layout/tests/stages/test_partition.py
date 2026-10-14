"""Acceptance skeletons: `stages.partition`."""

import dataclasses

import pytest
from samples import NO_HINTS, PROFILE, SHEET, column, drawn, hid

from fransys_layout.geometry import HintError, LayoutError
from fransys_layout.stages import (
    ColumnWidth,
    GroupInfo,
    GroupSet,
    LocationInfo,
    OrderHint,
    PageHints,
    Role,
    UnitInfo,
    column_widths,
    partition,
)
from fransys_layout.stages.partition import (
    GROUP_SPLIT,
    KEEP_TOGETHER_UNMET,
    ORDER_HINT_UNDONE,
    ORDER_HINT_UNMET,
    ColumnTables,
)

LOCATIONS = (LocationInfo(location=hid("aspect_node", 100), label="C1"),)


def _group(number: int, *, label: str | None = None) -> GroupInfo:
    return GroupInfo(
        group=hid("aspect_node", number),
        key=("invented", f"group{number}"),
        label=label or f"G{number}",
        description=f"Invented group {number}",
    )


def _width(name: str, width: int) -> ColumnWidth:
    return ColumnWidth(column=("invented", name), width=width)


def _plan(  # noqa: PLR0913 -- one plan-building helper for every test in this file
    columns, widths, groups, hints=NO_HINTS, *, locations=LOCATIONS, units=()
):
    return partition(
        columns,
        ColumnTables(widths=widths, groups=groups, locations=locations, units=units),
        hints=hints,
        profile=PROFILE,
        sheet=SHEET,
    )


def test_column_width_is_widest_keepout_plus_gap() -> None:
    """The sample symbol keep-out is 56 wide and the column gap 48."""
    widths = column_widths((column("a", (1, 2)),), (drawn(1), drawn(2)), profile=PROFILE)
    assert widths == (_width("a", 104),)


# --- unit tests -----------------------------------------------------------------------


def _col(  # noqa: PLR0913 -- one column-building helper for every test in this file
    name, number, *, group=1, role=Role.CONTROL, location=100, unit=None
):
    """Column `name` over function `number`, in `group`, with `role`, `location` and `unit`."""
    return dataclasses.replace(
        column(name, (number,), group=group),
        role=role,
        location=None if location is None else hid("aspect_node", location),
        unit=None if unit is None else hid("unit", unit),
    )


def _shape(pages):
    """The column names of every page, left to right."""
    return [[c.column[1] for c in p.columns] for p in pages]


def _wide(number, width):
    """Function `number` drawn with a keep-out box `width` wide."""
    base = drawn(number)
    keepout = dataclasses.replace(base.geometry.keepout, width=width)
    return dataclasses.replace(base, geometry=dataclasses.replace(base.geometry, keepout=keepout))


def _order(before, after):
    """One order hint, group `before` drawn before group `after`."""
    return PageHints(
        keep_together=(),
        break_before=(),
        order=(OrderHint(before=hid("aspect_node", before), after=hid("aspect_node", after)),),
    )


def _together(*numbers, breaks=()):
    """One keep-together set over `numbers`, with a break before each group in `breaks`."""
    return PageHints(
        keep_together=(GroupSet(groups=tuple(hid("aspect_node", n) for n in numbers)),),
        break_before=tuple(hid("aspect_node", n) for n in breaks),
        order=(),
    )


def test_column_width_takes_the_widest_cell() -> None:
    """A column is as wide as its widest keep-out box, not its first or its last."""
    widths = column_widths(
        (column("a", (1, 2, 3)),), (drawn(1), _wide(2, 80), drawn(3)), profile=PROFILE
    )
    assert widths == (_width("a", 128),)


def test_two_columns_of_one_key_raise() -> None:
    """Keys are unique within an engine run (columns.md 6.2, decision 0018), in either order."""
    columns = (column("a", (1,)), column("a", (2,)))
    for given in (columns, columns[::-1]):
        with pytest.raises(LayoutError, match="unique"):
            column_widths(given, (drawn(1), _wide(2, 80)), profile=PROFILE)


def test_a_column_cell_that_is_not_drawn_raises() -> None:
    """No placeholder box stands in for a missing symbol."""
    with pytest.raises(LayoutError):
        column_widths((column("a", (1, 2)),), (drawn(1),), profile=PROFILE)


def test_one_drawing_set_per_location_in_label_order() -> None:
    """Label order decides, not handle order: location 101 is labelled A1."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="Z1"),
        LocationInfo(location=hid("aspect_node", 101), label="A1"),
    )
    columns = (_col("a", 1, location=100), _col("b", 2, group=2, location=101))
    widths = (_width("a", 100), _width("b", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)), locations=locations)
    assert [(p.drawing_set, p.location, p.number) for p in pages] == [
        (1, hid("aspect_node", 101), 1),
        (2, hid("aspect_node", 100), 1),
    ]


_LEGACY_LOCATION_PAGE_COUNT = 2


_UNIT_1 = hid("unit", 1)
_UNIT_2 = hid("unit", 2)
_TWO_UNIT_BUCKETS = 2


_LOC = hid("aspect_node", 100)
_SUB_LOCATIONS = (
    LocationInfo(location=_LOC, label="L"),
    LocationInfo(location=hid("aspect_node", 101), label="L1"),
    LocationInfo(location=hid("aspect_node", 102), label="L2"),
)
_THREE_PAGES = 3


def test_a_unit_location_with_a_location_info_does_not_raise() -> None:
    """The near-identical input that passes: the same location, known."""
    pages, _ = _plan(
        (_col("a", 1, unit=1),),
        (_width("a", 100),),
        (_group(1),),
        units=(UnitInfo(unit=_UNIT_1, location=hid("aspect_node", 100)),),
    )
    assert [p.location for p in pages] == [hid("aspect_node", 100)]


def test_a_group_whose_columns_carry_two_roles_is_drawn_once_on_a_page_that_fits_both() -> None:
    """Roles may share a page, so one group whose two units fit together is listed once."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2))
    pages, findings = _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1),))
    assert _shape(pages) == [["a", "b"]]
    assert [g.group for p in pages for g in p.groups] == [hid("aspect_node", 1)]
    assert findings == ()


_FOUR_GROUPS = (_group(0), _group(1), _group(2), _group(3))
_FOUR_COLUMNS = (
    _col("d", 4, group=0),
    _col("a", 1, group=1),
    _col("b", 2, group=2),
    _col("c", 3, group=3),
)
_FOUR_WIDTHS = (_width("a", 100), _width("b", 100), _width("c", 100), _width("d", 100))


def test_keep_together_moves_a_later_group_forward_to_the_first_member() -> None:
    """The set sits where its first member sorts, and the group between them follows it."""
    pages, findings = _plan(_FOUR_COLUMNS, _FOUR_WIDTHS, _FOUR_GROUPS, _together(1, 3))
    assert _shape(pages) == [["d", "a", "c", "b"]]
    assert findings == ()


def test_a_split_group_fills_each_page_to_the_content_width() -> None:
    """Three columns of 640 split after the second, not after the first."""
    columns = (_col("a", 1), _col("b", 2), _col("c", 3))
    widths = tuple(_width(name, 640) for name in ("a", "b", "c"))
    pages, findings = _plan(columns, widths, (_group(1),))
    assert _shape(pages) == [["a", "b"], ["c"]]
    assert [f.code for f in findings] == [GROUP_SPLIT]


def test_exactly_the_content_width_fits_on_one_page() -> None:
    """The sheet's content width is the last width that fits."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    pages, _ = _plan(columns, (_width("a", 640), _width("b", 640)), (_group(1), _group(2)))
    assert _shape(pages) == [["a", "b"]]


def test_findings_are_sorted_by_code_and_subjects() -> None:
    """Group 3 is ranked, so it is drawn first, but its finding still comes second."""
    columns = (
        _col("a", 1, group=1),
        _col("b", 2, group=1),
        _col("c", 3, group=3),
        _col("d", 4, group=3),
    )
    widths = tuple(_width(name, 800) for name in ("a", "b", "c", "d"))
    groups = (_group(1), _group(3, label="control"))
    pages, findings = _plan(columns, widths, groups)
    assert _shape(pages) == [["c"], ["d"], ["a"], ["b"]]
    assert [f.subjects for f in findings] == [(hid("aspect_node", 1),), (hid("aspect_node", 3),)]


def test_the_same_order_hint_between_two_drawn_groups_does_not_raise() -> None:
    """The near-identical input that passes: both groups have a column."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    widths = (_width("a", 100), _width("b", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)), _order(1, 2))
    assert _shape(pages) == [["a", "b"]]


def test_keep_together_naming_a_group_with_no_column_raises() -> None:
    """The same rule for a keep-together set."""
    with pytest.raises(HintError):
        _plan((_col("a", 1),), (_width("a", 100),), (_group(1),), _together(1, 9))


def _three_blocks(hints):
    columns = (_col("a", 1), _col("b", 2, group=2), _col("c", 3, group=3))
    widths = (_width("a", 100), _width("b", 100), _width("c", 100))
    return _plan(columns, widths, (_group(1), _group(2), _group(3)), hints)


def _with_set(order, together):
    return PageHints(keep_together=together.keep_together, break_before=(), order=order.order)


def test_a_keep_together_reversing_an_order_hint_is_reported() -> None:
    """Order 2 before 3, together 1 and 3: the set pulls 3 ahead of 2 (layout-0231)."""
    pages, findings = _three_blocks(_with_set(_order(2, 3), _together(1, 3)))
    assert _shape(pages) == [["a", "c", "b"]]
    one, two, three = (hid("aspect_node", n) for n in (1, 2, 3))
    [found] = findings
    assert (found.code, found.severity.value) == (ORDER_HINT_UNDONE, "warning")
    assert set(found.subjects) == {one, two, three}


def test_a_keep_together_keeping_the_order_reports_nothing() -> None:
    """Order 1 before 3, together 1 and 3: the set agrees with the hint."""
    pages, findings = _three_blocks(_with_set(_order(1, 3), _together(1, 3)))
    assert _shape(pages) == [["a", "c", "b"]]
    assert findings == ()


def test_every_partition_finding_is_a_warning() -> None:
    """Layout problems are warnings; structural ones raise instead."""
    columns = (
        _col("a", 1, group=1, role=Role.POWER),
        _col("b", 2, group=2),
        _col("c", 3, group=2),
        _col("d", 4, group=2),
        _col("e", 5, group=3, location=101),
    )
    widths = (
        _width("a", 100),
        _width("b", 600),
        _width("c", 600),
        _width("d", 600),
        _width("e", 100),
    )
    one, two, three = (hid("aspect_node", n) for n in (1, 2, 3))
    hints = PageHints(
        keep_together=(GroupSet(groups=(one, two)),),
        break_before=(),
        order=(OrderHint(before=one, after=three),),
    )
    locations = (*LOCATIONS, LocationInfo(location=hid("aspect_node", 101), label="C2"))
    _, findings = _plan(
        columns, widths, (_group(1), _group(2), _group(3)), hints, locations=locations
    )
    assert [f.code for f in findings] == [GROUP_SPLIT, KEEP_TOGETHER_UNMET, ORDER_HINT_UNMET]
    assert {f.severity.value for f in findings} == {"warning"}


def test_groups_that_fit_share_a_page() -> None:
    """Two narrow groups of one role pack onto one page; pages are never planned by count."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    pages, findings = _plan(columns, (_width("a", 400), _width("b", 400)), (_group(1), _group(2)))
    assert [p.number for p in pages] == [1]
    assert [c.column for c in pages[0].columns] == [("invented", "a"), ("invented", "b")]
    assert findings == ()


def test_a_group_that_does_not_fit_moves_whole_to_the_next_page() -> None:
    """Group 2 (two columns) does not fit beside group 1, so it starts page 2 unsplit."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2), column("c", (3,), group=2))
    widths = (_width("a", 600), _width("b", 400), _width("c", 400))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)))
    assert [[c.column[1] for c in p.columns] for p in pages] == [["a"], ["b", "c"]]
    assert findings == ()


def test_a_group_wider_than_a_page_splits_between_columns_with_a_finding() -> None:
    """Only a group that alone exceeds the sheet is split, and it is reported."""
    columns = (column("a", (1,)), column("b", (2,)), column("c", (3,)))
    widths = (_width("a", 600), _width("b", 600), _width("c", 600))
    pages, findings = _plan(columns, widths, (_group(1),))
    assert len(pages) == 2
    assert [f.code for f in findings] == [GROUP_SPLIT]
    assert findings[0].subjects == (hid("aspect_node", 1),)


def test_order_hint_puts_one_group_before_another() -> None:
    """Group 2 is drawn before group 1 when the author says so."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    hints = PageHints(
        keep_together=(),
        break_before=(),
        order=(OrderHint(before=hid("aspect_node", 2), after=hid("aspect_node", 1)),),
    )
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1), _group(2)), hints)
    assert [c.column[1] for c in pages[0].columns] == ["b", "a"]


def test_order_hints_in_a_cycle_raise() -> None:
    """1 before 2 and 2 before 1 contradict each other; group 3 merely waits on them."""
    columns = (
        column("a", (1,), group=1),
        column("b", (2,), group=2),
        column("c", (3,), group=3),
    )
    one, two, three = (hid("aspect_node", n) for n in (1, 2, 3))
    hints = PageHints(
        keep_together=(),
        break_before=(),
        order=(
            OrderHint(before=one, after=two),
            OrderHint(before=two, after=one),
            OrderHint(before=one, after=three),
        ),
    )
    widths = (_width("a", 100), _width("b", 100), _width("c", 100))
    groups = (_group(1), _group(2), _group(3))
    with pytest.raises(HintError) as raised:
        _plan(columns, widths, groups, hints)
    assert raised.value.subjects == (one, two, three)


def test_keep_together_pulls_groups_onto_one_page_when_they_fit() -> None:
    """Groups 1 and 3 share a page although group 2 sorts between them."""
    columns = (
        column("a", (1,), group=1),
        column("b", (2,), group=2),
        column("c", (3,), group=3),
    )
    widths = (_width("a", 500), _width("b", 500), _width("c", 500))
    hints = PageHints(
        keep_together=(GroupSet(groups=(hid("aspect_node", 1), hid("aspect_node", 3))),),
        break_before=(),
        order=(),
    )
    pages, findings = _plan(columns, widths, (_group(1), _group(2), _group(3)), hints)
    first = {c.column[1] for c in pages[0].columns}
    assert first == {"a", "c"}
    assert findings == ()


def test_a_ranked_group_label_comes_before_an_unranked_one() -> None:
    """`PROFILE.group_ranks` ranks the label "control"; group 1 has no rank and goes last."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    groups = (_group(1), _group(2, label="control"))
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 100)), groups)
    assert [c.column[1] for c in pages[0].columns] == ["b", "a"]


def test_partition_is_independent_of_input_order() -> None:
    """Shuffled columns, widths and groups give the same pages."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2), column("c", (3,), group=2))
    widths = (_width("a", 600), _width("b", 400), _width("c", 400))
    groups = (_group(1), _group(2))
    forward, _ = _plan(columns, widths, groups)
    backward, _ = _plan(columns[::-1], widths[::-1], groups[::-1])
    assert forward == backward


def test_a_unit_with_columns_in_two_sub_locations_is_one_drawing_set() -> None:
    """Layout-0081: a unit is one drawing set whatever sub-locations its columns stand in.
    Each column is 800 wide on a 1280 sheet, so every one fills a page: the pages are numbered
    straight through one set, and every page carries the unit's own location, not a column's."""
    # UNDO: stages/types.py, `Column.drawing_set_key`: the unit branch returns
    #     `(self.unit, self.location)` again (two sets, numbers restart at 1)
    columns = (
        _col("a", 1, location=101, unit=1),
        _col("b", 2, group=2, location=102, unit=1),
        _col("c", 3, group=3, location=101, unit=1),
    )
    widths = (_width("a", 800), _width("b", 800), _width("c", 800))
    units = (UnitInfo(unit=_UNIT_1, location=_LOC),)
    pages, _ = _plan(
        columns, widths, (_group(1), _group(2), _group(3)), locations=_SUB_LOCATIONS, units=units
    )
    assert len(pages) == _THREE_PAGES
    assert [(p.drawing_set, p.number, p.unit, p.location) for p in pages] == [
        (1, 1, _UNIT_1, _LOC),
        (1, 2, _UNIT_1, _LOC),
        (1, 3, _UNIT_1, _LOC),
    ]
    assert _shape(pages) == [["a"], ["b"], ["c"]]


def test_an_order_hint_between_two_drawing_sets_cannot_be_met() -> None:
    """Two locations are two drawing sets, so no page order puts one group before the other."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="C1"),
        LocationInfo(location=hid("aspect_node", 101), label="C2"),
    )
    columns = (_col("a", 1), _col("b", 2, group=2, location=101))
    widths = (_width("a", 100), _width("b", 100))
    pages, findings = _plan(
        columns, widths, (_group(1), _group(2)), _order(2, 1), locations=locations
    )
    assert [p.drawing_set for p in pages] == [1, 2]
    assert [f.code for f in findings] == [ORDER_HINT_UNMET]


def test_an_order_hint_leaves_the_groups_it_does_not_name_where_they_were() -> None:
    """Group 2 is free, so it keeps the first free place; group 3 only overtakes group 1."""
    columns = (_col("a", 1), _col("b", 2, group=2), _col("c", 3, group=3))
    widths = (_width("a", 100), _width("b", 100), _width("c", 100))
    groups = (_group(1), _group(2), _group(3))
    pages, findings = _plan(columns, widths, groups, _order(3, 1))
    assert _shape(pages) == [["b", "c", "a"]]
    assert findings == ()


def test_a_box_column_too_wide_for_the_free_width_moves_whole_to_the_next_page() -> None:
    """A PLC box column is never cut; it leaves a page it does not fit (layout-0103)."""
    columns = (_col("a", 1, group=1), _col("box", 2, group=2))
    widths = (_width("a", 800), _width("box", 700))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)))
    assert _shape(pages) == [["a"], ["box"]]
    assert findings == ()
