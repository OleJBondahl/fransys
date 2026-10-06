"""S20 M12: a conductor that would turn back round a device is a reference pair.

Function `n` is the through symbol (`samples.drawn`): port `10n + 1` at the top, facing N; port
`10n + 2` below, facing S. Columns stand left to right on page 1, stacked by `place`'s own rule.
"""

from dataclasses import replace

from samples import PROFILE, SHEET, column, drawn, function_spec, hid, page_plan

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.stages import Connection, PortRef, Role
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import page_stack
from fransys_layout.stages.references.turned import turned_stars
from fransys_layout.stages.references.types import Seating
from fransys_layout.stages.terminal_rows import terminal_chains
from fransys_layout.stages.types import PlannedColumn


def _wire(handle: int, a: tuple[int, int], b: tuple[int, int]) -> Connection:
    """Conductor `handle` between ports `a` and `b`, each `(function, which)`: 1 top, 2 bottom."""
    return Connection(
        handle=hid("conductor", handle),
        physical_net=hid("net", handle),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a[0]), port=hid("port", a[0] * 10 + a[1])),
        b=PortRef(function=hid("function", b[0]), port=hid("port", b[0] * 10 + b[1])),
    )


def _spec(number: int, *, terminal: bool):
    if not terminal:
        return function_spec(number)
    return replace(
        function_spec(number, kind="terminal"), strip_text="X1", roles=kind_roles("terminal")
    )


def _turned(
    wires: tuple[Connection, ...],
    *columns: tuple[str, tuple[int, ...]],
    off_ports: frozenset = frozenset(),
    terminals: frozenset[int] = frozenset(),
):
    """The stars of `wires` on `columns` (each `(name, functions top to bottom)`).

    The functions of `terminals` are terminals of one strip, X1.
    """
    built = tuple(
        replace(column(name, numbers), key=("invented", name)) for name, numbers in columns
    )
    plan = replace(
        page_plan(tuple(name for name, _ in columns)),
        columns=tuple(PlannedColumn(column=one.key, index=i) for i, one in enumerate(built)),
    )
    numbers = sorted({n for _, one in columns for n in one})
    kind = dict.fromkeys(terminals, "terminal")
    functions = tuple(drawn(n, kind=kind.get(n, "contact_no")) for n in numbers)
    stack = page_stack(plan, built, functions, PageStacking(profile=PROFILE, sheet=SHEET))
    specs = tuple(_spec(n, terminal=n in terminals) for n in numbers)
    return turned_stars(
        wires,
        specs,
        Seating((plan,), built, functions, (), {(1, 1): stack}),
        chains=terminal_chains(specs, functions, wires),
        off_ports=off_ports,
    )


def test_a_bottom_pin_wired_to_a_pin_above_it_is_a_reference_pair() -> None:
    """Port 12 (S) of function 1, in row 1, to port 21 (N) of function 2 in row 0: above 1's top."""
    # UNDO: stages/references/turned.py `_turns_back`: `return False` at its head
    wires = (_wire(1, (1, 2), (2, 1)),)
    (star,) = _turned(wires, ("a", (9, 1)), ("b", (2,)))
    assert star.wires == frozenset({hid("conductor", 1)})
    assert {ref.port for ref in star.ports} == {hid("port", 12), hid("port", 21)}


def test_a_top_pin_wired_to_a_pin_below_it_is_a_reference_pair() -> None:
    """Port 11 (N) of function 1, in row 0, to port 22 (S) of function 2 in row 1."""
    (star,) = _turned((_wire(1, (1, 1), (2, 2)),), ("a", (1,)), ("b", (9, 2)))
    assert star.wires == frozenset({hid("conductor", 1)})


def test_a_pin_is_tested_against_its_device_edge_not_its_own_height() -> None:
    """Port 12 (S) of function 1 to port 21 (N) of function 2, both in row 0: 21 stands above
    port 12 but not above function 1's top edge (port 11), so the wire does not turn back."""
    # UNDO: stages/references/turned.py `_turns_back`: `own.body[0]` -> `own.end.offset`
    assert _turned((_wire(1, (1, 2), (2, 1)),), ("a", (1,)), ("b", (2,))) == ()


