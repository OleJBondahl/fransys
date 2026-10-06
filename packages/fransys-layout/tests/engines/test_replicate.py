"""`replicate_terminals`/`replicate_boundaries`: replica columns added after `columns` (layout-0021,
units spec U1).
"""

import dataclasses
from typing import Any

import pytest
from layout_cabinet import build_cabinet, unit_with_release
from samples import column, connection, function_spec, hid

from fransys_layout.engines.schematic.read import StageInputs, read_inputs
from fransys_layout.engines.schematic.read.units import unit_boundaries, unused_functions
from fransys_layout.geometry import LayoutError
from fransys_layout.stages import Cell, Column, Role, boundary_key, columns_from_chains
from fransys_layout.stages.replicate import (
    UnitBoundary,
    replicate_boundaries,
    replicate_terminals,
)
from fransys_model.kernel import Draft, Id, Model, Origin, freeze, make_id
from fransys_model.vocab import (
    AspectNode,
    Boundary,
    Conductor,
    ConductorKind,
    Function,
    FunctionKind,
    Item,
    Net,
    NetClass,
    Unit,
    functions,
    ports,
)

_ORIGIN = Origin(file="tests/engines/test_replicate.py", line=1, note="replicate tests")
_TERMINAL = function_spec(1, kind="terminal", group=1)
_HOME = column("home", (1,), group=1)
_X2 = ("cabinet", "x2", "1", "fn", "terminal")
_X3 = ("cabinet", "x3", "1", "fn", "terminal")
_X4 = ("cabinet", "x4", "1", "fn", "terminal")


def _replicas(result: tuple[Column, ...], columns: tuple[Column, ...]) -> tuple[Column, ...]:
    return tuple(c for c in result if c not in columns)


def _replica(served: Column, terminal_number: int, spec_key: tuple[str, ...]) -> Column:
    return Column(
        key=(*served.key, "terminal", *spec_key),
        cells=(Cell(function=hid("function", terminal_number), index=0),),
        group=served.group,
        role=served.role,
        location=served.location,
        unit=served.unit,
    )


def test_one_connection_from_another_group_asks_for_one_replica() -> None:
    """Terminal 1 (group 1) wired to function 2 (group 2): a replica beside 2's column."""
    served = column("a", (2,), group=2)
    columns = (_HOME, served)
    result = replicate_terminals(
        columns, (_TERMINAL, function_spec(2, group=2)), (connection(1, 1, 2),)
    )
    assert _replicas(result, columns) == (_replica(served, 1, ("invented", "fn1")),)
    assert [c.key for c in result] == [
        ("invented", "a"),
        ("invented", "a", "terminal", "invented", "fn1"),
        ("invented", "home"),
    ]


def test_many_connections_to_one_group_ask_for_one_replica_of_the_lowest_handle_asker() -> None:
    """Functions 2 and 3, both group 2: one replica, in the column of function 2 (lowest handle)."""
    late = dataclasses.replace(column("z", (2,), group=2), role=Role.POWER)
    early = column("a", (3,), group=2)
    columns = (_HOME, late, early)
    specs = (_TERMINAL, function_spec(2, group=2), function_spec(3, group=2))
    result = replicate_terminals(columns, specs, (connection(2, 1, 3), connection(1, 1, 2)))
    assert _replicas(result, columns) == (_replica(late, 1, ("invented", "fn1")),)


def test_two_groups_ask_for_two_replicas() -> None:
    """Functions 2 (group 2) and 3 (group 3) each get their own replica of terminal 1."""
    a, b = column("a", (2,), group=2), column("b", (3,), group=3)
    columns = (_HOME, a, b)
    specs = (_TERMINAL, function_spec(2, group=2), function_spec(3, group=3))
    result = replicate_terminals(columns, specs, (connection(1, 1, 2), connection(2, 1, 3)))
    found = _replicas(result, columns)
    assert found == (_replica(a, 1, ("invented", "fn1")), _replica(b, 1, ("invented", "fn1")))
    assert found[0].key != found[1].key


