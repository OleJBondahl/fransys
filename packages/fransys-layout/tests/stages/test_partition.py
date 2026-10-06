"""WP6 acceptance skeletons: `stages.partition` (ROADMAP WP6, docs/design/pages.md 6.3)."""

import dataclasses

import pytest
from samples import NO_HINTS, PROFILE, SHEET, column, drawn, hid

from fransys_layout.geometry import HintError, LayoutError
from fransys_layout.stages import (
    Cell,
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


def test_roles_share_a_page_when_they_fit() -> None:
    """A power column and a control column that fit together are one page, named for the first."""
    power = dataclasses.replace(column("a", (1,), group=1), role=Role.POWER)
    control = column("b", (2,), group=2)
    pages, _ = _plan((power, control), (_width("a", 100), _width("b", 100)), (_group(1), _group(2)))
    assert [p.role for p in pages] == [Role.POWER]
    assert [c.column[1] for c in pages[0].columns] == ["a", "b"]


def test_break_before_starts_a_new_page() -> None:
    """The hint splits two groups that would otherwise share a page."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    hints = PageHints(keep_together=(), break_before=(hid("aspect_node", 2),), order=())
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1), _group(2)), hints)
    assert len(pages) == 2


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


def test_keep_together_that_does_not_fit_is_packed_normally_with_a_finding() -> None:
    """Groups 1 and 2 are 800 wide each: no page holds both, so the hint is reported."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    widths = (_width("a", 800), _width("b", 800))
    hints = PageHints(
        keep_together=(GroupSet(groups=(hid("aspect_node", 1), hid("aspect_node", 2))),),
        break_before=(),
        order=(),
    )
    pages, findings = _plan(columns, widths, (_group(1), _group(2)), hints)
    assert [[c.column[1] for c in p.columns] for p in pages] == [["a"], ["b"]]
    assert [f.code for f in findings] == [KEEP_TOGETHER_UNMET]


def test_a_ranked_group_label_comes_before_an_unranked_one() -> None:
    """`PROFILE.group_ranks` ranks the label "control"; group 1 has no rank and goes last."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    groups = (_group(1), _group(2, label="control"))
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 100)), groups)
    assert [c.column[1] for c in pages[0].columns] == ["b", "a"]


def test_title_joins_group_descriptions_and_pages_number_from_one() -> None:
    """A page title is its groups' descriptions in order."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2))
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1), _group(2)))
    assert pages[0].number == 1
    assert pages[0].title == "Invented group 1, Invented group 2"


def test_partition_is_independent_of_input_order() -> None:
    """Shuffled columns, widths and groups give the same pages."""
    columns = (column("a", (1,), group=1), column("b", (2,), group=2), column("c", (3,), group=2))
    widths = (_width("a", 600), _width("b", 400), _width("c", 400))
    groups = (_group(1), _group(2))
    forward, _ = _plan(columns, widths, groups)
    backward, _ = _plan(columns[::-1], widths[::-1], groups[::-1])
    assert forward == backward


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


def test_column_widths_are_sorted_by_column_key() -> None:
    """Shuffled columns give the same tuple, in key order."""
    columns = (column("b", (2,)), column("a", (1,)))
    widths = column_widths(columns, (drawn(1), drawn(2)), profile=PROFILE)
    assert widths == (_width("a", 104), _width("b", 104))


def test_two_columns_of_one_key_raise() -> None:
    """Keys are unique within an engine run (columns.md 6.2, decision 0018), in either order."""
    columns = (column("a", (1,)), column("a", (2,)))
    for given in (columns, columns[::-1]):
        with pytest.raises(LayoutError, match="unique"):
            column_widths(given, (drawn(1), _wide(2, 80)), profile=PROFILE)


def test_two_columns_of_two_keys_still_give_one_row_each_in_key_order() -> None:
    """The near-identical input that passes: distinct keys keep their own rows, sorted."""
    columns = (column("b", (2,)), column("a", (1,)))
    widths = column_widths(columns, (drawn(1), _wide(2, 80)), profile=PROFILE)
    assert widths == (_width("a", 104), _width("b", 128))


