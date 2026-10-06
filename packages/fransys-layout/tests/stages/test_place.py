"""WP7 acceptance skeletons and unit tests: `stages.place` (ROADMAP WP7, design/place.md 6.4)."""

import dataclasses
import itertools

import pytest
from samples import PROFILE, SHEET, column, drawn, hid, page_plan, through_geometry

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Point,
    PortGeometry,
    overlaps,
    translate,
)
from fransys_layout.stages import Cell, Column, Role
from fransys_layout.stages import place as stage_place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import PAGE_OVERFULL, _reference_band


def place(plan, columns, functions, *, joins=(), **stacking):
    """`stages.place` with each stacking input as a keyword: the tests name the ones they vary."""
    return stage_place(plan, columns, functions, PageStacking(**stacking), joins)


def _by_function(placed):
    return {p.function: p for p in placed}


def _keepout(placed):
    return translate(placed.geometry.keepout, dx=placed.at.x, dy=placed.at.y)


def _port_x(placed, name):
    at = {port.name: port.at.x for port in placed.geometry.ports}
    return placed.at.x + at[name]


# Fixture arithmetic, by hand. The through symbol's keep-out box is 32 G tall (-16 to 16) and its
# N port sits at -16. PROFILE: row_gap 32, row_spacing 104, text_height 8, marker_padding 0.
_KEEPOUT_HEIGHT = 32
# M4: every page keeps a reference band along the content box's top and bottom; the columns start
# below the top band, so the first row's N port is one band below the box top and the symbol
# origin is 16 G (port) further down.
_BAND = _reference_band(SHEET, PROFILE)
_FIRST_ROW_Y = 16 + _BAND
# D3: a block sits `row_spacing` below the keep-out of the one before, so origins are one keep-out
# height plus `row_spacing` (136 G) apart.
_ROW_PITCH = _KEEPOUT_HEIGHT + PROFILE.row_spacing


def _row_y(row):
    """The origin y of natural row `row` of a column of through symbols (D3, M4)."""
    return _FIRST_ROW_Y + row * _ROW_PITCH


# A band aligns after stacking (D3, F5-A): a block pushed by a lowered band sits one keep-out
# height plus `row_spacing` (not the row gap) below the row that was lowered above it, so it is
# where natural row 2 would be.
_SPACED_BELOW_ROW_1 = _row_y(1) + _KEEPOUT_HEIGHT + PROFILE.row_spacing


def test_cells_stack_top_to_bottom_on_the_column_axis() -> None:
    """Cell 2 sits below cell 1 by at least the symbol height plus the row gap, same x."""
    placed, findings = place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    upper, lower = by[hid("function", 1)], by[hid("function", 2)]
    assert upper.at.x == lower.at.x
    assert lower.at.y - upper.at.y >= 32 + PROFILE.row_gap
    assert findings == ()


def test_a_side_cell_places_as_a_function_that_carries_its_carrier() -> None:
    """D2: the cell of function 2 stands beside function 1, so its placed function names 1 as its
    `carrier`; the host's has none."""
    # UNDO: stages/place.py place, drop `carrier=cell.carrier` from the `PlacedFunction(`
    side_by_side = Column(
        key=("invented", "a"),
        cells=(
            Cell(function=hid("function", 1), index=0),
            Cell(
                function=hid("function", 2), index=0, lane=1, side=True, carrier=hid("function", 1)
            ),
        ),
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )
    placed, _ = place(
        page_plan(("a",)),
        (side_by_side,),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].carrier is None
    assert by[hid("function", 2)].carrier == hid("function", 1)


def test_every_origin_is_on_the_wiring_grid_inside_the_content_box() -> None:
    """Placement snaps to the wiring grid and keeps every keep-out box on the sheet."""
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3,))),
        (drawn(1), drawn(2), drawn(3)),
        profile=PROFILE,
        sheet=SHEET,
    )
    content = Box(x=0, y=0, width=SHEET.content_width, height=SHEET.content_height)
    for p in placed:
        assert p.at.x % WIRING_GRID == 0
        assert p.at.y % WIRING_GRID == 0
        box = translate(p.geometry.keepout, dx=p.at.x, dy=p.at.y)
        assert content.x <= box.x
        assert box.x + box.width <= content.width


def test_columns_keep_plan_order_and_do_not_overlap() -> None:
    """Column b starts right of column a's keep-out edge plus the gap."""
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1,)), column("b", (2,))),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    left, right = by[hid("function", 1)], by[hid("function", 2)]
    left_edge = left.at.x + left.geometry.keepout.x + left.geometry.keepout.width
    assert right.at.x + right.geometry.keepout.x >= left_edge + PROFILE.column_gap


def test_a_terminal_takes_its_band_from_its_place_in_the_column() -> None:
    """First in the column is `terminal.first`, last is `terminal.last`: not one shared band."""
    ranks = frozendict({"terminal.first": 0, "contact_no": 2, "terminal": 4, "terminal.last": 5})
    profile = dataclasses.replace(PROFILE, band_ranks=ranks)
    drawn_functions = (
        drawn(1, kind="terminal"),
        drawn(2, kind="contact_no"),
        drawn(3, kind="terminal"),
        drawn(4, kind="terminal"),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3)), column("b", (4,))),
        drawn_functions,
        profile=profile,
        sheet=SHEET,
    )
    by = _by_function(placed)
    top, bottom, alone = (by[hid("function", n)] for n in (1, 3, 4))
    assert alone.at.y == top.at.y
    assert bottom.at.y > top.at.y


def test_equal_kinds_align_to_one_band_across_columns() -> None:
    """The `load` in the short column is lowered to the y of the `load` in the long one."""
    drawn_functions = (
        drawn(1, kind="protection"),
        drawn(2, kind="contact_no"),
        drawn(3, kind="load"),
        drawn(4, kind="load"),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3)), column("b", (4,))),
        drawn_functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 3)].at.y == by[hid("function", 4)].at.y


def test_primary_port_not_box_centre_sits_on_the_column_axis() -> None:
    """An asymmetric symbol is shifted so its primary ports line up with the cell above."""
    skewed_geometry = dataclasses.replace(
        through_geometry(), body=Box(x=-8, y=-16, width=40, height=32)
    )
    skewed = dataclasses.replace(drawn(2), geometry=skewed_geometry)
    placed, _ = place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), skewed),
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.x == by[hid("function", 2)].at.x


