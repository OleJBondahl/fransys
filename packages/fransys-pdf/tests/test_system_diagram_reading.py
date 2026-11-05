"""A SYSTEM document reads its block diagram without a subject unit (pdf-0052 Q3 amended).

`_diagrams` takes the reading from `document_scope(...).top_level`;
the SYSTEM preset has no unit.
"""

from typing import Any

import fransys as fr
from _build import PDF
from fransys._layout_need import diagram_sheets_of
from fransys_pdf import check

from fransys_model.vocab import DocumentPreset


def _system(tmp_path: Any) -> Any:
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("F", "Field"):
        hub = d.device("M0", "DEMO-MOTOR-4KW", place="L0")
        leaf = d.device("M1", "DEMO-MOTOR-4KW", place="L0")
    d.cable("W1", "DEMO-CBL-4G1.5", place="L0").core(1, hub["U"], leaf["U"])
    cover = tmp_path / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    return fr.build(d, fr.document(DocumentPreset.SYSTEM, None, cover=cover))


def test_a_system_document_asks_for_its_block_diagram_drawing(tmp_path):
    """No svg given: the SYSTEM reading finds the diagram's line and names the missing drawing.
    Negating the `top_level` read hides the finding."""
    built = _system(tmp_path)
    sheets = diagram_sheets_of(built.diagrams)
    found = [f.message for f in check(built.model, {}, diagrams=sheets, laid=frozendict(), pdf=PDF) if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert any(m.startswith("BLOCK_DIAGRAM: missing drawing for") for m in found), found
