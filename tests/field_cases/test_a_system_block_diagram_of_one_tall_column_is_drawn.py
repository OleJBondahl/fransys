"""Field case: a system block diagram with one tall column is drawn, not refused.

The engineering shape: one hub device joined by a cable to each of twenty leaf devices, read at the
top of the system. Every leaf sits in the one column right of the hub, so the diagram has a tall
column, as a station with many junction boxes does.

The bug: the column's boxes and gaps are taller than the A2 sheet. The placer returns no frame
(`arrange.stack`, `frame._stacked`), so no diagram records exist and `check` raises
`DOCUMENT_NO_DRAWINGS`, "the diagram has lines but could not be drawn". No document is written.

The rule: a diagram the sheet cannot hold is drawn on more than one sheet. Decision: API-FRICTION-1
F7 (RIO10). Today's engine is frozen (decision 0201); the repro waits for the new layout engine.
"""

import dataclasses
import tempfile
from pathlib import Path

import fransys as fr
import pytest

from fransys_model.layout import DiagramLine, layout_of

_LEAVES = 20


@pytest.mark.xfail(
    strict=True, reason="RIO10: a column taller than the sheet gives no diagram (arrange.py stack)"
)
def test_a_system_block_diagram_of_one_tall_column_is_drawn() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Station\n", encoding="utf-8")
        d = fr.design("demo_parts")
        hub = d.device("P0", "DEMO-CONN-2P")
        for k in range(1, _LEAVES + 1):
            leaf = d.device(f"P{k}", "DEMO-CONN-2P")
            d.cable(f"W{k}", "DEMO-CBL-4G1.5", length_m=2).core(1, hub[1], leaf[1])
        result = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))
    errors = [f.code for f in fr.check(result) if f.severity.name == "ERROR"]
    assert errors == []
    assert len(layout_of(result.model, DiagramLine)) == _LEAVES


def test_the_undrawn_tall_column_is_named_with_its_boxes_and_what_fits() -> None:
    """Today's limit: the INFO names the column and the count, the ERROR points to it."""
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Station\n", encoding="utf-8")
        d = fr.design("demo_parts")
        hub = d.device("P0", "DEMO-CONN-2P")
        for k in range(1, _LEAVES + 1):
            leaf = d.device(f"P{k}", "DEMO-CONN-2P")
            d.cable(f"W{k}", "DEMO-CBL-4G1.5", length_m=2).core(1, hub[1], leaf[1])
        result = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))
    by_code = {f.code: f for f in fr.check(result)}
    assert (
        "The system diagram is not drawn: column 2 holds 20 boxes and one sheet holds 17. "
        "This is a known limit of the system diagram."
    ) in by_code["DIAGRAM_COLUMN_TOO_TALL"].message
    assert "see DIAGRAM_COLUMN_TOO_TALL" in by_code["DOCUMENT_NO_DRAWINGS"].message


def test_an_undrawn_diagram_without_a_tall_column_finding_does_not_claim_one() -> None:
    """The ERROR points to DIAGRAM_COLUMN_TOO_TALL only when the build emitted that INFO."""
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Station\n", encoding="utf-8")
        d = fr.design("demo_parts")
        hub = d.device("P0", "DEMO-CONN-2P")
        for k in range(1, _LEAVES + 1):
            leaf = d.device(f"P{k}", "DEMO-CONN-2P")
            d.cable(f"W{k}", "DEMO-CBL-4G1.5", length_m=2).core(1, hub[1], leaf[1])
        built = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))
    kept = tuple(f for f in built.findings if f.code != "DIAGRAM_COLUMN_TOO_TALL")
    assert len(kept) < len(built.findings)
    by_code = {f.code: f for f in fr.check(dataclasses.replace(built, findings=kept))}
    message = by_code["DOCUMENT_NO_DRAWINGS"].message
    assert "could not be drawn (no finding names the cause)" in message
    assert "DIAGRAM_COLUMN_TOO_TALL" not in message