def test_a_column_taller_than_the_sheet_is_reported_not_scaled() -> None:
    """Thirty cells do not fit 886 G: `PAGE_OVERFULL`, and geometry is unchanged."""
    numbers = tuple(range(1, 31))
    placed, findings = place(
        page_plan(("a",)),
        (column("a", numbers),),
        tuple(drawn(n) for n in numbers),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [f.code for f in findings] == [PAGE_OVERFULL]
    assert all(p.geometry == through_geometry() for p in placed)


def test_placement_is_independent_of_input_order() -> None:
    """Shuffled columns, drawn functions and band ranks give the same placement."""
    columns = (column("a", (1, 2)), column("b", (3, 4)), column("c", (5,)))
    functions = (
        drawn(1, kind="protection"),
        drawn(2, kind="load"),
        drawn(3),
        drawn(4, kind="load"),
        drawn(5, kind="protection"),
    )
    shuffled_ranks = dataclasses.replace(
        PROFILE, band_ranks=frozendict({"load": 4, "protection": 1, "contact_no": 2})
    )
    plan = page_plan(("a", "b", "c"))
    forward, forward_findings = place(plan, columns, functions, profile=PROFILE, sheet=SHEET)
    backward, backward_findings = place(
        plan,
        (columns[1], columns[2], columns[0]),
        functions[::-1],
        profile=shuffled_ranks,
        sheet=SHEET,
    )
    assert forward == backward
    assert forward_findings == backward_findings == ()


# --- columns matched to the plan (decisions 0012 and 0018) ----------------------------


def test_two_columns_of_two_keys_take_their_planned_places() -> None:
    """Keys are unique (decision 0018): a page of shape ["b", "a"] puts b left of a."""
    columns = (column("a", (1,)), column("b", (2,)))
    forward, findings = place(
        page_plan(("b", "a")), columns, (drawn(1), drawn(2)), profile=PROFILE, sheet=SHEET
    )
    backward, _ = place(
        page_plan(("b", "a")), columns[::-1], (drawn(2), drawn(1)), profile=PROFILE, sheet=SHEET
    )
    by = _by_function(forward)
    assert forward == backward
    assert by[hid("function", 2)].at.x < by[hid("function", 1)].at.x
    assert findings == ()


def test_two_columns_carrying_one_key_raise() -> None:
    """The near-identical input that fails: keys are unique within an engine run (decision 0018)."""
    with pytest.raises(LayoutError, match="unique"):
        place(
            page_plan(("a",)),
            (column("a", (1,)), column("a", (2,))),
            (drawn(1), drawn(2)),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_a_column_key_carried_twice_raises_even_when_the_plan_does_not_name_it() -> None:
    """The engine's columns are unique whatever the page asks for."""
    with pytest.raises(LayoutError, match="unique"):
        place(
            page_plan(("b",)),
            (column("a", (1,)), column("a", (2,)), column("b", (3,))),
            (drawn(1), drawn(2), drawn(3)),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_a_plan_that_names_one_column_twice_raises() -> None:
    """One `Column` cannot be placed at two planned places."""
    with pytest.raises(LayoutError, match="no single Column"):
        place(
            page_plan(("a", "a")), (column("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET
        )


def test_a_planned_column_with_no_column_value_raises() -> None:
    """The plan asks for column b and no `Column` carries that key."""
    with pytest.raises(LayoutError):
        place(
            page_plan(("a", "b")), (column("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET
        )


def test_a_column_whose_key_the_plan_does_not_name_is_not_placed() -> None:
    """The engine may hand over every column of the drawing set; the rest belong to other pages."""
    plan = page_plan(("a",))
    with_other_page, findings = place(
        plan,
        (column("a", (1,)), column("c", (2,))),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    alone, _ = place(plan, (column("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET)
    assert with_other_page == alone
    assert findings == ()


def test_one_column_value_per_planned_column_does_not_raise() -> None:
    """The near-identical input that passes: one `Column` for each planned key."""
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1,)), column("b", (2,))),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(placed) == 2


def _bare(name, numbers):
    cells = tuple(Cell(function=hid("function", n), index=i) for i, n in enumerate(numbers))
    return Column(key=("invented", name), cells=cells, group=None, role=Role.CONTROL, location=None)


def test_a_column_with_no_cells_raises() -> None:
    """A column that places nothing is the engine assembling the inputs wrongly."""
    with pytest.raises(LayoutError):
        place(page_plan(("a",)), (_bare("a", ()),), (drawn(1),), profile=PROFILE, sheet=SHEET)


def test_a_column_with_one_cell_does_not_raise() -> None:
    """The near-identical input that passes: the same column with a cell in it."""
    placed, _ = place(
        page_plan(("a",)), (_bare("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET
    )
    assert len(placed) == 1


def test_a_cell_naming_a_function_that_is_not_drawn_raises() -> None:
    """A cell has no geometry without its `DrawnFunction`; nothing is substituted."""
    with pytest.raises(LayoutError):
        place(page_plan(("a",)), (column("a", (1, 2)),), (drawn(1),), profile=PROFILE, sheet=SHEET)


def test_a_cell_naming_a_drawn_function_does_not_raise() -> None:
    """The near-identical input that passes: both cells are drawn."""
    placed, _ = place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(placed) == 2


def test_one_function_drawn_twice_raises() -> None:
    """Two `DrawnFunction`s for one function would let the last win: an assembly fault."""
    with pytest.raises(LayoutError, match="drawn twice"):
        place(
            page_plan(("a",)),
            (column("a", (1,)),),
            (drawn(1), drawn(1)),
            profile=PROFILE,
            sheet=SHEET,
        )


def test_one_drawn_function_of_each_does_not_raise() -> None:
    """The near-identical input that passes: the same column with one `DrawnFunction`."""
    placed, _ = place(
        page_plan(("a",)), (column("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET
    )
    assert len(placed) == 1


def test_a_primary_port_that_is_not_a_port_of_the_symbol_raises() -> None:
    """The column axis has nothing to align to; no box centre is substituted for it."""
    stray = dataclasses.replace(drawn(1), primary_in="A1")
    with pytest.raises(LayoutError):
        place(page_plan(("a",)), (column("a", (1,)),), (stray,), profile=PROFILE, sheet=SHEET)


def _ported(port_x):
    return dataclasses.replace(
        through_geometry(),
        ports=(
            PortGeometry(name="in", at=Point(x=port_x, y=-16), facing=Facing.N),
            PortGeometry(name="out", at=Point(x=port_x, y=16), facing=Facing.S),
        ),
    )


def test_a_primary_port_off_the_wiring_grid_raises() -> None:
    """An axis port 4 G along would put every port of its column off the wiring grid."""
    off_grid = dataclasses.replace(drawn(1), geometry=_ported(4))
    with pytest.raises(LayoutError):
        place(page_plan(("a",)), (column("a", (1,)),), (off_grid,), profile=PROFILE, sheet=SHEET)


def test_a_primary_port_on_the_wiring_grid_does_not_raise() -> None:
    """The near-identical input that passes: the same symbol with its ports 8 G along."""
    on_grid = dataclasses.replace(drawn(1), geometry=_ported(8))
    placed, _ = place(
        page_plan(("a",)), (column("a", (1,)),), (on_grid,), profile=PROFILE, sheet=SHEET
    )
    assert placed[0].at.x % WIRING_GRID == 0


def test_a_primary_port_of_the_symbol_does_not_raise() -> None:
    """The near-identical input that passes: the primary port is a port of the symbol."""
    placed, _ = place(
        page_plan(("a",)),
        (column("a", (1,)),),
        (dataclasses.replace(drawn(1), primary_in="in"),),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(placed) == 1


# --- the column axis -----------------------------------------------------------------


def _offset_geometry(port_x, *, body=None):
    return dataclasses.replace(
        through_geometry(),
        body=body if body is not None else Box(x=-8, y=-16, width=16, height=32),
        ports=(
            PortGeometry(name="in", at=Point(x=0, y=-16), facing=Facing.N),
            PortGeometry(name="out", at=Point(x=port_x, y=16), facing=Facing.S),
        ),
    )


def test_a_cell_aligns_its_primary_in_not_its_primary_out() -> None:
    """Both ports are named and they sit 24 G apart: the axis runs through `primary_in`."""
    offset = dataclasses.replace(drawn(2), geometry=_offset_geometry(24))
    placed, _ = place(
        page_plan(("a",)), (column("a", (1, 2)),), (drawn(1), offset), profile=PROFILE, sheet=SHEET
    )
    by = _by_function(placed)
    assert _port_x(by[hid("function", 2)], "in") == _port_x(by[hid("function", 1)], "in")
    assert _port_x(by[hid("function", 2)], "out") != _port_x(by[hid("function", 1)], "in")


def test_a_cell_without_a_primary_in_aligns_its_primary_out() -> None:
    """`primary_out` is the fallback, so the axis still runs through a real port."""
    fallen_back = dataclasses.replace(
        drawn(2), geometry=_offset_geometry(24), primary_in=None, primary_out="out"
    )
    placed, _ = place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), fallen_back),
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert _port_x(by[hid("function", 2)], "out") == _port_x(by[hid("function", 1)], "in")
    assert min(_keepout(function).x for function in placed) == 0


def test_a_cell_with_no_primary_port_aligns_its_body_centre() -> None:
    """A symbol that continues no column has no port to align: the body centre, on the grid."""
    centred = dataclasses.replace(
        drawn(2),
        geometry=_offset_geometry(24, body=Box(x=-8, y=-16, width=40, height=32)),
        primary_in=None,
        primary_out=None,
    )
    placed, _ = place(
        page_plan(("a",)), (column("a", (1, 2)),), (drawn(1), centred), profile=PROFILE, sheet=SHEET
    )
    by = _by_function(placed)
    axis = _port_x(by[hid("function", 1)], "in")
    assert by[hid("function", 2)].at.x + 16 == axis
    assert by[hid("function", 2)].at.x % WIRING_GRID == 0


def test_an_off_centre_primary_port_shifts_the_symbol_not_the_axis() -> None:
    """Two symbols whose ports sit differently inside their bodies still line their ports up."""
    skewed = dataclasses.replace(
        drawn(2),
        geometry=dataclasses.replace(
            through_geometry(),
            ports=(
                PortGeometry(name="in", at=Point(x=16, y=-16), facing=Facing.N),
                PortGeometry(name="out", at=Point(x=16, y=16), facing=Facing.S),
            ),
        ),
    )
    placed, _ = place(
        page_plan(("a",)), (column("a", (1, 2)),), (drawn(1), skewed), profile=PROFILE, sheet=SHEET
    )
    upper, lower = (_by_function(placed)[hid("function", n)] for n in (1, 2))
    assert _port_x(upper, "in") == _port_x(lower, "in")
    assert upper.at.x - lower.at.x == 16


def test_a_multi_pole_cell_puts_pole_one_on_the_axis() -> None:
    """One repeated symbol, `1.in` on the axis; pole 2 hangs off to the side."""
    two_pole = dataclasses.replace(
        through_geometry(),
        poles=2,
        body=Box(x=-8, y=-16, width=48, height=32),
        keepout=Box(x=-8, y=-16, width=88, height=32),
        ports=(
            PortGeometry(name="1.in", at=Point(x=0, y=-16), facing=Facing.N),
            PortGeometry(name="1.out", at=Point(x=0, y=16), facing=Facing.S),
            PortGeometry(name="2.in", at=Point(x=32, y=-16), facing=Facing.N),
            PortGeometry(name="2.out", at=Point(x=32, y=16), facing=Facing.S),
        ),
    )
    repeated = dataclasses.replace(
        drawn(2), geometry=two_pole, primary_in="1.in", primary_out="1.out"
    )
    placed, _ = place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), repeated),
        profile=PROFILE,
        sheet=SHEET,
    )
    upper, lower = (_by_function(placed)[hid("function", n)] for n in (1, 2))
    assert _port_x(lower, "1.in") == _port_x(upper, "in")
    assert _port_x(lower, "2.in") == _port_x(upper, "in") + 32


def test_an_off_grid_keep_out_edge_keeps_the_origin_on_the_wiring_grid() -> None:
    """The real edges sit a few G in from the nominal ones; both origins stay on the grid.

    M4: the columns start below the top band, so the first keep-out top is at or below it; the
    keep-out edge, 5 G above the origin, is 3 G off a grid line.
    """
    off_grid = dataclasses.replace(through_geometry(), keepout=Box(x=-5, y=-5, width=56, height=32))
    functions = tuple(dataclasses.replace(drawn(n), geometry=off_grid) for n in (1, 2))
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1,)), column("b", (2,))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    left, right = (_by_function(placed)[hid("function", n)] for n in (1, 2))
    assert left.at.x % WIRING_GRID == 0
    assert left.at.y % WIRING_GRID == 0
    assert right.at.x % WIRING_GRID == 0
    assert _keepout(left).y >= _BAND
    assert (_keepout(left).x, _keepout(left).y % WIRING_GRID) == (3, 3)
    assert _keepout(left).y == left.at.y - 5
    assert _keepout(right).x == _keepout(left).x + _keepout(left).width + PROFILE.column_gap


# --- bands ---------------------------------------------------------------------------


def test_a_kind_with_no_band_rank_takes_part_in_no_band() -> None:
    """`terminal` is unranked in this profile, so it is never pulled to another column."""
    functions = (drawn(1), drawn(2, kind="terminal"), drawn(3, kind="terminal"))
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3,))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 3)].at.y == by[hid("function", 1)].at.y == _row_y(0)
    assert by[hid("function", 2)].at.y == _row_y(1)


def test_the_two_ends_of_a_column_look_their_bands_up_under_their_own_keys() -> None:
    """A terminal at the top of one column is not pulled to the terminal at the foot of another.

    D3: the first terminal stays on the first row. The contact_no band lowers function 4 to the
    row of function 2 and pushes the foot terminal 5 clear below it; had the foot been looked
    up as the plain `terminal`, it would have been drawn level with the top one.
    """
    ranks = frozendict({"terminal.first": 0, "contact_no": 2, "terminal": 4, "terminal.last": 5})
    profile = dataclasses.replace(PROFILE, band_ranks=ranks)
    functions = (
        drawn(1, kind="terminal"),
        drawn(2),
        drawn(3, kind="terminal"),
        drawn(4),
        drawn(5, kind="terminal"),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3)), column("b", (4, 5))),
        functions,
        profile=profile,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == _row_y(0)
    assert by[hid("function", 2)].at.y == by[hid("function", 4)].at.y == _row_y(1)
    assert by[hid("function", 5)].at.y == _SPACED_BELOW_ROW_1


