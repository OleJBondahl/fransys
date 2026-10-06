"""`inline_exits` (R7 B5): hand-made values, no model and no engine (D8).

Function 5 is a one-port terminal drawn as the samples' through symbol (model port 13 bound to
`in`, facing N, `out` below it facing S), in the column (1, 5, 2), so it is an in-line pole:
one wire arrives from function 1 above, the other leaves to function 2 below.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from samples import column, drawn, function_spec, hid, through_geometry

from fransys_layout.geometry import Facing, Point, PortGeometry
from fransys_layout.stages.arrange import inline_exits
from fransys_layout.stages.types import Connection, PortRef, Role

if TYPE_CHECKING:
    from fransys_layout.stages.types import DrawnFunction, FunctionSpec

TERMINAL = 5


def _terminal_spec(kind: str = "terminal", *, bound: int = 1) -> FunctionSpec:
    """Function 5 with its one model port, port 51 (`bound` 1) or 52 (`bound` 2)."""
    spec = function_spec(TERMINAL, kind=kind)
    return replace(spec, ports=spec.ports[bound - 1 : bound])


def _ref(number: int, port: int, symbol_port: str = "") -> PortRef:
    return PortRef(
        function=hid("function", number),
        port=hid("port", number * 10 + port),
        symbol_port=symbol_port,
    )


def _wire(number: int, a: PortRef, b: PortRef) -> Connection:
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        a=a,
        b=b,
    )


def _facing_pair(first: Facing, second: Facing) -> DrawnFunction:
    """Terminal 5 drawn with `in` facing `first` and `out` facing `second`."""
    ports = (
        PortGeometry(name="in", at=Point(x=0, y=-16), facing=first),
        PortGeometry(name="out", at=Point(x=0, y=16), facing=second),
    )
    return replace(drawn(TERMINAL), geometry=replace(through_geometry(), ports=ports))


def _inline(*, bound: int = 1) -> tuple[Connection, ...]:
    """The two wires of terminal 5, both on its model port `bound` (1 or 2): 1 above, 2 below."""
    return (
        _wire(1, _ref(1, 2), _ref(TERMINAL, bound)),
        _wire(2, _ref(TERMINAL, bound), _ref(2, 1)),
    )


def test_the_wire_to_a_later_row_lands_on_the_terminal_port_opposite_the_bound_one() -> None:
    """The lower wire's terminal end gets `symbol_port` `out`; the upper wire is unchanged."""
    # UNDO: stages/arrange.py:inline_exits, `and there[1] > here[1]` -> `and there[1] != here[1]`
    #     (the upper wire is landed on the opposite port too)
    specs = (function_spec(1), _terminal_spec(), function_spec(2))
    wires = _inline()

    result = inline_exits(wires, (column("a", (1, 5, 2)),), specs, (drawn(TERMINAL),))

    assert result == (wires[0], _wire(2, _ref(TERMINAL, 1, "out"), _ref(2, 1)))


def test_a_terminal_bound_at_its_s_port_lands_the_lower_wire_on_its_n_port() -> None:
    """Model port 14 is bound to `out` (S); the opposite port is `in`."""
    # UNDO: geometry/symbols.py:OPPOSITE, `S: N` -> `S: S` in the N/S pair
    specs = (function_spec(1), _terminal_spec(bound=2), function_spec(2))
    wires = _inline(bound=2)

    result = inline_exits(wires, (column("a", (1, 5, 2)),), specs, (drawn(TERMINAL),))

    assert result == (wires[0], _wire(2, _ref(TERMINAL, 2, "in"), _ref(2, 1)))


def test_a_terminal_bound_at_an_e_port_lands_the_lower_wire_on_its_w_port() -> None:
    """The symbol's `in` faces E and its `out` faces W: the opposite of E is W."""
    # UNDO: geometry/symbols.py:OPPOSITE, `W: E` -> `W: W` in the E/W pair
    specs = (function_spec(1), _terminal_spec(), function_spec(2))

    result = inline_exits(
        _inline(), (column("a", (1, 5, 2)),), specs, (_facing_pair(Facing.E, Facing.W),)
    )

    assert result[1] == _wire(2, _ref(TERMINAL, 1, "out"), _ref(2, 1))


def test_a_terminal_with_one_wire_keeps_its_connections() -> None:
    """Terminal 5 ends the column: only one wire is on its port, so nothing is in line."""
    # UNDO: stages/terminal_facts.py:inline_terminal, `read.wires == _IN_LINE_WIRES` -> `>= 1`
    specs = (function_spec(1), _terminal_spec(), function_spec(2))
    wires = (_wire(2, _ref(TERMINAL, 1), _ref(2, 1)),)

    assert inline_exits(wires, (column("a", (5, 2, 1)),), specs, (drawn(TERMINAL),)) == wires


def test_a_wire_with_both_ends_on_the_terminal_port_counts_once_toward_its_two_wires() -> None:
    """The lower wire and a loop on port 51 make two wires (the loop counts once): still in line."""
    # UNDO: stages/arrange.py:inline_exits, `for port in {c.a.port, c.b.port}:` ->
    #     `for port in (c.a.port, c.b.port):` (the loop counts twice, three wires)
    specs = (function_spec(1), _terminal_spec(), function_spec(2))
    lower = _wire(1, _ref(TERMINAL, 1), _ref(2, 1))
    loop = _wire(2, _ref(TERMINAL, 1), _ref(TERMINAL, 1))

    result = inline_exits((lower, loop), (column("a", (1, 5, 2)),), specs, (drawn(TERMINAL),))

    assert result == (_wire(1, _ref(TERMINAL, 1, "out"), _ref(2, 1)), loop)


def test_a_function_that_is_not_a_terminal_keeps_its_connections() -> None:
    """The same in-line shape with a contact in place of the terminal: no exit is landed."""
    # UNDO: stages/terminal_facts.py:inline_terminal, `read.terminal and ` -> ``
    specs = (function_spec(1), _terminal_spec("contact_no"), function_spec(2))
    wires = _inline()

    assert inline_exits(wires, (column("a", (1, 5, 2)),), specs, (drawn(TERMINAL),)) == wires


def test_a_wire_to_another_column_keeps_its_connections() -> None:
    """Function 2 stands in row 1 of another column, below the terminal's row 0: not in line."""
    # UNDO: stages/arrange.py:inline_exits, `and here[0] == there[0]` -> `and True`
    specs = (function_spec(1), _terminal_spec(), function_spec(2))
    wires = _inline()
    columns = (column("a", (5,)), column("b", (1, 2)))

    assert inline_exits(wires, columns, specs, (drawn(TERMINAL),)) == wires


def test_a_two_port_function_keeps_its_connections() -> None:
    """Function 5 keeps both its model ports: only a one-port terminal shares a port."""
    # UNDO: stages/terminal_facts.py:inline_terminal, `read.ports == 1` -> `read.ports >= 1`
    specs = (function_spec(1), function_spec(TERMINAL, kind="terminal"), function_spec(2))
    wires = _inline()

    assert inline_exits(wires, (column("a", (1, 5, 2)),), specs, (drawn(TERMINAL),)) == wires
