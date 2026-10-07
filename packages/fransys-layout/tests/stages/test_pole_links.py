"""EF-A2 part 6: `pole_links`, the column pairs a D1 pole link joins (deep-dive D4).

Functions are `samples.drawn(n)`: port `13` of function `n` at symbol port `in`, `14` at `out`,
both on the through path. `connection(number, upper, lower)` joins `14` of `upper` to `13` of
`lower`. Every case is one fact of the definition `lint/chains.py` uses for `CHAIN_BROKEN`.
"""

import dataclasses

from samples import column, connection, drawn, hid, through_geometry

from fransys_layout.stages import Cell, DrawnPort, Home, NetGroup, PortRef, Role
from fransys_layout.stages._polelinks import pole_links


def _key(name: str) -> tuple[str, str]:
    return ("invented", name)


def _pair(x: str, y: str) -> tuple[tuple[str, str], tuple[str, str]]:
    return (_key(x), _key(y))


def _cols(**cells: tuple[int, ...]):
    """One column per name, holding the functions given."""
    return tuple(column(name, numbers) for name, numbers in cells.items())


def _ref(number: int, end: int) -> PortRef:
    return PortRef(function=hid("function", number), port=hid("port", number * 10 + end))


def test_a_connection_between_two_through_paths_on_a_net_of_two_is_a_link() -> None:
    """Functions 1 and 2, in columns `a` and `b`, joined by one conductor."""
    links = pole_links(_cols(a=(1,), b=(2,)), (drawn(1), drawn(2)), (connection(1, 1, 2),), ())
    assert links == (_pair("a", "b"),)


def test_a_box_or_terminal_has_no_through_path_and_ends_no_link() -> None:
    """Function 2 without a through path: the same wire is no pole link."""
    boxed = dataclasses.replace(
        drawn(2), geometry=dataclasses.replace(through_geometry(), through=None)
    )
    links = pole_links(_cols(a=(1,), b=(2,)), (drawn(1), boxed), (connection(1, 1, 2),), ())
    assert links == ()


def test_a_port_off_the_through_path_ends_no_link() -> None:
    """Function 2's port `13` at a symbol port that is not `in`: not a pole port."""
    off = dataclasses.replace(
        drawn(2),
        ports=(DrawnPort(port=hid("port", 21), symbol_port="aux"), *drawn(2).ports[1:]),
    )
    links = pole_links(_cols(a=(1,), b=(2,)), (drawn(1), off), (connection(1, 1, 2),), ())
    assert links == ()


def test_a_net_of_three_ports_is_no_link() -> None:
    """A second conductor from port `14` of function 1 to function 3 makes a net of three."""
    wires = (connection(1, 1, 2), connection(2, 1, 3))
    links = pole_links(_cols(a=(1,), b=(2,), c=(3,)), (drawn(1), drawn(2), drawn(3)), wires, ())
    assert links == ()


def test_a_net_group_port_counts_toward_the_net() -> None:
    """A declared net that also holds function 3's port makes the same net three ports."""
    group = NetGroup(
        net=hid("net", 900),
        physical_net=hid("net", 900),
        role=Role.CONTROL,
        ports=(_ref(1, 2), _ref(3, 1)),
    )
    columns, functions = _cols(a=(1,), b=(2,), c=(3,)), (drawn(1), drawn(2), drawn(3))
    assert pole_links(columns, functions, (connection(1, 1, 2),), ()) == (_pair("a", "b"),)
    assert pole_links(columns, functions, (connection(1, 1, 2),), (group,)) == ()


def test_a_replica_cell_is_not_a_home() -> None:
    """Function 2 is also an attached replica in column `c`: the link runs to its home only."""
    columns = (
        column("a", (1,)),
        column("b", (2,)),
        dataclasses.replace(
            column("c", (3,)),
            cells=(
                Cell(function=hid("function", 3), index=0),
                Cell(function=hid("function", 2), index=1, home=Home.ELSEWHERE),
            ),
        ),
    )
    links = pole_links(columns, (drawn(1), drawn(2), drawn(3)), (connection(1, 1, 2),), ())
    assert links == (_pair("a", "b"),)


def test_two_functions_in_one_column_are_no_link_between_columns() -> None:
    """Functions 1 and 2 stand in column `a`: the pair is dropped."""
    links = pole_links(_cols(a=(1, 2)), (drawn(1), drawn(2)), (connection(1, 1, 2),), ())
    assert links == ()


def test_pairs_are_sorted_and_unique() -> None:
    """Two links between `a` and `b`, one written the other way round, and one with `c`."""
    columns = _cols(b=(1, 3), a=(2, 4), c=(5,))
    functions = tuple(drawn(n) for n in range(1, 6))
    wires = (connection(1, 1, 2), connection(2, 4, 3), connection(3, 3, 5))
    assert pole_links(columns, functions, wires, ()) == (_pair("a", "b"), _pair("b", "c"))
