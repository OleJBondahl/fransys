"""`drawn_symbol` builds the symbol a drawn record names from its texts (es-0076)."""

import pytest
from symdef import Orientation, SymdefError, measure

from electrical_symbols import LIBRARY, drawn_slots, drawn_symbol

_LONG = "A1.CHANNEL-17"


def test_no_texts_is_the_library_symbol() -> None:
    assert drawn_symbol("contact-row", (), library=LIBRARY) == LIBRARY.get("contact-row")


def test_a_box_has_a_port_per_row_in_the_rows_order() -> None:
    box = drawn_symbol("generic-box", (("2",), ("1",), (_LONG,)), library=LIBRARY)
    assert [p.id for p in box.ports] == ["2", "1", _LONG]


def test_a_longer_marking_widens_the_box_pitch() -> None:
    short = drawn_symbol("generic-box", (("1",), ("2",), ("3",)), library=LIBRARY)
    long = drawn_symbol("generic-box", (("1",), ("2",), ("A1.CHANNEL-17",)), library=LIBRARY)
    assert max(p.position.x for p in long.ports) > max(p.position.x for p in short.ports)


def test_a_table_has_its_keepout_top_left_at_the_origin() -> None:
    rows = (("NO", "NC"), ("13-14 N/A", "21-22 N/A"), ("23-24 N/A", ""))
    table = drawn_symbol("contact-head", rows, library=LIBRARY)
    corner = measure(table, Orientation.R0, LIBRARY).keepout.min
    assert (corner.x, corner.y) == (0, 0)


def test_the_headed_table_is_one_heading_taller_and_a_row_taller_grows_it() -> None:
    rows = (("NO", "NC", "-K1"), ("13-14 N/A", "21-22 N/A"))
    lone = drawn_symbol("contact-head", (("NO", "NC"), *rows[1:]), library=LIBRARY)
    headed = drawn_symbol("contact-head-headed", rows, library=LIBRARY)
    more = drawn_symbol("contact-head-headed", (*rows, ("a", "b")), library=LIBRARY)

    def height(symbol) -> int:
        return measure(symbol, Orientation.R0, LIBRARY).keepout.height

    assert height(headed) > height(lone)
    assert height(more) > height(headed)


def test_another_key_with_texts_is_refused() -> None:
    with pytest.raises(SymdefError, match="takes no texts"):
        drawn_symbol("contact-row", (("x",),), library=LIBRARY)


def test_a_box_marks_each_port_with_its_marking() -> None:
    slots = drawn_slots("generic-box", (("A1.Q",), ("2",)))
    assert slots == {"marking.A1.Q": "Q", "marking.2": "2"}
    box = drawn_symbol("generic-box", (("A1.Q",), ("2",)), library=LIBRARY)
    assert set(slots) <= {s.id for s in box.slots}


def test_a_table_sets_its_titles_heading_and_one_string_per_cell() -> None:
    texts = (("NO", "NC", "-K1"), ("13-14 N/A", "21-22 N/A"), ("23-24 N/A", ""))
    slots = drawn_slots("contact-head-headed", texts)
    assert slots == {
        "no": "NO",
        "nc": "NC",
        "heading": "-K1",
        "1.no": "13-14 N/A",
        "1.nc": "21-22 N/A",
        "2.no": "23-24 N/A",
    }
    table = drawn_symbol("contact-head-headed", texts, library=LIBRARY)
    assert set(slots) <= {s.id for s in table.slots}


def test_no_texts_set_no_strings() -> None:
    assert drawn_slots("break-contact", ()) == {}


def test_a_box_takes_the_sides_it_is_given():
    """es-0085: `sides` put each port on its own side; none keeps the alternating sides."""
    texts = (("a",), ("b",), ("c",))
    sides = {"a": "n", "b": "n", "c": "s"}
    box = drawn_symbol(
        "generic-box", texts, library=LIBRARY, offsets={"a": 0, "b": 16, "c": 0}, sides=sides
    )
    assert {p.id: p.direction.name for p in box.ports} == {"a": "N", "b": "N", "c": "S"}
    plain = drawn_symbol("generic-box", texts, library=LIBRARY)
    assert {p.id: p.direction.name for p in plain.ports} == {"a": "N", "b": "S", "c": "N"}