def test_a_replica_takes_the_location_role_and_unit_of_the_asking_column() -> None:
    """Same drawing set (one unit, one location) as the terminal's home, another role: the
    replica takes the asker's role and keeps the shared unit and location (layout-0076: a
    replica never leaves its terminal's drawing set, so the location is the home's too)."""
    unit = hid("unit", 9)
    home = dataclasses.replace(_HOME, unit=unit)
    served = dataclasses.replace(
        column("a", (2,), group=2), role=Role.SIGNAL, location=home.location, unit=unit
    )
    columns = (home, served)
    result = replicate_terminals(
        columns, (_TERMINAL, function_spec(2, group=2)), (connection(1, 1, 2),)
    )
    (replica,) = _replicas(result, columns)
    assert replica.location == home.location
    assert replica.role is Role.SIGNAL
    assert replica.unit == unit


@pytest.mark.parametrize("location", [hid("aspect_node", 200), None])
def test_a_replica_across_locations_is_not_asked_for(location) -> None:
    """Layout-0076: `F`'s column and `T`'s home column must share their drawing set, or no
    replica is asked for; at the top level (no unit) that is the location, and the wire is left
    for `links` to draw with a marker pair (or off stubs across top-level locations). An asker
    with no location is another location too (partition's unlocated set), not "the same as
    anyone's". Inside one unit the location no longer splits the set (layout-0081, below)."""
    # UNDO: stages/replicate.py, `replicate_terminals`: `served.drawing_set_key !=
    #     terminal_home.drawing_set_key` -> `served.unit != terminal_home.unit` (the unit-only test)
    served = dataclasses.replace(column("a", (2,), group=2), location=location)
    assert served.location != _HOME.location
    columns = (_HOME, served)
    result = replicate_terminals(
        columns, (_TERMINAL, function_spec(2, group=2)), (connection(1, 1, 2),)
    )
    assert _replicas(result, columns) == ()


@pytest.mark.parametrize("location", [hid("aspect_node", 200), None])
def test_a_replica_across_sub_locations_of_one_unit_is_asked_for(location) -> None:
    """Layout-0081: a unit is one drawing set whatever sub-locations its columns stand in, so
    `F`'s column and `T`'s home column share `drawing_set_key` and a replica IS asked for,
    beside `F` at `F`'s own location. The twin of the top-level test above, which stays."""
    # UNDO: stages/types.py, `Column.drawing_set_key`: the unit branch returns
    #     `(self.unit, self.location)` again (the replica is not asked for)
    unit = hid("unit", 9)
    home = dataclasses.replace(_HOME, unit=unit)
    served = dataclasses.replace(column("a", (2,), group=2), location=location, unit=unit)
    assert served.location != home.location
    columns = (home, served)
    result = replicate_terminals(
        columns, (_TERMINAL, function_spec(2, group=2)), (connection(1, 1, 2),)
    )
    (replica,) = _replicas(result, columns)
    assert (replica.group, replica.unit, replica.location) == (served.group, unit, location)


def test_a_replica_across_units_is_not_asked_for() -> None:
    """Units spec U2: `F`'s column and `T`'s home column must share a unit, or no replica is
    asked for at all -- a foreign unit's terminal never lands on another unit's own pages,
    even though their groups differ (which alone would ask for one)."""
    home = dataclasses.replace(_HOME, unit=hid("unit", 1))
    served = dataclasses.replace(column("a", (2,), group=2), unit=hid("unit", 2))
    columns = (home, served)
    result = replicate_terminals(
        columns, (_TERMINAL, function_spec(2, group=2)), (connection(1, 1, 2),)
    )
    assert _replicas(result, columns) == ()


def test_the_same_shape_within_one_unit_still_replicates() -> None:
    """The near-identical twin: both columns share one (non-`None`) unit, so replication is
    unaffected by the new check -- proves the fix is not a regression of the ordinary case."""
    unit = hid("unit", 9)
    home = dataclasses.replace(_HOME, unit=unit)
    served = dataclasses.replace(column("a", (2,), group=2), unit=unit)
    columns = (home, served)
    result = replicate_terminals(
        columns, (_TERMINAL, function_spec(2, group=2)), (connection(1, 1, 2),)
    )
    assert _replicas(result, columns) == (_replica(served, 1, ("invented", "fn1")),)


