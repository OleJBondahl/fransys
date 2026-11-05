"""Field case: an add-on contact block prints its contactor's designation and its contacts.
The bug: the block printed as a device with its own designation, and the contact table lacked its 53-54 and 61-62.
Fixed by model-0119 (amending model-0058), an add-on contact block is an accessory that prints its contactor's designation."""

from typing import Any

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive import designation_list, item_designation


def _build() -> tuple[fr.Model, Any, Any]:
    """K1 with an untagged add-on block and overload child: the model, the block, the overload."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Block", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    _cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN")
    with d.function("G", "Group"):
        feed, zero, load = strip[1], strip[2], strip[3]
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="block", parent=k1)
        overload = d.device(None, "DEMO-OVERLOAD-A2", name="overload", parent=k1)
    wire = (BU, 0.5)
    d.series(feed, k1.coil["A1"], wire=wire)
    d.series(k1.coil["A2"], zero, wire=wire)
    d.series(feed, block.no["53"], wire=wire)
    d.series(block.no["54"], load, wire=wire)
    d.series(block.no["53"], block.nc["61"], wire=wire)  # R1266: the feed point takes two conductors
    d.series(block.nc["62"], load, wire=wire)
    return fr.build(d, cabinet_document(_cabinet)).model, block, overload


def test_the_block_prints_the_contactors_designation_and_has_no_row() -> None:
    model, block, overload = _build()
    assert item_designation(model, block.id) == "K1"
    rows = {row.item for row in designation_list(model)}
    assert block.id not in rows
    assert item_designation(model, overload.id) != "K1"
    assert overload.id in rows
    tags = {t.text for drawing in drawn_pages(model).values() for t in drawing.texts if t.kind == "TAG" and not t.text.startswith("-X1")}
    assert tags == {"-K1"}
