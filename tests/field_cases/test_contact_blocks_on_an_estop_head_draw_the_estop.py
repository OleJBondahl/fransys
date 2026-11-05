"""Field case: an e-stop head sold apart from two break-contact blocks clipped on with parent=, each block opening its own circuit.
The bug: the blocks printed their own designations and drew plain break contacts, because nothing said what operates a switch.
Fixed by parts-0020 (operated_by), model-0222 (the holder's operator) and layout-0220 (a switch draws by its operator)."""

import csv
import io
from typing import TYPE_CHECKING, Any

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

if TYPE_CHECKING:
    from pathlib import Path


def _design() -> tuple[fr.Design, object, Any, Any]:
    """The head `S1` with two NC blocks, each in its own circuit off strip `X1`."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="E-stop", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    head = d.device("S1", "DEMO-HEAD-ESTOP")
    with d.function("G1", "Stop circuit 1"):
        first = d.device(None, "DEMO-BLOCK-1NC", name="block-1", parent=head)
    with d.function("G2", "Stop circuit 2"):
        second = d.device(None, "DEMO-BLOCK-1NC-21", name="block-2", parent=head)
    wire = (BU, 0.5)
    d.series(strip[1].inner, first["11"], wire=wire)
    d.series(first["12"], strip[2].inner, wire=wire)
    d.series(strip[3].inner, second["21"], wire=wire)
    d.series(second["22"], strip[4].inner, wire=wire)
    return d, cabinet, first, second


def test_every_block_draws_the_emergency_stop() -> None:
    """Each block draws its own mushroom."""
    d, cabinet, _, _ = _design()
    model = fr.build(d, cabinet_document(cabinet)).model
    pins = {"11", "21"}  # each block's first pin, the marking on its drawn symbol
    drawn = {
        dict(symbol.slots)["marking.in"]: symbol.key
        for drawing in drawn_pages(model).values()
        for symbol in drawing.symbols
        if dict(symbol.slots).get("marking.in") in pins
    }
    assert drawn == {"11": "emergency-stop", "21": "emergency-stop"}


def test_the_wire_list_prints_the_heads_designation_on_both_blocks(tmp_path: Path) -> None:
    d, cabinet, _, _ = _design()
    written = fr.write(fr.build(d, cabinet_document(cabinet)), tmp_path)
    (path,) = (p for p in written if p.name.endswith("wires.csv"))
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    ends = {end for row in rows for end in (row["from"], row["to"])}
    blocks = {end.rsplit("-", 1)[-1] for end in ends if not end.rsplit("-", 1)[-1].startswith("X")}
    assert blocks == {"S1:11", "S1:12", "S1:21", "S1:22"}
