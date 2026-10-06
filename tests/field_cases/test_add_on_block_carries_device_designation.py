"""Field case: an add-on contact block prints its contactor's designation and its contacts.

The engineering shape: a contactor with a clip-on auxiliary contact block (one NO, one NC) and an
overload relay mounted to it. The block has no tag of its own: it is part of the contactor, the
contactor's coil works its contacts, and an electrician reads the contactor's tag on it.

The bug: the block printed as a device of its own (a second designation, a row in the
designations list), and the contactor's contact table lacked the block's 53-54 and 61-62.

Fixing decision: model-0119 (an add-on contact block is an accessory, amending model-0058).
The invented parts are `demo_parts`' contactor, its `DEMO-CTR-BLOCK-1NO1NC` block and an overload.
"""

import fransys as fr
from _model_build_cover import system_document
from fransys.colours import BU

from fransys_model.derive import designation_list, item_designation
from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import Label, LabelKind, layout_of
from fransys_model.vocab.tables import functions


def _build() -> tuple[fr.Model, fr.Device, fr.Device]:
    """K1 with an untagged add-on block and overload child: the model, the block, the overload."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Block", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    with d.function("G", "Group"):
        feed, zero, load = strip[1], strip[2], strip[3]
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="block", parent=k1)
        overload = d.device(None, "DEMO-OVERLOAD-A2", name="overload", parent=k1)
    wire = (BU, 0.5)
    d.wire(feed, k1.coil["A1"], wire=wire)
    d.wire(k1.coil["A2"], zero, wire=wire)
    d.wire(feed, block.no["53"], wire=wire)
    d.wire(block.no["54"], load, wire=wire)
    d.wire(feed, block.nc["61"], wire=wire)
    d.wire(block.nc["62"], load, wire=wire)
    return fr.build(d, system_document()).model, block, overload


def test_the_block_prints_the_contactors_designation_and_has_no_row() -> None:
    model, block, overload = _build()
    assert item_designation(model, block.id) == "K1"
    rows = {row.item for row in designation_list(model)}
    assert block.id not in rows
    assert item_designation(model, overload.id) != "K1"
    assert overload.id in rows
    tags = {
        label_text(model, label)
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.TAG
        and label.function
        and functions(model)[label.function].item == block.id
    }
    assert tags == {"-K1"}


def test_the_contactors_contact_table_lists_the_block_contacts() -> None:
    model, _, _ = _build()
    (table,) = (
        label_text(model, label).split("\n")
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.CROSS_REFERENCE and label.slot == "contacts"
    )
    entries = [entry.split(" ")[0] for line in table[1:] for entry in line.split(" | ")]
    assert "53-54" in entries
    assert "61-62" in entries