def test_a_connection_with_both_ends_on_terminals_asks_for_nothing() -> None:
    """Terminals 1 (group 1) and 2 (group 2) wired together: neither is replicated."""
    columns = (_HOME, column("a", (2,), group=2))
    specs = (_TERMINAL, function_spec(2, kind="terminal", group=2))
    result = replicate_terminals(columns, specs, (connection(1, 1, 2),))
    assert len(result) == 2
    assert _replicas(result, columns) == ()


def test_a_connection_inside_one_group_asks_for_nothing() -> None:
    """Terminal 1 and function 2 both in group 1: the terminal is already on the page."""
    columns = (_HOME, column("a", (2,), group=1))
    specs = (_TERMINAL, function_spec(2, group=1))
    result = replicate_terminals(columns, specs, (connection(1, 1, 2),))
    assert len(result) == 2
    assert _replicas(result, columns) == ()


def test_a_column_with_no_group_is_the_group_none() -> None:
    """A groupless asker differs from a grouped terminal and asks; two groupless do not."""
    served = column("a", (2,), group=None)
    columns = (_HOME, served)
    specs = (_TERMINAL, function_spec(2, group=None))
    result = replicate_terminals(columns, specs, (connection(1, 1, 2),))
    (replica,) = _replicas(result, columns)
    assert replica.group is None

    loose = (column("home", (1,), group=None), served)
    loose_specs = (function_spec(1, kind="terminal", group=None), function_spec(2, group=None))
    assert _replicas(replicate_terminals(loose, loose_specs, (connection(1, 1, 2),)), loose) == ()


def test_the_result_does_not_depend_on_input_order() -> None:
    """Shuffled columns, functions and connections give equal results."""
    a, b = column("a", (2,), group=2), column("b", (3,), group=3)
    columns = (_HOME, a, b)
    specs = (_TERMINAL, function_spec(2, group=2), function_spec(3, group=3))
    wires = (connection(1, 1, 2), connection(2, 1, 3))
    forward = replicate_terminals(columns, specs, wires)
    backward = replicate_terminals(columns[::-1], specs[::-1], wires[::-1])
    assert forward == backward


@pytest.mark.parametrize("missing", ["column", "spec"])
def test_a_connection_end_that_is_not_in_the_inputs_raises(missing: str) -> None:
    """Every end is a drawn function in a column: anything else is an engine-assembly fault."""
    columns = (_HOME,) if missing == "column" else (_HOME, column("a", (2,), group=2))
    specs = (_TERMINAL, function_spec(2, group=2)) if missing == "column" else (_TERMINAL,)
    with pytest.raises(LayoutError):
        replicate_terminals(columns, specs, (connection(1, 1, 2),))


# --- the cabinet ---------------------------------------------------------------------


def _cabinet_pairs(draft: Draft) -> tuple[StageInputs, set[tuple[tuple[str, ...], Id[Any] | None]]]:
    """The inputs, and each replica as (its terminal's function key, its group)."""
    inputs = read_inputs(freeze(draft))
    columns, _ = columns_from_chains(inputs.chains, inputs.functions)
    result = replicate_terminals(columns, inputs.functions, inputs.connections)
    key_of = {spec.function: spec.key for spec in inputs.functions}
    return inputs, {(key_of[r.cells[0].function], r.group) for r in _replicas(result, columns)}


def test_the_cabinet_replicates_exactly_the_terminals_a_connection_needs() -> None:
    """X2:1 (`=SUP`) is wired from `=P1` and `=P2`, and X4:1 (`=P1`) from lamp H1 in `=SUP`."""
    _, pairs = _cabinet_pairs(build_cabinet())
    assert pairs == {
        (_X2, make_id(AspectNode, ("p1",))),
        (_X2, make_id(AspectNode, ("p2",))),
        (_X4, make_id(AspectNode, ("sup",))),
    }


