"""WP5 acceptance skeletons for `stages.columns` (ROADMAP WP5, columns.md 6.2), and stage-level
chain discovery (deep-dive D1, D2), which replaced the WP16 ladder discovery."""

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
    PolePair,
    PortRef,
    PortSpec,
    Role,
    columns_from_chains,
)
from fransys_layout.stages.chains import ChainRecords, discover_chains
from fransys_layout.stages.columns import FUNCTION_UNPLACED_IN_COLUMN, build_column
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


def test_a_chain_whose_neighbours_are_not_connected_raises() -> None:
    """A rung is strictly series: no port of 1 and of 3 lies on one physical net."""
    specs = (function_spec(1), function_spec(2), function_spec(3))
    with pytest.raises(HintError):
        columns_from_chains((_chain(1, (1, 3)),), specs)


def test_one_function_in_two_chains_raises() -> None:
    """A function is drawn in one column; two chains claiming it contradict each other."""
    specs = (function_spec(1), function_spec(2), function_spec(3))
    with pytest.raises(HintError):
        columns_from_chains((_chain(1, (1, 2)), _chain(2, (2, 3))), specs)


def test_role_is_the_strongest_port_role_in_the_column() -> None:
    """One function on a power net makes the whole column a power column."""
    specs = (function_spec(1, role=Role.POWER), function_spec(2), function_spec(3))
    columns, _ = columns_from_chains((_chain(1, (1, 2, 3)),), specs)
    assert columns[0].role is Role.POWER


def test_a_column_of_signal_and_control_ports_is_a_control_column() -> None:
    """`CONTROL` beats `SIGNAL`, and no power port means no power column."""
    specs = (function_spec(1, role=Role.SIGNAL), function_spec(2))
    columns, _ = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert columns[0].role is Role.CONTROL


def test_group_hint_overrides_the_aspect_group() -> None:
    """A straddling function is drawn with the hinted group, not its own `=` node."""
    hinted = dataclasses.replace(function_spec(1), group_hint=hid("aspect_node", 9))
    columns, _ = columns_from_chains((), (hinted,))
    assert columns[0].group == hid("aspect_node", 9)


def test_function_in_no_chain_is_its_own_column_with_a_finding() -> None:
    """Nothing is dropped: an unhinted function is placed alone and reported."""
    columns, findings = columns_from_chains((), (function_spec(1),))
    assert [len(c.cells) for c in columns] == [1]
    assert [f.code for f in findings] == [FUNCTION_UNPLACED_IN_COLUMN]


def test_a_chained_function_gives_no_unplaced_finding() -> None:
    """The finding can also stay silent."""
    specs = (function_spec(1), function_spec(2))
    _, findings = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert findings == ()


def test_columns_are_independent_of_input_order() -> None:
    """Shuffled chains and functions give the same columns and the same findings."""
    specs = tuple(function_spec(n) for n in (1, 2, 3, 4, 5, 6))
    chains = (_chain(1, (1, 2)), _chain(2, (3, 4)))
    forward, forward_findings = columns_from_chains(chains, specs)
    backward, backward_findings = columns_from_chains(chains[::-1], specs[::-1])
    assert forward == backward
    assert [f.subjects for f in forward_findings] == [(hid("function", 5),), (hid("function", 6),)]
    assert forward_findings == backward_findings


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


def test_a_chain_column_is_exactly_the_expected_value() -> None:
    """Cells keep the authored indices, the key is the chain's, and entry order is irrelevant."""
    specs = (function_spec(1), function_spec(2))
    chain = Chain(
        chain=hid("layout.chain", 1),
        key=("invented", "chain1"),
        entries=(
            ChainEntry(function=hid("function", 2), index=20),
            ChainEntry(function=hid("function", 1), index=10),
        ),
    )
    columns, findings = columns_from_chains((chain,), specs)
    assert columns == (
        Column(
            key=("invented", "chain1"),
            cells=(
                Cell(function=hid("function", 1), index=10),
                Cell(function=hid("function", 2), index=20),
            ),
            group=hid("aspect_node", 1),
            role=Role.CONTROL,
            location=hid("aspect_node", 100),
        ),
    )
    assert findings == ()