def test_a_column_cell_that_is_not_drawn_raises() -> None:
    """No placeholder box stands in for a missing symbol."""
    with pytest.raises(LayoutError):
        column_widths((column("a", (1, 2)),), (drawn(1),), profile=PROFILE)


def test_the_same_column_with_every_cell_drawn_does_not_raise() -> None:
    """The near-identical input that passes: both cells are drawn."""
    widths = column_widths((column("a", (1, 2)),), (drawn(1), drawn(2)), profile=PROFILE)
    assert widths == (_width("a", 104),)


def test_a_column_with_no_cells_raises() -> None:
    """A column with no cell has no keep-out box to measure."""
    empty = dataclasses.replace(column("a", (1,)), cells=())
    with pytest.raises(LayoutError):
        column_widths((empty,), (drawn(1),), profile=PROFILE)


def test_a_column_with_one_cell_does_not_raise() -> None:
    """The near-identical input that passes: one cell."""
    cells = (Cell(function=hid("function", 1), index=0),)
    one = dataclasses.replace(column("a", (1,)), cells=cells)
    assert column_widths((one,), (drawn(1),), profile=PROFILE) == (_width("a", 104),)


def test_a_column_with_no_width_raises() -> None:
    """`partition` never guesses a width it was not given."""
    with pytest.raises(LayoutError):
        _plan((_col("a", 1),), (_width("b", 100),), (_group(1),))


def test_a_column_with_a_width_does_not_raise() -> None:
    """The near-identical input that passes: the width names the column."""
    pages, _ = _plan((_col("a", 1),), (_width("a", 100),), (_group(1),))
    assert _shape(pages) == [["a"]]


def test_a_group_with_no_info_raises() -> None:
    """A group without a `GroupInfo` has no label, no rank and no key to order it by."""
    with pytest.raises(LayoutError):
        _plan((_col("a", 1, group=2),), (_width("a", 100),), (_group(1),))


def test_a_group_with_an_info_does_not_raise() -> None:
    """The near-identical input that passes: the info names the group."""
    pages, _ = _plan((_col("a", 1, group=2),), (_width("a", 100),), (_group(2),))
    assert _shape(pages) == [["a"]]


def test_a_location_with_no_info_raises() -> None:
    """A location without a `LocationInfo` has no label to order its drawing set by."""
    with pytest.raises(LayoutError):
        _plan((_col("a", 1, location=101),), (_width("a", 100),), (_group(1),))


def test_a_location_with_an_info_does_not_raise() -> None:
    """The near-identical input that passes: the info names the location."""
    locations = (LocationInfo(location=hid("aspect_node", 101), label="C2"),)
    pages, _ = _plan(
        (_col("a", 1, location=101),), (_width("a", 100),), (_group(1),), locations=locations
    )
    assert pages[0].location == hid("aspect_node", 101)


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


def test_equal_location_labels_are_ordered_by_handle() -> None:
    """Two locations with one label still have one drawing set order."""
    locations = (
        LocationInfo(location=hid("aspect_node", 101), label="C1"),
        LocationInfo(location=hid("aspect_node", 100), label="C1"),
    )
    columns = (_col("a", 1, location=101), _col("b", 2, group=2, location=100))
    widths = (_width("a", 100), _width("b", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)), locations=locations)
    assert [p.location for p in pages] == [hid("aspect_node", 100), hid("aspect_node", 101)]


_LEGACY_LOCATION_PAGE_COUNT = 2


