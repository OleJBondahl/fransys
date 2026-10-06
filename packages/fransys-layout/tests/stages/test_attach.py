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
from fransys_layout.stages.types import Cell, Connection, PortRef, Role

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
        replica=True,
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


def test_a_replica_wired_to_a_host_n_port_lands_above_it() -> None:
    """Terminal 5 is wired to the `in` (N) port of function 1: it is attached in row 0, above."""
    # UNDO: stages/attach.py:_with_attached, `for group in (above, None, below):` ->
    #     `for group in (None, above, below):` puts an N attachment below its host
    home, replica = column("hub", (1,)), column("rep", (5,))
    wires = (_wire(1, _ref(1, "in"), _ref(5, "out")),)

    result = _attach((home, replica), (home,), (drawn(1), drawn(5)), wires)

    assert result == (replace(home, cells=(_attached(5, 0, 1, "in"), _cell(1, 1))),)


def test_a_replica_whose_port_faces_the_same_way_as_its_host_port_is_flipped() -> None:
    """Terminal 5's `out` (S) meets the host's `out` (S): the terminal turns (`flip`)."""
    # UNDO: stages/attach.py:_replica_host, `flip = own_facing != (...)` -> `flip = False`
    home, replica = column("hub", (1,)), column("rep", (5,))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "out")),)

    result = _attach((home, replica), (home,), (drawn(1), drawn(5)), wires)

    turned = replace(_attached(5, 1, 1, "out"), flip=True)
    assert result == (replace(home, cells=(_cell(1, 0), turned)),)


def test_replicas_of_one_row_take_their_lanes_in_the_order_of_the_host_port_x() -> None:
    """Hosts 1 and 2 share a row; port `out` of 1 is at x 8, of 2 at x 0: terminal 6 is lane 0."""
    # UNDO: stages/attach.py:_with_attached, `sorted(group, key=lambda a: a[2])` -> `sorted(group)`
    row = (_cell(1, 0, 0), _cell(2, 0, 1))
    home = replace(column("hub", (1, 2)), cells=row)
    hosts = (
        replace(drawn(1), geometry=_out_at(8)),
        replace(drawn(2), geometry=_out_at(0)),
    )
    replicas = (column("r5", (5,)), column("r6", (6,)))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")), _wire(2, _ref(2, "out"), _ref(6, "in")))

    result = _attach((home, *replicas), (home,), (*hosts, drawn(5), drawn(6)), wires)

    first, second = _attached(6, 1, 2, "out"), replace(_attached(5, 1, 1, "out"), lane=1)
    assert result == (replace(home, cells=(*row, first, second)),)


def test_attachments_above_and_below_renumber_the_rows_of_the_column() -> None:
    """Host 1 (row 0) gets terminal 5 above and 6 below; function 2 moves from row 1 to row 3."""
    # UNDO: stages/attach.py:_with_attached, the last `index += 1` of the row loop (after the
    #     attachment cells are extended, 12 spaces of indent) -> `index += 0`
    home = column("hub", (1, 2))
    wires = (_wire(1, _ref(1, "in"), _ref(5, "out")), _wire(2, _ref(1, "out"), _ref(6, "in")))

    result = _attach(
        (home, column("r5", (5,)), column("r6", (6,))),
        (home,),
        (drawn(1), drawn(2), drawn(5), drawn(6)),
        wires,
    )

    assert result == (
        replace(
            home,
            cells=(_attached(5, 0, 1, "in"), _cell(1, 1), _attached(6, 2, 1, "out"), _cell(2, 3)),
        ),
    )


def test_a_replica_with_wires_to_two_home_functions_is_attached_to_the_first_column() -> None:
    """V4: terminal 5 reaches functions 1 and 2 in home columns: drawn once, over the first."""
    # UNDO: stages/attach.py:_replica_host, `min(hosts, key=...)` -> `max(hosts, key=...)`
    #     (the attachment goes to the last column), or `if not hosts:` -> `if len(hosts) != 1:`
    homes = (column("a", (1,)), column("b", (2,)))
    replica = column("rep", (5,))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")), _wire(2, _ref(2, "out"), _ref(5, "out")))

    result = _attach((*homes, replica), homes, (drawn(1), drawn(2), drawn(5)), wires)

    assert result == (replace(homes[0], cells=(_cell(1, 0), _attached(5, 1, 1, "out"))), homes[1])


def test_a_wire_between_two_other_functions_is_not_one_of_the_replica_s_wires() -> None:
    """Terminal 5 has one wire, to host 1; the wire between homes 1 and 2 is none of its own."""
    # UNDO: stages/attach.py:_replica_host, `for c in touching.get(terminal, ())` ->
    #     `for c in (c for cs in touching.values() for c in cs)` (every wire is the terminal's)
    home, replica = column("hub", (1, 2)), column("rep", (5,))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")), _wire(2, _ref(1, "in"), _ref(2, "in")))

    result = _attach((home, replica), (home,), (drawn(1), drawn(2), drawn(5)), wires)

    assert result == (replace(home, cells=(_cell(1, 0), _attached(5, 1, 1, "out"), _cell(2, 2))),)


def test_a_replica_wired_to_a_side_port_of_its_host_is_not_attached() -> None:
    """The host's `out` port faces E: an attachment sits only at an N or S port, so it stays."""
    # UNDO: stages/attach.py:_replica_host, `not in ("n", "s")` -> `not in ("n", "s", "e")`
    home, replica = column("hub", (1,)), column("rep", (5,))
    host = replace(drawn(1), geometry=_out_at(0, facing=Facing.E))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _attach((home, replica), (home,), (host, drawn(5)), wires)

    assert result == (home, replica)


def test_a_replica_in_another_group_than_its_host_is_not_attached() -> None:
    """The host stands in group 1, the terminal in group 2."""
    # UNDO: stages/attach.py:_replica_host, `and home_of[other.function].group == column.group`
    #     -> `and True`
    home, replica = column("hub", (1,)), column("rep", (5,), group=2)
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _attach((home, replica), (home,), (drawn(1), drawn(5)), wires)

    assert result == (home, replica)


def test_a_replica_in_another_unit_than_its_host_is_not_attached() -> None:
    """The host's column has no unit, the terminal's column stands in unit 1: never into its set."""
    # UNDO: stages/attach.py:_replica_host, `and home_of[other.function].unit == column.unit`
    #     -> `and True`
    home = column("hub", (1,))
    replica = replace(column("rep", (5,)), unit=hid("unit", 1))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _attach((home, replica), (home,), (drawn(1), drawn(5)), wires)

    assert result == (home, replica)


def test_a_column_of_several_cells_is_not_attached() -> None:
    """Column (5, 6) is wired to host 1 at terminal 5, but only a one-cell column is a replica."""
    # UNDO: stages/attach.py:attach_replicas, `or len(column.cells) != 1:` -> `or False:`
    home, several = column("hub", (1,)), column("rep", (5, 6))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _attach((home, several), (home,), (drawn(1), drawn(5), drawn(6)), wires)

    assert result == (home, several)


def test_a_one_cell_home_column_is_never_attached_to_another_home_column() -> None:
    """Both columns are homes: function 5 is wired to host 1, but a home column stays as it is."""
    # UNDO: stages/attach.py:attach_replicas, `if column.key in home_keys or len(...)` ->
    #     `if len(column.cells) != 1:` (drop the `column.key in home_keys or` half)
    homes = (column("hub", (1,)), column("other", (5,)))
    wires = (_wire(1, _ref(1, "out"), _ref(5, "in")),)

    result = _attach(homes, homes, (drawn(1), drawn(5)), wires)

    assert result == homes
