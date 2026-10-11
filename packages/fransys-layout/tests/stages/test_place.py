"""Acceptance skeletons and unit tests: `stages.place`."""

import dataclasses

import pytest
from samples import PROFILE, SHEET, column, drawn, hid, page_plan, through_geometry

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    Point,
    PortGeometry,
    translate,
)
from fransys_layout.stages import Cell, Column, Role
from fransys_layout.stages import place as stage_place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import _reference_band


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
# Every page keeps a reference band along the content box's top and bottom; the columns start
# below the top band, so the first row's N port is one band below the box top and the symbol
# origin is 16 G (port) further down.
_BAND = _reference_band(SHEET, PROFILE)
_FIRST_ROW_Y = 16 + _BAND
# A block sits `row_spacing` below the keep-out of the one before, so origins are one keep-out
# height plus `row_spacing` (136 G) apart.
_ROW_PITCH = _KEEPOUT_HEIGHT + PROFILE.row_spacing


def _row_y(row):
    """The origin y of natural row `row` of a column of through symbols."""
    return _FIRST_ROW_Y + row * _ROW_PITCH


# A band aligns after stacking: a block pushed by a lowered band sits one keep-out
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


# --- columns matched to the plan (decisions 0012 and 0018) ----------------------------


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


def test_a_plan_that_names_one_column_twice_raises() -> None:
    """One `Column` cannot be placed at two planned places."""
    with pytest.raises(LayoutError, match="no single Column"):
        place(
            page_plan(("a", "a")), (column("a", (1,)),), (drawn(1),), profile=PROFILE, sheet=SHEET
        )


def _bare(name, numbers):
    cells = tuple(Cell(function=hid("function", n), index=i) for i, n in enumerate(numbers))
    return Column(key=("invented", name), cells=cells, group=None, role=Role.CONTROL, location=None)


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


# --- bands ---------------------------------------------------------------------------


def test_bands_are_aligned_in_rank_order_not_in_the_order_the_page_holds_them() -> None:
    """The `load` band is met first on the page and last by rank: rank decides who yields.

    Layout-0061: the protection band lowers function 3 onto function 2's row and pushes
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
    """A changeover's second throw row is glued to its host as the first row is.

    Functions 2 and 3 are attachments of function 1 in two rows under it (two throw rows);
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


# --- the page ------------------------------------------------------------------------


def test_page_overfull_names_only_the_cells_below_the_content_box() -> None:
    """Sixteen cells narrowed to `row_gap`: the thirteenth and every later one reach past
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


# The least height seven 32 G cells need: both bands and `row_gap` between the cells.
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
    """A top end's replica (R0, mating face S) stands above its host (R180, mating face N)."""
    # UNDO: stages/place.py `_align_faces`: drop the `row_of` branch (the face cell goes to the
    # host's body bottom, the base's only case): this fails, the replica overlapping its host
    face, host = _mated(above=True)
    assert _body(face).y + _body(face).height == _body(host).y
    assert face.at.x == host.at.x


def test_a_cell_aligns_its_primary_in_not_its_primary_out() -> None:
    """Both ports are named and they sit 24 G apart: the axis runs through `primary_in`."""
    offset = dataclasses.replace(drawn(2), geometry=_offset_geometry(24))
    placed, _ = place(
        page_plan(("a",)), (column("a", (1, 2)),), (drawn(1), offset), profile=PROFILE, sheet=SHEET
    )
    by = _by_function(placed)
    assert _port_x(by[hid("function", 2)], "in") == _port_x(by[hid("function", 1)], "in")
    assert _port_x(by[hid("function", 2)], "out") != _port_x(by[hid("function", 1)], "in")


def test_an_attachment_row_under_a_lowered_band_row_keeps_the_row_gap_from_its_host() -> None:
    """The attachment stays glued to its host; only the next block is spaced.

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


def test_a_column_of_only_boxes_pushed_by_a_band_keeps_the_row_gap() -> None:
    """Terminals are drawn compact; a lowered band row pushes them a row gap.

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