def test_no_units_gives_byte_identical_drawing_sets_to_before_units_existed() -> None:
    """Regression pin (units spec U1): with `units=()` every plan's `unit` is `None` and the
    drawing-set numbering is exactly what `test_one_drawing_set_per_location_in_label_order`
    already pinned before this dimension existed."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="Z1"),
        LocationInfo(location=hid("aspect_node", 101), label="A1"),
    )
    columns = (_col("a", 1, location=100), _col("b", 2, group=2, location=101))
    widths = (_width("a", 100), _width("b", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)), locations=locations)
    assert len(pages) == _LEGACY_LOCATION_PAGE_COUNT
    assert [(p.unit, p.drawing_set, p.location, p.number) for p in pages] == [
        (None, 1, hid("aspect_node", 101), 1),
        (None, 2, hid("aspect_node", 100), 1),
    ]


_UNIT_1 = hid("unit", 1)
_UNIT_2 = hid("unit", 2)
_TWO_UNIT_BUCKETS = 2


def test_two_units_at_the_same_location_label_are_two_drawing_sets() -> None:
    """U1: two units' content at one location label are different drawing sets, in unit id
    order, not interleaved by label -- `units` is shuffled to prove order does not depend on it."""
    where = hid("aspect_node", 100)
    units = (UnitInfo(unit=_UNIT_2, location=where), UnitInfo(unit=_UNIT_1, location=where))
    columns = (_col("a", 1, unit=2), _col("b", 2, group=2, unit=1))
    widths = (_width("a", 100), _width("b", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)), units=units)
    assert len(pages) == _TWO_UNIT_BUCKETS
    assert [(p.unit, p.location, p.drawing_set) for p in pages] == [
        (_UNIT_1, hid("aspect_node", 100), 1),
        (_UNIT_2, hid("aspect_node", 100), 2),
    ]


_LOC = hid("aspect_node", 100)
_SUB_LOCATIONS = (
    LocationInfo(location=_LOC, label="L"),
    LocationInfo(location=hid("aspect_node", 101), label="L1"),
    LocationInfo(location=hid("aspect_node", 102), label="L2"),
)
_THREE_PAGES = 3


def test_a_unit_with_columns_in_two_sub_locations_is_one_drawing_set() -> None:
    """Layout-0081 (LD6): a unit is one drawing set whatever sub-locations its columns stand in.
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


def test_two_top_level_columns_in_two_locations_are_still_two_drawing_sets() -> None:
    """The top-level twin of the unit case above: locations split sets outside any unit, and
    the numbers restart at 1 in each."""
    columns = (_col("a", 1, location=101), _col("b", 2, group=2, location=102))
    widths = (_width("a", 800), _width("b", 800))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)), locations=_SUB_LOCATIONS)
    assert [(p.drawing_set, p.number, p.unit, p.location) for p in pages] == [
        (1, 1, None, hid("aspect_node", 101)),
        (2, 1, None, hid("aspect_node", 102)),
    ]


def test_a_unit_with_no_location_gives_pages_with_no_location() -> None:
    """`UnitInfo.location=None` is the plan's location `None`, though the column has one."""
    pages, _ = _plan(
        (_col("a", 1, location=101, unit=1),),
        (_width("a", 100),),
        (_group(1),),
        locations=_SUB_LOCATIONS,
        units=(UnitInfo(unit=_UNIT_1, location=None),),
    )
    assert [(p.unit, p.location) for p in pages] == [(_UNIT_1, None)]


def test_a_unit_location_with_no_location_info_raises() -> None:
    """A `UnitInfo.location` names a `+` node like a column's location does, so it needs a row."""
    with pytest.raises(LayoutError):
        _plan(
            (_col("a", 1, unit=1),),
            (_width("a", 100),),
            (_group(1),),
            units=(UnitInfo(unit=_UNIT_1, location=hid("aspect_node", 999)),),
        )


def test_a_unit_location_with_a_location_info_does_not_raise() -> None:
    """The near-identical input that passes: the same location, known."""
    pages, _ = _plan(
        (_col("a", 1, unit=1),),
        (_width("a", 100),),
        (_group(1),),
        units=(UnitInfo(unit=_UNIT_1, location=hid("aspect_node", 100)),),
    )
    assert [p.location for p in pages] == [hid("aspect_node", 100)]


