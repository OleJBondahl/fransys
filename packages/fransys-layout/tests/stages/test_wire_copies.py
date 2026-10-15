"""`with_wire_copies` (model-0220): a terminal stands at each named wire, a copy of its own.

Terminal 5 has a column of its own; devices 1 and 2 stand in theirs. Every symbol is the
samples' vertical through symbol: `in` (port 13) on top facing N, `out` (port 14) below facing S.
"""

from dataclasses import replace

from samples import column, drawn, function_spec, hid

from fransys_layout.geometry import Facing, Point, PortGeometry
from fransys_layout.stages.tags import TagTexts
from fransys_layout.stages.types import Cell, Connection, Home, PortRef, Role
from fransys_layout.stages.wire_copies import (
    copy_handle,
    copy_map,
    copy_subjects,
    copy_texts,
    with_wire_copies,
)
from fransys_model.kernel import Finding, Severity

_T = hid("function", 5)


def _ref(number: int, end: str = "in") -> PortRef:
    """The `in` (port 13) or `out` (port 14) end of function `number`."""
    return PortRef(
        function=hid("function", number), port=hid("port", number * 10 + (end == "out") + 1)
    )


def _wire(number: int, device: int) -> Connection:
    """Conductor `number` from terminal 5's `out` to device `device`'s `in`."""
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        a=_ref(5, "out"),
        b=_ref(device),
    )


def _run(columns, wires, *, named=None, drawn_=None):
    """`with_wire_copies` over terminal 5 and devices 1 and 2, naming every wire by default."""
    functions = (function_spec(1), function_spec(2), function_spec(5, kind="terminal"))
    drawn_ = drawn_ or (drawn(1), drawn(2), drawn(5, kind="terminal"))
    names = {w.handle for w in wires} if named is None else named
    return with_wire_copies(columns, drawn_, functions, wires, names)


def _copies(columns):
    return [cell for col in columns for cell in col.cells if cell.at_wire]


def test_a_named_star_wire_gets_a_copy_at_its_far_pin() -> None:
    """The copy stands attached at device 1's `in`; the wire ends at the copy's port."""
    wire = _wire(1, 1)
    result = _run((column("t", (5,)), column("d", (1,))), (wire,))

    handle = copy_handle(_T, _ref(1).port)
    (cell,) = _copies(result.columns)
    assert (cell.function, cell.host, cell.port, cell.home) == (
        handle,
        hid("function", 1),
        "in",
        Home.ELSEWHERE,
    )
    assert handle in {f.function for f in result.functions}
    assert handle in {f.function for f in result.drawn}
    (rewired,) = result.connections
    assert handle in (rewired.a.function, rewired.b.function)
    assert result.real[handle] == _T


def test_a_wire_not_named_gets_no_copy() -> None:
    columns, wire = (column("t", (5,)), column("d", (1,))), _wire(1, 1)
    result = _run(columns, (wire,), named=set())

    assert result.columns == columns
    assert result.connections == (wire,)
    assert result.real == {}


def test_a_copys_wire_has_a_net_of_its_own() -> None:
    """The router never runs a copy's wire along another copy's line: the nets differ."""
    wire = _wire(1, 1)
    (rewired,) = _run((column("t", (5,)), column("d", (1,))), (wire,)).connections

    assert rewired.physical_net != wire.physical_net
    assert _run((column("t", (5,)), column("d", (1,))), (wire,)).real[rewired.physical_net] == (
        wire.physical_net
    )


def test_a_copys_wire_keeps_its_net_where_another_wire_names_the_far_pin() -> None:
    """Device 2's wire to device 1's `in` takes no copy, so both wires name the pin's one net."""
    wire = _wire(1, 1)
    other = replace(wire, handle=hid("conductor", 2), a=_ref(2, "out"), b=_ref(1))
    rewired = _run((column("t", (5,)), column("d", (1,))), (wire, other)).connections

    assert [c.physical_net for c in rewired] == [wire.physical_net, wire.physical_net]
    copy = copy_handle(_T, _ref(1).port)
    assert any(copy in (c.a.function, c.b.function) for c in rewired)


