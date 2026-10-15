"""Field case: two contact blocks on one emergency-stop head, in two circuits.

The engineering shape: an e-stop head sold apart from its contact blocks, with two break-contact
blocks clipped on and joined to it with `parent=`. Each block opens its own circuit. An
electrician reads the head's tag on both blocks, and each block's contact is an e-stop contact.

The bug: the blocks printed their own designations (`-S2:11`, `-S3:21`) and drew plain break
contacts, because nothing said what operates a `switch`.

Fixing decisions: parts-0020 (`[part] operated_by`), model-0222 (the holder's operator, and switch
blocks under a stating head print its designation) and layout-0220 (a switch draws by its
operator). Invented parts from `demo_parts`: `DEMO-HEAD-ESTOP`, `DEMO-BLOCK-1NC` and
`DEMO-BLOCK-1NC-21`.
The drawn symbol is a layout record, read through `fransys_model.layout` as
`test_add_on_block_carries_device_designation.py` does; the public API has no reader for it.
"""

import csv
import io
from typing import TYPE_CHECKING

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from pathlib import Path


def _design() -> tuple[fr.Design, object, fr.Device, fr.Device]:
    """The head `S1` with two NC blocks, each in its own circuit off strip `X1`."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="E-stop", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    d.layout.profile(actuator_each_contact=False)  # one actuator per device (the default is True)
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    head = d.device("S1", "DEMO-HEAD-ESTOP")
    with d.function("G1", "Stop circuit 1"):
        first = d.device(None, "DEMO-BLOCK-1NC", name="block-1", parent=head)
    with d.function("G2", "Stop circuit 2"):
        second = d.device(None, "DEMO-BLOCK-1NC-21", name="block-2", parent=head)
    wire = (BU, 0.5)
    d.detail.wire(strip[1], first["11"], wire=wire)
    d.detail.wire(first["12"], strip[2], wire=wire)
    d.detail.wire(strip[3], second["21"], wire=wire)
    d.detail.wire(second["22"], strip[4], wire=wire)
    return d, cabinet, first, second


def test_the_lead_block_draws_the_emergency_stop_and_the_other_its_contact() -> None:
    """ACTUATOR-ONCE (layout-0237): one mushroom, at 11-12; 21-22 keeps its positive opening."""
    d, cabinet, first, second = _design()
    model = fr.build(d, cabinet_document(cabinet)).model
    blocks = {first.id, second.id}
    drawn = [
        p.symbol
        for p in layout_of(model, SymbolPlacement).values()
        if p.function and functions(model)[p.function].item in blocks
    ]
    assert drawn == ["emergency-stop", "break-contact-positive-opening"]


def test_the_wire_list_prints_the_heads_designation_on_both_blocks(tmp_path: Path) -> None:
    d, cabinet, _, _ = _design()
    written = fr.write(fr.build(d, cabinet_document(cabinet)), tmp_path)
    (path,) = (p for p in written if p.name.endswith("wires.csv"))
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    ends = {end for row in rows for end in (row["from"], row["to"])}
    blocks = {end.rsplit("-", 1)[-1] for end in ends if not end.rsplit("-", 1)[-1].startswith("X")}
    assert blocks == {"S1:11", "S1:12", "S1:21", "S1:22"}
