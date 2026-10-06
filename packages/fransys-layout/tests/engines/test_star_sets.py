"""D9 per drawing set (layout-0070): the star's pure steps, on hand-made ports and `Beside`s.

Ports are `hid("port", 10 * n + 1)` of function `n` (`samples.function_spec`). `_beside` says
where each pair is wired beside and where each port stands, per drawing set.
`Star.set_cluster` holds `(set, port, first)` for a port that is not its cluster's first there.
"""

import dataclasses

from samples import PROFILE, SHEET, drawn, function_spec, hid, placed

from fransys_layout.stages import PortRef, Role
from fransys_layout.stages.references.markers import star_markers
from fransys_layout.stages.references.nets import (
    _is_star,
    _set_clusters,
    branch_pages,
    star_nets,
)
from fransys_layout.stages.references.types import Beside, MarkerScene, Star
from fransys_layout.stages.types import Connection


def _port(n: int):
    return hid("port", 10 * n + 1)


def _wire(handle: int, a: int, b: int) -> Connection:
    return Connection(
        handle=hid("conductor", handle),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a), port=_port(a)),
        b=PortRef(function=hid("function", b), port=_port(b)),
    )


def _beside(pairs: dict[tuple[int, int], set[int]], stands: dict[int, set[int]]) -> Beside:
    """Ports of functions a, b are beside in `pairs[a, b]`; function n stands in `stands[n]`."""
    return Beside(
        pairs={(_port(a), _port(b)): frozenset(s) for (a, b), s in pairs.items()},
        sets={_port(n): frozenset(s) for n, s in stands.items()},
    )


def _stars(wires: list[Connection], beside: Beside | None) -> tuple[Star, ...]:
    numbers = {int(w.a.function.value, 16) for w in wires} | {
        int(w.b.function.value, 16) for w in wires
    }
    return star_nets(tuple(wires), tuple(function_spec(n) for n in sorted(numbers)), (), beside)


def test_a_net_beside_in_no_single_set_is_a_star_though_the_union_is_one_cluster() -> None:
    """P-Q is beside in set 1 only and Q-R in set 2 only, all three stand in both: in each set one
    port is apart, so the net is a star (the union of the sets' wires is one cluster)."""
    # UNDO: stages/references/nets.py, `is_star`: `if sets_of is None:` to `if True:` (the
    #     old global test): FAILED test_a_net_beside_in_no_single_set_is_a_star_though_the_union...
    stands = {1: {1, 2}, 2: {1, 2}, 3: {1, 2}}
    beside = _beside({(1, 2): {1}, (2, 3): {2}}, stands)
    (star,) = _stars([_wire(1, 1, 2), _wire(2, 2, 3)], beside)
    assert star.ref.port == _port(2)  # the hub
    assert star.conductors == frozenset()  # both wires are beside somewhere, both stay routed
    assert set(star.set_cluster) == {(1, _port(2), _port(1)), (2, _port(3), _port(2))}


def test_a_net_all_beside_in_one_set_and_apart_in_another_it_stands_in_is_a_star() -> None:
    """P-Q-R are wired beside in set 1 and all stand in set 2 with no wire beside: set 2 has three
    clusters, so a star; set 1 has no marker for it, set 2 a branch for each port but the hub."""
    # UNDO: stages/references/nets.py, `is_star`: `if sets_of is None:` to `if True:`:
    #     FAILED test_a_net_all_beside_in_one_set_and_apart_in_another_it_stands_in_is_a_star
    stands = {1: {1, 2}, 2: {1, 2}, 3: {1, 2}}
    beside = _beside({(1, 2): {1}, (2, 3): {1}}, stands)
    (star,) = _stars([_wire(1, 1, 2), _wire(2, 2, 3)], beside)
    assert {(s, p) for s, p, _ in star.set_cluster} == {(1, _port(2)), (1, _port(3))}
    pages = [(1, 1), (2, 1)]
    marked = {n: branch_pages(pages, _port(n), star.ref.port, star.set_cluster) for n in (1, 3)}
    assert marked == {1: [(2, 1)], 3: [(2, 1)]}


def test_a_net_wired_beside_in_every_set_it_stands_in_is_no_star() -> None:
    """Control: P-Q-R are one cluster in each set they stand in: no star, all wires drawn."""
    # UNDO: stages/references/nets.py, `is_star`: `return False` at the end to `return True`:
    #     FAILED test_a_net_wired_beside_in_every_set_it_stands_in_is_no_star
    stands = {1: {1, 2}, 2: {1, 2}, 3: {1}}
    beside = _beside({(1, 2): {1, 2}, (2, 3): {1}}, stands)
    assert _stars([_wire(1, 1, 2), _wire(2, 2, 3)], beside) == ()


def test_without_placements_the_old_global_test_stands() -> None:
    """No `sets_of`: a net is a star when the kept wires, all sets joined, leave two clusters."""
    # UNDO: stages/references/nets.py, `is_star`: in the `sets_of is None` branch,
    #     `>= 2` to `>= 0`: FAILED test_without_placements_the_old_global_test_stands
    counted = [_port(1), _port(2), _port(3)]
    both = [(_wire(1, 1, 2), frozenset({1})), (_wire(2, 2, 3), frozenset({2}))]
    assert not _is_star(counted, both, None)
    assert _is_star(counted, both[:1], None)


def test_set_clusters_keeps_one_entry_per_port_that_is_not_its_clusters_first() -> None:
    """A wire beside in set 1 only makes entries for set 1; a set with no wire has none."""
    # UNDO: stages/references/nets.py, `set_clusters`: `if drawing_set in sets` to `if sets`:
    #     the wire also joins set 2: FAILED test_set_clusters_keeps_one_entry_per_port...
    wires = [(_wire(1, 1, 2), frozenset({1})), (_wire(2, 2, 3), frozenset({1, 3}))]
    counted = [_port(1), _port(2), _port(3)]
    assert _set_clusters(counted, wires) == (
        (1, _port(2), _port(1)),
        (1, _port(3), _port(1)),
        (3, _port(3), _port(2)),
    )