def test_a_terminal_next_to_its_device_in_one_column_takes_no_copy() -> None:
    """The column draws the wire between the two cells (layout-0090)."""
    assert _copies(_run((column("d", (5, 1)),), (_wire(1, 1),)).columns) == []


def test_a_terminal_apart_from_its_device_in_one_column_takes_a_copy() -> None:
    """Device 2 stands between them: the copy goes to device 1's pin, no reference pair."""
    (cell,) = _copies(_run((column("d", (5, 2, 1)),), (_wire(1, 1),)).columns)
    assert cell.host == hid("function", 1)


def test_a_far_pin_facing_east_gets_no_copy() -> None:
    side = drawn(1)
    ports = (
        PortGeometry(name="in", at=Point(x=0, y=-16), facing=Facing.E),
        PortGeometry(name="out", at=Point(x=0, y=16), facing=Facing.S),
    )
    side = replace(side, geometry=replace(side.geometry, ports=ports))
    columns = (column("t", (5,)), column("d", (1,)))
    result = _run(columns, (_wire(1, 1),), drawn_=(side, drawn(2), drawn(5, kind="terminal")))

    assert result.columns == columns
    assert result.real == {}


def test_a_far_column_of_another_drawing_set_gets_no_copy() -> None:
    """Terminal 5 stands nowhere in device 1's set, so it is not drawn there."""
    columns = (column("t", (5,)), replace(column("d", (1,)), location=hid("aspect_node", 101)))
    result = _run(columns, (_wire(1, 1),))

    assert result.columns == columns
    assert result.real == {}


def test_two_wires_to_two_devices_give_two_copies() -> None:
    columns = (column("t", (5,)), column("d1", (1,)), column("d2", (2,)))
    result = _run(columns, (_wire(1, 1), _wire(2, 2)))

    hosts = {cell.host: cell.function for cell in _copies(result.columns)}
    assert hosts == {
        hid("function", 1): copy_handle(_T, _ref(1).port),
        hid("function", 2): copy_handle(_T, _ref(2).port),
    }


def test_a_replica_at_the_pin_is_adopted_as_the_copy() -> None:
    """A replica of terminal 5 already attached at device 1's `in` becomes the copy."""
    replica = Cell(function=_T, index=1, host=hid("function", 1), port="in", home=Home.ELSEWHERE)
    device = replace(column("d", (1,)), cells=(*column("d", (1,)).cells, replica))
    result = _run((column("t", (5,)), device), (_wire(1, 1),))

    (cell,) = _copies(result.columns)
    assert cell.function == copy_handle(_T, _ref(1).port)
    assert _T not in {c.function for c in result.columns[1].cells}


def test_a_home_moved_to_the_pin_keeps_the_wire() -> None:
    """Terminal 5's home attached at device 1's `in` already draws the wire: no copy."""
    home = Cell(function=_T, index=1, host=hid("function", 1), port="in", home=Home.MOVED)
    device = replace(column("d", (1,)), cells=(*column("d", (1,)).cells, home))
    columns = (column("t", (5,)), device)
    result = _run(columns, (_wire(1, 1),))

    assert result.real == {}
    assert _copies(result.columns) == []


def test_copy_map_reads_the_pairs() -> None:
    assert copy_map(((hid("function", 9), _T),)) == {hid("function", 9): _T}


def test_a_finding_on_a_copy_names_the_model_id() -> None:
    alias = copy_handle(_T, hid("port", 11))
    found = Finding(code="X", severity=Severity.INFO, subjects=(alias,), message="m")

    (named,) = copy_subjects((found,), {alias: _T})
    assert named.subjects == (_T,)


def test_copy_texts_with_no_copies_returns_its_inputs() -> None:
    texts, requests = TagTexts(str, str, bool, str, str, lambda *_: None), ()
    assert copy_texts(texts, requests, (), ()) == (texts, requests)
