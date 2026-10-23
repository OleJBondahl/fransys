"""The 16-channel card's port names stand apart (PIN-OVER-PIN, Ruling 102 and 102a).

Pin over pin puts the N and S pins of a pair at one x. Each name stands inside the body at its own
port's edge, so a two-sided box shows 16 names and no two boxes meet.
"""

from itertools import combinations

import fransys as fr
from _card_case import card_case_drafts
from _drawn_pages import drawn_pages
from symdef import slot_box

from electrical_symbols import LIBRARY, drawn_symbol
lazy from fransys_layout.drawing import DrawnSymbol

_TEXT_HEIGHT = 1.0  # M, the house text height the box pitch is sized for


def _name_boxes(record: DrawnSymbol, *, sides: bool):
    made = drawn_symbol(
        record.key,
        record.texts,
        library=LIBRARY,
        offsets=dict(record.offsets),
        sides=dict(record.sides) if sides else None,
    )
    slots = dict(record.slots)
    return {
        slot.id: slot_box(slot, slots[slot.id], _TEXT_HEIGHT, LIBRARY.font, LIBRARY.grid)
        for slot in made.slots
        if slot.id in slots
    }


def _apart(a, b) -> bool:
    return a.max.x <= b.min.x or b.max.x <= a.min.x or a.max.y <= b.min.y or b.max.y <= a.min.y


def _card() -> DrawnSymbol:
    model = fr.build(*card_case_drafts(16)).model
    return next(
        s
        for drawing in drawn_pages(model).values()
        for s in drawing.symbols
        if s.key == "generic-box"
    )


def test_no_two_port_names_of_the_card_overlap() -> None:
    record = _card()
    boxes = _name_boxes(record, sides=True)
    assert len(boxes) == 16
    assert all(_apart(a, b) for a, b in combinations(boxes.values(), 2))


def test_names_without_the_record_sides_overlap_pair_by_pair() -> None:
    """Control: the alternating sides put CH01 and CH09 on one side at one x."""
    boxes = _name_boxes(_card(), sides=False)
    assert not _apart(boxes["marking.CH01-"], boxes["marking.CH09-"])