def _cabinet_with_link_between_x3_1_and_lamp(*, wired: bool) -> Draft:
    """The cabinet plus a link from field terminal X3:1 (`=P1`) to lamp H1 (`=SUP`)."""
    model = freeze(build_cabinet())

    def port(function_key: tuple[str, ...], name: str) -> Id[Any]:
        (found,) = (
            p.id
            for p in ports(model).values()
            if functions(model)[p.function].key == function_key and p.name == name
        )
        return found

    ends = (port(_X3, "external"), port(("cabinet", "h1", "fn", "lamp"), "2"))
    key = ("cabinet", "tap")
    record = (
        Conductor(
            id=make_id(Conductor, key),
            key=key,
            a=ends[0],
            b=ends[1],
            kind=ConductorKind.WIRE,
            carrier=None,
        )
        if wired
        else Net(id=make_id(Net, key), key=key, name="TAP", net_class=NetClass.CONTROL, ports=ends)
    )
    draft = build_cabinet()
    draft.extend((record,), origin=_ORIGIN)
    return draft


def test_a_net_group_asks_for_no_replica_but_the_same_ports_as_a_conductor_do() -> None:
    """The twin proves the check can fail: only a conductor makes X3:1 appear in `=SUP`."""
    inputs, pairs = _cabinet_pairs(_cabinet_with_link_between_x3_1_and_lamp(wired=False))
    assert any(group.net == make_id(Net, ("cabinet", "tap")) for group in inputs.net_groups)
    assert all(key != _X3 for key, _ in pairs)

    _, wired = _cabinet_pairs(_cabinet_with_link_between_x3_1_and_lamp(wired=True))
    assert (_X3, make_id(AspectNode, ("sup",))) in wired


# --- board-unit home plans: retired `drop_board_unit_homes` (units spec U1, model-0041) ---
#
# OLD premise, both tests below tested `drop_board_unit_homes` directly: a unit in
# `board_units` (predicate `_reading.board_only_units`, also deleted) got no `PagePlan` of its
# own at all, and a plan of another unit or the top level was unaffected. Both predicates
# existed because a board that only held its own `CONNECTOR` function had nothing else the
# schematic engine drew (board spec B1). NEW premise: after the board-unit carve-out
# (`schematic_functions`, `is_sole_unit_root`, model-0041), a board that is the *sole* root of
# its own unit is a nested unit, not empty furniture, so its home plan is never dropped; there
# is no longer a predicate or a drop function to unit-test directly. NEW assertion: see
# `packages/fransys-layout/tests/engines/test_read.py::
# test_a_board_that_is_the_sole_root_of_its_unit_keeps_its_own_home_page`, which runs the full
# engine over such a board and confirms its home `PagePlan` survives to `Layout.pages` with its
# real content (the board's connector and its child's function) placed on it.


# --- replicate_boundaries (units spec U1's black box) -----------------------------------


def _boundary_model() -> tuple[Model, Id[Any], Unit, Unit]:
    """A bare item/function with no port and no connection at all, declared as the boundary
    of a unit nested one level under a top unit: the minimal shape `replicate_boundaries` needs.
    """
    top, top_release = unit_with_release(("boundary-fixture", "top"), name="top")
    child, child_release = unit_with_release(
        ("boundary-fixture", "child"), name="child", parent=top.id
    )
    item_key = ("boundary-fixture", "owner")
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag="B1",
        description="boundary fixture item",
        unit=child.id,
    )
    function_key = (*item_key, "fn", "x")
    function = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=None,
        name="x",
        kind=FunctionKind.CONNECTOR,
    )
    record_key = (*child.key, "boundary")
    record = Boundary(
        id=make_id(Boundary, record_key), key=record_key, unit=child.id, function=function.id
    )
    draft = Draft()
    draft.extend((top_release, child_release, top, child, item, function, record), origin=_ORIGIN)
    return freeze(draft), function.id, top, child


