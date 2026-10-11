"""`pole_links`, the column pairs a pole link joins.

Functions are `samples.drawn(n)`: port `13` of function `n` at symbol port `in`, `14` at `out`,
both on the through path. `connection(number, upper, lower)` joins `14` of `upper` to `13` of
`lower`. Every case is one fact of the definition `lint/chains.py` uses for `CHAIN_BROKEN`.
"""

import dataclasses

from samples import column, connection, drawn, hid, through_geometry

from fransys_layout.stages import PortRef
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


def test_a_net_of_three_ports_is_no_link() -> None:
    """A second conductor from port `14` of function 1 to function 3 makes a net of three."""
    wires = (connection(1, 1, 2), connection(2, 1, 3))
    links = pole_links(_cols(a=(1,), b=(2,), c=(3,)), (drawn(1), drawn(2), drawn(3)), wires, ())
    assert links == ()
