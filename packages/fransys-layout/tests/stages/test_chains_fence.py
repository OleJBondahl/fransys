"""Behaviour fence for `discover_chains`: the paths the rest of the suite never executes."""

import dataclasses
from typing import Any

from samples import connection, drawn, function_spec, hid, through_geometry

from fransys_layout.geometry import Facing, Point, PortGeometry, ThroughPath
from fransys_layout.stages import (
    Cell,
    Column,
    Connection,
    DrawnFunction,
    DrawnPort,
    FunctionSpec,
    PolePair,
    PortRef,
    PortSpec,
    Role,
)
from fransys_layout.stages.chains import ChainRecords, discover_chains
from fransys_layout.stages.types import MatedFunctions

type _Pair = tuple[FunctionSpec, DrawnFunction]


def _stub(number: int, *, kind: str = "terminal") -> _Pair:
    """A one-port function: model port `number * 10 + 1`, drawn at `in` (N)."""
    spec = function_spec(number, kind=kind)
    shown = drawn(number, kind=kind)
    return (
        dataclasses.replace(spec, ports=spec.ports[:1], poles=0, pole_pairs=()),
        dataclasses.replace(shown, ports=shown.ports[:1]),
    )


def _plain(number: int) -> _Pair:
    """A two-port function on no pole (no through path): ports 13 (N) and 14 (S)."""
    shown = drawn(number)
    return (
        dataclasses.replace(function_spec(number), poles=0, pole_pairs=()),
        dataclasses.replace(shown, geometry=dataclasses.replace(shown.geometry, through=None)),
    )


def _hub(number: int, facing: Facing = Facing.N) -> _Pair:
    """A three-port function on no pole (ports a, b, c at x 0, 16, 32, all facing `facing`)."""
    names = ("a", "b", "c")
    ports = tuple(
        PortSpec(
            port=hid("port", number * 10 + i + 1),
            name=name,
            physical_net=hid("net", 900 + i),
            role=Role.CONTROL,
        )
        for i, name in enumerate(names)
    )
    spec = dataclasses.replace(function_spec(number), poles=0, pole_pairs=(), ports=ports)
    geometry = dataclasses.replace(
        through_geometry(),
        through=None,
        ports=tuple(
            PortGeometry(name=name, at=Point(x=16 * i, y=-16), facing=facing)
            for i, name in enumerate(names)
        ),
    )
    shown = DrawnFunction(
        function=spec.function,
        item=spec.item,
        key=spec.key,
        kind=spec.kind,
        geometry=geometry,
        ports=tuple(DrawnPort(port=p.port, symbol_port=p.name) for p in ports),
        primary_in="a",
        primary_out="c",
        roles=drawn(number).roles,
    )
    return spec, shown


def _two_pole(number: int) -> _Pair:
    """A contact of two poles, ports 1-2 and 3-4, each pole's first port N and second S."""
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
    shown = dataclasses.replace(
        drawn(number),
        geometry=geometry,
        ports=tuple(
            DrawnPort(port=p.port, symbol_port=s) for p, s in zip(ports, symbols, strict=True)
        ),
        primary_in="1.in",
        primary_out="1.out",
    )
    return spec, shown


def _wire(number: int, a: tuple[FunctionSpec, int], b: tuple[FunctionSpec, int]) -> Connection:
    """One conductor: port index `a[1]` of function `a[0]` to port index `b[1]` of `b[0]`."""
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", 800 + number),
        role=Role.CONTROL,
        a=PortRef(function=a[0].function, port=a[0].ports[a[1]].port),
        b=PortRef(function=b[0].function, port=b[0].ports[b[1]].port),
    )


def _terminal(number: int) -> _Pair:
    return function_spec(number, kind="terminal"), drawn(number, kind="terminal")


def _found(
    pairs: tuple[_Pair, ...], wires: tuple[Connection, ...], **kw: Any
) -> list[tuple[tuple[str, ...], tuple[Cell, ...]]]:
    """Every column's key and cells, from `discover_chains` on `pairs` and `wires`."""
    records = ChainRecords(
        tuple(s for s, _ in pairs),
        tuple(d for _, d in pairs),
        wires,
        (),
        kw.pop("mates", ()),
        kw.pop("edge_mates", ()),
        fixed=kw.pop("fixed", frozenset()),
    )
    columns: tuple[Column, ...] = discover_chains(records, **kw)
    return [(column.key, column.cells) for column in columns]


def _key(number: int) -> tuple[str, ...]:
    return ("chain", "", "invented", f"fn{number}")


def _cell(number: int, index: int, lane: int = 0, **kw: Any) -> Cell:
    return Cell(function=hid("function", number), index=index, lane=lane, **kw)