def test_a_join_between_neighbouring_columns_stays_a_wire() -> None:
    """Top to top and bottom to bottom stand at one offset: no pin is left from outward."""
    # UNDO: stages/references/turned.py `_turns_back`: `>`/`<` -> `>=`/`<=`
    wires = (_wire(1, (1, 1), (2, 1)), _wire(2, (1, 2), (2, 2)))
    assert _turned(wires, ("a", (1,)), ("b", (2,))) == ()


def test_a_same_side_join_stays_a_wire_at_any_column_distance() -> None:
    """Top to top and bottom to bottom across a column between them: the turn test passes at
    both ends, so the wires stay wires (ADDENDUM 19 fix 2, no neighbour requirement)."""
    # UNDO: stages/references/turned.py `_turns`: prefix the test with
    #     `abs(pairs[0][0].index - pairs[0][1].index) > 1 or` (a neighbour requirement)
    wires = (_wire(1, (1, 1), (2, 1)), _wire(2, (1, 2), (2, 2)))
    assert _turned(wires, ("a", (1,)), ("b", (7,)), ("c", (2,))) == ()


def test_a_wire_down_the_column_from_a_bottom_pin_stays_a_wire() -> None:
    """Port 12 (S) of the upper function to port 21 (N) of the one below it goes down."""
    assert _turned((_wire(1, (1, 2), (2, 1)),), ("a", (1, 2))) == ()


def test_conductors_sharing_a_pin_are_one_star_with_one_reference() -> None:
    """Two turned conductors from port 12 make one star, so the pin takes one text."""
    wires = (_wire(1, (1, 2), (2, 1)), _wire(2, (1, 2), (3, 1)))
    (star,) = _turned(wires, ("a", (9, 1)), ("b", (2,)), ("c", (3,)))
    assert star.wires == frozenset({hid("conductor", 1), hid("conductor", 2)})


def test_the_reference_stands_at_the_port_with_an_off_stub() -> None:
    """A stub on port 21 makes it the reference, so the stub joins its box (S20 M12)."""
    # UNDO: stages/references/turned.py `_at_stub`: `replace(star, ref=at[0]) if at else star`
    #     -> `star`
    wires = (_wire(1, (1, 2), (2, 1)),)
    (plain,) = _turned(wires, ("a", (9, 1)), ("b", (2,)))
    (star,) = _turned(wires, ("a", (9, 1)), ("b", (2,)), off_ports=frozenset({hid("port", 21)}))
    assert star.ref.port == hid("port", 21)
    assert plain.ref.port == hid("port", 12)


def test_a_link_of_a_terminal_chain_never_turns_even_where_its_row_is_stacked() -> None:
    """Terminals 1 and 2 of strip X1 are jumpered bottom to bottom, 1 below function 9 and 2 at
    the top of the next column: the S pin of 1 sees 2 above it, a turn for any other wire."""
    # UNDO: stages/references/turned.py `_turns`: drop `or conductor.handle in chains.links`
    wires = (_wire(1, (1, 2), (2, 2)),)
    columns = (("a", (9, 1)), ("b", (2,)))
    assert len(_turned(wires, *columns)) == 1  # control: no strip, the wire turns
    assert _turned(wires, *columns, terminals=frozenset({1, 2})) == ()


def test_two_chain_members_joined_by_a_wire_that_is_no_link_still_face_the_turn_test() -> None:
    """Terminals 1 and 2 are a chain (jumpered top to top, wire 1). Wire 2 joins 1's bottom
    port to 2's top port: no link, and 2 stands above 1's device, so it turns back like any
    other wire. Only wire 2 is a star."""
    # UNDO: stages/references/turned.py `_turns`: `conductor.handle in chains.links` -> `ends <=
    #     {function of 1, function of 2}` (the chain's members, as before this test)
    wires = (_wire(1, (1, 1), (2, 1)), _wire(2, (1, 2), (2, 1)))
    columns = (("a", (9, 1)), ("b", (2,)))
    stars = _turned(wires, *columns, terminals=frozenset({1, 2}))
    assert [star.wires for star in stars] == [frozenset({hid("conductor", 2)})]
