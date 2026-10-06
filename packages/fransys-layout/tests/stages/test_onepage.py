"""`page_wiring`: where each function stands at home, the conductor's page and the wired ends.

Hand-made values. Functions 1 and 2 are joined by conductor 1 (port 22 of function 2 to port 11
of function 1). Column `a` is a home column; column `r` is a replica column when it is named so.
"""

from typing import TYPE_CHECKING

from samples import connection, hid, placed

from fransys_layout.stages.onepage import page_wiring
from fransys_layout.stages.types import NetGroup, PortRef, Role

if TYPE_CHECKING:
    from fransys_layout.stages.types import PlacedFunction


def _seats(*stands: tuple[int, int, str]) -> tuple[PlacedFunction, ...]:
    """The placed functions `(function, page, column name)`: where each stands."""
    return tuple(placed(n, x=0, y=0, page=page, name=name) for n, page, name in stands)


def test_two_functions_on_one_page_are_at_home_and_both_ends_are_wired_there() -> None:
    """Both functions stand on page 1: at home, the conductor needs no chosen page, and the wiring
    holds each end's `(port, drawing set, page)`."""
    # UNDO: stages/onepage.py `page_wiring`: `wired_ends(connections, at_home, routed_on)` ->
    #   `frozenset()` (nothing is wired)
    at_home, routed_on, wired = page_wiring(
        (connection(1, 2, 1),), (), _seats((1, 1, "a"), (2, 1, "a")), frozenset()
    )
    assert at_home == {(hid("function", 1), (1, 1)): True, (hid("function", 2), (1, 1)): True}
    assert routed_on == {}
    assert wired == {(hid("port", 22), 1, 1), (hid("port", 11), 1, 1)}


def test_a_conductor_between_two_pages_is_routed_on_the_page_where_its_ends_are_at_home() -> None:
    """Both functions stand on page 1 in column `a` and on page 2 in the replica column `r`: the
    conductor is routed on page 1, so only page 1 holds its ends in the wiring, and page 2's
    placements are not at home."""
    # UNDO: stages/onepage.py `page_wiring`: `homes(seats, replicas, attached)` ->
    #   `homes(seats, frozenset(), attached)` (page 2 counts as home: FAILED this
    #   test alone on `at_home[...] is False`)
    stands = ((1, 1, "a"), (2, 1, "a"), (1, 2, "r"), (2, 2, "r"))
    at_home, routed_on, wired = page_wiring(
        (connection(1, 2, 1),), (), _seats(*stands), frozenset({("invented", "r")})
    )
    assert at_home[hid("function", 1), (1, 2)] is False
    assert at_home[hid("function", 1), (1, 1)] is True
    assert routed_on == {hid("conductor", 1): (1, 1)}
    assert wired == {(hid("port", 22), 1, 1), (hid("port", 11), 1, 1)}


def test_the_ports_of_a_net_group_with_a_mate_on_the_page_are_wired_there() -> None:
    """S20 M7: `route` joins a declared net's ports on a page, so each has a wire there; a net
    port alone on its page (function 3, page 2) has none."""
    # UNDO: stages/onepage.py `page_wiring`: `| net_wired(net_groups, at_home)` -> nothing
    #   (a net group's ports are not wired: FAILED this test alone)
    group = NetGroup(
        net=hid("net", 500),
        physical_net=hid("net", 500),
        role=Role.CONTROL,
        ports=tuple(
            PortRef(function=hid("function", n), port=hid("port", n * 10 + 2)) for n in (1, 2, 3)
        ),
    )
    stands = ((1, 1, "a"), (2, 1, "a"), (3, 2, "b"))
    *_, wired = page_wiring((), (), _seats(*stands), frozenset(), (group,))
    assert wired == {(hid("port", 12), 1, 1), (hid("port", 22), 1, 1)}