def test_a_column_with_an_unknown_unit_raises() -> None:
    """A column's unit must have a `UnitInfo`, just like its group or location."""
    with pytest.raises(LayoutError):
        _plan((_col("a", 1, unit=1),), (_width("a", 100),), (_group(1),))


def test_a_column_with_a_known_unit_does_not_raise() -> None:
    """The near-identical input that passes: the info names the unit."""
    pages, _ = _plan(
        (_col("a", 1, unit=1),),
        (_width("a", 100),),
        (_group(1),),
        units=(UnitInfo(unit=_UNIT_1),),
    )
    assert _shape(pages) == [["a"]]


def test_two_unit_infos_for_one_unit_raise() -> None:
    """Two rows for one unit would give the table whichever came last."""
    with pytest.raises(LayoutError):
        _plan(
            (_col("a", 1),),
            (_width("a", 100),),
            (_group(1),),
            units=(UnitInfo(unit=_UNIT_1), UnitInfo(unit=_UNIT_1)),
        )


def test_two_unit_infos_for_two_units_do_not_raise() -> None:
    """The near-identical input that passes: one row per unit."""
    pages, _ = _plan(
        (_col("a", 1),),
        (_width("a", 100),),
        (_group(1),),
        units=(UnitInfo(unit=_UNIT_1), UnitInfo(unit=_UNIT_2)),
    )
    assert _shape(pages) == [["a"]]


def test_columns_with_no_location_go_to_a_drawing_set_of_their_own_last() -> None:
    """The location-less drawing set comes after every located one."""
    columns = (_col("a", 1), _col("b", 2, group=2, location=None))
    widths = (_width("a", 100), _width("b", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2)))
    assert [(p.drawing_set, p.location) for p in pages] == [(1, hid("aspect_node", 100)), (2, None)]


def test_page_numbers_run_through_the_drawing_set_and_restart_in_the_next() -> None:
    """Numbers count the pages of one drawing set (both roles share page 1) and restart at 1."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="C1"),
        LocationInfo(location=hid("aspect_node", 101), label="C2"),
    )
    columns = (
        _col("a", 1, role=Role.POWER),
        _col("b", 2, group=2),
        _col("c", 3, group=3, location=101),
    )
    widths = (_width("a", 100), _width("b", 100), _width("c", 100))
    pages, _ = _plan(columns, widths, (_group(1), _group(2), _group(3)), locations=locations)
    assert [(p.drawing_set, p.number, p.role) for p in pages] == [
        (1, 1, Role.POWER),
        (2, 1, Role.CONTROL),
    ]
    assert _shape(pages) == [["a", "b"], ["c"]]


def test_a_column_with_no_group_comes_last_and_adds_nothing_to_the_title() -> None:
    """A group-less column is its own unit, drawn after every group, with no description."""
    columns = (_col("b", 2, group=None), _col("a", 1))
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1),))
    (page,) = pages
    assert _shape(pages) == [["a", "b"]]
    assert [(g.group, g.index) for g in page.groups] == [(hid("aspect_node", 1), 0), (None, 1)]
    assert [(c.column[1], c.index) for c in page.columns] == [("a", 0), ("b", 1)]
    assert page.title == "Invented group 1"


def test_a_page_of_only_group_less_columns_has_an_empty_title() -> None:
    """No stray separator when no group on the page has a description."""
    columns = (_col("a", 1, group=None), _col("b", 2, group=None))
    pages, findings = _plan(columns, (_width("a", 100), _width("b", 100)), ())
    assert [p.title for p in pages] == [""]
    assert findings == ()


def test_a_group_whose_columns_carry_two_roles_is_drawn_once_on_a_page_that_fits_both() -> None:
    """Roles may share a page, so one group whose two units fit together is listed once."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2))
    pages, findings = _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1),))
    assert _shape(pages) == [["a", "b"]]
    assert [g.group for p in pages for g in p.groups] == [hid("aspect_node", 1)]
    assert findings == ()