def test_neighbours_joined_by_any_one_port_pair_are_in_series() -> None:
    """One shared physical net is enough, whichever port of each lies on it."""
    upper = _on_nets(function_spec(1), 5, 6)
    lower = _on_nets(function_spec(2), 7, 5)
    (only,), findings = columns_from_chains((_chain(1, (1, 2)),), (upper, lower))
    assert [c.function for c in only.cells] == [hid("function", 1), hid("function", 2)]
    assert findings == ()


def test_neighbours_sharing_no_physical_net_raise_with_their_handles() -> None:
    """The near-identical case of the test above: no net in common."""
    upper = _on_nets(function_spec(1), 5, 6)
    lower = _on_nets(function_spec(2), 7, 8)
    with pytest.raises(HintError, match="not joined") as caught:
        columns_from_chains((_chain(1, (1, 2)),), (upper, lower))
    assert caught.value.subjects == (
        hid("layout.chain", 1),
        hid("function", 1),
        hid("function", 2),
    )


def test_only_consecutive_entries_have_to_be_joined() -> None:
    """1-2-3 is in series though 1 and 3 share nothing."""
    specs = (function_spec(1), function_spec(2), function_spec(3))
    (only,), _ = columns_from_chains((_chain(1, (1, 2, 3)),), specs)
    assert len(only.cells) == 3


def test_a_break_deep_in_the_chain_raises() -> None:
    """2 and 4 are not joined even though 1-2 and 3-4 are."""
    specs = (function_spec(1), function_spec(2), function_spec(3), function_spec(4))
    with pytest.raises(HintError, match="not joined"):
        columns_from_chains((_chain(1, (1, 2, 4)),), specs)


def test_two_entries_at_one_index_raise() -> None:
    """Equal indices give a chain no order; the subjects do not depend on entry order."""
    specs = (function_spec(1), function_spec(2))
    for order in ((1, 2), (2, 1)):
        chain = Chain(
            chain=hid("layout.chain", 1),
            key=("invented", "chain1"),
            entries=tuple(ChainEntry(function=hid("function", n), index=3) for n in order),
        )
        with pytest.raises(HintError, match="share an index") as caught:
            columns_from_chains((chain,), specs)
        assert caught.value.subjects == (
            hid("layout.chain", 1),
            hid("function", 1),
            hid("function", 2),
        )


def test_entries_at_distinct_indices_do_not_raise() -> None:
    """The near-identical twin: the same two functions at indices 3 and 4."""
    specs = (function_spec(1), function_spec(2))
    chain = Chain(
        chain=hid("layout.chain", 1),
        key=("invented", "chain1"),
        entries=(
            ChainEntry(function=hid("function", 1), index=3),
            ChainEntry(function=hid("function", 2), index=4),
        ),
    )
    (only,), _ = columns_from_chains((chain,), specs)
    assert [c.index for c in only.cells] == [3, 4]


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


def test_a_chain_with_one_entry_is_a_column_of_one_cell() -> None:
    """The near-identical twin: one entry is enough."""
    (only,), findings = columns_from_chains((_chain(1, (1,)),), (function_spec(1),))
    assert [c.function for c in only.cells] == [hid("function", 1)]
    assert findings == ()


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


def test_a_group_hint_on_one_cell_overrides_the_aspect_group() -> None:
    """The hint may sit on any cell, not only the first."""
    hinted = dataclasses.replace(function_spec(2), group_hint=hid("aspect_node", 8))
    (with_hint,), _ = columns_from_chains(
        (_chain(1, (1, 2, 3)),), (function_spec(1), hinted, function_spec(3))
    )
    (without,), _ = columns_from_chains(
        (_chain(1, (1, 2, 3)),), (function_spec(1), function_spec(2), function_spec(3))
    )
    assert with_hint.group == hid("aspect_node", 8)
    assert without.group == hid("aspect_node", 1)


def test_cells_hinting_the_same_group_do_not_raise() -> None:
    """Equal hints agree: the column takes that group (and cells without a hint do not object)."""
    first = dataclasses.replace(function_spec(1), group_hint=hid("aspect_node", 8))
    last = dataclasses.replace(function_spec(3), group_hint=hid("aspect_node", 8))
    (only,), _ = columns_from_chains((_chain(1, (1, 2, 3)),), (first, function_spec(2), last))
    assert only.group == hid("aspect_node", 8)