def test_the_last_cell_of_a_column_is_not_in_the_band_of_a_middle_cell() -> None:
    """`terminal.last` is its own band: the foot of one column ignores a mid-column terminal.

    D3: function 4 stays where the stack puts it (row 3); the mid-column terminal 6 is only
    pushed clear below function 5, which the contact_no band lowered to row 1.
    """
    ranks = frozendict({"terminal.first": 0, "terminal": 1, "contact_no": 2, "terminal.last": 5})
    profile = dataclasses.replace(PROFILE, band_ranks=ranks)
    functions = (
        drawn(1, kind="terminal"),
        drawn(2),
        drawn(3),
        drawn(4, kind="terminal"),
        drawn(5),
        drawn(6, kind="terminal"),
        drawn(7),
        drawn(8),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3, 4)), column("b", (5, 6, 7, 8))),
        functions,
        profile=profile,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 4)].at.y == _row_y(3)
    assert by[hid("function", 6)].at.y == _SPACED_BELOW_ROW_1


def test_an_unranked_prefixed_key_falls_back_to_the_plain_kind() -> None:
    """With no `terminal.last` rank, the foot of a column joins the plain `terminal` band.

    D3: the contact_no band lowers function 4 to row 1 and pushes function 5 clear below it;
    function 3, the foot of column a, joins function 5's band and is raised level with it. Were
    the foot in no band it would stay on row 2.
    """
    ranks = frozendict({"terminal.first": 0, "contact_no": 2, "terminal": 4})
    profile = dataclasses.replace(PROFILE, band_ranks=ranks)
    functions = (
        drawn(1, kind="terminal"),
        drawn(2),
        drawn(3, kind="terminal"),
        drawn(4),
        drawn(5, kind="terminal"),
        drawn(6),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3)), column("b", (4, 5, 6))),
        functions,
        profile=profile,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == _row_y(0)
    assert by[hid("function", 3)].at.y == by[hid("function", 5)].at.y == _SPACED_BELOW_ROW_1


