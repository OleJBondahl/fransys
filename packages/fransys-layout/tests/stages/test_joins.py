"""S12 (LD9): the horizontal join and "wired beside" as one rule, on hand-made columns.

Function `n` is the through symbol (`samples.drawn`): port `10n + 1` (`13`) at `in` on top,
facing N; port `10n + 2` (`14`) at `out` below, facing S; a keep-out 32 G high. Columns stand
left to right on page 1 of drawing set 1 in the order `_spots` is given, stacked by `place`'s
own rule (`place.page_stack`): rows `row_spacing` (104 G) apart.
"""

from dataclasses import replace

from samples import PROFILE, SHEET, column, drawn, function_spec, hid, page_plan, through_geometry

from fransys_layout.stages import Connection, DrawnPort, PortRef, Role
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import page_stack
from fransys_layout.stages.references.joins import (
    JoinEnd,
    _wired_beside,
    join_y,
    port_spots,
)
from fransys_layout.stages.references.nets import star_nets
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun
from fransys_layout.stages.terminal_rows import NO_CHAINS
from fransys_layout.stages.types import PlannedColumn

_ROOM = 800
_ROOMS = {(1, 1): _ROOM}


def _port(function: int, which: int):
    """Port `13` (`which` 1, top, N) or `14` (`which` 2, bottom, S) of function `function`."""
    return hid("port", function * 10 + which)


def _wire(handle: int, a: tuple[int, int], b: tuple[int, int]) -> Connection:
    """Conductor `handle` between port `a` and port `b`, each `(function, which)`."""
    return Connection(
        handle=hid("conductor", handle),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a[0]), port=_port(*a)),
        b=PortRef(function=hid("function", b[0]), port=_port(*b)),
    )


def _spots(
    *columns: tuple[str, tuple[int, ...]],
    keys: dict[str, tuple] | None = None,
    tall: dict[int, int] | None = None,
    attached: dict[int, int] | None = None,
):
    """`port_spots` of `columns` (`(name, functions top to bottom)`), left to right on page 1.

    `tall` gives a function `n` a through symbol of half height `tall[n]`, so its row is taller;
    `attached` makes function `n` an attachment hosted by function `attached[n]`."""
    keys = keys or {}
    attached = attached or {}
    tall = tall or {}
    built = tuple(
        replace(
            column(name, numbers),
            key=keys.get(name, ("invented", name)),
            cells=tuple(
                replace(cell, host=hid("function", attached[n]), port="in")
                if n in attached
                else cell
                for cell, n in zip(column(name, numbers).cells, numbers, strict=True)
            ),
        )
        for name, numbers in columns
    )
    plan = replace(
        page_plan(tuple(name for name, _ in columns)),
        columns=tuple(PlannedColumn(column=one.key, index=i) for i, one in enumerate(built)),
    )
    functions = tuple(
        replace(drawn(n), geometry=through_geometry(half_height=tall[n])) if n in tall else drawn(n)
        for n in sorted({n for _, numbers in columns for n in numbers})
    )
    stack = page_stack(plan, built, functions, PageStacking(profile=PROFILE, sheet=SHEET))
    return port_spots(built, (plan,), functions, {(1, 1): stack})


# --- join_y ---------------------------------------------------------------------------


def test_a_run_aligns_at_its_deepest_offset() -> None:
    """Two ends in row 0: `place` lowers the shallower column to the deeper port's offset."""
    # UNDO: stages/stacking.py `join_y`: `max(end.offset ...)` -> `min(...)`
    ends = (
        JoinEnd(port=_port(1, 1), row=0, offset=0, height=32),
        JoinEnd(port=_port(2, 1), row=0, offset=8, height=40),
    )
    assert join_y(ends, _ROOM) == 8


def test_a_run_whose_ends_stand_in_different_rows_is_refused() -> None:
    """A bottom run over columns of unequal row counts never lands on one y."""
    # UNDO: stages/stacking.py `join_y`: drop the `len({end.row ...}) != 1` test
    ends = (
        JoinEnd(port=_port(2, 2), row=1, offset=168, height=168),
        JoinEnd(port=_port(5, 2), row=2, offset=304, height=304),
    )
    assert join_y(ends, _ROOM) is None


