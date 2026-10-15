"""Field case: an input card prints its pins in marking order, whatever its partners' order (R11).

Two engineering shapes on one 16-channel digital input module, each in its own design.
- Interleaved: three groups of two contactors each; group A's auxiliary contacts go to channels 1
  and 4, B's to 2 and 5, C's to 3 and 6. Each contact hangs under its channel.
- Fan: six make contacts in a row, each fed from its own pin of one controller connector and wired
  on to channel n of the module.

The bug: the box ordered a wired pin by its partners' x, so the pins followed the contacts. The
interleaved shape printed `1 3 2 5 4 6`; the fan printed `2 3 4 5 6 1`.

The rule (layout-0264, amending layout-0250): a box's pins follow marking order, and the columns
hung under it follow those pins.
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
INTERLEAVED = {"A": (1, 4), "B": (2, 5), "C": (3, 6)}


@cache
def _built(shape: str) -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G0", "PLC inputs"):
        module = d.device("K1", "DEMO-PLC-DI-16")
    if shape == "interleaved":
        for group, channels in INTERLEAVED.items():
            with d.function(group, f"Group {group}"):
                for n in channels:
                    contactor = d.device(f"Q{n}", "DEMO-CTR-3P-NC")
                    d.detail.wire(
                        contactor.aux["13"], getattr(module, f"di_{n}")[str(n)], wire=WIRE
                    )
    else:
        source = d.device("A1", "DEMO-CTRL-8")
        for n in range(1, 7):
            with d.function(f"B{n}", f"Block {n}"):
                contact = d.device(f"S{n}", "DEMO-BLOCK-1NO")
                d.detail.wire(source.X1[str(n)], contact.no["13"], wire=WIRE)
                d.detail.wire(contact.no["14"], getattr(module, f"di_{n}")[str(n)], wire=WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model
    results, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return model, results.layout


def _box_pins(model, layout) -> tuple:
    """The card's placement and each channel's (pin x, pin y in the box)."""
    (card,) = (i.id for i in items(model).values() if i.tag == "K1")
    (box,) = (p for p in layout.placed if p.function == card)
    pins = {
        int(g.name.split("_")[1].split(".")[0]): (box.at.x + g.at.x, g.at.y)
        for g in box.geometry.ports
    }
    return box, pins


def _contacts(model, layout, name: str) -> dict:
    """Each wired contact's placement, keyed by the channel its tag carries."""
    tag_of = {i.id: i.tag or "" for i in items(model).values()}
    named = {f.id: (tag_of[f.item], f.name) for f in functions(model).values()}
    return {
        int(named[p.function][0][1:]): p
        for p in layout.placed
        if named.get(p.function, ("", ""))[1] == name
    }


def _each_side_in_order(pins: dict) -> None:
    for side in {y for _, y in pins.values()}:
        row = [n for n in sorted(pins) if pins[n][1] == side]
        assert sorted(row, key=lambda n: pins[n][0]) == row, side
        assert len({pins[n][0] for n in row}) == len(row), side


def test_interleaved_groups_hang_six_straight_drops_under_pins_in_order() -> None:
    model, layout = _built("interleaved")
    box, pins = _box_pins(model, layout)
    _each_side_in_order(pins)
    assert [pins[n][0] for n in range(1, 7)] == sorted(pins[n][0] for n in range(1, 7))
    contacts = _contacts(model, layout, "aux")
    assert sorted(contacts) == list(range(1, 7))
    for n, contact in contacts.items():
        (end,) = (g for g in contact.geometry.ports if g.name == "in")
        assert (contact.drawing_set, contact.page) == (box.drawing_set, box.page), n
        assert contact.at.x + end.at.x == pins[n][0], n


def test_a_fan_of_contacts_lands_on_pins_in_marking_order() -> None:
    model, layout = _built("fan")
    _, pins = _box_pins(model, layout)
    _each_side_in_order(pins)
    wired = [n for n in sorted(pins) if n <= 6]
    assert {pins[n][1] for n in wired} == {pins[1][1]}
    assert sorted(wired, key=lambda n: pins[n][0]) == [1, 2, 3, 4, 5, 6]
    assert sorted(_contacts(model, layout, "no")) == [1, 2, 3, 4, 5, 6]


def test_the_fan_columns_stand_in_pin_order_and_cross_no_more_than_before_the_pins_moved() -> None:
    """Acceptance R11-COLUMNS: S1 sorted after S6 (its column took the card's group); 17 crossed."""
    model, layout = _built("fan")
    contacts = _contacts(model, layout, "no")
    assert sorted(contacts, key=lambda n: contacts[n].at.x) == [1, 2, 3, 4, 5, 6]
    assert len(layout.routes) == 12, "every wire is drawn"
    assert page_crossings(layout) <= 4