def test_a_deeper_band_member_keeps_its_spaced_top_and_the_others_are_lowered_to_it() -> None:
    """The load band meets at the shallowest top every member can reach (D3, layout-0051).

    Function 5 is on row 2 of its column and function 2 on row 1 of the other. Raising 5 to
    row 1 would close function 4 above it to the row gap, which D3 forbids (104 G); so the
    band meets at 5's own spaced top, row 2, and function 2 is lowered there. Function 4 stays
    on row 1. The protection band, met later, is level.
    """
    ranks = frozendict({"load": 1, "protection": 4})
    profile = dataclasses.replace(PROFILE, band_ranks=ranks)
    functions = (
        drawn(1, kind="protection"),
        drawn(2, kind="load"),
        drawn(3, kind="protection"),
        drawn(4, kind="protection"),
        drawn(5, kind="load"),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3, 4, 5))),
        functions,
        profile=profile,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == by[hid("function", 3)].at.y == _row_y(0)
    assert by[hid("function", 2)].at.y == by[hid("function", 5)].at.y == _row_y(2)
    assert by[hid("function", 4)].at.y == _row_y(1)
    above, load = _keepout(by[hid("function", 4)]), _keepout(by[hid("function", 5)])
    assert load.y - (above.y + above.height) == PROFILE.row_spacing