def test_a_run_whose_lowered_column_leaves_the_room_is_refused() -> None:
    """Lowering the shallow column by 100 G makes it 700 G tall, past a 650 G room."""
    # UNDO: stages/stacking.py `join_y`: `> room` -> `> room + 1000`
    ends = (
        JoinEnd(port=_port(1, 2), row=0, offset=500, height=600),
        JoinEnd(port=_port(2, 2), row=0, offset=600, height=610),
    )
    assert join_y(ends, 650) is None
    assert join_y(ends, 700) == 600


# --- port_spots -----------------------------------------------------------------------


def test_a_port_spot_says_its_row_its_offset_and_its_columns_height() -> None:
    """Column a holds functions 1 and 2: port 22 (`out` of row 1) stands 32 + 104 + 32 G down."""
    # UNDO: stages/place.py `page_stack`: `cell.origin.y + g.at.y - top` -> drop `- top` (the
    #     page's C14 text room above row 0, 16 G, then counts in the offset)
    spots = _spots(("a", (1, 2)))
    (spot,) = spots[_port(2, 2)]
    assert (spot.page, spot.index, spot.cell, spot.last) == ((1, 1), 0, 1, 1)
    assert spot.end == JoinEnd(port=_port(2, 2), row=1, offset=168, height=168)


def test_a_function_drawn_twice_takes_its_ports_from_its_first_drawing() -> None:
    """Two drawings of function 1: port 12 is in the first, port 19 (also `out`) in the second."""
    # UNDO: stages/references/joins.py `port_spots`: `drawn_of.setdefault(one.function, one)` ->
    #     `drawn_of[one.function] = one` (the last drawing wins)
    first = drawn(1)
    second = replace(first, ports=(DrawnPort(port=_port(1, 9), symbol_port="out"),))
    columns, plan = (column("a", (1,)),), page_plan(("a",))
    stack = page_stack(plan, columns, (first,), PageStacking(profile=PROFILE, sheet=SHEET))
    spots = port_spots(columns, (plan,), (first, second), {(1, 1): stack})
    assert _port(1, 2) in spots
    assert _port(1, 9) not in spots


# --- wired_beside ---------------------------------------------------------------------


def test_two_ports_in_consecutive_rows_of_one_column_are_beside() -> None:
    """D1's first wire case, from `columns` alone: 12 (row 0) to 21 (row 1) of column a."""
    # UNDO: stages/references/joins.py `wired_beside`: `abs(x.cell - y.cell) == 1` -> `== 2`
    wire = _wire(1, (1, 2), (2, 1))
    joins = _wired_beside((wire,), _spots(("a", (1, 2))), _ROOMS, NO_CHAINS)
    assert joins.beside.pairs[_port(1, 2), _port(2, 1)] == frozenset({1})
    assert joins.beside.sets[_port(1, 2)] == frozenset({1})
    assert joins.findings == ()
    assert joins.runs == ()


def test_the_feeds_of_neighbouring_columns_along_the_top_are_one_joined_run() -> None:
    """LD9: ports 11, 21 and 31 face N at the top of columns a, b and c: one run, all beside."""
    # UNDO: stages/references/joins.py `_neighbours`: `abs(x.index - y.index) == 1` -> `== 2`
    wires = (_wire(1, (1, 1), (2, 1)), _wire(2, (2, 1), (3, 1)))
    spots = _spots(("a", (1,)), ("b", (2,)), ("c", (3,)))
    joins = _wired_beside(wires, spots, _ROOMS, NO_CHAINS)
    assert joins.beside.pairs[_port(1, 1), _port(2, 1)] == frozenset({1})
    assert joins.beside.pairs[_port(2, 1), _port(3, 1)] == frozenset({1})
    assert joins.findings == ()
    ends = tuple(
        JoinedEnd(column=("invented", name), port=_port(n, 1))
        for name, n in (("a", 1), ("b", 2), ("c", 3))
    )
    assert joins.runs == (JoinedRun(drawing_set=1, page=1, ends=ends),)


def _bottom_run(column_b: tuple[int, ...]):
    """A 3-port net: 22 (bottom of column a, S) to 42 (bottom of column b, S) to 61 (column c's
    top, N). Returns its `Joins` and stars."""
    wires = (_wire(1, (2, 2), (4, 2)), _wire(2, (4, 2), (6, 1)))
    spots = _spots(("a", (1, 2)), ("b", column_b), ("c", (6,)))
    joins = _wired_beside(wires, spots, _ROOMS, NO_CHAINS)
    specs = tuple(function_spec(n) for n in sorted({1, 2, 6, *column_b}))
    stars = star_nets(wires, specs, (), joins.beside)
    return joins, stars


