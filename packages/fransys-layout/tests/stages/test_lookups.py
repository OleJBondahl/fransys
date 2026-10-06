"""The shared stage lookups: each is the one home of a rule several stages used to copy."""

from types import SimpleNamespace

import pytest
from samples import drawn, hid, placed

from fransys_layout.geometry import OPPOSITE, Facing, LayoutError, translate
from fransys_layout.stages import ROLE_ORDER, Role
from fransys_layout.stages.lookups import (
    drawn_of,
    group_of,
    nets_from_pairs,
    owner_of,
    placed_keepout,
    placed_of,
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


def test_opposite_flips_every_facing_and_flips_back():
    assert {f: OPPOSITE[f] for f in Facing} == {
        Facing.N: Facing.S,
        Facing.S: Facing.N,
        Facing.E: Facing.W,
        Facing.W: Facing.E,
    }


def test_role_order_is_strongest_first_and_complete():
    assert ROLE_ORDER == (Role.POWER, Role.CONTROL, Role.SIGNAL)
    assert set(ROLE_ORDER) == set(Role)


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
