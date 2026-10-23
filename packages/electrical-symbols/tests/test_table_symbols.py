"""The table symbols (SYMDEF-SLOTS SS5 a): rows and heads, each head authored in its row's frame."""

import pytest
from symdef import body_box, fitted_table, from_divisions, keepout_box, table

from electrical_symbols import LIBRARY

CABLE = ("cable-column", "cable-head", "x", "core")
CONTACT = ("contact-row", "contact-head", "y", ("no", "nc"))
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
        for name in (extra,) if isinstance(extra, str) else extra or ():
            assert f"{k}.{name}" in slots
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
        for slot in LIBRARY.get(head).slots:
            at = next(s for s in built.slots if s.id == slot.id).position
            assert at == slot.position


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


def test_fitted_contact_table_sizes_each_column_to_its_widest_text():
    """A coil's NO and NC cells: each column is as wide as its widest text, rows stack on y."""
    row, head = LIBRARY.get("contact-row"), LIBRARY.get("contact-head")
    height = from_divisions(LIBRARY.grid, 8)
    short = fitted_table(row, "y", [{"no": "13 /1.1", "nc": "21 /1.1"}], LIBRARY, height, head=head)
    long = fitted_table(
        row, "y", [{"no": "13 /1.1", "nc": "21 /99.99 and more"}], LIBRARY, height, head=head
    )
    wide = lambda t: body_box(t).max.x - body_box(t).min.x  # noqa: E731 - a one-use measure
    xs = lambda t: {s.id: s.position.x for s in t.slots}  # noqa: E731 - a one-use read
    assert wide(long) > wide(short)
    assert xs(long)["1.nc"] == xs(short)["1.nc"]
    assert xs(long)["nc"] == xs(short)["nc"]


def test_stacked_contact_rows_keep_the_closing_pad_out_of_the_keepout():
    """The row's `pad` slot box lies 0.25 below its body; symdef 0.22 keeps it out."""
    row, head = LIBRARY.get("contact-row"), LIBRARY.get("contact-head")
    built = fitted_table(
        row, "y", [{"no": "13 /1.1"}] * 3, LIBRARY, from_divisions(LIBRARY.grid, 8), head=head
    )
    assert keepout_box(built).max.y == body_box(built).max.y


def test_the_headed_contact_head_is_one_module_above_the_plain_head_with_a_heading_slot():
    """es-0075: the headed form adds a heading line over the titles; the plain head is unchanged."""
    plain, headed = LIBRARY.get("contact-head"), LIBRARY.get("contact-head-headed")
    assert slot_ids(plain) == {"no", "nc"}
    assert slot_ids(headed) == {"no", "nc", "heading"}
    assert body_box(headed).max.y == body_box(plain).max.y == 0
    assert body_box(plain).min.y - body_box(headed).min.y == 1.0
    assert headed.stretch == plain.stretch
    heading = next(s for s in headed.slots if s.id == "heading")
    titles = next(s for s in headed.slots if s.id == "no")
    assert heading.position.y < titles.position.y
    assert heading.position.x == titles.position.x


def test_the_headed_head_takes_the_heading_text_and_grows_at_the_row_cuts():
    row, head = LIBRARY.get("contact-row"), LIBRARY.get("contact-head-headed")
    height = from_divisions(LIBRARY.grid, 8)
    rows = [{"no": "13 /1.1", "nc": "21 /1.1"}]
    plain = fitted_table(row, "y", rows, LIBRARY, height, head=head)
    long = fitted_table(
        row, "y", rows, LIBRARY, height, head=head, head_texts={"heading": "-U1-K1234567890"}
    )
    wide = lambda t: body_box(t).max.x - body_box(t).min.x  # noqa: E731 - a one-use measure
    assert wide(long) > wide(plain)