def test_a_raise_leaves_the_block_above_row_spacing_clear() -> None:
    """D3 (layout-0051): raising a band member never closes the block above to the row gap.

    The protection band lowers function 4 onto function 2's row (row 1) and pushes function 5,
    the contact_no of column b, down to row 2. The contact_no band then raises function 5 to
    function 7's row (row 1); function 4, above it, gives way only as far as `row_spacing`
    (104 G) from its keep-out bottom, that is back to row 0, not to the row gap (32 G).

    D3 (layout-0061) flips the outcome: function 4 is the protection band's, and a later band
    never moves it, so function 5 leaves the contact_no band and stays on row 2, `row_spacing`
    clear of function 4 (on row 1, level with function 2).
    """
    # UNDO: an empty `blockers` list in `_align_bands` (drop the guard) turns the second assert
    # red: function 4 is pulled back to row 0, function 5 raised to row 1.
    functions = (
        drawn(1, kind="filler"),
        drawn(2, kind="protection"),
        drawn(3, kind="filler"),
        drawn(4, kind="protection"),
        drawn(5),
        drawn(6, kind="filler"),
        drawn(7),
    )
    placed, _ = place(
        page_plan(("a", "b", "c")),
        (column("a", (1, 2, 3)), column("b", (4, 5)), column("c", (6, 7))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    above, raised = _keepout(by[hid("function", 4)]), _keepout(by[hid("function", 5)])
    assert raised.y - (above.y + above.height) >= PROFILE.row_spacing
    assert by[hid("function", 2)].at.y == by[hid("function", 4)].at.y == _row_y(1)
    assert by[hid("function", 5)].at.y == _row_y(2)
    assert by[hid("function", 7)].at.y == _row_y(1)


def test_a_member_that_cannot_reach_the_band_top_at_the_spacing_leaves_the_band() -> None:
    """D3, A9 (layout-0051): the band top is a member's spaced top, never a squeezed one.

    Function 10 (row 2 of column b) can rise to row 1 only by pressing the row above it to the
    row gap, which D3 forbids; the others would follow it down to row 2, but column a is seven
    rows tall and reaches the page foot, so it cannot. Function 10 leaves the band: it stays
    at its spaced top (row 2), while functions 2 and 12 keep the band on row 1.
    """
    # UNDO: `stacked` taken before `_space` (row-gap minimum) turns the first assert red:
    # function 10 is raised onto row 1 with the row above it squeezed.
    functions = (
        *(drawn(n, kind="filler") for n in (1, 3, 4, 5, 6, 7)),
        drawn(2),
        drawn(8, kind="filler"),
        drawn(9, kind="filler"),
        drawn(10),
        drawn(11, kind="filler"),
        drawn(12),
    )
    placed, _ = place(
        page_plan(("a", "b", "c")),
        (
            column("a", (1, 2, 3, 4, 5, 6, 7)),
            column("b", (8, 9, 10)),
            column("c", (11, 12)),
        ),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 10)].at.y == _row_y(2)
    assert by[hid("function", 2)].at.y == by[hid("function", 12)].at.y == _row_y(1)


def test_a_later_band_never_raises_a_row_an_earlier_band_aligned() -> None:
    """D3 (layout-0061): band order wins; a raise that would pull an aligned row up leaves the band.

    The protection band lowers function 4 onto function 2's row (row 1), pushing the filler 8
    to row 2 and function 5 to row 3. The contact_no band would raise function 5 to function 7's
    row (row 2), and the raise would pull the filler and then function 4 back up. Function 4 is
    the protection band's, so function 5 leaves the contact_no band and stays where it is.
    """
    # UNDO: an empty `blockers` list in `_align_bands` (drop the guard) turns the second assert
    # red: function 4 is pulled back to row 0.
    functions = (
        drawn(1, kind="filler"),
        drawn(2, kind="protection"),
        drawn(3, kind="filler"),
        drawn(4, kind="protection"),
        drawn(8, kind="filler"),
        drawn(5),
        drawn(6, kind="filler"),
        drawn(9, kind="filler"),
        drawn(7),
    )
    placed, _ = place(
        page_plan(("a", "b", "c")),
        (column("a", (1, 2, 3)), column("b", (4, 8, 5)), column("c", (6, 9, 7))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 2)].at.y == by[hid("function", 4)].at.y == _row_y(1)
    assert by[hid("function", 8)].at.y == _row_y(2)
    assert by[hid("function", 5)].at.y == _row_y(3)
    assert by[hid("function", 7)].at.y == _row_y(2)


def test_a_later_band_never_lowers_a_row_an_earlier_band_aligned() -> None:
    """D3 (layout-0061): a cascade that would push an aligned row down leaves the band.

    The protection band is level on row 1 (functions 3 and 5). The contact_no band would lower
    function 4 (row 0 of column b) to function 8's row (row 2), and the cascade would push
    function 5, the protection band's, down to row 3. Function 4 leaves the contact_no band and
    stays on row 0; the protection band stays level.
    """
    # UNDO: an empty `blockers` list in `_align_bands` (drop the guard) turns the second assert
    # red: function 5 is pushed to row 3, off function 3's row.
    functions = (
        drawn(1, kind="filler"),
        drawn(3, kind="protection"),
        drawn(4),
        drawn(5, kind="protection"),
        drawn(6, kind="filler"),
        drawn(7, kind="filler"),
        drawn(8),
    )
    placed, _ = place(
        page_plan(("a", "b", "c")),
        (column("a", (1, 3)), column("b", (4, 5)), column("c", (6, 7, 8))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 3)].at.y == by[hid("function", 5)].at.y == _row_y(1)
    assert by[hid("function", 4)].at.y == _row_y(0)
    assert by[hid("function", 8)].at.y == _row_y(2)


def test_a_later_band_that_moves_only_its_own_rows_still_aligns() -> None:
    """D3 (layout-0061): the guard does not switch alignment off.

    The protection band is level on row 1 (functions 2 and 7). The contact_no band lowers
    function 4 to function 3's row (row 2) and pushes only the unaligned filler 5 below it.
    """
    # UNDO: a guard that refuses every move turns the first assert red: function 4 stays on row 0.
    functions = (
        drawn(1, kind="filler"),
        drawn(2, kind="protection"),
        drawn(3),
        drawn(4),
        drawn(5, kind="filler"),
        drawn(6, kind="filler"),
        drawn(7, kind="protection"),
    )
    placed, _ = place(
        page_plan(("a", "b", "c")),
        (column("a", (1, 2, 3)), column("b", (4, 5)), column("c", (6, 7))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 3)].at.y == by[hid("function", 4)].at.y == _row_y(2)
    assert by[hid("function", 5)].at.y == _row_y(3)
    assert by[hid("function", 2)].at.y == by[hid("function", 7)].at.y == _row_y(1)


def test_a_band_with_two_cells_in_one_column_is_measured_on_the_topmost() -> None:
    """The second `contact_no` of a column does not drag the other column's cell down."""
    functions = (drawn(1), drawn(2), drawn(3))
    placed, findings = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3,))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == by[hid("function", 3)].at.y == _row_y(0)
    assert by[hid("function", 2)].at.y == _row_y(1)
    assert findings == ()