def test_an_order_hint_between_two_roles_is_met() -> None:
    """Role order is the base order only: a hint against it is honoured, without a finding."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2, group=2))
    widths = (_width("a", 100), _width("b", 100))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)), _order(2, 1))
    assert _shape(pages) == [["b", "a"]]
    assert findings == ()


def test_the_same_order_hint_inside_one_role_is_met() -> None:
    """The near-identical input that passes: both groups are control groups."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    widths = (_width("a", 100), _width("b", 100))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)), _order(2, 1))
    assert _shape(pages) == [["b", "a"]]
    assert findings == ()


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


def test_order_hints_that_contradict_across_roles_raise() -> None:
    """A cycle is a cycle inside one drawing set whatever the roles."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2, group=2))
    one, two = hid("aspect_node", 1), hid("aspect_node", 2)
    hints = PageHints(
        keep_together=(),
        break_before=(),
        order=(OrderHint(before=one, after=two), OrderHint(before=two, after=one)),
    )
    widths = (_width("a", 100), _width("b", 100))
    with pytest.raises(HintError) as raised:
        _plan(columns, widths, (_group(1), _group(2)), hints)
    assert raised.value.subjects == (one, two)


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


def test_break_before_on_a_sets_first_group_breaks_before_the_whole_set() -> None:
    """Both hints are met: the set stays together and starts a page."""
    hints = _together(1, 3, breaks=(1,))
    pages, findings = _plan(_FOUR_COLUMNS, _FOUR_WIDTHS, _FOUR_GROUPS, hints)
    assert _shape(pages) == [["d"], ["a", "c", "b"]]
    assert findings == ()


def test_break_before_inside_a_set_dissolves_it() -> None:
    """A break on a later member cannot be met with the set: the set loses, the break wins."""
    hints = _together(1, 3, breaks=(3,))
    pages, findings = _plan(_FOUR_COLUMNS, _FOUR_WIDTHS, _FOUR_GROUPS, hints)
    assert _shape(pages) == [["d", "a", "b"], ["c"]]
    assert [(f.code, f.subjects) for f in findings] == [
        (KEEP_TOGETHER_UNMET, (hid("aspect_node", 1), hid("aspect_node", 3)))
    ]


def test_keep_together_across_two_roles_is_met() -> None:
    """Groups of two roles may share a page, so the set is merged and nothing is reported."""
    columns = (_col("a", 1, role=Role.POWER), _col("b", 2, group=2))
    widths = (_width("a", 100), _width("b", 100))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)), _together(1, 2))
    assert _shape(pages) == [["a", "b"]]
    assert findings == ()


def test_an_oversized_group_starts_a_fresh_page_and_shares_its_last() -> None:
    """Column b would fit beside a, but the split group starts fresh; e joins its last page."""
    columns = (
        _col("a", 1, group=1),
        _col("b", 2, group=2),
        _col("c", 3, group=2),
        _col("e", 5, group=3),
    )
    widths = (_width("a", 500), _width("b", 700), _width("c", 700), _width("e", 500))
    groups = (_group(1), _group(2), _group(3))
    pages, findings = _plan(columns, widths, groups)
    assert _shape(pages) == [["a"], ["b"], ["c", "e"]]
    assert [(f.code, f.subjects) for f in findings] == [(GROUP_SPLIT, (hid("aspect_node", 2),))]


def test_a_split_group_fills_each_page_to_the_content_width() -> None:
    """Three columns of 640 split after the second, not after the first."""
    columns = (_col("a", 1), _col("b", 2), _col("c", 3))
    widths = tuple(_width(name, 640) for name in ("a", "b", "c"))
    pages, findings = _plan(columns, widths, (_group(1),))
    assert _shape(pages) == [["a", "b"], ["c"]]
    assert [f.code for f in findings] == [GROUP_SPLIT]


def test_a_keep_together_set_exactly_the_content_width_is_met() -> None:
    """The content width is the widest a merged set may be."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    widths = (_width("a", 640), _width("b", 640))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)), _together(1, 2))
    assert _shape(pages) == [["a", "b"]]
    assert findings == ()


