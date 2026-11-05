"""Known answers for the pure reads of a Drawing (R218)."""

from fransys_layout.core.values import Box, Size
from fransys_layout.drawing import (
    Drawing,
    DrawnOutline,
    DrawnSymbol,
    DrawnText,
    DrawnWire,
    page_texts,
    struck_texts,
    text_overlaps,
    wire_bends,
    wire_crossings,
    wire_length,
)


def _wire(name, *points):
    return DrawnWire(name, tuple(points), "s")


def _text(x, y, w=10, h=4, text="t"):
    return DrawnText(text, Box(x, y, w, h), "k", "NW")


def test_crossing_counts_one() -> None:
    assert wire_crossings([_wire("a", (0, 5), (10, 5)), _wire("b", (5, 0), (5, 10))]) == 1


def test_crossing_negatives() -> None:
    parallel = [_wire("a", (0, 5), (10, 5)), _wire("b", (0, 6), (10, 6))]
    assert wire_crossings(parallel) == 0
    tee = [_wire("a", (0, 5), (10, 5)), _wire("b", (5, 5), (5, 10))]
    assert wire_crossings(tee) == 0
    same = [_wire("a", (0, 5), (10, 5)), _wire("a", (5, 0), (5, 10))]
    assert wire_crossings(same) == 0
    diagonal = [_wire("a", (0, 5), (10, 5)), _wire("b", (0, 0), (10, 10))]
    assert wire_crossings(diagonal) == 0


def test_bends() -> None:
    assert wire_bends([_wire("a", (0, 0), (10, 0), (10, 10), (20, 10))]) == 2


def test_bends_straight_and_zero_length() -> None:
    assert wire_bends([_wire("a", (0, 0), (5, 0), (5, 0), (10, 0))]) == 0


def test_length() -> None:
    assert wire_length([_wire("a", (0, 0), (10, 0), (10, 5)), _wire("b", (0, 0), (0, 3))]) == 18
    assert wire_length([_wire("a", (4, 4))]) == 0


def test_text_overlaps() -> None:
    assert text_overlaps([_text(0, 0), _text(5, 2), _text(100, 100)]) == 1


def test_text_touching_does_not_overlap() -> None:
    assert text_overlaps([_text(0, 0), _text(10, 0), _text(0, 4)]) == 0


def test_struck() -> None:
    text = _text(0, 0)
    assert struck_texts([_wire("a", (-5, 2), (20, 2))], [text]) == 1
    assert struck_texts([_wire("a", (5, -5), (5, 20))], [text]) == 1


def test_struck_negatives() -> None:
    text = _text(0, 0)
    assert struck_texts([_wire("a", (-5, 4), (20, 4))], [text]) == 0
    assert struck_texts([_wire("a", (-5, 2), (0, 2))], [text]) == 0


def test_page_texts_ends_with_the_ink_of_each_slot_string() -> None:
    owner = DrawnSymbol("s", "k", 0, 0, "R0", slot_ink=(("marking.a", Box(3, 3, 6, 2)),))
    drawing = Drawing(Size(100, 100), (owner,), (), (_text(0, 0),), (), "v")
    assert [t.box for t in page_texts(drawing)] == [Box(0, 0, 10, 4), Box(3, 3, 6, 2)]


def test_page_texts_order() -> None:
    free, outlined = _text(0, 0, text="f"), _text(2, 2, text="o")
    drawing = Drawing(
        Size(100, 100),
        (),
        (_wire("a", (0, 0), (1, 0)), _wire("b", (0, 0), (1, 0))),
        (free,),
        (DrawnOutline("o", "k", (), outlined), DrawnOutline("p", "k", (), None)),
        "v",
    )
    assert page_texts(drawing) == (free, outlined)
