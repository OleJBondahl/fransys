"""Field case: a box device's contact stands in the circuit it switches, apart from its box.

The engineering shape: a redundancy module fed by two supplies (a box: two input groups, one
output) with a DC-OK contact 13/14. The contact feeds a relay coil K1 from the 24 V rail, and
K1's own contact reports to a PLC input.

The bug: the one contact function with a default symbol broke the box's merge condition, so the
module was drawn as three boxes (OUT, IN1, IN2) plus the contact.
The rule (decision layout-0123, owner 2026-10-06 A2): the module keeps its box-drawn functions as
one box and carries a contact image of its contacts; the contact stands in K1's circuit and shows
the box's position, the way a coil's contact shows its coil's.
"""

import functools
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import fransys as fr
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from fransys.colours import BN, BU

from fransys_model.derive.drawing_text import tag_text
from fransys_model.vocab.tables import functions, items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

BOX = "generic-box"


@functools.cache
def _built(*, rails: bool = True) -> Model:
    """The plant, built once per variant; `rails=False` declares no supply (OUT to terminals)."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    with d.function("G", "Group"):
        psus = [d.device(f"T{n}", "DEMO-PSU-24") for n in (1, 2)]
        m1 = d.device("M1", "DEMO-RED-2IN")
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        di = d.device("U1", "DEMO-PLC-DI-2")
    for n, psu in enumerate(psus, start=1):
        group = getattr(m1, f"in_{n}")
        d.detail.wire(psu.output["+"], group[f"{n}+"], wire=(BN, 1.5))
        d.detail.wire(psu.output["-"], group[f"{n}-"], wire=(BU, 1.5))
    if rails:
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.detail.wire(m1.out["+"], live[1].outer, wire=(BN, 1.5))
    d.detail.wire(m1.out["-"], zero[1].outer, wire=(BU, 1.5))
    d.detail.wire(live[2].outer, m1.dc_ok["13"], wire=(BN, 0.5))
    d.detail.wire(m1.dc_ok["14"], k1.coil["A1"], wire=(BN, 0.5))
    d.detail.wire(k1.coil["A2"], zero[2].outer, wire=(BU, 0.5))
    d.detail.wire(live[2].outer, k1.co_1["11"], wire=(BN, 0.5))
    d.detail.wire(k1.co_1["14"], di["1"], wire=(BN, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _contact(model):
    """The module's 13/14 contact function."""
    (contact,) = (f.id for f in functions(model).values() if f.name == "dc_ok")
    return contact


def _drawn(model, tag: str, symbol: str | None = None) -> list:
    """The drawn symbols of item `tag`'s functions, optionally of one library symbol."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    wanted = {f.id.value for f in functions(model).values() if tag_of[f.item] == tag}
    return [s for s in symbol_subjects(model) if s.owner in wanted and symbol in (None, s.key)]


def _image(model) -> list:
    """The contact images drawn under the module M1 (a contact table of M1's functions)."""
    return _drawn(model, "M1", "contact-head")


def test_the_module_is_one_box_with_its_inputs_north_and_output_south() -> None:
    """One placed M1 box, no other placed thing of M1; IN1 and IN2 above the middle, OUT below."""
    model = _built()
    boxes = _drawn(model, "M1", BOX)
    assert len(boxes) == 1, "M1 is not drawn as one box"
    sides = dict(boxes[0].sides)
    assert {"in_1", "in_2", "out"} <= {n.split(".")[0] for n in sides}
    for name, side in sides.items():
        assert (side == "n") == name.startswith(("in_1", "in_2")), f"{name} on the wrong side"


def test_the_contact_stands_in_k1s_circuit_and_shows_the_boxs_position() -> None:
    """The 13/14 contact is placed with K1 and its reference names the M1 box's place."""
    model = _built()
    (here,) = _drawn(model, "M1", "make-contact")
    assert here.page in {one.page for one in _drawn(model, "K1")}
    msg = "not readable on the core: the contact's cross-reference to the M1 box"
    raise AssertionError(msg)


def test_the_contact_prints_its_item_tag_over_the_boxs_cell() -> None:
    """The contact carries the tag "-M1" as any contact does, though the box stands on the page."""
    model = _built()
    (here,) = _drawn(model, "M1", "make-contact")
    assert tag_text(model, _contact(model)) == "-M1"
    assert [
        t
        for page, drawing in drawn_pages(model).items()
        if page == here.page
        for t in drawing.texts
        if t.text == "-M1"
    ]


def test_the_image_under_the_module_lists_13_14_with_the_contacts_position() -> None:
    """The module's contact image lists 13-14 under NO with a place, and nothing under NC."""
    model = _built()
    (image,) = _image(model)
    no, nc = image.texts[1:]
    assert [row for row in no if row.startswith("13-14 ")]
    assert not [row for row in no if "N/A" in row]
    assert not [row for row in nc if row.startswith("13-14")]


def test_the_box_stands_on_a_function_drawn_in_it_not_on_one_drawn_apart() -> None:
    """The box's placement is no contact's: with the lowest id drawn apart, the next one stands."""
    model = _built()
    (box,) = _drawn(model, "M1", BOX)
    assert box.owner != _contact(model).value
    msg = "not readable on the core: the item_function write key with a view apart"
    raise AssertionError(msg)


def test_the_image_stands_clear_of_the_ink_below_the_module() -> None:
    """layout-0134: the image meets no drawn marker, stub or power symbol of its page."""
    model = _built()
    (image,) = _image(model)
    msg = f"not readable on the core: the markers on page {image.page}"
    raise AssertionError(msg)


def test_the_image_of_a_module_wired_to_terminals_crosses_no_wire() -> None:
    """layout-0123 F1: with OUT wired down to strip terminals, the image starts right of OUT-."""
    model = _built(rails=False)
    (image,) = _image(model)
    msg = f"not readable on the core: the routes on page {image.page}"
    raise AssertionError(msg)


def test_a_box_with_a_contact_is_not_a_coil() -> None:
    """layout-0123 F3: the box and K1's coil both own contacts apart; only the coil is a coil."""
    model = _built()
    assert _drawn(model, "M1", "make-contact"), "the box's contact is drawn apart"
    assert not _drawn(model, "M1", "operating-device")
    assert _drawn(model, "K1", "operating-device")
    assert _drawn(model, "K1", "change-over-contact"), "the coil's contacts are drawn apart"