def test_an_order_hint_leaves_the_groups_it_does_not_name_where_they_were() -> None:
    """Group 2 is free, so it keeps the first free place; group 3 only overtakes group 1."""
    columns = (_col("a", 1), _col("b", 2, group=2), _col("c", 3, group=3))
    widths = (_width("a", 100), _width("b", 100), _width("c", 100))
    groups = (_group(1), _group(2), _group(3))
    pages, findings = _plan(columns, widths, groups, _order(3, 1))
    assert _shape(pages) == [["b", "c", "a"]]
    assert findings == ()


def test_a_single_column_wider_than_a_page_is_never_split() -> None:
    """One column cannot be split between columns, so nothing is reported and nothing scaled."""
    pages, findings = _plan((_col("a", 1),), (_width("a", 2000),), (_group(1),))
    assert _shape(pages) == [["a"]]
    assert findings == ()


def test_exactly_the_content_width_fits_on_one_page() -> None:
    """The sheet's content width is the last width that fits."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    pages, _ = _plan(columns, (_width("a", 640), _width("b", 640)), (_group(1), _group(2)))
    assert _shape(pages) == [["a", "b"]]


def test_one_grid_unit_more_than_the_content_width_does_not() -> None:
    """The near-identical input that splits: one grid unit wider."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    pages, _ = _plan(columns, (_width("a", 640), _width("b", 641)), (_group(1), _group(2)))
    assert _shape(pages) == [["a"], ["b"]]


def test_adding_a_column_to_the_last_group_changes_no_earlier_page() -> None:
    """Stability: a new column moves only the pages of its own group."""
    columns = (_col("a", 1), _col("b", 2, group=2), _col("c", 3, group=2))
    widths = (_width("a", 600), _width("b", 400), _width("c", 400))
    groups = (_group(1), _group(2))
    before, _ = _plan(columns, widths, groups)
    after, _ = _plan((*columns, _col("d", 4, group=2)), (*widths, _width("d", 400)), groups)
    assert _shape(before) == [["a"], ["b", "c"]]
    assert _shape(after) == [["a"], ["b", "c", "d"]]
    assert after[0] == before[0]


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


def test_an_order_hint_naming_a_group_with_no_column_raises() -> None:
    """A hint about a group that is not drawn is a contradiction, not a no-op."""
    columns = (_col("a", 1), _col("b", 2, group=2))
    with pytest.raises(HintError):
        _plan(columns, (_width("a", 100), _width("b", 100)), (_group(1), _group(2)), _order(1, 3))


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


def test_break_before_naming_a_group_with_no_column_raises() -> None:
    """And for a break-before."""
    hints = PageHints(keep_together=(), break_before=(hid("aspect_node", 9),), order=())
    with pytest.raises(HintError):
        _plan((_col("a", 1),), (_width("a", 100),), (_group(1),), hints)


def test_two_column_widths_with_one_key_raise() -> None:
    """A table with two rows for one column would keep whichever came last."""
    with pytest.raises(LayoutError):
        _plan((_col("a", 1),), (_width("a", 100), _width("a", 200)), (_group(1),))


def test_two_column_widths_with_two_keys_do_not_raise() -> None:
    """The near-identical input that passes: one row per column."""
    columns = (_col("a", 1), _col("b", 2))
    pages, _ = _plan(columns, (_width("a", 100), _width("b", 200)), (_group(1),))
    assert _shape(pages) == [["a", "b"]]


def test_two_group_infos_for_one_group_raise() -> None:
    """Two rows for one group would give it whichever label and key came last."""
    with pytest.raises(LayoutError):
        _plan((_col("a", 1),), (_width("a", 100),), (_group(1), _group(1, label="control")))


