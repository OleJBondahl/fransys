"""Field case: a row of contacts fed from a strip lands on a card's pins in the pins' order (R11).

The engineering shape: three contacts F5, F6 and F7 of one group, each fed from a terminal of one
strip (F5 from 1, F6 from 2, F7 from 3) and wired on to channels of an input card: F5 to channel
6, F6 to channel 4, F7 to channel 5. The card prints its channels 4, 5, 6.

The bug: the row stood in the order the strip and the tags gave it, not in the order of the
channels it lands on, so the wires stepped across each other on the way to the card.

The rule (layout-0264): every column wired to a box's pins takes the order of the pins it lands
on, inside a group as between groups.
"""

import itertools
import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
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
            d.detail.wire(strip[terminal], contact.no["13"], wire=WIRE)
            d.detail.wire(contact.no["14"], getattr(card, f"di_{channel}")[str(channel)], wire=WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _crossings(wires: tuple) -> int:
    """Horizontal-over-vertical crossings, strictly inside both segments, between drawn wires."""
    found = 0
    for one, two in itertools.combinations(wires, 2):
        for (a0, a1), (b0, b1) in itertools.product(
            itertools.pairwise(one.points), itertools.pairwise(two.points)
        ):
            if (a0[1] == a1[1]) == (b0[1] == b1[1]):
                continue
            (h0, h1), (v0, v1) = ((a0, a1), (b0, b1)) if a0[1] == a1[1] else ((b0, b1), (a0, a1))
            found += min(h0[0], h1[0]) < v0[0] < max(h0[0], h1[0]) and min(v0[1], v1[1]) < h0[
                1
            ] < max(v0[1], v1[1])
    return found


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
    assert sum(_crossings(d.wires) for d in drawn_pages(result.model).values()) == 0
