"""`hub_order` hands back the replica keys under the keys it re-keyed the columns to."""

from dataclasses import replace

from samples import column, connection, function_spec

from fransys_layout.stages.attach import hub_order


def test_a_hub_home_column_is_not_a_replica_and_a_re_keyed_replica_column_is() -> None:
    """Function 1 fans out to functions 2 and 3, so its home column and its replica are both hubs.

    Both get new keys. Only the replica's new key is in the returned set.
    """
    # UNDO: stages/attach.py:hub_order, return `frozenset(rekey.values())`
    #     (every re-keyed column, the home hub too) instead of `frozenset(rekey.get(key, key) ...)`
    home = column("hub", (1,))
    branches = (column("b2", (2,)), column("b3", (3,)))
    replica = column("hub-replica", (1,))
    replica = replace(replica, cells=tuple(replace(cell, replica=True) for cell in replica.cells))
    specs = tuple(function_spec(number) for number in (1, 2, 3))
    wires = (connection(1, 1, 2), connection(2, 1, 3))

    columns, replicas = hub_order(
        (home, *branches, replica), specs, wires, frozenset({replica.key})
    )

    new_home, _, _, new_replica = columns
    assert new_home.key != home.key
    assert new_replica.key != replica.key
    assert replicas == {new_replica.key}
    assert new_home.key not in replicas


def test_a_rack_column_keeps_its_key_though_it_is_a_hub() -> None:
    """F1: the hub of function 1 has a key starting "rack", so it keeps its slot.

    Whether `rack_order` produced that key does not matter: the key is the test.
    """
    # UNDO: stages/attach.py:hub_order, `and not is_rack_key(column.key)` -> `and True`
    home = replace(column("hub", (1,)), key=("rack", "x"))
    branches = (column("b2", (2,)), column("b3", (3,)))
    specs = tuple(function_spec(number) for number in (1, 2, 3))
    wires = (connection(1, 1, 2), connection(2, 1, 3))

    columns, replicas = hub_order((home, *branches), specs, wires, frozenset())

    assert columns == (home, *branches)
    assert replicas == frozenset()