def test_a_one_port_terminal_with_two_wires_is_an_in_line_pole_and_guards_skip() -> None:
    """R7 B5: terminal 2 with two wires links 1 above 3 in one column; a mate of an unknown
    function, a mate over ports already in poles, edge mates that cannot apply, and a one-port
    terminal on no net change nothing."""
    one, two, three, orphan = function_spec(1), _stub(2), function_spec(3), _stub(7)
    pairs = ((one, drawn(1)), two, (three, drawn(3)))
    wires = (_wire(1, (one, 1), (two[0], 0)), _wire(2, (two[0], 0), (three, 0)))
    expected = [(_key(1), (_cell(1, 0), _cell(2, 1), _cell(3, 2)))]
    assert _found(pairs, wires) == expected
    unknown = hid("function", 99)
    mates = (
        MatedFunctions(a=one.function, b=unknown),
        MatedFunctions(a=one.function, b=three.function),
    )
    edges = (
        MatedFunctions(a=two[0].function, b=one.function),  # 2's port is already in its pole
        MatedFunctions(a=one.function, b=unknown),
    )
    assert _found((*pairs, orphan), wires, mates=mates, edge_mates=edges) == expected


def test_a_changeover_with_no_throw_roles_chains_through_its_path_alone() -> None:
    """A three-port function with a through path and no `throw` on any port: one pole, no
    throw pair (S13 never applies)."""
    spec, shown = function_spec(5), drawn(5)
    extra = PortSpec(
        port=hid("port", 53), name="11", physical_net=hid("net", 53), role=Role.CONTROL
    )
    spec = dataclasses.replace(spec, poles=0, pole_pairs=(), ports=(*spec.ports, extra))
    geometry = dataclasses.replace(
        shown.geometry,
        ports=(
            *shown.geometry.ports,
            PortGeometry(name="nc", at=Point(x=16, y=0), facing=Facing.E),
        ),
    )
    shown = dataclasses.replace(
        shown,
        geometry=geometry,
        ports=(*shown.ports, DrawnPort(port=extra.port, symbol_port="nc")),
    )
    assert _found(((spec, shown),), ()) == [(_key(5), (_cell(5, 0),))]


def test_single_chains_ending_on_one_hub_merge_bottom_packed_under_the_lowest_port() -> None:
    """A hub reached through a merged (iii) group takes the lane of that group's chain.

    Hub 11 is reached by chain 1-2-3, merged under chain 4-5 (designer ruling 2026-10-02), so it
    stands in lane 1 above that chain and spans at its port `c`, not at lane 0 with no span port.
    """
    chain = {i: function_spec(i) for i in (1, 2, 3, 4, 5)}
    pairs = (*((chain[i], drawn(i)) for i in chain), _hub(10), _hub(11))
    hub, other = pairs[5][0], pairs[6][0]
    wires = (
        connection(1, 1, 2),
        connection(2, 2, 3),
        connection(3, 4, 5),
        _wire(10, (chain[3], 1), (hub, 1)),
        _wire(11, (chain[5], 1), (hub, 0)),
        _wire(12, (other, 2), (chain[1], 0)),
    )
    assert _found(pairs, wires) == [
        (
            _key(11),
            (
                _cell(11, 0, 1, span_port="c"),
                _cell(1, 1, 1),
                _cell(4, 2),
                _cell(2, 2, 1),
                _cell(5, 3),
                _cell(3, 3, 1),
                _cell(10, 4, span_port="a"),
            ),
        )
    ]


def test_end_reached_functions_of_two_lanes_share_one_row_each_in_its_lane() -> None:
    """C9: a two-pole contact's two single-pole lanes end on plain functions 1 and 2: both stand
    below in one row, 1 in lane 0 and 2 in lane 1, each spanning at its symbol port `in`."""
    multi, one, two = _two_pole(10), _plain(1), _plain(2)
    wires = (_wire(1, (multi[0], 1), (one[0], 0)), _wire(2, (multi[0], 3), (two[0], 0)))
    assert _found((multi, one, two), wires) == [
        (
            _key(10),
            (
                _cell(10, 0),
                _cell(1, 1, span_port="in"),
                _cell(2, 1, 1, span_port="in"),
            ),
        )
    ]


def test_a_reached_function_whose_port_is_not_drawn_has_no_span_port() -> None:
    """C12: hub 10 is reached at its port a, which its drawn function lacks: it stands below the
    chain with no span port."""
    one, two = function_spec(1), function_spec(2)
    spec, shown = _hub(10)
    shown = dataclasses.replace(shown, ports=shown.ports[1:])
    wires = (connection(1, 1, 2), _wire(2, (two, 1), (spec, 0)))
    assert _found(((one, drawn(1)), (two, drawn(2)), (spec, shown)), wires) == [
        (_key(1), (_cell(1, 0), _cell(2, 1), _cell(10, 2)))
    ]


