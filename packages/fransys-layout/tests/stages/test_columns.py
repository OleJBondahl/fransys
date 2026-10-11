"""Acceptance skeletons for `stages.columns`, and stage-level
chain discovery, which replaced the ladder discovery."""

import dataclasses
from typing import Any

import pytest
from samples import connection, drawn, function_spec, hid, through_geometry

from fransys_layout.geometry import (
    Facing,
    HintError,
    LayoutError,
    Point,
    PortGeometry,
    ThroughPath,
)
from fransys_layout.stages import (
    Cell,
    Chain,
    ChainEntry,
    Column,
    Connection,
    DrawnFunction,
    DrawnPort,
    FunctionSpec,
    Home,
    PolePair,
    PortRef,
    PortSpec,
    Role,
    columns_from_chains,
)
from fransys_layout.stages.chains import ChainRecords, discover_chains
from fransys_layout.stages.columns import FUNCTION_UNPLACED_IN_COLUMN
from fransys_layout.stages.types import MatedFunctions
from fransys_model.kernel import Id, Severity


def _chain(number: int, functions: tuple[int, ...]) -> Chain:
    return Chain(
        chain=hid("layout.chain", number),
        key=("invented", f"chain{number}"),
        entries=tuple(
            ChainEntry(function=hid("function", f), index=i) for i, f in enumerate(functions)
        ),
    )


def test_a_chain_becomes_one_column_in_index_order() -> None:
    """Chain 1-2-3, connected in series, is one column with cells in index order."""
    specs = (function_spec(1), function_spec(2), function_spec(3))
    columns, findings = columns_from_chains((_chain(1, (1, 2, 3)),), specs)
    (only,) = columns
    assert [c.function for c in only.cells] == [hid("function", n) for n in (1, 2, 3)]
    assert only.group == hid("aspect_node", 1)
    assert only.location == hid("aspect_node", 100)
    assert findings == ()


def test_function_in_no_chain_is_its_own_column_with_a_finding() -> None:
    """Nothing is dropped: an unhinted function is placed alone and reported."""
    columns, findings = columns_from_chains((), (function_spec(1),))
    assert [len(c.cells) for c in columns] == [1]
    assert [f.code for f in findings] == [FUNCTION_UNPLACED_IN_COLUMN]


def _on_nets(spec: FunctionSpec, *nets: int) -> FunctionSpec:
    """`spec` with its ports, in order, moved to physical nets `nets`."""
    ports = tuple(
        dataclasses.replace(port, physical_net=hid("net", net))
        for port, net in zip(spec.ports, nets, strict=True)
    )
    return dataclasses.replace(spec, ports=ports)


def _with_paths(
    spec: FunctionSpec, group: tuple[int, ...], location: tuple[int, ...] = (100,)
) -> FunctionSpec:
    return dataclasses.replace(
        spec,
        group_path=tuple(hid("aspect_node", n) for n in group),
        location_path=tuple(hid("aspect_node", n) for n in location),
    )


def test_one_function_twice_in_a_chain_raises() -> None:
    """Twice in one chain is as much a contradiction as once in each of two."""
    specs = (function_spec(1), function_spec(2))
    with pytest.raises(HintError, match="twice in one chain") as caught:
        columns_from_chains((_chain(1, (1, 2, 1)),), specs)
    assert caught.value.subjects == (hid("layout.chain", 1), hid("function", 1))


def test_a_chain_naming_an_undrawn_function_raises() -> None:
    """A hint on a function that is not drawn is not silently dropped."""
    specs = (function_spec(1),)
    with pytest.raises(HintError, match="not drawn") as caught:
        columns_from_chains((_chain(1, (1, 2)),), specs)
    assert caught.value.subjects == (hid("layout.chain", 1), hid("function", 2))
    (only,), _ = columns_from_chains((_chain(1, (1,)),), specs)
    assert len(only.cells) == 1


def test_a_chain_with_no_entries_raises() -> None:
    """A stub chain is a hint that places nothing; it is reported, not skipped."""
    with pytest.raises(HintError, match="no entries") as caught:
        columns_from_chains((_chain(1, ()),), (function_spec(1),))
    assert caught.value.subjects == (hid("layout.chain", 1),)


