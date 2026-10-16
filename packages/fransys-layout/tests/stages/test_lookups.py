"""The shared stage lookups: each is the one home of a rule several stages used to copy."""

import dataclasses
from types import SimpleNamespace

import pytest
from samples import drawn, hid, placed

from fransys_layout.geometry import LayoutError, translate
from fransys_layout.stages.lookups import (
    device_turns,
    drawn_of,
    group_of,
    nets_from_pairs,
    owner_of,
    placed_keepout,
    placed_of,
    set_rank,
    turn_mirrors,
)


def test_drawn_of_keys_by_function_and_names_the_caller_on_a_duplicate():
    one = drawn(1)
    assert drawn_of((one,), "place") == {one.function: one}
    with pytest.raises(LayoutError, match="drawn functions route was given"):
        drawn_of((one, one), "route")


def test_placed_of_keys_by_function_and_names_the_caller_on_a_duplicate():
    one = placed(1, x=0, y=0)
    assert placed_of((one,), "route") == {one.function: one}
    with pytest.raises(LayoutError, match="on the page route was given"):
        placed_of((one, one), "route")


def test_owner_of_maps_each_drawn_port_to_its_function():
    one = drawn(1)
    assert owner_of((one,)) == {port.port: one.function for port in one.ports}
    assert owner_of((one,))


def test_a_port_drawn_by_its_function_and_by_its_pin_cell_is_owned_by_the_function():
    # UNDO: stages/lookups.py, `owner_of`: the `owner.get(...) == port.port` test -> `True`
    whole = drawn(1)
    port = whole.ports[0]
    cell = dataclasses.replace(drawn(2), function=port.port, ports=(port,))
    for order in ((whole, cell), (cell, whole)):
        assert owner_of(order)[port.port] == whole.function


def test_placed_keepout_is_the_keepout_moved_by_the_origin():
    one = placed(1, x=40, y=80)
    assert placed_keepout(one) == translate(one.geometry.keepout, dx=40, dy=80)
    assert placed_keepout(one) != one.geometry.keepout


def test_group_of_prefers_the_hint_then_the_last_of_the_path():
    a, b = hid("aspect", 1), hid("aspect", 2)

    def spec(hint, path):
        return SimpleNamespace(group_hint=hint, group_path=path)

    assert group_of(spec(a, (b,))) == a
    assert group_of(spec(None, (a, b))) == b
    assert group_of(spec(None, ())) is None


def test_nets_from_pairs_joins_transitively_and_registers_members():
    a, b, c, d, e = (hid("port", n) for n in range(1, 6))
    nets = nets_from_pairs([(a, b), (b, c), (d, e)], members=[hid("port", 9)])
    groups = {tuple(sorted(ports)) for ports in nets.groups().values()}
    assert groups == {(a, b, c), (d, e), (hid("port", 9),)}


def test_terminal_lift_is_two_text_heights():
    from samples import PROFILE

    from fransys_layout.stages.references.markers import terminal_lift

    assert terminal_lift(PROFILE) == 2 * PROFILE.text_height
    assert PROFILE.text_height > 0


def test_link_world_holds_the_drawn_functions_by_handle_and_the_seats_by_page():
    from samples import PROFILE, SHEET

    from fransys_layout.stages.references.cuts import link_world
    from fransys_layout.stages.references.types import MarkerScene

    one = drawn(1)
    world = link_world(MarkerScene(seats=(), drawn=(one,), sheet=SHEET, profile=PROFILE))
    assert world.drawn_of == {one.function: one}
    assert world.where == {}


def test_turn_mirrors_spares_a_terminal() -> None:
    """The one form of a turn: a strip terminal turns at R180, any other pole at MR180."""
    # UNDO: stages/lookups.py `turn_mirrors`, return `terminal`
    assert turn_mirrors(terminal=False) is True
    assert turn_mirrors(terminal=True) is False


def test_device_turns_needs_a_wired_pole_and_every_vote_against() -> None:
    """layout-0062 (TURN-VOTE): no vote keeps R0, a split vote keeps R0."""
    # UNDO: stages/lookups.py `device_turns`, return `bool(votes)`
    assert device_turns([True]) is True
    assert device_turns([True, True]) is True
    assert device_turns([True, False]) is False
    assert device_turns([]) is False


def test_set_rank_reads_the_rank_and_raises_naming_the_set_and_the_fix() -> None:
    assert set_rank({2: 1}, 2) == 1
    with pytest.raises(ValueError, match=r"drawing set 3 has no rank: pass derive\.set_ranks"):
        set_rank({2: 1}, 3)