def test_cells_hinting_different_groups_raise_with_their_functions_in_handle_order() -> None:
    """Function 3 comes first in the chain, yet the subjects are (2, 3)."""
    top = dataclasses.replace(function_spec(3), group_hint=hid("aspect_node", 8))
    bottom = dataclasses.replace(function_spec(2), group_hint=hid("aspect_node", 9))
    with pytest.raises(HintError, match="different group hints") as caught:
        columns_from_chains((_chain(1, (3, 2)),), (top, bottom))
    assert caught.value.subjects == (hid("function", 2), hid("function", 3))


def test_a_third_hint_that_differs_from_the_first_two_raises() -> None:
    """Two equal hints are followed by a differing one: the clash is still found."""
    hints = (8, 8, 9)
    specs = tuple(
        dataclasses.replace(function_spec(n), group_hint=hid("aspect_node", h))
        for n, h in zip((1, 2, 3), hints, strict=True)
    )
    with pytest.raises(HintError, match="different group hints") as caught:
        columns_from_chains((_chain(1, (1, 2, 3)),), specs)
    assert caught.value.subjects == (hid("function", 1), hid("function", 3))


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


_NESTED_LOCATION_COLUMNS = 2


def test_two_nested_locations_under_one_parent_stay_two_drawing_sets() -> None:
    """U9: `+ER+C1` and `+ER+C2`, both under `+ER`, must not both take `+ER`'s location."""
    specs = (
        _with_paths(function_spec(1), (1,), (100, 101)),
        _with_paths(function_spec(2), (1,), (100, 101)),
        _with_paths(function_spec(3), (1,), (100, 102)),
        _with_paths(function_spec(4), (1,), (100, 102)),
    )
    chains = (_chain(1, (1, 2)), _chain(2, (3, 4)))
    columns, _ = columns_from_chains(chains, specs)
    assert len(columns) == _NESTED_LOCATION_COLUMNS
    by_function = {c.cells[0].function: c for c in columns}
    first = by_function[hid("function", 1)]
    second = by_function[hid("function", 3)]
    assert {first.location, second.location} == {
        hid("aspect_node", 101),
        hid("aspect_node", 102),
    }
    # The U9 collapse this test guards against: neither location may be the shared parent.
    assert first.location != hid("aspect_node", 100)
    assert second.location != hid("aspect_node", 100)


def test_a_column_whose_cells_share_a_unit_takes_it() -> None:
    """All cells drawn for one unit make a column of that unit (units spec U1)."""
    unit = hid("unit", 1)
    specs = (
        dataclasses.replace(function_spec(1), unit=unit),
        dataclasses.replace(function_spec(2), unit=unit),
    )
    (only,), _ = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert only.unit == unit


def test_a_column_with_no_unit_stays_none() -> None:
    """The legacy case, unchanged: cells with no unit give a column with none."""
    specs = (function_spec(1), function_spec(2))
    (only,), _ = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert only.unit is None


def test_two_cells_of_different_units_raise() -> None:
    """An assembly fault: nothing upstream of `build_column` is to mix units in one column."""
    mixed = (
        dataclasses.replace(function_spec(1), unit=hid("unit", 1)),
        dataclasses.replace(function_spec(2), unit=hid("unit", 2)),
    )
    with pytest.raises(LayoutError, match="different units") as caught:
        columns_from_chains((_chain(1, (1, 2)),), mixed)
    assert "different units" in str(caught.value)


def test_a_column_of_signal_ports_only_is_a_signal_column() -> None:
    """`SIGNAL` is what is left when nothing stronger is present."""
    specs = (function_spec(1, role=Role.SIGNAL), function_spec(2, role=Role.SIGNAL))
    (only,), _ = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert only.role is Role.SIGNAL


def test_power_beats_control_beats_signal_wherever_the_port_is() -> None:
    """A power port on the last cell, mixed with the other roles, still decides."""
    signal = function_spec(1, role=Role.SIGNAL)
    control = function_spec(2, role=Role.CONTROL)
    power = function_spec(3, role=Role.POWER)
    (mixed,), _ = columns_from_chains((_chain(1, (1, 2, 3)),), (signal, control, power))
    (weaker,), _ = columns_from_chains((_chain(1, (1, 2)),), (signal, control))
    assert mixed.role is Role.POWER
    assert weaker.role is Role.CONTROL