def test_the_group_is_the_deepest_node_the_cells_share() -> None:
    """(1, 2) and (1, 3) share 1; (1, 2) and (1, 2) share 2."""
    apart = (
        _with_paths(function_spec(1), (1, 2)),
        _with_paths(function_spec(2), (1, 3)),
    )
    together = (
        _with_paths(function_spec(1), (1, 2)),
        _with_paths(function_spec(2), (1, 2)),
    )
    (up,), _ = columns_from_chains((_chain(1, (1, 2)),), apart)
    (down,), _ = columns_from_chains((_chain(1, (1, 2)),), together)
    assert up.group == hid("aspect_node", 1)
    assert down.group == hid("aspect_node", 2)


def test_a_shallower_path_limits_the_group() -> None:
    """A cell directly under node 1 pulls the column up to 1."""
    specs = (
        _with_paths(function_spec(1), (1,)),
        _with_paths(function_spec(2), (1, 2)),
    )
    (only,), _ = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert only.group == hid("aspect_node", 1)


def test_cells_with_no_common_group_give_a_column_without_one() -> None:
    """Different roots share no node; a cell with no `=` placement is external (0103)."""
    roots = (_with_paths(function_spec(1), (1,)), _with_paths(function_spec(2), (2,)))
    bare = (_with_paths(function_spec(1), (1,)), _with_paths(function_spec(2), ()))
    (first,), _ = columns_from_chains((_chain(1, (1, 2)),), roots)
    (second,), _ = columns_from_chains((_chain(1, (1, 2)),), bare)
    assert first.group is None
    assert second.group == hid("aspect_node", 1)


def test_cells_hinting_different_groups_raise_with_their_functions_in_handle_order() -> None:
    """Function 3 comes first in the chain, yet the subjects are (2, 3)."""
    top = dataclasses.replace(function_spec(3), group_hint=hid("aspect_node", 8))
    bottom = dataclasses.replace(function_spec(2), group_hint=hid("aspect_node", 9))
    with pytest.raises(HintError, match="different group hints") as caught:
        columns_from_chains((_chain(1, (3, 2)),), (top, bottom))
    assert caught.value.subjects == (hid("function", 2), hid("function", 3))


_NESTED_LOCATION_COLUMNS = 2


def test_two_cells_of_different_units_raise() -> None:
    """An assembly fault: nothing upstream of `build_column` is to mix units in one column."""
    mixed = (
        dataclasses.replace(function_spec(1), unit=hid("unit", 1)),
        dataclasses.replace(function_spec(2), unit=hid("unit", 2)),
    )
    with pytest.raises(LayoutError, match="different units") as caught:
        columns_from_chains((_chain(1, (1, 2)),), mixed)
    assert "different units" in str(caught.value)


def test_an_unplaced_function_column_and_finding_are_exactly_the_expected_values() -> None:
    """The column is keyed by the function's own key, cell index 0."""
    columns, findings = columns_from_chains((), (function_spec(4),))
    assert columns == (
        Column(
            key=("invented", "fn4"),
            cells=(Cell(function=hid("function", 4), index=0),),
            group=hid("aspect_node", 1),
            role=Role.CONTROL,
            location=hid("aspect_node", 100),
        ),
    )
    assert [(f.code, f.severity, f.subjects) for f in findings] == [
        (FUNCTION_UNPLACED_IN_COLUMN, Severity.INFO, (hid("function", 4),))
    ]


# --- stage-level chain discovery, which replaced ladder discovery ---
#
# `discover_chains` finds the columns of every function no authored chain claims, from
# connectivity alone: no rails, no search bound, no refusal. Every expected value below is
# derived by hand, on `samples.drawn` (port 13 at `in`, facing N; port 14 at `out`,
# facing S), so a lone directed pole runs top to bottom from 13 to 14.


def _drawn_for(specs: tuple[FunctionSpec, ...]) -> tuple[DrawnFunction, ...]:
    """`samples.drawn` for each two-port `function_spec`, as its number and kind give."""
    return tuple(drawn(int(spec.function.value, 16), kind=spec.kind) for spec in specs)


def _discover(
    specs: tuple[FunctionSpec, ...],
    wires: tuple[Connection, ...],
    *,
    rank_of: dict[Id[Any], int] | None = None,
) -> tuple[Column, ...]:
    return discover_chains(
        ChainRecords(specs, _drawn_for(specs), wires, (), ()), rank_of=rank_of, key_order={}
    )


def _functions_of(columns: tuple[Column, ...]) -> list[list[Id[Any]]]:
    """Each column's functions, top to bottom, in the columns' own order."""
    return [[cell.function for cell in column.cells] for column in columns]


