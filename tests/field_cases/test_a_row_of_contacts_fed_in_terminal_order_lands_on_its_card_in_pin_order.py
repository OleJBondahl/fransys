"""Field case: a row of contacts fed from a strip lands on a card's pins in the pins' order (R11).

The engineering shape: three contacts F5, F6 and F7 of one group, each fed from a terminal of one
strip (F5 from 1, F6 from 2, F7 from 3) and wired on to channels of an input card: F5 to channel
6, F6 to channel 4, F7 to channel 5. The card prints its channels 4, 5, 6.

The bug: the row stood in the order the strip and the tags gave it, not in the order of the
channels it lands on, so the wires stepped across each other on the way to the card.

The rule (layout-0264): every column wired to a box's pins takes the order of the pins it lands
on, inside a group as between groups.
"""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from fransys.colours import BU
from fransys_el import OPTIONS
from route_meter import page_crossings

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items

WIRE = (BU, 0.5)
LANDS = {"F5": 6, "F6": 4, "F7": 5}  # contact -> the channel it feeds, fed from terminal 1, 2, 3


@cache
def _built() -> tuple:
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
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return model, results.layout


def test_the_contacts_stand_in_the_order_of_the_channels_they_feed() -> None:
    model, layout = _built()
    tag_of = {i.id: i.tag for i in items(model).values()}
    named = {f.id: tag_of[f.item] for f in functions(model).values()}
    x = {named[p.function]: p.at.x for p in layout.placed if named.get(p.function) in LANDS}
    assert sorted(LANDS, key=x.__getitem__) == sorted(LANDS, key=LANDS.__getitem__)


def test_no_wire_crosses_on_the_way_to_the_card() -> None:
    layout = _built()[1]
    assert len(layout.routes) == 6, "every wire is drawn"
    assert page_crossings(layout) == 0