def test_only_the_topmost_cell_of_a_band_in_a_column_takes_part() -> None:
    """Two `contact_no` cells in one column cannot share a top: the second follows the chain."""
    functions = (drawn(1), drawn(2), drawn(3, kind="protection"), drawn(4))
    placed, findings = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3, 4))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == by[hid("function", 4)].at.y == _row_y(1)
    assert by[hid("function", 2)].at.y == _SPACED_BELOW_ROW_1
    assert findings == ()


def test_raising_a_band_pushes_the_cells_below_it_down_its_column() -> None:
    """The `load` under a raised `contact_no` moves down with it, keep-out boxes clear."""
    functions = (drawn(1), drawn(2, kind="load"), drawn(3, kind="protection"), drawn(4))
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3, 4))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == _row_y(1)
    assert by[hid("function", 2)].at.y == _SPACED_BELOW_ROW_1
    assert _keepout(by[hid("function", 2)]).y >= _keepout(by[hid("function", 1)]).y + 32 + 32


def test_bands_are_aligned_in_rank_order_not_in_the_order_the_page_holds_them() -> None:
    """The `load` band is met first on the page and last by rank: rank decides who yields.

    D3 (layout-0061): the protection band lowers function 3 onto function 2's row and pushes
    function 4 below it. The load band would lower function 1 onto function 4's row and push
    function 2, the protection band's, down; function 1 leaves the load band and stays on row 0.
    """
    functions = (
        drawn(1, kind="load"),
        drawn(2, kind="protection"),
        drawn(3, kind="protection"),
        drawn(4, kind="load"),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3, 4))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    # UNDO: an empty `blockers` list in `_align_bands` (drop the guard) turns the first assert
    # red: function 2 is pushed to row 3, off function 3's row.
    assert by[hid("function", 2)].at.y == by[hid("function", 3)].at.y == _row_y(1)
    assert by[hid("function", 1)].at.y == _row_y(0)
    assert by[hid("function", 4)].at.y == _SPACED_BELOW_ROW_1


def test_a_band_that_contradicts_the_column_order_yields_to_the_earlier_band() -> None:
    """One column has the load under the protection, the other above it: the earlier band wins.

    D3 (layout-0061): the protection band lowers function 1 onto function 4's row (row 1) and
    pushes function 2 to row 2. The load band would lower function 3 onto function 2's row and
    push function 4, the protection band's, down; function 3 leaves the load band.
    """
    functions = (
        drawn(1, kind="protection"),
        drawn(2, kind="load"),
        drawn(3, kind="load"),
        drawn(4, kind="protection"),
    )
    placed, findings = place(
        page_plan(("a", "b")),
        (column("a", (1, 2)), column("b", (3, 4))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    # UNDO: an empty `blockers` list in `_align_bands` (drop the guard) turns the first assert
    # red: function 4 is pushed to row 3, off function 1's row.
    assert by[hid("function", 1)].at.y == by[hid("function", 4)].at.y == _row_y(1)
    assert by[hid("function", 2)].at.y == _SPACED_BELOW_ROW_1
    assert by[hid("function", 3)].at.y == _row_y(0)
    assert findings == ()
    for column_cells in ((1, 2), (3, 4)):
        upper, lower = (_keepout(by[hid("function", n)]) for n in column_cells)
        assert lower.y >= upper.y + upper.height + PROFILE.row_gap


def test_a_block_pushed_by_a_lowered_band_lands_row_spacing_below_the_one_before() -> None:
    """F5-A, D3: a lowered band row pushes each later block `row_spacing`, not the row gap.

    Function 1 is lowered onto function 5's row (row 1); function 2 follows it and function 3
    follows function 2, each one keep-out height plus `row_spacing` (104 G) origin to origin.
    """
    # UNDO: `_cascade` stepping by `row_gap` instead of the block spacing turns this red.
    functions = (
        drawn(1),
        drawn(2, kind="load"),
        drawn(3, kind="load"),
        drawn(4, kind="protection"),
        drawn(5),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3)), column("b", (4, 5))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == by[hid("function", 5)].at.y == _row_y(1)
    step = _KEEPOUT_HEIGHT + PROFILE.row_spacing
    assert by[hid("function", 2)].at.y == by[hid("function", 1)].at.y + step
    assert by[hid("function", 3)].at.y == by[hid("function", 2)].at.y + step


def test_an_attachment_row_under_a_lowered_band_row_keeps_the_row_gap_from_its_host() -> None:
    """F5-A, R7.1: the attachment stays glued to its host; only the next block is spaced.

    Function 2 is an attachment of function 1 (at its `out` port). Function 1 is lowered onto
    function 5's row: function 2 stays one row gap under it, function 3 a `row_spacing` under
    function 2.
    """
    # UNDO: `_cascade` stepping by `row_spacing` after every row (the attachment row too) turns
    # the first assert red; stepping by `row_gap` after every row turns the second red.
    functions = (drawn(1), drawn(2), drawn(3, kind="load"), drawn(4, kind="protection"), drawn(5))
    host_column = Column(
        key=("invented", "a"),
        cells=(
            Cell(function=hid("function", 1), index=0),
            Cell(function=hid("function", 2), index=1, host=hid("function", 1), port="out"),
            Cell(function=hid("function", 3), index=2),
        ),
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (host_column, column("b", (4, 5))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == by[hid("function", 5)].at.y == _row_y(1)
    assert (
        by[hid("function", 2)].at.y
        == by[hid("function", 1)].at.y + _KEEPOUT_HEIGHT + PROFILE.row_gap
    )
    assert (
        by[hid("function", 3)].at.y
        == by[hid("function", 2)].at.y + _KEEPOUT_HEIGHT + PROFILE.row_spacing
    )


def _with_out_at(one, x: int):
    """`one` with its `out` port `x` right of its axis."""
    ports = tuple(
        dataclasses.replace(p, at=Point(x=x, y=p.at.y)) if p.name == "out" else p
        for p in one.geometry.ports
    )
    return dataclasses.replace(one, geometry=dataclasses.replace(one.geometry, ports=ports))


def test_an_attachment_of_an_attachment_sits_at_its_hosts_port_x() -> None:
    """layout-0122: function 3 hangs on function 2, which hangs on function 1; each is one step
    of the `out` port offset right of its host, whichever row the host is in."""
    # UNDO: host_offsets._attach_at_host, drop the `_attach_at_host(host, by_function)` line, and
    #     function 3 is placed from function 2's x before function 2 has moved
    functions = tuple(_with_out_at(drawn(n), 16) for n in (1, 2, 3))
    chain = Column(
        key=("invented", "a"),
        cells=(
            Cell(function=hid("function", 3), index=0, host=hid("function", 2), port="out"),
            Cell(function=hid("function", 2), index=1, host=hid("function", 1), port="out"),
            Cell(function=hid("function", 1), index=2),
        ),
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )
    placed, _ = place(page_plan(("a",)), (chain,), functions, profile=PROFILE, sheet=SHEET)
    by = _by_function(placed)
    step = by[hid("function", 2)].at.x - by[hid("function", 1)].at.x
    assert step != 0
    assert by[hid("function", 3)].at.x - by[hid("function", 2)].at.x == step


def test_a_second_attachment_row_under_one_host_keeps_the_row_gap() -> None:
    """S13, R7.1: a changeover's second throw row is glued to its host as the first row is.

    Functions 2 and 3 are attachments of function 1 in two rows under it (S13's two throw rows);
    function 4 is the next block. Row 2 stands one row gap under row 1, and function 4 a
    `row_spacing` under row 2.
    """
    # UNDO: `_blocks` looking for the host in the block's last row only (not its every row)
    # leaves row 2 a block of its own: it moves a `row_spacing` under row 1, and function 4 a
    # row gap under it, so both asserts turn red.
    functions = tuple(drawn(n) for n in (1, 2, 3, 4))
    host_column = Column(
        key=("invented", "a"),
        cells=(
            Cell(function=hid("function", 1), index=0),
            Cell(function=hid("function", 2), index=1, host=hid("function", 1), port="out"),
            Cell(function=hid("function", 3), index=2, host=hid("function", 1), port="out"),
            Cell(function=hid("function", 4), index=3),
        ),
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )
    placed, _ = place(page_plan(("a",)), (host_column,), functions, profile=PROFILE, sheet=SHEET)
    by = _by_function(placed)
    row_1 = by[hid("function", 2)].at.y
    assert row_1 == by[hid("function", 1)].at.y + _KEEPOUT_HEIGHT + PROFILE.row_gap
    assert by[hid("function", 3)].at.y == row_1 + _KEEPOUT_HEIGHT + PROFILE.row_gap
    assert (
        by[hid("function", 4)].at.y
        == by[hid("function", 3)].at.y + _KEEPOUT_HEIGHT + PROFILE.row_spacing
    )


def test_a_column_of_only_boxes_pushed_by_a_band_keeps_the_row_gap() -> None:
    """F5-A, R6 D4: terminals are drawn compact; a lowered band row pushes them a row gap.

    Function 1 (a terminal) is lowered onto function 5's row (row 1); functions 2 and 3, the
    terminals under it, follow one keep-out height plus `row_gap` apart, not `row_spacing`.
    """
    # UNDO: `_cascade` stepping by `row_spacing` in a column of only boxy cells turns this red.
    ranks = frozendict({"terminal": 2})
    profile = dataclasses.replace(PROFILE, band_ranks=ranks)
    functions = (
        drawn(1, kind="terminal"),
        drawn(2, kind="terminal"),
        drawn(3, kind="terminal"),
        drawn(4),
        drawn(5, kind="terminal"),
    )
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (1, 2, 3)), column("b", (4, 5))),
        functions,
        profile=profile,
        sheet=SHEET,
    )
    by = _by_function(placed)
    assert by[hid("function", 1)].at.y == by[hid("function", 5)].at.y
    step = _KEEPOUT_HEIGHT + PROFILE.row_gap
    assert by[hid("function", 2)].at.y == by[hid("function", 1)].at.y + step
    assert by[hid("function", 3)].at.y == by[hid("function", 2)].at.y + step


