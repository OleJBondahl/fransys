"""Field case: a system block diagram of one tall column is drawn, not refused.
The bug: the column is taller than the A2 sheet, so no frame is placed and check raises DOCUMENT_NO_DRAWINGS with no document written.
A tall column continues on the next sheet; each hub line to a moved box ends in a marker on both sheets (BLOCK-DIAGRAM-CUT)."""

import tempfile
from pathlib import Path

import fransys as fr

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_diagrams

_LEAVES = 20


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
    diagrams, found = lay_out_diagrams(result.model, LIBRARY)
    assert found == ()  # no label overlaps the hub (BLOCK-DIAGRAM)
    lines = tuple(line for d in diagrams.diagrams for sheet in d.sheets for line in sheet.lines)
    assert len({line.cable for line in lines}) == _LEAVES
    (diagram,) = diagrams.diagrams
    assert len(diagram.sheets) == 2
    assert sum(len(sheet.markers) for sheet in diagram.sheets) == 2 * (len(lines) - _LEAVES)
