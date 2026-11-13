"""Field case: a generic box on a card with eight long pin names, seven on one edge, one wired.
The bug: the card's pin pitch ignored the name width, so the names printed over each other and no finding said so.
Fixed by layout-0578 (the OVERLAP check counts a box's pin names; the pitch fits them)."""

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from electrical_symbols import GENERIC_BOX_KEY
from fransys_layout.drawing_reads import SlotText, page_texts, text_overlaps


def test_a_box_prints_each_pin_name_in_its_slot_ink_and_no_two_overprint() -> None:
    """Every pin name is a measured box the page checks read (TEXT-BOX-MEASURED); the pitch fits them: no OVERLAP, no shared area."""
    pins = tuple(f"CHANNEL{n}" for n in range(1, 9))
    d = fr.design("demo_parts", place="CAB")
    with d.function("PLC", "Card"):
        card = d.device("A1", None, pins=pins, external=True)
    zero = d.terminal_strip("X0", "DEMO-TB-2.5", 2, bridged=True, rail=True)
    d.dc_supply("S", plus=d.terminal_strip("X24", "DEMO-TB-2.5", 1)[1], minus=zero[1], voltage=24)
    with d.function("B", "Relays"):
        relay = d.device("K1", "DEMO-RLY-2CO-24")
        d.series(card[pins[0]], relay.coil["A1"], wire=(BU, 0.5))
        d.series(relay.coil["A2"], zero[1].outer, wire=(BU, 0.5))
    built = fr.build(d, unit_document(d.location("CAB", "Cabinet")))
    assert "OVERLAP" not in {f.code for f in built.findings}
    for drawing in drawn_pages(built.model).values():
        read = {t.box for t in page_texts(drawing)}
        for box in (s for s in drawing.symbols if s.key == GENERIC_BOX_KEY):
            assert len(box.slot_ink) == len(pins)
            assert {ink for _, ink in box.slot_ink} <= read
            assert not text_overlaps([SlotText(ink, box.id) for _, ink in box.slot_ink])