# --- the page ------------------------------------------------------------------------


def test_page_overfull_names_only_the_cells_below_the_content_box() -> None:
    """Sixteen cells narrowed to `row_gap` (M11): the thirteenth and every later one reach past
    the floor.

    The columns start below the top band, so row k (from 0) of a 32 G cell and a 32 G gap ends
    at `_BAND + 32 + 64 k`; the floor is the content height less the bottom band, 838 G. Row 11
    ends at 836 G, row 12 at 900 G.
    """
    numbers = tuple(range(1, 17))
    _, findings = place(
        page_plan(("a",)),
        (column("a", numbers),),
        tuple(drawn(n) for n in numbers),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert len(findings) == 1
    assert findings[0].subjects == tuple(sorted(hid("function", n) for n in range(13, 17)))
    assert findings[0].severity.name == "WARNING"


def test_a_page_that_ends_inside_the_content_box_is_not_reported() -> None:
    """M11: seven cells at the house spacing would reach 896 G, past the floor (the content
    height less the bottom band, 838 G), so the column narrows its spacing evenly and ends
    inside the bands: no finding, the first keep-out top on the top band, the last bottom on
    or above the floor, every gap equal and at least `row_gap`."""
    placed, findings = _seven(SHEET.content_height)
    assert findings == ()
    boxes = sorted((_keepout(p) for p in placed), key=lambda box: box.y)
    assert len(boxes) == 7
    assert boxes[0].y == _BAND
    assert boxes[-1].y + boxes[-1].height <= SHEET.content_height - _BAND
    gaps = {lower.y - (upper.y + upper.height) for upper, lower in itertools.pairwise(boxes)}
    assert len(gaps) == 1
    assert PROFILE.row_gap <= gaps.pop() < PROFILE.row_spacing


# M11: the least height seven 32 G cells need: both bands and `row_gap` between the cells.
_SEVEN_LEAST = 2 * _BAND + 7 * _KEEPOUT_HEIGHT + 6 * PROFILE.row_gap


def _seven(content_height):
    """Seven 32 G cells in one column on a sheet `content_height` high."""
    numbers = tuple(range(1, 8))
    return place(
        page_plan(("a",)),
        (column("a", numbers),),
        tuple(drawn(n) for n in numbers),
        profile=PROFILE,
        sheet=dataclasses.replace(SHEET, content_height=content_height),
    )


def test_a_keep_out_box_ending_on_the_content_edge_is_not_overfull() -> None:
    """M11: on the least height (both bands, seven cells, `row_gap` between) the lowest
    keep-out box ends on the floor, flush, and the page is not overfull; the cells stand
    `row_gap` apart."""
    placed, findings = _seven(_SEVEN_LEAST)
    assert findings == ()
    boxes = sorted((_keepout(p) for p in placed), key=lambda box: box.y)
    assert boxes[-1].y + boxes[-1].height == _SEVEN_LEAST - _BAND
    assert boxes[1].y - (boxes[0].y + boxes[0].height) == PROFILE.row_gap


def test_a_keep_out_box_one_grid_unit_past_the_content_edge_is_overfull() -> None:
    """The near-identical input that reports: the same page one G lower than the least height,
    where spacing cannot narrow further (M11: only below that is it `PAGE_OVERFULL`)."""
    _, findings = _seven(_SEVEN_LEAST - 1)
    assert [f.code for f in findings] == [PAGE_OVERFULL]
    assert findings[0].subjects == (hid("function", 7),)


def test_an_overfull_page_is_placed_exactly_like_the_page_that_fits() -> None:
    """Nothing is scaled and nothing moves: only the finding tells the two pages apart."""
    fits, no_findings = _seven(_SEVEN_LEAST)
    overfull, findings = _seven(_SEVEN_LEAST - 1)
    assert [function.at for function in overfull] == [function.at for function in fits]
    assert no_findings == ()
    assert [f.code for f in findings] == [PAGE_OVERFULL]


def test_a_placed_function_carries_its_drawing_set_page_and_column() -> None:
    """Identity is `(function, drawing_set, page)`; the column key comes from the plan."""
    plan = dataclasses.replace(page_plan(("a",), number=2), drawing_set=2)
    placed, _ = place(plan, (column("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET)
    assert [(p.drawing_set, p.page, p.column) for p in placed] == [(2, 2, ("invented", "a"))]


def test_the_result_is_sorted_by_function_handle_not_by_page_order() -> None:
    """The cells are drawn 3, 2, 1 across the page and come back 1, 2, 3."""
    placed, _ = place(
        page_plan(("a", "b")),
        (column("a", (3, 2)), column("b", (1,))),
        (drawn(1), drawn(2), drawn(3)),
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [p.function for p in placed] == [hid("function", n) for n in (1, 2, 3)]


def test_row_spacing_is_measured_on_the_keep_out_box_not_the_body() -> None:
    """A keep-out box taller than its body holds the next cell further down (D3).

    The next cell's origin is the 48 G keep-out height plus `row_spacing` below this one's.
    """
    tall = dataclasses.replace(through_geometry(), keepout=Box(x=-8, y=-24, width=56, height=48))
    functions = tuple(dataclasses.replace(drawn(n), geometry=tall) for n in (1, 2))
    placed, _ = place(
        page_plan(("a",)), (column("a", (1, 2)),), functions, profile=PROFILE, sheet=SHEET
    )
    by = _by_function(placed)
    assert by[hid("function", 2)].at.y - by[hid("function", 1)].at.y == 48 + PROFILE.row_spacing


def test_no_two_keep_out_boxes_of_a_page_overlap() -> None:
    """Mixed symbols over three columns: every keep-out box has the page to itself.

    The widest cell is the first of its column, so a column spaced by anything but its
    widest keep-out box would run into the cell its band lines up with.
    """
    wide = dataclasses.replace(through_geometry(), keepout=Box(x=-8, y=-24, width=160, height=48))
    functions = (
        dataclasses.replace(drawn(1, kind="protection"), geometry=wide),
        drawn(2),
        drawn(3, kind="load"),
        drawn(4, kind="protection"),
        drawn(5, kind="load"),
    )
    placed, _ = place(
        page_plan(("a", "b", "c")),
        (column("a", (1, 2, 3)), column("b", (4,)), column("c", (5,))),
        functions,
        profile=PROFILE,
        sheet=SHEET,
    )
    assert [p.function for p in placed] == sorted(p.function for p in placed)
    for one, other in itertools.combinations(placed, 2):
        assert not overlaps(_keepout(one), _keepout(other))


def test_a_two_cell_column_places_its_second_cell_one_spacing_below_the_first() -> None:
    """R13 (owner): the last symbol is just the next one down, `row_spacing` below the one
    before, never at the page foot. Can-fail, checked by hand: with the second cell pushed
    toward the page foot (700 G down, as the old fill would) this fails."""
    placed, _ = place(
        page_plan(("a",)),
        (column("a", (1, 2)),),
        (drawn(1), drawn(2)),
        profile=PROFILE,
        sheet=SHEET,
    )
    first, second = sorted((_keepout(p) for p in placed), key=lambda box: box.y)
    assert second.y == first.y + first.height + PROFILE.row_spacing


def _mated(*, above: bool):
    """A column of a mated pair: cell 1 and cell 2, the face cell above or below its host."""
    one, two = hid("function", 1), hid("function", 2)
    if above:
        cells = (
            Cell(function=one, index=0, face=True, host=two, port="in"),
            Cell(function=two, index=1, flip=True),
        )
    else:
        cells = (
            Cell(function=two, index=0),
            Cell(function=one, index=1, flip=True, face=True, host=two, port="in"),
        )
    mated = Column(
        key=("invented", "a"),
        cells=cells,
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )
    placed, _ = place(
        page_plan(("a",)), (mated,), (drawn(1), drawn(2)), profile=PROFILE, sheet=SHEET
    )
    by = _by_function(placed)
    return by[hid("function", 1)], by[hid("function", 2)]


def _body(placed):
    return translate(placed.geometry.body, dx=placed.at.x, dy=placed.at.y)


def test_a_face_cell_above_its_host_has_its_body_bottom_on_the_hosts_body_top() -> None:
    """D8: a top end's replica (R0, mating face S) stands above its host (R180, mating face N)."""
    # UNDO: stages/place.py `_align_faces`: drop the `row_of` branch (the face cell goes to the
    # host's body bottom, the base's only case): this fails, the replica overlapping its host
    face, host = _mated(above=True)
    assert _body(face).y + _body(face).height == _body(host).y
    assert face.at.x == host.at.x


def test_a_face_cell_below_its_host_has_its_body_top_on_the_hosts_body_bottom() -> None:
    """R7 A: as before, the lower pin (R180) stands under its host with the faces touching."""
    face, host = _mated(above=False)
    assert _body(face).y == _body(host).y + _body(host).height