def test_a_run_of_two_port_nets_is_one_chain_top_to_bottom() -> None:
    """Fn 1's port 14 and fn 2's port 13 alone share a net, so they link in series; the
    directed poles point 13 to 14, so 1 is on top of 2."""
    columns = _discover((function_spec(1), function_spec(2)), (connection(2, 1, 2),))
    assert _functions_of(columns) == [[hid("function", 1), hid("function", 2)]]


def _two_pole_function(number: int) -> tuple[FunctionSpec, DrawnFunction]:
    """A contact of two poles, ports "1"-"2" and "3"-"4" (model ports `number * 10 + 1..4`),
    drawn with each pole's first port facing N and its second S."""
    names = ("1", "2", "3", "4")
    ports = tuple(
        PortSpec(
            port=hid("port", number * 10 + i + 1),
            name=name,
            physical_net=hid("net", 700 + i),
            role=Role.CONTROL,
        )
        for i, name in enumerate(names)
    )
    pairs = (PolePair(index=0, first="1", second="2"), PolePair(index=1, first="3", second="4"))
    spec = dataclasses.replace(function_spec(number), poles=2, pole_pairs=pairs, ports=ports)
    symbols = ("1.in", "1.out", "2.in", "2.out")
    facings = (Facing.N, Facing.S, Facing.N, Facing.S)
    geometry = dataclasses.replace(
        through_geometry(),
        poles=2,
        through=ThroughPath(start="1.in", end="1.out"),
        ports=tuple(
            PortGeometry(
                name=symbol, at=Point(x=16 * (i // 2), y=-16 if i % 2 == 0 else 16), facing=facing
            )
            for i, (symbol, facing) in enumerate(zip(symbols, facings, strict=True))
        ),
    )
    return spec, DrawnFunction(
        function=spec.function,
        item=spec.item,
        key=spec.key,
        kind="contact_no",
        geometry=geometry,
        ports=tuple(
            DrawnPort(port=port.port, symbol_port=symbol)
            for port, symbol in zip(ports, symbols, strict=True)
        ),
        primary_in="1.in",
        primary_out="1.out",
    )


def _wire(number: int, a: tuple[FunctionSpec, int], b: tuple[FunctionSpec, int]) -> Connection:
    """One conductor: port index `a[1]` of function `a[0]` to port index `b[1]` of `b[0]`."""
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", 800 + number),
        role=Role.CONTROL,
        a=PortRef(function=a[0].function, port=a[0].ports[a[1]].port),
        b=PortRef(function=b[0].function, port=b[0].ports[b[1]].port),
    )


def _terminals(first_designation: str, second_designation: str) -> tuple[FunctionSpec, ...]:
    """Terminals 1 and 2, direction-free, with the given designations."""
    return (
        dataclasses.replace(function_spec(1, kind="terminal"), designation=first_designation),
        dataclasses.replace(function_spec(2, kind="terminal"), designation=second_designation),
    )


def test_a_one_port_terminal_on_an_unwired_pole_is_still_placed() -> None:
    """Pole 1 of a two-pole contact is wired only to a one-port terminal (a hidden side
    element); pole 0 is in a longer chain. The pole counts as wired, so the terminal's host stays.
    """
    # UNDO: stages/_chain_walk.py `drop_unwired_poles`: count `members` (hidden ports removed), not
    # the unfiltered net sizes
    multi, multi_drawn = _two_pole_function(10)
    feed, load = function_spec(1, kind="terminal"), function_spec(3, kind="terminal")
    stub = function_spec(5, kind="terminal")
    stub = dataclasses.replace(stub, ports=stub.ports[:1], poles=0, pole_pairs=())
    stub_drawn = drawn(5, kind="terminal")
    stub_drawn = dataclasses.replace(stub_drawn, ports=stub_drawn.ports[:1])
    wires = (
        _wire(1, (feed, 1), (multi, 0)),
        _wire(2, (multi, 1), (load, 0)),
        _wire(3, (stub, 0), (multi, 3)),
    )
    drawns = (*_drawn_for((feed,)), multi_drawn, *_drawn_for((load,)), stub_drawn)
    columns = discover_chains(
        ChainRecords((feed, multi, load, stub), drawns, wires, (), ()), key_order={}
    )
    assert stub.function in {cell.function for column in columns for cell in column.cells}


def _flipped(
    functions: tuple[int, ...],
    wires: tuple[Connection, ...],
    *,
    kinds: dict[int, str],
    drawn_numbers: tuple[int, ...] | None = None,
) -> set[Id[Any]]:
    """The functions `columns_from_chains` flips for the chain `functions`, its wires `wires`."""
    specs = tuple(function_spec(n, kind=kinds.get(n, "terminal")) for n in functions)
    shown = tuple(drawn(n, kind=kinds.get(n, "terminal")) for n in (drawn_numbers or functions))
    (column,), _ = columns_from_chains(
        (_chain(1, functions),), specs, drawn=shown, connections=wires
    )
    return {cell.function for cell in column.cells if cell.flip}


def test_a_terminal_entered_by_its_south_port_is_flipped() -> None:
    """T2's wire to T1 lands on its port 14 (S), so T2 is flipped; T1 (entered by N) is not."""
    # UNDO: stages/columns.py `_entered_from_south`: `== "s"` -> `== "n"` (flips T1, not T2)
    wire = _wire(1, (function_spec(1), 1), (function_spec(2), 1))
    assert _flipped((1, 2), (wire,), kinds={}) == {hid("function", 2)}


# --- A cross-unit mate stands at an end of its column, the replica outside it ---


def _edge_column(*, top: bool) -> tuple[Column, Cell, Cell, Cell]:
    """The column of one two-port function 1 and a plug 5 mated across a unit edge to pin 6.

    `top`: the plug's wire runs to port 13 (the N port), so the chain enters from the unit edge
    and the plug heads it; else the wire runs from port 14, the plug ends the column.
    """
    plug = dataclasses.replace(function_spec(5, kind="terminal"), pole_pairs=())
    plug = dataclasses.replace(plug, ports=plug.ports[:1])
    pin = dataclasses.replace(function_spec(6, kind="terminal"), pole_pairs=())
    pin = dataclasses.replace(pin, ports=pin.ports[:1])
    relay = function_spec(1)
    plug_port = PortRef(function=plug.function, port=plug.ports[0].port)
    relay_port = PortRef(function=relay.function, port=relay.ports[0 if top else 1].port)
    wire = Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 801),
        role=Role.CONTROL,
        a=plug_port if top else relay_port,
        b=relay_port if top else plug_port,
    )
    (column,) = discover_chains(
        ChainRecords(
            (relay, plug, pin),
            (drawn(1),),
            (wire,),
            (),
            (),
            edge_mates=(MatedFunctions(a=plug.function, b=pin.function),),
        ),
        key_order={},
    )
    cells = {cell.function: cell for cell in column.cells}
    return column, cells[plug.function], cells[pin.function], cells[relay.function]


