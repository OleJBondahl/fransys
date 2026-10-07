"""`box_ports`: the one home of a generic box's port names, order, sides and grid (D47)."""

import pytest

from electrical_symbols import (
    G_PER_MODULE,
    GENERIC_BOX_KEY,
    PORT_PITCH,
    PORT_PITCH_G,
    WIRING_GRID,
    box_port_marking,
    box_port_name,
    default_order,
    default_sides,
    draw_order,
    generic_box,
    is_generic_box,
)


def test_only_the_box_key_is_a_generic_box():
    assert is_generic_box(GENERIC_BOX_KEY)
    assert not is_generic_box("circuit-breaker")


def test_a_box_port_name_is_the_function_dot_the_port_and_its_marking_is_the_port():
    name = box_port_name("K1", "A1")
    assert name == "K1.A1"
    assert box_port_marking(name) == "A1"
    assert box_port_marking("A1") == "A1"
    assert box_port_marking(box_port_name("K1", "x.y")) == "y"


@pytest.mark.parametrize(
    ("count", "sides"),
    [(0, ()), (1, ("n",)), (2, ("n", "s")), (5, ("n", "s", "n", "s", "n"))],
)
def test_default_sides_alternate_from_north(count, sides):
    assert default_sides(count) == sides


def test_generic_box_without_sides_uses_the_default_sides():
    symbol = generic_box(("a", "b", "c"))
    assert tuple("n" if p.direction.name == "N" else "s" for p in symbol.ports) == default_sides(3)


def test_draw_order_is_left_to_right_and_north_before_south_at_one_x():
    ports = [(16, "n"), (0, "s"), (0, "n"), (16, "s")]
    assert sorted(ports, key=lambda p: draw_order(*p)) == [
        (0, "n"),
        (0, "s"),
        (16, "n"),
        (16, "s"),
    ]


def test_the_grid_constants_agree_with_the_box_it_draws():
    assert PORT_PITCH_G == PORT_PITCH * G_PER_MODULE == 16
    assert WIRING_GRID == G_PER_MODULE == 8
    ports = generic_box(("a", "b", "c")).ports
    assert [p.position.x for p in ports] == [0, 0, PORT_PITCH]


def test_default_order_sorts_the_names():
    assert default_order(["b", "K1.A2", "a", "K1.A1"]) == ("K1.A1", "K1.A2", "a", "b")
