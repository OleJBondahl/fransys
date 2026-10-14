"""A lone conductor from a bottom pin to the first top pin of another column hangs as a wire.

Function `n` is the through symbol (`samples.drawn`): port `10n + 1` at the top, facing N; port
`10n + 2` below, facing S. Columns stand left to right on page 1, stacked by `place`'s own rule.
Function 9 is a device that pushes function 1 down to row 1, so function 2, first in its own
column, would stand above port 12 and the wire would turn back (layout-0224).
"""

from dataclasses import replace

from samples import PROFILE, SHEET, column, drawn, function_spec, hid, page_plan

from fransys_layout.stages import Connection, PortRef, Role
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import page_stack
from fransys_layout.stages.references.hung import HANG, hung_joins
from fransys_layout.stages.references.types import Beside, Joins, Seating
from fransys_layout.stages.stacking import JoinedEnd, JoinedRun
from fransys_layout.stages.terminal_rows import terminal_chains
from fransys_layout.stages.types import PlannedColumn

_NONE = Joins(Beside(pairs={}, sets={}), (), ())


def _wire(a: tuple[int, int], b: tuple[int, int]) -> Connection:
    """The conductor between ports `a` and `b`, each `(function, which)`: 1 top, 2 bottom."""
    return Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a[0]), port=hid("port", a[0] * 10 + a[1])),
        b=PortRef(function=hid("function", b[0]), port=hid("port", b[0] * 10 + b[1])),
    )


def _hung(
    wire: Connection,
    *columns: tuple[str, tuple[int, ...]],
    joins: Joins = _NONE,
    room: int | None = None,
) -> Joins:
    """`hung_joins` of `wire` on `columns` (each `(name, functions top to bottom)`)."""
    built = tuple(
        replace(column(name, numbers), key=("invented", name)) for name, numbers in columns
    )
    plan = replace(
        page_plan(tuple(name for name, _ in columns)),
        columns=tuple(PlannedColumn(column=one.key, index=i) for i, one in enumerate(built)),
    )
    numbers = sorted({n for _, one in columns for n in one})
    functions = tuple(drawn(n, kind="contact_no") for n in numbers)
    stack = page_stack(plan, built, functions, PageStacking(profile=PROFILE, sheet=SHEET))
    stack = stack if room is None else replace(stack, room=room)
    specs = tuple(function_spec(n) for n in numbers)
    return hung_joins(
        joins,
        (wire,),
        specs,
        Seating((plan,), built, functions, (), {(1, 1): stack}),
        terminal_chains(specs, functions, (wire,)),
    )


def test_a_bottom_pin_to_a_first_top_pin_above_it_hangs_the_second_column() -> None:
    """Port 12 (row 1) to port 21 (row 0, above 12): a run, host 12 above, 21 lowered."""
    # UNDO: stages/references/hung.py `_hangable`: `if _hangs(host, branch, rooms)` -> `if False`
    wire = _wire((1, 2), (2, 1))
    found = _hung(wire, ("a", (9, 1)), ("b", (2,)))
    (run,) = found.runs
    host, branch = sorted(run.ends, key=lambda end: not end.anchor)
    assert (host.port, host.drop, host.anchor) == (hid("port", 12), HANG, True)
    assert (branch.port, branch.drop, branch.anchor) == (hid("port", 21), 0, False)
    assert found.beside.hung == {(wire.a.port, wire.b.port)}
    assert found.beside.pairs[wire.a.port, wire.b.port] == {1}


def test_a_top_pin_that_is_not_first_in_its_column_stays_a_pair() -> None:
    """Port 21 is in row 1 of its column, above port 12 (row 3): the turn stays."""
    # UNDO: stages/references/hung.py `_hangs`: drop the `branch.end.row != 0` test
    found = _hung(_wire((1, 2), (2, 1)), ("a", (9, 7, 6, 1)), ("b", (8, 2)))
    assert found == _NONE


def test_a_hop_the_page_room_refuses_stays_a_pair() -> None:
    """With no room below, lowering the column by `HANG` would leave the page: no run."""
    # UNDO: stages/references/hung.py `_hangs`: `return lowered <= rooms[...]` -> `return True`
    found = _hung(_wire((1, 2), (2, 1)), ("a", (9, 1)), ("b", (2,)), room=0)
    assert found == _NONE


def test_a_port_already_in_a_run_is_left_to_that_run() -> None:
    """Port 21 is an end of a joined run: a second drop would pull it two ways."""
    # UNDO: stages/references/hung.py `_claimed`: drop `{end.port for end in run.ends} | `
    ends = (JoinedEnd(column=("invented", "x"), port=hid("port", 21)),)
    taken = replace(_NONE, runs=(JoinedRun(drawing_set=1, page=1, ends=ends),))
    found = _hung(_wire((1, 2), (2, 1)), ("a", (9, 1)), ("b", (2,)), joins=taken)
    assert found == taken


def test_a_pair_that_does_not_turn_back_is_none_of_its_business() -> None:
    """Port 12 and port 21 are both in row 0: no turn back, a plain wire, no run."""
    # UNDO: stages/references/hung.py `_hangs`: drop the `turns_back` test
    found = _hung(_wire((1, 2), (2, 1)), ("a", (1,)), ("b", (2,)))
    assert found == _NONE


def test_a_column_already_in_a_run_is_not_hung() -> None:
    """Another run ends in column b: `place` aligns a column once, so the hop stays a pair."""
    # UNDO: stages/references/hung.py `_claimed`: drop `| {end.column for end in run.ends}`
    ends = (JoinedEnd(column=("invented", "b"), port=hid("port", 99)),)
    taken = replace(_NONE, runs=(JoinedRun(drawing_set=1, page=1, ends=ends),))
    found = _hung(_wire((1, 2), (2, 1)), ("a", (9, 1)), ("b", (2,)), joins=taken)
    assert found == taken


def test_a_hop_that_leaves_the_page_stays_a_marker_pair() -> None:
    """Port 12 is on page 1, port 21 on page 2: no wire joins them, so no run hangs."""
    # UNDO: stages/references/turned.py `lone_pair`: drop the `if x.page == y.page` filter
    wire = _wire((1, 2), (2, 1))
    plans = (page_plan(("a",), number=1), page_plan(("b",), number=2))
    built = (column("a", (9, 1)), column("b", (2,)))
    functions = tuple(drawn(n, kind="contact_no") for n in (1, 2, 9))
    stacking = PageStacking(profile=PROFILE, sheet=SHEET)
    stacks = {(1, plan.number): page_stack(plan, built, functions, stacking) for plan in plans}
    specs = tuple(function_spec(n) for n in (1, 2, 9))
    found = hung_joins(
        _NONE,
        (wire,),
        specs,
        Seating(plans, built, functions, (), stacks),
        terminal_chains(specs, functions, (wire,)),
    )
    assert found == _NONE
