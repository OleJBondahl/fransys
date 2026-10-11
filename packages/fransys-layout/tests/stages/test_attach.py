"""`attach_replicas` (R7 B8, L9): hand-made values, no model and no engine (D8).

Function 1 is the host and stays in its home column; function 5 (and 6) is a replica terminal
in a column of its own. Every symbol here is the samples' vertical through symbol: `in` on top
facing N and `out` below facing S, so a wire to a host's `in` reaches its N port.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from samples import column, drawn, hid, through_geometry

from fransys_layout.geometry import Facing, Point, PortGeometry
from fransys_layout.stages.attach import attach_replicas
from fransys_layout.stages.types import Cell, Connection, Home, PortRef, Role

if TYPE_CHECKING:
    from fransys_layout.geometry import SymbolGeometry


def _attach(columns, homes, drawn_, wires):
    """`attach_replicas` with a sheet every column fits."""
    return attach_replicas(columns, homes, drawn_, wires, lambda _: True)


def _ref(number: int, end: str) -> PortRef:
    """The `in` (model port 13) or `out` (model port 14) end of function `number`."""
    return PortRef(
        function=hid("function", number), port=hid("port", number * 10 + (end == "out") + 1)
    )


def _wire(number: int, a: PortRef, b: PortRef) -> Connection:
    return Connection(
        handle=hid("conductor", number),
        physical_net=hid("net", number),
        role=Role.CONTROL,
        a=a,
        b=b,
    )


def _out_at(x: int, *, facing: Facing = Facing.S) -> SymbolGeometry:
    """The through symbol whose `out` port stands at `x` and faces `facing`."""
    return replace(
        through_geometry(),
        ports=(
            PortGeometry(name="in", at=Point(x=0, y=-16), facing=Facing.N),
            PortGeometry(name="out", at=Point(x=x, y=16), facing=facing),
        ),
    )


def _attached(number: int, index: int, host: int, port: str) -> Cell:
    return Cell(
        function=hid("function", number),
        index=index,
        host=hid("function", host),
        port=port,
        home=Home.ELSEWHERE,
    )


def _cell(number: int, index: int, lane: int = 0) -> Cell:
    return Cell(function=hid("function", number), index=index, lane=lane)


def test_a_replica_wired_to_a_host_s_port_lands_below_it_and_its_own_column_goes() -> None:
    """Terminal 5 is wired to the `out` (S) port of function 1: it is attached in row 1, below."""
    # UNDO: stages/attach.py:_with_attached, `for group in (above, None, below):` ->
    #     `for group in (above, below, None):` puts an S attachment above its host
    # UNDO: stages/attach.py:attach_replicas, `drop.add(column.key)` -> `drop.add(())`
    #     (the replica's own column stays)
    home, replica = column("hub", (1,)), column("rep", (5,))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _attach((home, replica), (home,), (drawn(1), drawn(5)), wires)

    assert result == (replace(home, cells=(_cell(1, 0), _attached(5, 1, 1, "out"))),)


def test_a_replica_with_wires_to_two_home_functions_is_attached_to_the_first_column() -> None:
    """V4: terminal 5 reaches functions 1 and 2 in home columns: drawn once, over the first."""
    # UNDO: stages/attach.py:_replica_host, `min(hosts, key=...)` -> `max(hosts, key=...)`
    #     (the attachment goes to the last column), or `if not hosts:` -> `if len(hosts) != 1:`
    homes = (column("a", (1,)), column("b", (2,)))
    replica = column("rep", (5,))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")), _wire(2, _ref(2, "out"), _ref(5, "out")))

    result = _attach((*homes, replica), homes, (drawn(1), drawn(2), drawn(5)), wires)

    assert result == (replace(homes[0], cells=(_cell(1, 0), _attached(5, 1, 1, "out"))), homes[1])
