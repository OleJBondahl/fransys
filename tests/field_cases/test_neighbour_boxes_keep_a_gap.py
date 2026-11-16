"""Field case: two boxes side by side in one row never touch.
The bug: the lamp's lane lay inside the motor box's width, so the boxes shared an edge and read as one (SYMBOL_OVERLAP).
Fixed by place._keep_gap, a row keeps the column gap between any two neighbours after the lane offsets."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _drawn_facts import item_box, symbol_subjects
from _model_build_cover import unit_document
from fransys.colours import BK, RD
from test_spare_contact_in_contact_table import _built

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY
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


class _Io(NamedTuple):
    X1: Any


@pytest.mark.rule("BOX-GAP-BELOW")
@pytest.mark.parametrize(
    ("card", "chained"),
    [("DO1", True), ("DO1", False), ("1A", False)],
    ids=["pole-chain-and-card", "pole-to-card-and-strip", "card-sorts-before-strip"],
)
def test_a_card_box_clears_the_end_of_every_lane_of_its_column(card: str, *, chained: bool) -> None:
    """BOX-GAP-BELOW: the card box stands clear of a column whose other lane runs past the lane on the card's pin.

    One pole stands alone on the card pin, the other runs on (a fuse, a contactor, a strip terminal, or a strip terminal alone).
    The bug: `_attach_y` read lane 0 only, so the box stood in the longer lane (OVERLAP, OUTLINE_NO_ROOM).
    """

    @fr.unit("bars", revision=1, interface_version=1, date="2026-11-07", text="first", by="AB", title="Bars", number="N-1")
    def _unit(u: Any):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
        s1, f1, k1 = u.device("S1", "DEMO-SWITCH-DC-2P"), u.device("F1", "DEMO-FUSE-DC-160"), u.device("K1", "DEMO-CONTACTOR-DC")
        pins = u.device(card, None, pins=("13", "14", "23", "24", "43", "44"), external=True)
        long_pole = (f1.element, k1.pole, x1[1].inner) if chained else (x1[2].inner,)
        u.series(s1.main.pole(1), pins["13"], wire=(BK, 100))
        u.series(s1.main.pole(2), *long_pole, wire=(RD, 100))
        return _Io(x1)

    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    built = fr.build(d, unit_document("bars"))
    codes = {f.code for f in (*built.findings, *fr.check(built))}
    assert not codes & {"OVERLAP", "OUTLINE_NO_ROOM", "SYMBOL_OVERLAP", "CONNECTION_NOT_DRAWN"}
    assert item_box(built.model, f"U1-{card}").key == GENERIC_BOX_KEY