def test_a_bottom_run_over_columns_of_equal_rows_is_a_wire() -> None:
    """Columns a and b have two rows each: 22 and 42 are a joined run, the wire stays routed."""
    # CAN-FAIL (acceptance 2): column b as `(5, 3, 4)` (three rows, 42 still at its bottom) makes
    #     the run unalignable: JOIN_UNALIGNED fires and the conductor is dropped for markers
    joins, (star,) = _bottom_run((3, 4))
    assert joins.beside.pairs[_port(2, 2), _port(4, 2)] == frozenset({1})
    assert joins.findings == ()
    assert hid("conductor", 1) not in star.conductors  # routed, not drawn as markers


def test_a_bottom_run_over_columns_of_unequal_rows_keeps_its_references() -> None:
    """Column b has three rows: 42 stands in row 2, 22 in row 1, so `place` cannot align them.
    22 lies above the top edge of 42's device: the wire would leave 42 outward and come back
    past it. The turn test (S20 M12) refuses it first: references, no candidate, no finding."""
    # UNDO: stages/references/joins.py `_neighbours`: drop `turns_back(x, y) or turns_back(y, x)`
    #     (the run is a candidate again and `JOIN_UNALIGNED` fires)
    joins, (star,) = _bottom_run((5, 3, 4))
    assert (_port(2, 2), _port(4, 2)) not in joins.beside.pairs
    assert joins.findings == ()
    assert joins.runs == ()
    assert hid("conductor", 1) in star.conductors  # drawn as references (markers)


def test_a_run_whose_columns_have_unequal_row_heights_gives_join_unaligned() -> None:
    """S12: columns a (1, 2, 3) and b (4, 5); 32 and 52 are both last ports facing S, so the run
    is a candidate and the turn test passes, but 4 and 5 stand tall: `place` cannot put the two
    ports on one y. One `JOIN_UNALIGNED` names both ports, no run, no wired pair. Reached at the
    stage boundary (hand-made columns); no engine build in the 4b6d measure produced one."""
    # UNDO: stages/references/joins.py `_unaligned`: `code=JOIN_UNALIGNED` -> `code="NOT_"
    #     + JOIN_UNALIGNED` (the finding gets another code)
    spots = _spots(("a", (1, 2, 3)), ("b", (4, 5)), tall={4: 56, 5: 56})
    joins = _wired_beside((_wire(1, (3, 2), (5, 2)),), spots, _ROOMS, NO_CHAINS)
    assert [finding.code for finding in joins.findings] == ["JOIN_UNALIGNED"]
    assert joins.findings[0].subjects == (_port(3, 2), _port(5, 2))
    assert joins.runs == ()
    assert joins.beside.pairs == {}


def test_ends_facing_different_ways_are_no_join() -> None:
    """Port 12 faces S at the bottom of column a, 21 N at the top of column b: no candidate."""
    # UNDO: stages/references/joins.py `_neighbours`: drop `or x.facing is not y.facing`
    wire = _wire(1, (1, 2), (2, 1))
    joins = _wired_beside((wire,), _spots(("a", (1,)), ("b", (2,))), _ROOMS, NO_CHAINS)
    assert joins.beside.pairs == {}
    assert joins.findings == ()


def test_a_port_mid_column_beside_a_top_port_is_no_join() -> None:
    """Port 21 faces N in row 1 of column b, 11 at the top of column a: not an LD9 run (21 is not
    at its column's end), and on one y only by moving a column: no wire, no finding."""
    # UNDO: stages/references/joins.py `wired_beside`: the `level` test `== {join_y(...)}` ->
    #     `True` (a level pair is joined whatever column it moves)
    wire = _wire(1, (1, 1), (2, 1))
    joins = _wired_beside((wire,), _spots(("a", (1,)), ("b", (3, 2))), _ROOMS, NO_CHAINS)
    assert joins.beside.pairs == {}
    assert joins.findings == ()