def _top_level_boundary_model() -> tuple[Model, Id[Any]]:
    """A unit whose own `Unit.parent` is `None`, with a declared boundary function."""
    top, release = unit_with_release(("boundary-fixture", "top-only"), name="top-only")
    item_key = ("boundary-fixture", "top-owner")
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag="B2",
        description="top-level boundary fixture item",
        unit=top.id,
    )
    function_key = (*item_key, "fn", "y")
    function = Function(
        id=make_id(Function, function_key),
        key=function_key,
        item=item.id,
        template=None,
        name="y",
        kind=FunctionKind.CONNECTOR,
    )
    record_key = (*top.key, "boundary")
    record = Boundary(
        id=make_id(Boundary, record_key), key=record_key, unit=top.id, function=function.id
    )
    draft = Draft()
    draft.extend((release, top, item, function, record), origin=_ORIGIN)
    return freeze(draft), function.id


def test_a_boundary_function_gets_a_black_box_replica_in_its_parent_unit() -> None:
    """The replica takes its location, group and role from the home column; its own unit is
    the boundary unit's *parent*, and its key is `boundary_key`'s (units spec U1)."""
    model, function_id, top, child = _boundary_model()
    inputs = read_inputs(model)
    (spec,) = (s for s in inputs.functions if s.function == function_id)
    home = Column(
        key=("boundary-fixture", "home"),
        cells=(Cell(function=function_id, index=0),),
        group=hid("aspect_node", 1),
        role=Role.SIGNAL,
        location=hid("aspect_node", 100),
        unit=child.id,
    )
    result = _replicate_boundaries((home,), model, inputs.functions, (home,))
    (replica,) = _replicas(result, (home,))
    assert replica.cells == (Cell(function=function_id, index=0),)
    assert replica.group == home.group
    assert replica.role == home.role
    assert replica.location == home.location
    assert replica.unit == top.id
    assert replica.key == boundary_key(spec.key, top.key)


def test_the_black_box_takes_its_group_from_the_home_and_not_from_a_terminal_replica() -> None:
    """A terminal replica column of the same function stands in `columns` (after
    `replicate_terminals`) and holds it in a cell too; only `homes` says which is the home
    (layout-0076: the black box took the replica's group, the two keys collided)."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `for column in homes for cell` ->
    #     `for column in columns for cell` (the replica column, keyed after the home, wins)
    model, function_id, top, child = _boundary_model()
    inputs = read_inputs(model)
    home = Column(
        key=("boundary-fixture", "a-home"),
        cells=(Cell(function=function_id, index=0),),
        group=hid("aspect_node", 1),
        role=Role.SIGNAL,
        location=hid("aspect_node", 100),
        unit=child.id,
    )
    terminal_replica = dataclasses.replace(
        home, key=("boundary-fixture", "z-replica"), group=hid("aspect_node", 2)
    )
    result = _replicate_boundaries((home, terminal_replica), model, inputs.functions, (home,))
    (replica,) = _replicas(result, (home, terminal_replica))
    assert replica.group == home.group != terminal_replica.group
    assert replica.unit == top.id


def test_a_boundary_function_with_no_outside_connection_still_replicates() -> None:
    """Can-fail: replication is unconditional, not triggered by a connection -- this fixture's
    function has zero ports and zero conductors and still gets its black-box replica."""
    model, function_id, _, child = _boundary_model()
    inputs = read_inputs(model)
    (spec,) = (s for s in inputs.functions if s.function == function_id)
    assert spec.ports == ()
    home = Column(
        key=("boundary-fixture", "home"),
        cells=(Cell(function=function_id, index=0),),
        group=None,
        role=Role.CONTROL,
        location=None,
        unit=child.id,
    )
    result = _replicate_boundaries((home,), model, inputs.functions, (home,))
    assert len(_replicas(result, (home,))) == 1


def test_a_top_level_units_own_boundary_gets_a_replica_in_the_top_level_set() -> None:
    """`Unit.parent is None`: the black box goes to the top level, not skipped (units spec U1,
    "or the top level"). The replica's own `unit` is `None` and its key uses `boundary_key`'s
    `("top",)` branch."""
    model, function_id = _top_level_boundary_model()
    inputs = read_inputs(model)
    (spec,) = (s for s in inputs.functions if s.function == function_id)
    home = Column(
        key=("boundary-fixture", "top-home"),
        cells=(Cell(function=function_id, index=0),),
        group=hid("aspect_node", 1),
        role=Role.SIGNAL,
        location=hid("aspect_node", 100),
        unit=None,
    )
    result = _replicate_boundaries((home,), model, inputs.functions, (home,))
    (replica,) = _replicas(result, (home,))
    assert replica.cells == (Cell(function=function_id, index=0),)
    assert replica.group == home.group
    assert replica.role == home.role
    assert replica.location == home.location
    assert replica.unit is None
    assert replica.key == boundary_key(spec.key, None)
    assert replica.key[-2:] == ("boundary", "top")


def test_a_boundary_function_with_no_spec_raises() -> None:
    """A unit's boundary names a function `read_inputs` never drew: an assembly fault."""
    model, _function_id, _, _child = _boundary_model()
    with pytest.raises(LayoutError, match="no spec"):
        _replicate_boundaries((), model, (), ())