def test_at_a_bottom_end_the_replica_is_in_the_row_after_the_plug_and_turned() -> None:
    """The control, today's shape: the plug ends the column, the replica under it at R180."""
    column, plug, pin, relay = _edge_column(top=False)
    assert [cell.function for cell in column.cells] == [relay.function, plug.function, pin.function]
    assert (relay.index, plug.index, pin.index) == (0, 1, 2)
    assert (pin.flip, pin.face, pin.home, pin.host) == (True, True, Home.ELSEWHERE, plug.function)
    assert plug.flip is False


def test_the_location_is_the_deepest_node_the_cells_share() -> None:
    """Node 101 nested under 100 when both cells reach it, else just 100 where they diverge;
    two different roots or one cell with no `+` path give no location at all."""
    deep = (
        _with_paths(function_spec(1), (1,), (100, 101)),
        _with_paths(function_spec(2), (1,), (100, 102)),
    )
    same_leaf = (
        _with_paths(function_spec(1), (1,), (100, 101)),
        _with_paths(function_spec(2), (1,), (100, 101)),
    )
    apart = (
        _with_paths(function_spec(1), (1,), (100,)),
        _with_paths(function_spec(2), (1,), (200,)),
    )
    bare = (
        _with_paths(function_spec(1), (1,), (100,)),
        _with_paths(function_spec(2), (1,), ()),
    )
    (shared,), _ = columns_from_chains((_chain(1, (1, 2)),), deep)
    (split,), _ = columns_from_chains((_chain(1, (1, 2)),), apart)
    (missing,), _ = columns_from_chains((_chain(1, (1, 2)),), bare)
    (same,), _ = columns_from_chains((_chain(1, (1, 2)),), same_leaf)
    assert shared.location == hid("aspect_node", 100)
    assert same.location == hid("aspect_node", 101)
    assert split.location is None
    assert missing.location is None


