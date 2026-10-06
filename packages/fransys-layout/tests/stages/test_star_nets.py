"""`joined_nets` and `port_clusters` (stages/references/nets): hand-made conductors.

`joined_nets` lists the ports of every net in first-seen order.

Conductor `n` from `samples.connection` runs from port `upper * 10 + 2` to port `lower * 10 + 1`.
"""

from samples import connection, hid

from fransys_layout.stages.references.nets import _joined_nets, _port_clusters


def _port(function: int, position: int):
    return hid("port", function * 10 + position)


def test_conductors_sharing_a_port_are_one_net() -> None:
    # UNDO: stages/references/nets.py `joined_nets`:
    #   `joined.union(connection.a.port, connection.b.port)` -> `pass`
    #   (no conductor joins its two ports)
    conductors = (connection(1, 1, 2), connection(2, 3, 2), connection(3, 4, 5))

    owner, nets = _joined_nets(conductors, {})

    assert owner == {
        _port(1, 2): hid("function", 1),
        _port(2, 1): hid("function", 2),
        _port(3, 2): hid("function", 3),
        _port(4, 2): hid("function", 4),
        _port(5, 1): hid("function", 5),
    }
    assert nets == [[_port(1, 2), _port(2, 1), _port(3, 2)], [_port(4, 2), _port(5, 1)]]


def test_a_split_wire_ends_at_its_stand_in_and_the_terminal_port_counts_in_both_halves() -> None:
    # UNDO: stages/references/nets.py `joined_nets`:
    #   `nets[joined.find(stand_in)].append(port)` -> `pass`
    #   (the terminal's port is in one half only)
    into, out_of = connection(1, 1, 2), connection(2, 3, 2)  # both end at port 21
    terminal_port = _port(2, 1)

    _, nets = _joined_nets((into, out_of), {out_of.handle: terminal_port})

    assert nets == [[_port(1, 2), terminal_port], [_port(3, 2), terminal_port]]


def test_a_port_cluster_is_named_by_its_lowest_port_whatever_the_wire_order() -> None:
    # UNDO: stages/references/nets.py `port_clusters`:
    #   `joined.union(c.a.port, c.b.port)` -> `pass` (no wire joins its two ports)
    wires = [connection(2, 3, 2), connection(1, 1, 2)]  # 32-21 first, then 12-21
    counted = [_port(4, 2), _port(3, 2), _port(2, 1), _port(1, 2)]

    assert _port_clusters(counted, wires) == {
        _port(4, 2): _port(4, 2),
        _port(3, 2): _port(1, 2),
        _port(2, 1): _port(1, 2),
        _port(1, 2): _port(1, 2),
    }
