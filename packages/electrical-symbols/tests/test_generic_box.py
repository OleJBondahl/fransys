"""`generic_box`: the labelled-box placeholder as a real toolkit symbol."""

import pytest
from symdef.boxes import body_box, slot_box
from symdef.geometry import Box, Direction, Point, Polyline
from symdef.model import SymbolKind

from electrical_symbols import GENERIC_BOX_KEY, box_pitch, generic_box


def _widths(names: tuple[str, ...]) -> tuple[int, ...]:
    """Marking widths in G the caller would measure: "longmarking" is 41 G, any other 4 G."""
    return tuple(41 if "longmarking" in name else 4 for name in names)


def _box(names, **kwargs):
    return generic_box(names, marking_widths=_widths(names), **kwargs)


def test_the_key_is_the_symbol_reference_number():
    symbol = _box(())
    assert symbol.reference.number == GENERIC_BOX_KEY
    assert symbol.kind is SymbolKind.SYMBOL


def test_a_generic_box_without_ports_is_the_minimum_body_and_has_no_ports():
    symbol = _box(())
    assert symbol.ports == ()
    assert body_box(symbol) == Box(Point(-2, -2), Point(2, 2))
    (outline,) = symbol.elements
    assert isinstance(outline, Polyline)
    assert outline.closed is True


def test_three_ports_are_two_pairs_and_a_wider_body():
    """Port i is at x = 2 M x (i // 2): `a`, `b`, `c` sit at (0,-2), (0,2), (2,-2)."""
    symbol = _box(("a", "b", "c"))
    assert [(p.id, p.position, p.direction) for p in symbol.ports] == [
        ("a", Point(0, -2), Direction.N),
        ("b", Point(0, 2), Direction.S),
        ("c", Point(2, -2), Direction.N),
    ]
    assert body_box(symbol) == Box(Point(-2, -2), Point(4, 2))


def test_the_tag_slot_is_where_design_puts_it():
    symbol = _box(())
    (tag,) = symbol.slots
    assert tag.id == "tag"
    assert tag.position == Point(2.5, 0)
    assert tag.side is Direction.E
    assert tag.box == (6, 1)
    assert slot_box(tag) == Box(Point(2.5, -0.5), Point(8.5, 0.5))


def test_the_symbol_is_never_repeated():
    assert _box(("a", "b")).pole_pitch is None


def test_explicit_sides_overrides_the_alternating_rule():
    """`sides` puts every named port where asked, not on the alternating N/S rule."""
    symbol = _box(("a", "b"), sides=("n", "n"))
    assert [port.direction for port in symbol.ports] == [Direction.N, Direction.N]


def test_sides_shorter_than_port_names_raises():
    # `match=r"."` only satisfies ruff's PT011 (a bare `pytest.raises(ValueError)` is "too
    # broad"); it asserts nothing about the message's wording, which is `zip`'s own, an
    # implementation detail this test does not pin.
    with pytest.raises(ValueError, match=r"."):
        _box(("a", "b"), sides=("n",))


def test_a_marking_slot_sits_beside_each_port():
    """One `marking.<port id>` slot per port, E of its wire, just inside the body."""
    symbol = _box(("a", "b", "function.longmarking"))
    markings = symbol.slots[1:]
    assert [marking.id for marking in markings] == ["marking.a", "marking.b", "marking.function.longmarking"]
    # CAN-FAIL: generic_box.py `_marks`: `width / G_PER_MODULE` -> a fixed 1.5 gives 1.5, not 41/8, for the long one
    assert [marking.box for marking in markings] == [(0.5, 1), (0.5, 1), (41 / 8, 1)]
    for marking, port in zip(markings, symbol.ports, strict=True):
        assert marking.side is Direction.E
        offset_y = 0.75 if port.direction is Direction.N else -0.75
        assert marking.position == Point(port.position.x + 0.25, port.position.y + offset_y)


def test_pitch_rounds_the_offset_up_not_down():
    """Pitch is `ceil(text_width / 8 + 0.5)` M; "longmarking" (41 G) needs 6 M, not 5."""
    # CAN-FAIL: generic_box.py `_pitch`: `math.ceil` -> `math.floor` (5 M) fails the box width
    symbol = _box(("function.longmarking",))
    assert body_box(symbol) == Box(Point(-2, -2), Point(10, 2))


def test_offsets_set_each_ports_x_and_the_body_ends_one_pitch_past_the_last():
    """model-0129: `offsets` (M) replace the pitch; the body covers the farthest port."""
    # UNDO: generic_box.py `x=offsets[i]` -> the pitch rule: the ports stand at 0 and 2
    symbol = _box(("a", "b"), sides=("n", "n"), offsets=(0, 10))
    assert [port.position.x for port in symbol.ports] == [0, 10]
    assert body_box(symbol).max.x == 12


def test_offsets_of_the_wrong_length_raise():
    with pytest.raises(ValueError, match=r"offsets"):
        _box(("a", "b"), sides=("n", "n"), offsets=(0,))


def test_no_offsets_leaves_the_default_box_as_it_was():
    assert _box(("a", "b", "c")) == _box(("a", "b", "c"), offsets=())


def test_a_side_other_than_n_or_s_raises():
    """A side is "n" or "s"; any other is refused, with or without offsets, never drawn south."""
    with pytest.raises(ValueError, match="got 'e'"):
        _box(("a", "b"), sides=("n", "e"))
    with pytest.raises(ValueError, match="got 'e'"):
        _box(("a", "b"), sides=("n", "e"), offsets=(0.0, 2.0))


@pytest.mark.parametrize("count", [8, 9, 16])
def test_the_kth_north_and_south_pin_of_a_half_split_box_share_one_x(count: int):
    """BOX-SIDES D: the half split (first half N, rest S) puts pin k over pin k at one pitch."""
    names = tuple(f"p{i:02d}" for i in range(count))
    north = (count + 1) // 2
    sides = ("n",) * north + ("s",) * (count - north)
    symbol = _box(names, sides=sides)
    x = {port.id: port.position.x for port in symbol.ports}
    over, under = names[:north], names[north:]
    assert [x[a] for a in over[: len(under)]] == [x[b] for b in under]
    assert x[names[1]] - x[names[0]] == box_pitch(_widths(names))


def test_box_marking_widths_are_symdefs_widths_rounded_up_to_the_grid():
    """Pinned to symdef's answer in the library font (CC1): ceil of the 1 M wide marking in G."""
    from electrical_symbols import LIBRARY, box_marking_widths

    assert box_marking_widths(LIBRARY, ["1", "A1", "PE", "LONGNAME", "13"]) == (5, 10, 9, 42, 10)


def test_turned_markings_stand_beside_their_wires_inside_a_body_that_holds_them():
    """R2069: a turned slot is 1 M wide and as long as its text, from its edge; the pitch is 2 M and the body holds one from each edge."""
    # CAN-FAIL: generic_box.py `_height` returns 4 M when turned: the body is shorter than the long slot's 5.25 M
    symbol = generic_box(("function.longmarking", "b"), marking_widths=_widths(("function.longmarking", "b")), turn=True)
    long, short = symbol.slots[1:]
    assert (long.turn, long.side, long.box) == (True, Direction.S, (1.0, 41 / 8))
    assert (short.turn, short.side) == (True, Direction.N)
    assert body_box(symbol).max.y - body_box(symbol).min.y >= 2 * long.box[1]
    assert [p.position.x for p in symbol.ports] == [0.0, 0.0]
    assert [p.position.x for p in generic_box(("a", "b", "c", "d"), marking_widths=(41,) * 4, turn=True).ports] == [0.0, 0.0, 2.0, 2.0]
