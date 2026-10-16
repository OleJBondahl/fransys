"""The table symbols (SYMDEF-SLOTS SS5 a): rows and heads, each head authored in its row's frame."""

import pytest
from symdef import body_box, table

from electrical_symbols import LIBRARY

CABLE = ("cable-column", "cable-head", "x", "core")
CONTACT = ("contact-row", "contact-head", "y", "place")
PIN = ("pin-cell", None, "y", None)
PIN_WIDE = ("pin-cell-wide", None, "y", None)


def build(row, head, axis, n=3):
    return table(LIBRARY.get(row), n, axis, head=LIBRARY.get(head) if head else None)


def slot_ids(symbol):
    return {slot.id for slot in symbol.slots}


@pytest.mark.parametrize(("row", "head", "axis", "extra"), [CABLE, CONTACT, PIN, PIN_WIDE])
def test_table_names_ports_and_slots_per_copy(row, head, axis, extra):
    """Copy k has ports `k.<port>`, `marking.k.<port>` slots and `k.<slot>` for the others."""
    source = LIBRARY.get(row)
    built = build(row, head, axis)
    ports = {p.id for p in built.ports}
    slots = slot_ids(built)
    for k in (1, 2, 3):
        for port in source.ports:
            assert f"{k}.{port.id}" in ports
            if f"marking.{port.id}" in slot_ids(source):
                assert f"marking.{k}.{port.id}" in slots
        if extra:
            assert f"{k}.{extra}" in slots
    assert len(ports) == 3 * len(source.ports)


def test_cable_head_sits_above_the_first_column_and_starts_at_its_left_edge():
    """Compared by body boxes: the head ends where the column begins, on the column's x origin."""
    column = body_box(LIBRARY.get("cable-column"))
    head = body_box(LIBRARY.get("cable-head"))
    assert head.max.y == column.min.y
    assert head.min.x == column.min.x


def test_contact_head_lies_before_the_first_row_on_the_axis():
    row = body_box(LIBRARY.get("contact-row"))
    head = body_box(LIBRARY.get("contact-head"))
    assert head.max.y == row.min.y


def test_head_stays_where_it_is_authored_in_the_built_table():
    """table() never moves the head (amendment 2): its slot keeps its place and the rows follow."""
    for row, head, axis, _ in (CABLE, CONTACT):
        built = build(row, head, axis)
        at = next(s for s in built.slots if s.id == "heading").position
        assert at == next(s for s in LIBRARY.get(head).slots if s.id == "heading").position


def test_cable_head_is_stretched_to_n_steps():
    """The built table's body spans n columns, and the head spans all of it."""
    column = body_box(LIBRARY.get("cable-column"))
    step = column.max.x - column.min.x
    for n in (1, 3, 5):
        built = build("cable-column", "cable-head", "x", n)
        box = body_box(built)
        assert box.max.x - box.min.x == n * step
        head_xs = [
            p.x for e in built.elements if hasattr(e, "points") for p in e.points if p.y == -5
        ]
        assert max(head_xs) - min(head_xs) == n * step