def test_a_star_pin_whose_port_already_faces_the_member_is_not_flipped() -> None:
    """I4 Q2: pin 3 (port faces N) on the star at 1's S port stands below 1, unflipped."""
    one, two = function_spec(1), function_spec(2)
    pin, pin_drawn = _stub(3, kind="contact_no")
    pin = dataclasses.replace(pin, pin_function=hid("function", 90))
    wires = (_wire(1, (one, 1), (two, 1)), _wire(2, (one, 1), (pin, 0)))
    assert _found(((one, drawn(1)), (two, drawn(2)), (pin, pin_drawn)), wires) == [
        (_key(1), (_cell(1, 0), _cell(3, 1))),
        (_key(2), (_cell(2, 0),)),
    ]


def test_a_side_element_of_a_carrier_in_two_columns_is_placed_once() -> None:
    """D1/D2: 11's two poles strap 10's two; 10 stays in the first column by key (1, 10, 11
    beside it), the second column (2, 3) shows neither 10 nor 11 again."""
    carrier, side = _two_pole(10), _two_pole(11)
    t1, t2, t3 = _terminal(1), _terminal(2), _terminal(3)
    wires = (
        _wire(1, (t1[0], 1), (carrier[0], 0)),
        _wire(2, (t1[0], 1), (side[0], 0)),
        _wire(3, (carrier[0], 1), (side[0], 1)),
        _wire(4, (t2[0], 1), (carrier[0], 2)),
        _wire(5, (t2[0], 1), (side[0], 2)),
        _wire(6, (carrier[0], 3), (t3[0], 0)),
        _wire(7, (side[0], 3), (t3[0], 0)),
    )
    assert _found((carrier, side, t1, t2, t3), wires) == [
        (
            _key(1),
            (
                _cell(1, 0),
                _cell(10, 1),
                _cell(11, 1, 1, side=True, carrier=hid("function", 10)),
            ),
        ),
        (_key(2), (_cell(2, 0), _cell(3, 1))),
    ]


def test_a_terminal_wired_to_a_port_facing_east_stays_in_its_own_column() -> None:
    """R7.1: terminal 2's only wire reaches 1's E-facing port (a fork with 3): nothing attaches."""
    one, shown = function_spec(1), drawn(1)
    east = dataclasses.replace(shown.geometry.ports[0], facing=Facing.E)
    shown = dataclasses.replace(
        shown,
        geometry=dataclasses.replace(shown.geometry, ports=(east, shown.geometry.ports[1])),
    )
    term, three = _terminal(2), function_spec(3)
    wires = (_wire(1, (term[0], 1), (one, 0)), _wire(2, (three, 1), (one, 0)))
    assert _found(((one, shown), term, (three, drawn(3))), wires) == [
        (_key(1), (_cell(1, 0),)),
        (_key(2), (_cell(2, 0),)),
        (_key(3), (_cell(3, 0),)),
    ]


def test_single_chains_ending_on_fixed_south_pins_stand_under_their_hub() -> None:
    """V1: two single chains end on S-facing pins of one hub; fixed, the hub is above, both lanes
    under it; unfixed the hub stays below the chains, as before."""
    chain = {i: function_spec(i) for i in (1, 2, 3, 4)}
    hub = _hub(10, Facing.S)
    pairs = (*((chain[i], drawn(i)) for i in chain), hub)
    wires = (
        connection(1, 1, 2),
        connection(2, 3, 4),
        _wire(10, (chain[2], 1), (hub[0], 0)),
        _wire(11, (chain[4], 1), (hub[0], 1)),
    )
    fixed = frozenset(hub[0].ports[i].port for i in (0, 1))
    above = [
        _cell(10, 0, span_port="a"),
        _cell(1, 1),
        _cell(3, 1, 1),
        _cell(2, 2),
        _cell(4, 2, 1),
    ]
    below = [_cell(1, 0), _cell(3, 0, 1), _cell(2, 1), _cell(4, 1, 1), _cell(10, 2, span_port="a")]
    # UNDO: stages/_chain_reach.py:_vote_lane, `if hit[1] in r.fixed` -> `if False` (hub below)
    assert [cells for _, cells in _found(pairs, wires, fixed=fixed)] == [tuple(above)]
    assert [cells for _, cells in _found(pairs, wires)] == [tuple(below)]
