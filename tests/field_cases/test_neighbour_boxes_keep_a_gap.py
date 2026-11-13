"""Field case: two boxes side by side in one row never touch.
The bug: the lamp's lane lay inside the motor box's width, so the boxes shared an edge and read as one (SYMBOL_OVERLAP).
Fixed by place._keep_gap, a row keeps the column gap between any two neighbours after the lane offsets."""

from typing import Any

from _drawn_facts import symbol_subjects
from test_spare_contact_in_contact_table import _built

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, symbol_shape


def _clearance(model, first: str, second: str) -> Any:
    """The clear space between the drawn outlines of the symbols of items `first` and `second`.

    The larger of the x gap and the y gap: positive when the two boxes share no edge or area.
    """
    outline = {}
    for one in symbol_subjects(model):
        tag = one.tag
        if tag in (first, second):
            body = symbol_shape(library_symbol(LIBRARY, one.key), LIBRARY).body
            outline[tag] = (one.x + body.x, one.y + body.y, body.w, body.h)
    (ax, ay, aw, ah), (bx, by, bw, bh) = outline[first], outline[second]
    return max(bx - (ax + aw), ax - (bx + bw), by - (ay + ah), ay - (by + bh))


def test_neighbour_boxes_keep_a_gap() -> None:
    """No SYMBOL_OVERLAP, and the motor's and the lamp's drawn outlines have a positive gap."""
    built = _built(hide=False, mains=False)
    assert not [f for f in built.findings if f.code == "SYMBOL_OVERLAP"]
    assert _clearance(built.model, "M1", "P1") > 0