def test_the_strongest_port_decides_whichever_port_of_a_function_it_is() -> None:
    """A power port second in port order, on a function that is otherwise signal."""
    signal = function_spec(1, role=Role.SIGNAL)
    mixed = dataclasses.replace(
        signal,
        ports=(signal.ports[0], dataclasses.replace(signal.ports[1], role=Role.POWER)),
    )
    columns, _ = columns_from_chains((), (mixed,))
    assert columns[0].role is Role.POWER


def test_a_function_with_no_ports_is_a_control_column() -> None:
    """No port, no declared net: `CONTROL`, as for a port whose net declares none."""
    portless = dataclasses.replace(function_spec(1), ports=())
    columns, _ = columns_from_chains((), (portless,))
    assert columns[0].role is Role.CONTROL


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


def test_only_the_functions_outside_every_chain_are_reported() -> None:
    """Chained 1-2 is silent; 3 and 4, in no chain, get a finding each, by handle."""
    specs = tuple(function_spec(n) for n in (4, 1, 3, 2))
    columns, findings = columns_from_chains((_chain(1, (1, 2)),), specs)
    assert [f.subjects for f in findings] == [(hid("function", 3),), (hid("function", 4),)]
    assert [len(c.cells) for c in columns] == [2, 1, 1]


def test_columns_sort_by_key_then_by_first_function() -> None:
    """Chain and unplaced columns interleave by key; equal keys are ordered by their functions."""
    same_key = ("invented", "a-same")
    early = dataclasses.replace(function_spec(1), key=same_key)
    late = dataclasses.replace(function_spec(2), key=same_key)
    chain_same = Chain(
        chain=hid("layout.chain", 9),
        key=same_key,
        entries=(ChainEntry(function=hid("function", 3), index=0),),
    )
    specs = (early, late, function_spec(3), function_spec(4))
    forward, _ = columns_from_chains((chain_same,), specs)
    backward, _ = columns_from_chains((chain_same,), specs[::-1])
    assert [(c.key, c.cells[0].function) for c in forward] == [
        (same_key, hid("function", 1)),
        (same_key, hid("function", 2)),
        (same_key, hid("function", 3)),
        (("invented", "fn4"), hid("function", 4)),
    ]
    assert forward == backward


def test_chains_with_equal_keys_are_taken_in_handle_order() -> None:
    """Which of two equally keyed chains raises does not depend on their order."""
    specs = (function_spec(1), function_spec(2), function_spec(3))
    first = _chain(1, (1, 2))
    second = Chain(chain=hid("layout.chain", 2), key=first.key, entries=_chain(2, (2, 3)).entries)
    for chains in ((first, second), (second, first)):
        with pytest.raises(HintError) as caught:
            columns_from_chains(chains, specs)
        assert caught.value.subjects == (hid("layout.chain", 2), hid("function", 2))


# --- stage-level chain discovery (deep-dive D1, D2), which replaced ladder discovery ---
#
# `discover_chains` finds the columns of every function no authored chain claims, from
# connectivity alone: no rails, no search bound, no refusal. Every expected value below is
# derived by hand from D1/D2, on `samples.drawn` (port 13 at `in`, facing N; port 14 at `out`,
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
    return discover_chains(ChainRecords(specs, _drawn_for(specs), wires, (), ()), rank_of=rank_of)


def _functions_of(columns: tuple[Column, ...]) -> list[list[Id[Any]]]:
    """Each column's functions, top to bottom, in the columns' own order."""
    return [[cell.function for cell in column.cells] for column in columns]


def test_a_run_of_two_port_nets_is_one_chain_top_to_bottom() -> None:
    """D1: fn 1's port 14 and fn 2's port 13 alone share a net, so they link in series; the
    directed poles point 13 to 14, so 1 is on top of 2."""
    columns = _discover((function_spec(1), function_spec(2)), (connection(2, 1, 2),))
    assert _functions_of(columns) == [[hid("function", 1), hid("function", 2)]]