def test_a_boundary_function_in_no_column_raises() -> None:
    """The function has a spec but no column: also an assembly fault."""
    model, _function_id, _, _child = _boundary_model()
    inputs = read_inputs(model)
    with pytest.raises(LayoutError, match="no column"):
        _replicate_boundaries((), model, inputs.functions, ())


# --- replicate_boundaries over hand-built UnitBoundary values (D8) ------------------------

_PARENT = hid("unit", 7)
_PARENT_KEY = ("invented", "parent")


def test_a_unit_with_one_boundary_function_replicates_it_into_its_parents_column() -> None:
    """One `UnitBoundary`: its function gets one replica, in the parent's unit, keyed by
    `boundary_key`, with the home column's group, role and location."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `unit=unit.parent` ->
    #     `unit=home_column.unit`
    spec = function_spec(1)
    home = column("home", (1,), group=1)
    unit = UnitBoundary(functions=(spec.function,), parent=_PARENT, parent_key=_PARENT_KEY)

    result = replicate_boundaries((home,), (unit,), frozenset(), (spec,), (home,))

    (replica,) = _replicas(result, (home,))
    assert replica.cells == (Cell(function=spec.function, index=0),)
    assert replica.key == boundary_key(spec.key, _PARENT_KEY)
    assert replica.unit == _PARENT
    assert (replica.group, replica.role, replica.location) == (
        home.group,
        home.role,
        home.location,
    )


def test_an_unused_boundary_function_with_no_spec_is_skipped() -> None:
    """W3: a boundary function declared unused draws no pin, so it is no assembly fault."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `if function_id in unused:` -> `if False:`
    ghost = hid("function", 2)
    unit = UnitBoundary(functions=(ghost,), parent=_PARENT, parent_key=_PARENT_KEY)
    home = column("home", (1,), group=1)

    result = replicate_boundaries((home,), (unit,), frozenset({ghost}), (), (home,))

    assert result == (home,)
    with pytest.raises(LayoutError, match="no spec"):
        replicate_boundaries((home,), (unit,), frozenset(), (), (home,))


def test_a_boundary_rail_terminal_keeps_its_replica_and_loses_its_home_cell() -> None:
    """RB2 (layout-0120): the parent draws the terminal; the unit's own pages do not."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `_without_rail_homes(columns, functions)`
    #     -> `columns`
    spec = dataclasses.replace(function_spec(1), rail=True)
    home = column("home", (1,), group=1)
    unit = UnitBoundary(functions=(spec.function,), parent=_PARENT, parent_key=_PARENT_KEY)

    result = replicate_boundaries((home,), (unit,), frozenset(), (spec,), (home,))

    (only,) = result
    assert only.unit == _PARENT
    assert only.cells == (Cell(function=spec.function, index=0),)


def _replicate_boundaries(
    columns: tuple[Column, ...], model: Model, functions: tuple[Any, ...], homes: tuple[Column, ...]
) -> tuple[Column, ...]:
    """The stage fed what `read.units` reads from `model`."""
    return replicate_boundaries(
        columns, unit_boundaries(model), unused_functions(model), functions, homes
    )
