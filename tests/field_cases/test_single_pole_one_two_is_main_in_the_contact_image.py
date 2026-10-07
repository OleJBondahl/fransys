"""Field case: a single-pole 1-2 contact is a main contact in the contact image; 13-14 is auxiliary.

The engineering shape: a three-pole contactor with a 13-14 auxiliary contact and a clip-on
single-pole contact (pins 1-2, a DC pole) mounted to it, all worked by the contactor's coil.

The bug: the image called a contact main only when its function had exactly one pole, so the lone
1-2 pole counted as auxiliary and printed after the three-pole 1-2, 3-4, 5-6.
The rule (decision model-0138): a pole with pins 1-2 (3-4, 5-6, ...) is main and a pole with pins
13-14 (21-22, ...) is auxiliary, whatever the pole count of its function; main prints first.
"""

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive.drawing_text import contact_image
from fransys_model.layout import Label, LabelKind, layout_of


def _poles() -> list[str]:
    """The NO column of K1's contact table: each entry's pole pair, in printed order."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Pole", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    _cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    with d.function("G", "Group"):
        feed, zero, load = strip[1], strip[2], strip[3]
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        pole = d.device(None, "DEMO-CONTACTOR-DC", name="pole", parent=k1)
    wire = (BU, 0.5)
    d.wire(feed, k1.coil["A1"], wire=wire)
    d.wire(k1.coil["A2"], zero, wire=wire)
    d.wire(feed, k1.aux["13"], wire=wire)
    d.wire(k1.aux["14"], load, wire=wire)
    d.wire(feed, pole["1"], wire=wire)
    d.wire(pole["2"], load, wire=wire)
    model = fr.build(d, cabinet_document(_cabinet)).model
    (label,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE and one.slot == "contacts"
    )
    no, _ = contact_image(model, label)
    return [entry.split(" ")[0] for entry in no]


def test_the_single_pole_one_two_prints_with_the_main_contacts() -> None:
    """13-14 is last; the lone 1-2 stands with the main poles (1-2, 1-2, 3-4, 5-6)."""
    assert _poles() == ["1-2", "1-2", "3-4", "5-6", "13-14"]