def test_the_chain_is_found_from_conductors_not_from_the_physical_net_field() -> None:
    """D1 (chains.py item 2: nets are conductors and declared nets): every port of both functions
    is given one and the same `physical_net`, as a pass-through run of linked devices collapses to
    one in the model. With the wire the chain is still 1-2; without it the same shared
    `physical_net` joins nothing.
    """
    shared = hid("net", 500)

    def on_shared_net(spec: FunctionSpec) -> FunctionSpec:
        ports = tuple(dataclasses.replace(p, physical_net=shared) for p in spec.ports)
        return dataclasses.replace(spec, ports=ports)

    specs = (on_shared_net(function_spec(1)), on_shared_net(function_spec(2)))
    assert _functions_of(_discover(specs, (connection(2, 1, 2),))) == [
        [hid("function", 1), hid("function", 2)]
    ]
    assert sorted(_functions_of(_discover(specs, ()))) == [
        [hid("function", 1)],
        [hid("function", 2)],
    ]


def test_a_fork_net_of_three_ports_ends_every_chain_and_nothing_is_claimed_twice() -> None:
    """D1: fn 1's port 14 is wired to fn 2 and to fn 3, a net of three pole ports, which links
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


def test_two_parallel_chains_through_a_multi_pole_function_are_one_bundle_column() -> None:
    """D2: two chains with one sequence of (item, kind) through a two-pole function (terminal,
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
    (column,) = discover_chains(ChainRecords(specs, drawns, wires, (), ()))
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


def test_discovery_is_independent_of_the_order_of_its_inputs() -> None:
    """D17: the same functions, drawn functions and conductors in the reverse order give equal
    columns. Two chains (1-2 and 3-4-5) so the columns' own order is exercised too."""
    specs = tuple(function_spec(n) for n in (1, 2, 3, 4, 5))
    wires = (connection(2, 1, 2), connection(4, 3, 4), connection(5, 4, 5))
    forward = discover_chains(ChainRecords(specs, _drawn_for(specs), wires, (), ()))
    backward = discover_chains(
        ChainRecords(specs[::-1], _drawn_for(specs)[::-1], wires[::-1], (), ())
    )
    assert forward == backward
    assert sorted(_functions_of(forward)) == [
        [hid("function", 1), hid("function", 2)],
        [hid("function", 3), hid("function", 4), hid("function", 5)],
    ]


def _terminals(first_designation: str, second_designation: str) -> tuple[FunctionSpec, ...]:
    """Terminals 1 and 2, direction-free, with the given designations."""
    return (
        dataclasses.replace(function_spec(1, kind="terminal"), designation=first_designation),
        dataclasses.replace(function_spec(2, kind="terminal"), designation=second_designation),
    )


@pytest.mark.parametrize(
    ("first_end_rank", "second_end_rank", "expected_top"),
    [(1, 0, 2), (0, 1, 1)],
    ids=["the-second-end-is-higher", "the-first-end-is-higher"],
)
def test_a_direction_free_chain_puts_the_end_of_higher_potential_on_top(
    first_end_rank: int, second_end_rank: int, expected_top: int
) -> None:
    """D1 direction: no pole is directed, so "the end net with the higher potential rank is on
    top" (D16: a lower rank number is higher, L1 is 0). The designations say the opposite of the
    ranks each time, so the rank is what decides.
    """
    first, second = _terminals("X1", "X2") if expected_top == 2 else _terminals("X2", "X1")
    rank_of = {
        first.ports[0].port: first_end_rank,  # the first terminal's outer port
        second.ports[1].port: second_end_rank,  # the second terminal's outer port
    }
    columns = _discover((first, second), (connection(2, 1, 2),), rank_of=rank_of)
    other = 1 if expected_top == 2 else 2
    assert _functions_of(columns) == [[hid("function", expected_top), hid("function", other)]]


@pytest.mark.parametrize(
    ("first_designation", "second_designation", "expected_top"),
    [("X1", "X2", 1), ("X2", "X1", 2)],
    ids=["lower-first", "lower-second"],
)
def test_without_a_rank_the_end_item_of_lower_designation_is_on_top(
    first_designation: str, second_designation: str, expected_top: int
) -> None:
    """D1 direction: no directed pole and no potential rank, so "the end item with the lower
    designation is on top", never the model handle (the first is always the lower handle)."""
    specs = _terminals(first_designation, second_designation)
    columns = _discover(specs, (connection(2, 1, 2),))
    other = 1 if expected_top == 2 else 2
    assert _functions_of(columns) == [[hid("function", expected_top), hid("function", other)]]


def test_parallel_contacts_on_the_same_two_nets_are_one_row_with_a_side_element() -> None:
    """D2: K20 and K21 stand on the same two nets, so the later key's (K21) is the side element of
    K20: drawn in K20's row, one lane to the right. The column runs on through the coil to the
    last terminal, and the function is placed once. D1 has no refusal for the reconvergent shape.
    """
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
    cells = {cell.function: cell for cell in column.cells}
    assert len(column.cells) == len(cells) == 5
    assert [f for f in (c.function for c in column.cells) if not cells[f].side] == [
        feed.function,
        k20.function,
        coil.function,
        last.function,
    ]
    assert (cells[k21.function].side, cells[k21.function].lane) == (True, 1)
    assert cells[k21.function].index == cells[k20.function].index
    assert (cells[k20.function].side, cells[k20.function].lane) == (False, 0)
    # the twin: with the keys swapped the other contact is the later one, so it is the side
    swapped_k20 = dataclasses.replace(k20, key=k21.key)
    swapped_k21 = dataclasses.replace(k21, key=k20.key)
    (twin,) = _discover((feed, swapped_k20, swapped_k21, coil, last), wires)
    twin_cells = {cell.function: cell for cell in twin.cells}
    assert (twin_cells[k20.function].side, twin_cells[k21.function].side) == (True, False)


def test_a_side_element_cell_carries_the_function_it_stands_beside() -> None:
    """D2: K21, the side element of K20 (the same two nets as in the test above), has K20's
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


def test_functions_no_net_joins_stand_alone_and_no_input_gives_no_column() -> None:
    """D1: only a net of exactly two pole ports links two poles. Two functions with no conductor
    between them are two one-cell columns, and nothing at all is no column."""
    columns = _discover((function_spec(1), function_spec(2)), ())
    assert sorted(_functions_of(columns)) == [[hid("function", 1)], [hid("function", 2)]]
    assert _discover((), ()) == ()


def test_a_function_left_out_as_already_chained_is_not_pulled_into_a_discovered_chain() -> None:
    """D1: "every function that no authored `layout.chain` claims takes part". The engine leaves a
    chain-claimed function out of `functions`; a wire to it then joins nothing, and discovery never
    places it. Function 2 is alone in its column, function 1 in none.
    """
    fn2 = function_spec(2)
    columns = discover_chains(
        ChainRecords((fn2,), _drawn_for((function_spec(1), fn2)), (connection(2, 1, 2),), (), ())
    )
    assert _functions_of(columns) == [[hid("function", 2)]]


def test_a_one_port_terminal_on_an_unwired_pole_is_still_placed() -> None:
    """D2: pole 1 of a two-pole contact is wired only to a one-port terminal (a hidden side
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
    columns = discover_chains(ChainRecords((feed, multi, load, stub), drawns, wires, (), ()))
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
    """D1: T2's wire to T1 lands on its port 14 (S), so T2 is flipped; T1 (entered by N) is not."""
    # UNDO: stages/columns.py `_entered_from_south`: `== "s"` -> `== "n"` (flips T1, not T2)
    wire = _wire(1, (function_spec(1), 1), (function_spec(2), 1))
    assert _flipped((1, 2), (wire,), kinds={}) == {hid("function", 2)}


def test_a_one_entry_chain_is_not_flipped() -> None:
    """D1: a lone terminal has no neighbour to be entered from, whatever its ports face."""
    # UNDO: stages/columns.py `_entered_from_south`: the last `else: continue` ->
    # `else: entries = [spec.ports[1]]` (the S port is taken as the entry)
    assert _flipped((2,), (), kinds={}) == set()


def test_terminals_joined_only_through_a_net_group_are_not_flipped() -> None:
    """D1: no conductor joins T1 and T2 (the chain rests on a net group), so no entry port shows."""
    # UNDO: stages/columns.py `_entered_from_south`: `entries = [...]` of the `at > 0` branch
    # -> `entries = [...] or list(spec.ports[1:])` (falls back to the S port)
    assert _flipped((1, 2), (), kinds={}) == set()


def test_a_terminal_whose_entry_port_is_not_unique_is_not_flipped() -> None:
    """D1: both ports of T2 are wired to T1, so neither is the entry port: not flipped."""
    # UNDO: stages/columns.py `_entered_from_south`: `if len(entries) != 1: continue` ->
    # `if not entries: continue`, and `(entry,) = entries` -> `entry = entries[-1]`
    one, two = function_spec(1), function_spec(2)
    wires = (_wire(1, (one, 1), (two, 0)), _wire(2, (one, 1), (two, 1)))
    assert _flipped((1, 2), wires, kinds={}) == set()


def test_a_mixed_chain_flips_only_the_terminal_that_is_entered_from_south() -> None:
    """D1: a breaker then a terminal wired to the breaker's port 13 flips the terminal alone."""
    # UNDO: stages/columns.py `_entered_from_south`: drop `not spec.roles.terminal or` from the
    # first guard (the breaker's own S port is then read as an entry and flips it too)
    breaker, terminal = function_spec(1), function_spec(2, kind="terminal")
    wire = _wire(1, (breaker, 0), (terminal, 1))
    assert _flipped((1, 2), (wire,), kinds={1: "contact_no"}) == {hid("function", 2)}


def test_a_terminal_of_a_chain_missing_from_a_given_drawn_raises() -> None:
    """D1: `drawn` names some functions but not T2: its facing is unknown, a `LayoutError`."""
    # UNDO: stages/columns.py `_entered_from_south`: `if drawn_of:` -> `if False:` (skips T2)
    wire = _wire(1, (function_spec(1), 1), (function_spec(2), 1))
    with pytest.raises(LayoutError):
        _flipped((1, 2), (wire,), kinds={}, drawn_numbers=(1,))


def test_a_terminal_port_that_maps_to_no_symbol_port_raises() -> None:
    """D1: T2's drawn function maps only one of its two ports: a `LayoutError`, not a skip."""
    # UNDO: stages/columns.py `_entered_from_south`: delete the `not in symbol_port` check
    one, two = function_spec(1, kind="terminal"), function_spec(2, kind="terminal")
    two_drawn = drawn(2, kind="terminal")
    short = dataclasses.replace(two_drawn, ports=two_drawn.ports[:1])
    with pytest.raises(LayoutError):
        columns_from_chains(
            (_chain(1, (1, 2)),),
            (one, two),
            drawn=(drawn(1, kind="terminal"), short),
            connections=(_wire(1, (one, 1), (two, 1)),),
        )


# --- D8: a cross-unit mate stands at an end of its column, the replica outside it ---


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
        )
    )
    cells = {cell.function: cell for cell in column.cells}
    return column, cells[plug.function], cells[pin.function], cells[relay.function]


