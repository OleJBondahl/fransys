"""`generic_box`: the labelled-box placeholder as a real toolkit symbol (decision D41)."""

import pytest
from graphical_symbols.boxes import body_box, slot_box
from graphical_symbols.geometry import Box, Direction, Point, Polyline
from graphical_symbols.model import SymbolKind

from electrical_symbols import GENERIC_BOX_KEY, box_pitch, generic_box


def test_the_key_is_the_symbol_reference_number():
    symbol = generic_box(())
    assert symbol.reference.number == GENERIC_BOX_KEY
    assert symbol.kind is SymbolKind.SYMBOL


def test_a_generic_box_without_ports_is_the_minimum_body_and_has_no_ports():
    symbol = generic_box(())
    assert symbol.ports == ()
    assert body_box(symbol) == Box(Point(-2, -2), Point(2, 2))
    (outline,) = symbol.elements
    assert isinstance(outline, Polyline)
    assert outline.closed is True


def test_three_ports_are_two_pairs_and_a_wider_body():
    """Port i is at x = 2 M x (i // 2): `a`, `b`, `c` sit at (0,-2), (0,2), (2,-2)."""
    symbol = generic_box(("a", "b", "c"))
    assert [(p.id, p.position, p.direction) for p in symbol.ports] == [
        ("a", Point(0, -2), Direction.N),
        ("b", Point(0, 2), Direction.S),
        ("c", Point(2, -2), Direction.N),
    ]
    assert body_box(symbol) == Box(Point(-2, -2), Point(4, 2))


def test_the_tag_slot_is_where_design_puts_it():
    symbol = generic_box(())
    (tag,) = symbol.slots
    assert tag.id == "tag"
    assert tag.position == Point(2.5, 0)
    assert tag.side is Direction.E
    assert tag.box == (6, 1)
    assert slot_box(tag) == Box(Point(2.5, -0.5), Point(8.5, 0.5))


def test_the_symbol_is_never_repeated():
    assert generic_box(("a", "b")).pole_pitch is None


def test_explicit_sides_overrides_the_alternating_rule():
    """R7 C5: `sides` puts every named port where asked, not on the alternating N/S rule."""
    symbol = generic_box(("a", "b"), sides=("n", "n"))
    assert [port.direction for port in symbol.ports] == [Direction.N, Direction.N]


def test_sides_shorter_than_port_names_raises():
    # `match=r"."` only satisfies ruff's PT011 (a bare `pytest.raises(ValueError)` is "too
    # broad"); it asserts nothing about the message's wording, which is `zip`'s own, an
    # implementation detail this test does not pin (review R3).
    with pytest.raises(ValueError, match=r"."):
        generic_box(("a", "b"), sides=("n",))


def test_a_marking_slot_sits_beside_each_port():
    """R7 B3: one `marking.<port id>` slot per port, E of its wire, just inside the body."""
    symbol = generic_box(("a", "b", "c"))
    markings = symbol.slots[1:]
    assert [marking.id for marking in markings] == ["marking.a", "marking.b", "marking.c"]
    for marking, port in zip(markings, symbol.ports, strict=True):
        assert marking.side is Direction.E
        assert marking.box == (1.5, 1)
        offset_y = 0.75 if port.direction is Direction.N else -0.75
        assert marking.position == Point(port.position.x + 0.25, port.position.y + offset_y)


def test_pitch_rounds_the_offset_up_not_down():
    """R7 B3: pitch is `ceil(text_width / 8 + 0.5)` M; "longmarking" (41 G) needs 6 M, not 5."""
    # CAN-FAIL: generic_box.py `_pitch`: `math.ceil` -> `math.floor` (5 M) fails the box width
    symbol = generic_box(("function.longmarking",))
    assert body_box(symbol) == Box(Point(-2, -2), Point(10, 2))


def test_offsets_set_each_ports_x_and_the_body_ends_one_pitch_past_the_last():
    """model-0129: `offsets` (M) replace the pitch; the body covers the farthest port."""
    # UNDO: generic_box.py `x=offsets[i]` -> the pitch rule: the ports stand at 0 and 2
    symbol = generic_box(("a", "b"), sides=("n", "n"), offsets=(0, 10))
    assert [port.position.x for port in symbol.ports] == [0, 10]
    assert body_box(symbol).max.x == 12


def test_offsets_of_the_wrong_length_raise():
    with pytest.raises(ValueError, match=r"offsets"):
        generic_box(("a", "b"), sides=("n", "n"), offsets=(0,))


def test_no_offsets_leaves_the_default_box_as_it_was():
    assert generic_box(("a", "b", "c")) == generic_box(("a", "b", "c"), offsets=())


def test_a_side_other_than_n_or_s_raises():
    """A side is "n" or "s"; any other is refused, with or without offsets, never drawn south."""
    with pytest.raises(ValueError, match="got 'e'"):
        generic_box(("a", "b"), sides=("n", "e"))
    with pytest.raises(ValueError, match="got 'e'"):
        generic_box(("a", "b"), sides=("n", "e"), offsets=(0.0, 2.0))


def test_box_pitch_fits_the_widest_thing_standing_at_a_port():
    """layout-0132: `stand` G wide needs `ceil(stand / 8 + 0.5)` M, never less than markings."""
    # CAN-FAIL: generic_box.py `box_pitch`: `max(longest, stand)` -> `longest` gives 2 M, not 3 M
    assert box_pitch(("+", "-")) == 2.0
    assert box_pitch(("+", "-"), stand=16) == 3.0
    assert box_pitch(("+", "-"), stand=4) == 2.0
    assert box_pitch(("function.longmarking",), stand=16) == 6.0


def test_a_stand_spaces_the_ports_at_the_wider_pitch_and_keeps_the_plain_body_margin():
    """`stand` 20 G: ports 3 M apart; the body ends at the last port plus plain pitch plus 2 M."""
    symbol = generic_box(("a", "b", "c"), stand=20)
    assert [p.position.x for p in symbol.ports] == [0, 0, 3]
    assert body_box(symbol) == Box(Point(-2, -2), Point(5, 2))
    assert generic_box(("a", "b", "c"), stand=0) == generic_box(("a", "b", "c"))