def test_the_paralleled_mains_of_two_neighbours_mid_column_stay_wires() -> None:
    """Designer 2026-09-27 (S12's second case): mains 1 and 2 stand in row 1 of neighbouring
    columns a and b, each under one cell and over one, so 11-21 (N) and 12-22 (S) are already on
    one y with no column moved: both straps stay wires, and no finding."""
    # UNDO: stages/references/joins.py `wired_beside`, the `level` loop's `_add` -> `pass`
    wires = (_wire(1, (1, 1), (2, 1)), _wire(2, (1, 2), (2, 2)))
    spots = _spots(("a", (5, 1, 6)), ("b", (7, 2, 8)))
    joins = _wired_beside(wires, spots, _ROOMS, NO_CHAINS)
    assert joins.beside.pairs[_port(1, 1), _port(2, 1)] == frozenset({1})
    assert joins.beside.pairs[_port(1, 2), _port(2, 2)] == frozenset({1})
    assert joins.findings == ()
    assert len(joins.runs) == 2


def test_same_side_ends_two_columns_apart_stay_a_wire() -> None:
    """S20 M12: 11 and 31 face N at the top of columns x and z, with column y between them: the
    turn test passes at both ends (each leaves its pin outward), so the star net stays a wire at
    any column distance, one joined run and no finding."""
    # UNDO: stages/references/joins.py `_neighbours`: `return not (turns_back(x, y) or
    #     turns_back(y, x))` -> `return abs(x.index - y.index) == 1`
    spots = _spots(("x", (1,)), ("y", (2,)), ("z", (3,)))
    joins = _wired_beside((_wire(1, (1, 1), (3, 1)),), spots, _ROOMS, NO_CHAINS)
    assert joins.beside.pairs[_port(1, 1), _port(3, 1)] == frozenset({1})
    assert joins.findings == ()
    assert len(joins.runs) == 1


def _shifted_member(*, joined_first: bool, attached: bool = True):
    """Ports 11 and 21 face N at the top of columns a and b; port 31 is the second row of column c
    (a row above it is taken, by an attachment hosted by 3 when `attached`), so its pin stands
    lower than both. Wires 21-31, and 11-21 when `joined_first`."""
    wires = (_wire(2, (2, 1), (3, 1)),)
    if joined_first:
        wires = (_wire(1, (1, 1), (2, 1)), *wires)
    spots = _spots(("a", (1,)), ("b", (2,)), ("c", (9, 3)), attached={9: 3} if attached else None)
    return _wired_beside(wires, spots, _ROOMS, NO_CHAINS)


def test_a_wire_from_a_joined_end_to_a_shifted_member_gives_join_unaligned() -> None:
    """V6: 11 and 21 are one run; 21's wire to 31 turns back past b's device (31 stands a row
    lower), so it is no join, and `JOIN_UNALIGNED` names it instead of dropping it silently."""
    # UNDO: stages/references/joins.py `turned_findings`: `if ... & joined` -> `if False`
    #     (the shifted member's wire is dropped with no finding)
    joins = _shifted_member(joined_first=True, attached=False)
    assert [finding.code for finding in joins.findings] == ["JOIN_UNALIGNED"]
    assert joins.findings[0].subjects == (_port(2, 1), _port(3, 1))
    assert [end.port for run in joins.runs for end in run.ends] == [_port(1, 1), _port(2, 1)]


def test_a_turned_wire_to_a_member_under_an_attached_part_gives_join_unaligned() -> None:
    """I4: 31 stands a row lower because attachment 9 is above it; no run joined 21, and the
    wire still gives `JOIN_UNALIGNED` (layout-0099)."""
    # UNDO: stages/references/joins.py `turned_findings`: drop `x.shifted or y.shifted or`
    joins = _shifted_member(joined_first=False)
    assert [finding.code for finding in joins.findings] == ["JOIN_UNALIGNED"]
    assert joins.findings[0].subjects == (_port(2, 1), _port(3, 1))
    assert joins.runs == ()


def test_a_turned_wire_to_a_member_under_an_ordinary_device_stays_silent() -> None:
    """The same wire with 9 an ordinary device, not an attachment: an ordinary reference pair."""
    # UNDO: stages/references/joins.py `_under_attachment`: drop the `c.host == cell.function` test
    joins = _shifted_member(joined_first=False, attached=False)
    assert joins.findings == ()
    assert joins.runs == ()
