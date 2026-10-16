"""The box symbols (SYMDEF-SLOTS SS5 b): the diagram box, its by-others variant and the card."""

import pytest
from symdef import Polyline, Style, body_box, stretch

from electrical_symbols import LIBRARY

CHANNELS = {"c1": 8, "c2": 40, "c3": 64, "c4": 104}


def port_at(symbol, port_id):
    return next(p.position for p in symbol.ports if p.id == port_id)


def slot_at(symbol, slot_id):
    return next(s.position for s in symbol.slots if s.id == slot_id)


def outline(symbol):
    return next(e for e in symbol.elements if isinstance(e, Polyline))


def test_card_natural_width_is_32_and_cut_at_16():
    """The spec's worked example starts from a 4-channel card, 32 wide, cut at x = 16."""
    card = LIBRARY.get("card")
    box = body_box(card)
    assert box.max.x - box.min.x == 32
    assert [(s.axis, s.at) for s in card.stretch] == [("x", 16)]
    assert [p.id for p in card.ports] == ["c1", "c2", "c3", "c4"]


def test_stretched_card_has_the_passed_width_and_port_positions():
    """Spec worked example (port ids start with a letter in the guide's id grammar)."""
    wide = stretch(LIBRARY.get("card"), "x", 112, CHANNELS)
    box = body_box(wide)
    assert box.max.x - box.min.x == 112
    for port_id, x in CHANNELS.items():
        assert port_at(wide, port_id).x == x
        assert slot_at(wide, f"marking.{port_id}").x == x + 0.25  # the marking follows its port


def test_diagram_box_stretches_on_x_then_y_with_offsets():
    box = LIBRARY.get("diagram-box")
    first = body_box(box)
    wide = stretch(box, "x", 40)
    tall = stretch(wide, "y", 20, {"w1": 4, "w2": 16, "e1": 6, "e2": 14})
    after = body_box(tall)
    assert after.max.x - after.min.x == 40
    assert after.max.y - after.min.y == 20
    assert first.max.y - first.min.y == 6
    assert [port_at(tall, name).y for name in ("w1", "w2", "e1", "e2")] == [4, 16, 6, 14]
    assert port_at(tall, "e1").x == port_at(box, "e1").x + 40 - 16  # the east leads moved with x
    assert slot_at(tall, "marking.w2").y == 16 - 0.5  # the marking follows its port


def test_offsets_on_the_wrong_edge_raise():
    """An x offset names a west port, which is not on a north or south edge."""
    with pytest.raises(ValueError, match="w1"):
        stretch(LIBRARY.get("diagram-box"), "x", 40, {"w1": 2})


def test_by_others_variant_draws_the_body_dashed():
    plain = LIBRARY.get("diagram-box")
    others = LIBRARY.get("diagram-box-by-others")
    assert outline(plain).style is Style.SOLID
    assert outline(others).style is Style.DASHED
    assert {p.id for p in plain.ports} == {p.id for p in others.ports}