def test_two_group_infos_for_two_groups_do_not_raise() -> None:
    """The near-identical input that passes: one row per group."""
    pages, _ = _plan((_col("a", 1),), (_width("a", 100),), (_group(1), _group(2)))
    assert _shape(pages) == [["a"]]


def test_two_location_infos_for_one_location_raise() -> None:
    """Two rows for one location would order its drawing set by whichever label came last."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="C1"),
        LocationInfo(location=hid("aspect_node", 100), label="A1"),
    )
    with pytest.raises(LayoutError):
        _plan((_col("a", 1),), (_width("a", 100),), (_group(1),), locations=locations)


def test_two_location_infos_for_two_locations_do_not_raise() -> None:
    """The near-identical input that passes: one row per location."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="C1"),
        LocationInfo(location=hid("aspect_node", 101), label="A1"),
    )
    pages, _ = _plan((_col("a", 1),), (_width("a", 100),), (_group(1),), locations=locations)
    assert _shape(pages) == [["a"]]


def test_an_empty_keep_together_set_raises() -> None:
    """A set that names no group states nothing: the engine assembled it wrongly."""
    hints = PageHints(keep_together=(GroupSet(groups=()),), break_before=(), order=())
    with pytest.raises(LayoutError):
        _plan((_col("a", 1),), (_width("a", 100),), (_group(1),), hints)


def test_a_keep_together_set_of_one_group_does_not_raise() -> None:
    """The near-identical input that passes: one group, trivially kept together."""
    pages, findings = _plan((_col("a", 1),), (_width("a", 100),), (_group(1),), _together(1))
    assert _shape(pages) == [["a"]]
    assert findings == ()


def test_an_order_hint_leaves_columns_with_no_group_at_the_end() -> None:
    """Two group-less columns share no order key, and a hint between groups skips them."""
    columns = (
        _col("a", 1),
        _col("b", 2, group=2),
        _col("c", 3, group=None),
        _col("d", 4, group=None),
    )
    widths = tuple(_width(name, 100) for name in ("a", "b", "c", "d"))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)), _order(2, 1))
    assert _shape(pages) == [["b", "a", "c", "d"]]
    assert findings == ()


def test_partition_is_independent_of_input_order_with_locations_roles_and_hints() -> None:
    """Every ordering key: two drawing sets, two roles, an order hint and a keep-together set."""
    locations = (
        LocationInfo(location=hid("aspect_node", 100), label="C1"),
        LocationInfo(location=hid("aspect_node", 101), label="A1"),
    )
    columns = (
        _col("a", 1, group=1, role=Role.POWER),
        _col("b", 2, group=2),
        _col("c", 3, group=3),
        _col("d", 4, group=4, location=101),
        _col("e", 5, group=None, location=None),
    )
    widths = tuple(_width(name, 300) for name in ("a", "b", "c", "d", "e"))
    groups = (_group(1), _group(2), _group(3), _group(4))
    two, three = hid("aspect_node", 2), hid("aspect_node", 3)
    hints = PageHints(
        keep_together=(GroupSet(groups=(two, three)),),
        break_before=(),
        order=(
            OrderHint(before=three, after=two),
            OrderHint(before=two, after=hid("aspect_node", 1)),
        ),
    )
    flipped = dataclasses.replace(hints, order=hints.order[::-1])
    forward = _plan(columns, widths, groups, hints, locations=locations)
    backward = _plan(columns[::-1], widths[::-1], groups[::-1], flipped, locations=locations[::-1])
    assert forward == backward


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


def test_a_box_column_too_wide_for_the_free_width_moves_whole_to_the_next_page() -> None:
    """V5: a PLC box column is never cut; it leaves a page it does not fit (layout-0103)."""
    columns = (_col("a", 1, group=1), _col("box", 2, group=2))
    widths = (_width("a", 800), _width("box", 700))
    pages, findings = _plan(columns, widths, (_group(1), _group(2)))
    assert _shape(pages) == [["a"], ["box"]]
    assert findings == ()