def test_a_port_that_sorts_below_the_hub_takes_no_branch_beside_it() -> None:
    """Port 1 is the first of the hub's cluster (hub 2, joined to 1 in set 1): no branch there.
    Port 3, wired to nothing, takes one; in set 2, where nothing is wired, both do."""
    # UNDO: stages/references/nets.py, `branch_pages`: drop `and port != first.get(...)`:
    #     FAILED test_a_port_that_sorts_below_the_hub_takes_no_branch_beside_it
    in_cluster = ((1, _port(2), _port(1)),)
    pages = [(1, 1), (2, 1)]
    hub = _port(2)
    assert branch_pages(pages, _port(1), hub, in_cluster) == [(2, 1)]
    assert branch_pages(pages, _port(3), hub, in_cluster) == [(1, 1), (2, 1)]


def test_a_port_apart_in_two_sets_takes_a_branch_in_each() -> None:
    """A port standing in sets 1, 2 and 3, apart in all: one branch per set, not the last only."""
    # UNDO: stages/references/nets.py, `branch_pages`: `for drawing_set, page in
    #     home.items()` to `for drawing_set, page in list(home.items())[-1:]`:
    #     FAILED test_a_port_apart_in_two_sets_takes_a_branch_in_each
    pages = [(1, 1), (2, 4), (3, 2)]
    assert branch_pages(pages, _port(3), _port(2), ()) == pages


def test_a_port_on_two_pages_of_one_set_takes_one_branch_on_the_first_page() -> None:
    """A replica in one set: one branch, on the set's first page; a wire beside there removes it."""
    # UNDO: stages/references/nets.py, `branch_pages`: `home.setdefault(page[0], page)` to
    #     `home[page[0]] = page` (the last page): FAILED test_a_port_on_two_pages_of_one_set...
    pages = [(3, 2), (3, 5)]
    assert branch_pages(pages, _port(3), _port(2), ()) == [(3, 2)]
    beside_the_hub = ((3, _port(3), _port(2)),)  # 3 is joined to 2 by a wire beside on page 5
    assert branch_pages(pages, _port(3), _port(2), beside_the_hub) == []


def _markers(stands: dict[int, list[tuple[int, int]]], star: Star | None = None):
    """`star_markers` of one star (default: hub 2, functions 1, 3); `stands[n]`: `(set, page)`s."""
    star = star or Star(
        ports=tuple(PortRef(function=hid("function", n), port=_port(n)) for n in (1, 2, 3)),
        ref=PortRef(function=hid("function", 2), port=_port(2)),
        conductors=frozenset({hid("conductor", 1)}),
        by_designation=True,
    )
    at = [
        dataclasses.replace(placed(n, x=40 + 80 * n, y=64, page=page), drawing_set=drawing_set)
        for n, pages in stands.items()
        for drawing_set, page in pages
    ]
    found = star_markers(
        (star,),
        MarkerScene(tuple(at), tuple(drawn(n) for n in stands), SHEET, PROFILE),
    )
    return {
        (m.star, int(m.port.value, 16) // 10, m.drawing_set, m.page): (
            m.partner_set,
            m.partner_page,
        )
        for m in found
    }


def test_a_branch_names_the_reference_on_its_page_else_in_its_set_else_at_home() -> None:
    """The hub stands in set 1 page 1 and set 3 page 1. Port 1 (set 3 page 1) names it on its own
    page; port 3 (set 3 page 4) names it in its own set, not the set-1 home; port 1 also stands
    in set 2, where the hub does not, and names the home."""
    # UNDO: stages/references/markers.py, `star_markers`: the line `target = refs.get(page) or
    #     next(iter(own_set), home)` to `target = home`:
    #     FAILED test_a_branch_names_the_reference_on_its_page_else_in_its_set_else_at_home
    found = _markers({1: [(3, 1), (2, 1)], 2: [(1, 1), (3, 1)], 3: [(3, 4)]})
    assert found[("branch", 1, 3, 1)] == (3, 1)
    assert found[("branch", 3, 3, 4)] == (3, 1)
    assert found[("branch", 1, 2, 1)] == (1, 1)
    assert found[("ref", 2, 3, 1)][0] == 3  # the reference in set 3 lists the two branches there


def test_a_star_that_drops_no_conductor_still_draws_its_markers() -> None:
    """Both wires are beside in set 1 only and all three ports stand in sets 1 and 2: a star
    with no conductor dropped. `star_markers` takes a wire of the net as the markers' connection
    (a hand-made star with none has no marker to draw) and marks set 2, where nothing is wired."""
    # UNDO: stages/references/markers.py, `star_markers`: `min(star.conductors or star.wires)` to
    #     `min(star.conductors)`: FAILED test_a_star_that_drops_no_conductor_still_draws_its_markers
    #     (ValueError, min() of an empty set)
    pages = [(1, 1), (2, 1)]
    stands = {1: {1, 2}, 2: {1, 2}, 3: {1, 2}}
    beside = _beside({(1, 2): {1}, (2, 3): {1}}, stands)
    (star,) = _stars([_wire(1, 1, 2), _wire(2, 2, 3)], beside)
    assert star.conductors == frozenset()
    assert star.wires == frozenset({hid("conductor", 1), hid("conductor", 2)})
    found = _markers({1: pages, 2: pages, 3: pages}, star)
    assert {key for key in found if key[0] == "branch"} == {
        ("branch", 1, 2, 1),
        ("branch", 3, 2, 1),
    }