def test_at_a_top_end_the_replica_is_in_the_row_before_the_turned_parent_side_pin() -> None:
    """D8: the chain enters the edge pole from the unit edge: the replica (R0, face to face with
    the plug's N face) heads the column, the plug under it is turned (R180), its wire runs down."""
    # UNDO: stages/_chain_cells.py `_position_rows`: `rows.append((face_above, []))` after its own
    # (the replica row goes below again) fails the index asserts
    column, plug, pin, relay = _edge_column(top=True)
    assert [cell.function for cell in column.cells] == [pin.function, plug.function, relay.function]
    assert (pin.index, plug.index, relay.index) == (0, 1, 2)
    assert (pin.flip, pin.face, pin.replica, pin.host) == (False, True, True, plug.function)
    assert plug.flip is True


def test_at_a_bottom_end_the_replica_is_in_the_row_after_the_plug_and_turned() -> None:
    """D8: the control, today's shape: the plug ends the column, the replica under it at R180."""
    column, plug, pin, relay = _edge_column(top=False)
    assert [cell.function for cell in column.cells] == [relay.function, plug.function, pin.function]
    assert (relay.index, plug.index, pin.index) == (0, 1, 2)
    assert (pin.flip, pin.face, pin.replica, pin.host) == (True, True, True, plug.function)
    assert plug.flip is False


def test_an_external_member_does_not_count_toward_a_columns_group() -> None:
    """layout-0103: a +EXT pin (no group) stands in the column of the in-scope pins it joins."""
    # UNDO: stages/columns.py:build_column, drop the `if s.group_path` filter
    external, inside = function_spec(1, group=None), function_spec(2, group=1)
    cells = (Cell(function=external.function, index=0), Cell(function=inside.function, index=1))
    column = build_column(("invented", "mixed"), cells, (external, inside))
    assert column.group == hid("aspect_node", 1)
    only = build_column(("invented", "alone"), cells[:1], (external,))
    assert only.group is None, "a column of external members alone has no group"
