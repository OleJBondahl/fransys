"""Field case: a row of contacts fed from a strip lands on a card's pins in the pins' order (R11).
The bug: the row stood in strip and tag order, not the channel order it lands on, so the wires crossed on the way.
Fixed by layout-0264: every column wired to a box's pins takes the order of the pins it lands on, within and between groups."""

from functools import cache

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _field_designs import wire_crossings
from _model_build_cover import unit_document
from fransys.colours import BU

WIRE = (BU, 0.5)
LANDS = {"F5": 6, "F6": 4, "F7": 5}  # contact -> the channel it feeds, fed from terminal 1, 2, 3


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "PLC inputs"):
        card = d.device("K1", "DEMO-PLC-DI-16")
    with d.function("F", "Feed"):
        strip = d.terminal_strip("XF2", "DEMO-TB-2.5", 4)
        for terminal, (tag, channel) in enumerate(LANDS.items(), 1):
            contact = d.device(tag, "DEMO-BLOCK-1NO")
            d.series(strip[terminal].inner, contact.no["13"], wire=WIRE)
            d.series(contact.no["14"], getattr(card, f"di_{channel}")[str(channel)], wire=WIRE)
    return fr.build(d, unit_document(cab))


def test_the_contacts_stand_in_the_order_of_the_channel_pins_they_feed() -> None:
    """A card stands channels on two sides: the contacts follow the pins x, not the numbers."""
    model = _built().model
    drawn = {s.tag: s for s in symbol_subjects(model)}
    card = drawn["K1"]
    pin_x = {tag: card.x + dict(card.offsets)[f"di_{ch}.{ch}"] for tag, ch in LANDS.items()}
    x = {tag: drawn[tag].x for tag in LANDS}
    assert sorted(LANDS, key=x.__getitem__) == sorted(LANDS, key=pin_x.__getitem__)
    assert x == pin_x, "each contact stands over the pin it feeds"


def test_no_wire_crosses_on_the_way_to_the_card() -> None:
    result = _built()
    assert {f.code for f in fr.check(result)} & {"FUNCTION_NOT_DRAWN", "NET_NOT_DRAWN"} == set()
    assert sum(wire_crossings(d.wires) for d in drawn_pages(result.model).values()) == 0
