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
from itertools import combinations, pairwise
from pathlib import Path

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.vocab.tables import functions, items

WIRE = (BU, 0.5)
INTERLEAVED = {"A": (1, 4), "B": (2, 5), "C": (3, 6)}


@cache
def _built(shape: str):
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
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model


def _box_pins(model) -> tuple:
    """The card's symbol and each channel's (pin x, side of the box: `n` or `s`)."""
    (card,) = (i.tag for i in items(model).values() if i.tag == "K1")
    (box,) = (one for one in symbol_subjects(model) if one.key == "generic-box" and one.tag == card)
    pins = {
        int(name.split("_")[1].split(".")[0]): (box.x + at, dict(box.sides)[name])
        for name, at in dict(box.offsets).items()
    }
    return box, pins


def _contacts(model, name: str) -> dict:
    """Each wired contact's symbol, keyed by the channel its tag carries."""
    named = {f.id: f.name for f in functions(model).values()}
    return {
        int(one.tag[1:]): one for one in symbol_subjects(model) if named.get(one.function) == name
    }


def _page_crossings(model) -> int:
    """Wire-over-wire crossings, page by page: a horizontal and a vertical run crossing."""
    by_page = {
        page: [list(pairwise(wire.points)) for wire in drawing.wires]
        for page, drawing in drawn_pages(model).items()
    }
    return sum(
        _cross(s, t) or _cross(t, s)
        for wires in by_page.values()
        for one, two in combinations(wires, 2)
        for s in one
        for t in two
    )


def _cross(a: tuple, b: tuple) -> bool:
    (ax0, ay0), (ax1, ay1) = a
    (bx0, by0), (bx1, by1) = b
    if ay0 != ay1 or bx0 != bx1:
        return False
    return min(ax0, ax1) < bx0 < max(ax0, ax1) and min(by0, by1) < ay0 < max(by0, by1)


def _each_side_in_order(pins: dict) -> None:
    for side in {y for _, y in pins.values()}:
        row = [n for n in sorted(pins) if pins[n][1] == side]
        assert sorted(row, key=lambda n: pins[n][0]) == row, side
        assert len({pins[n][0] for n in row}) == len(row), side


def test_interleaved_groups_hang_six_straight_drops_under_pins_in_order() -> None:
    model = _built("interleaved")
    box, pins = _box_pins(model)
    _each_side_in_order(pins)
    assert [pins[n][0] for n in range(1, 7)] == sorted(pins[n][0] for n in range(1, 7))
    contacts = _contacts(model, "aux")
    assert sorted(contacts) == list(range(1, 7))
    for n, contact in contacts.items():
        assert contact.page == box.page, n
        assert contact.x == pins[n][0], n  # a contact's origin stands on its port axis: a drop


def test_a_fan_of_contacts_lands_on_pins_in_marking_order() -> None:
    model = _built("fan")
    _, pins = _box_pins(model)
    _each_side_in_order(pins)
    wired = [n for n in sorted(pins) if n <= 6]
    assert {pins[n][1] for n in wired} == {pins[1][1]}
    assert sorted(wired, key=lambda n: pins[n][0]) == [1, 2, 3, 4, 5, 6]
    assert sorted(_contacts(model, "no")) == [1, 2, 3, 4, 5, 6]


def test_the_fan_columns_stand_in_pin_order_and_cross_no_more_than_before_the_pins_moved() -> None:
    """Acceptance R11-COLUMNS: S1 sorted after S6 (its column took the card's group); 17 crossed."""
    model = _built("fan")
    contacts = _contacts(model, "no")
    assert sorted(contacts, key=lambda n: contacts[n].x) == [1, 2, 3, 4, 5, 6]
    assert sum(len(d.wires) for d in drawn_pages(model).values()) == 12, "every wire is drawn"
    assert _page_crossings(model) <= 4
