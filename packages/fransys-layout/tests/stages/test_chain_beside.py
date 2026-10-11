"""A chain stood beside a host (layout-0174): its reading order, its link, its horizontal joins.

Function `n` is the sample through symbol (`samples`): model port `13` at the top (`in`, N) on net
`n - 1` and `14` below (`out`, S) on net `n`. The host takes other nets so a branch of functions
2 and 3 (end nets 1 and 3) leaves it by two of its nets.
"""

from dataclasses import replace

from samples import drawn, function_spec, hid
from test_joins import _spots, _wire

from fransys_layout.geometry import WIRING_GRID, Facing
from fransys_layout.stages import Chain, ChainEntry, columns_from_chains
from fransys_layout.stages._chain_beside import beside_hosts, beside_links
from fransys_layout.stages.references.beside_runs import beside_runs, joined_pairs

_HOST = hid("function", 1)
_ROOMS = {(1, 1): 800}


def _host(top_net: int, bottom_net: int):
    """Function 1 with its top port on net `top_net` and its bottom port on `bottom_net`."""
    spec = function_spec(1)
    top, bottom = spec.ports
    return replace(
        spec,
        ports=(
            replace(top, physical_net=hid("net", top_net)),
            replace(bottom, physical_net=hid("net", bottom_net)),
        ),
    )


def _columns(top_net: int, bottom_net: int):
    chain = Chain(
        chain=hid("layout.chain", 2),
        key=("invented", "branch"),
        entries=tuple(
            ChainEntry(function=hid("function", f), index=i) for i, f in enumerate((2, 3))
        ),
        beside=_HOST,
    )
    host = Chain(
        chain=hid("layout.chain", 1),
        key=("invented", "host"),
        entries=(ChainEntry(function=_HOST, index=0),),
    )
    specs = (_host(top_net, bottom_net), function_spec(2), function_spec(3))
    columns, _ = columns_from_chains((chain, host), specs, drawn=(drawn(1), drawn(2), drawn(3)))
    return {column.key[-1]: column for column in columns}


def _order(column) -> list[int]:
    return [cell.function.value for cell in column.cells]


def test_a_branch_whose_first_end_is_the_hosts_lower_net_reads_reversed() -> None:
    """The branch 2, 3 leaves net 1 first; the host's net 1 is its bottom, so 3 stands on top."""
    # UNDO: stages/_chain_beside.py `_upside_down`: `first > last` -> `first < last`
    by_key = _columns(top_net=3, bottom_net=1)
    assert [cell.index for cell in by_key["branch"].cells] == [0, 1]
    assert [cell.function for cell in by_key["branch"].cells] == [
        hid("function", 3),
        hid("function", 2),
    ]
    assert by_key["branch"].beside == _HOST


def test_a_branch_whose_first_end_is_the_hosts_upper_net_keeps_its_order() -> None:
    by_key = _columns(top_net=1, bottom_net=3)
    assert [cell.function for cell in by_key["branch"].cells] == [
        hid("function", 2),
        hid("function", 3),
    ]


def test_a_beside_column_is_linked_to_its_hosts_column() -> None:
    """`beside_hosts` maps the branch column to the host's; `beside_links` is that pair, sorted."""
    # UNDO: stages/_chain_beside.py `beside_hosts`: `column.beside in homes` -> `False`
    by_key = _columns(top_net=3, bottom_net=1)
    columns = tuple(by_key.values())
    assert beside_hosts(columns) == {by_key["branch"].key: by_key["host"].key}
    assert beside_links(columns) == {tuple(sorted((by_key["branch"].key, by_key["host"].key)))}


def _runs(hosts, rooms):
    """Function 1 (host) in column a, function 3 (branch) in column b: its top joins a's bottom."""
    spots = _spots(("a", (1,)), ("b", (3,)))
    a, b = ("invented", "a"), ("invented", "b")
    wire = _wire(1, (1, 2), (3, 1))
    (x,) = spots[wire.a.port]
    (y,) = spots[wire.b.port]
    return wire, beside_runs([(wire, x, y)], hosts(a, b), rooms)


def test_the_wire_between_a_beside_column_and_its_host_is_one_aligned_run() -> None:
    """Both ends are in one run `place` aligns, flagged `aside`, and the wire is a joined pair."""
    # UNDO: references/beside_runs.py `_is_beside`: drop `or hosts.get(y.column) == x.column`
    wire, (joined, runs, refused) = _runs(lambda a, b: {b: a}, _ROOMS)
    assert [c for c, _, _ in joined] == [wire]
    assert refused == []
    (run,) = runs
    assert run.aside
    assert {end.port for end in run.ends} == {wire.a.port, wire.b.port}
    assert joined_pairs(joined) == {(wire.a.port, wire.b.port): {1}}


def test_a_wire_that_leaves_the_page_room_is_refused() -> None:
    """Lowering the shallower end past the page room refuses the join, whatever else holds."""
    # UNDO: stages/references/beside_runs.py `beside_runs`: `> rooms[spot.page]` -> `> 10**6`
    _, (joined, runs, refused) = _runs(lambda a, b: {b: a}, {(1, 1): 1})
    assert (joined, runs) == ([], [])
    assert len(refused) == 1


def test_a_wire_between_unrelated_columns_is_none_of_its_business() -> None:
    _, (joined, runs, refused) = _runs(lambda *_: {}, _ROOMS)
    assert (joined, runs, refused) == ([], [], [])


def test_a_crowded_host_pin_leaves_one_grid_before_its_run_turns() -> None:
    """Pins of the host's cell share the pin's row: the run's y stands one grid past it."""
    # UNDO: stages/references/beside_runs.py `_drop`: `if not spot.crowded:` -> `if True:`
    spots = _spots(("a", (1,)), ("b", (3,)))
    wire = _wire(1, (1, 2), (3, 1))
    (host,) = spots[wire.a.port]
    (branch,) = spots[wire.b.port]
    crowded = replace(host, crowded=True, facing=Facing.S)
    _, runs, _ = beside_runs(
        [(wire, crowded, branch)], {("invented", "b"): ("invented", "a")}, _ROOMS
    )
    (run,) = runs
    assert {end.port: end.drop for end in run.ends} == {wire.a.port: WIRING_GRID, wire.b.port: 0}