def test_a_fork_net_of_three_ports_ends_every_chain_and_nothing_is_claimed_twice() -> None:
    """Fn 1's port 14 is wired to fn 2 and to fn 3, a net of three pole ports, which links
    nothing. Three one-cell columns, no trunk-and-branch column (that was ladder discovery):
    every function in exactly one column.
    """
    specs = (function_spec(1), function_spec(2), function_spec(3))
    columns = _discover(specs, (connection(2, 1, 2), connection(3, 1, 3)))
    assert sorted(_functions_of(columns)) == [
        [hid("function", 1)],
        [hid("function", 2)],
        [hid("function", 3)],
    ]


def test_two_parallel_chains_through_a_multi_pole_function_are_one_bundle_column() -> None:
    """Two chains with one sequence of (item, kind) through a two-pole function (terminal,
    contact, terminal, each) form one bundle column: rows are chain positions, the contact is one
    cell, and the poles stand side by side (lane 0 for pole 0's chain, lane 1 for pole 1's).
    """
    multi, multi_drawn = _two_pole_function(10)
    feed_a, feed_b = function_spec(1, kind="terminal"), function_spec(2, kind="terminal")
    load_a, load_b = function_spec(3, kind="terminal"), function_spec(4, kind="terminal")
    specs = (feed_a, feed_b, multi, load_a, load_b)
    wires = (
        _wire(1, (feed_a, 1), (multi, 0)),  # feed A -> pole 0, in
        _wire(2, (multi, 1), (load_a, 0)),  # pole 0, out -> load A
        _wire(3, (feed_b, 1), (multi, 2)),  # feed B -> pole 1, in
        _wire(4, (multi, 3), (load_b, 0)),  # pole 1, out -> load B
    )
    drawns = (*_drawn_for((feed_a, feed_b)), multi_drawn, *_drawn_for((load_a, load_b)))
    (column,) = discover_chains(ChainRecords(specs, drawns, wires, (), ()), key_order={})
    cells = {cell.function: cell for cell in column.cells}
    assert len(column.cells) == len(cells) == 5  # the contact is one cell, not two
    assert {f: (c.index, c.side) for f, c in cells.items()} == {
        feed_a.function: (0, False),
        feed_b.function: (0, False),
        multi.function: (1, False),
        load_a.function: (2, False),
        load_b.function: (2, False),
    }
    assert cells[feed_a.function].lane == 0
    assert cells[feed_b.function].lane == 1
    assert cells[load_a.function].lane == 0
    assert cells[load_b.function].lane == 1


def test_a_side_element_cell_carries_the_function_it_stands_beside() -> None:
    """K21, the side element of K20 (the same two nets as in the test above), has K20's
    function as its `carrier`; every other cell of the column has none."""
    # UNDO: stages/_chain_cells.py `_side_cell`, the plain side Cell: drop `carrier=carrier_of[...]`
    feed, k20, k21 = function_spec(1, kind="terminal"), function_spec(20), function_spec(21)
    coil, last = function_spec(22, kind="coil"), function_spec(9, kind="terminal")
    wires = (
        _wire(1, (feed, 1), (k20, 0)),
        _wire(2, (feed, 1), (k21, 0)),
        _wire(3, (k20, 1), (coil, 0)),
        _wire(4, (k21, 1), (coil, 0)),
        _wire(5, (coil, 1), (last, 0)),
    )
    (column,) = _discover((feed, k20, k21, coil, last), wires)
    carriers = {cell.function: (cell.side, cell.carrier) for cell in column.cells}
    assert carriers == {
        feed.function: (False, None),
        k20.function: (False, None),
        k21.function: (True, k20.function),
        coil.function: (False, None),
        last.function: (False, None),
    }


def test_at_a_top_end_the_replica_is_in_the_row_before_the_turned_parent_side_pin() -> None:
    """The chain enters the edge pole from the unit edge: the replica (R0, face to face with
    the plug's N face) heads the column, the plug under it is turned (R180), its wire runs down."""
    # UNDO: stages/_chain_cells.py `_position_rows`: `rows.append((face_above, []))` after its own
    # (the replica row goes below again) fails the index asserts
    column, plug, pin, relay = _edge_column(top=True)
    assert [cell.function for cell in column.cells] == [pin.function, plug.function, relay.function]
    assert (pin.index, plug.index, relay.index) == (0, 1, 2)
    assert (pin.flip, pin.face, pin.home, pin.host) == (False, True, Home.ELSEWHERE, plug.function)
    assert plug.flip is True
