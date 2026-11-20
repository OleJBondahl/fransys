"""`fr.build` lays out the schematic only when a document keeps a SCHEMATIC page (decision 0118)."""

import fransys as fr
import fransys_parts
from _model_build_cover import cabinet_document, layout_trigger_document, system_document
from demo_designs import cabinet_design
from fransys_author.design import Design

from fransys_model.kernel import Severity


def _build(document_for):
    parts = fransys_parts.load("demo_parts")
    design = cabinet_design(parts)
    c1 = Design(parts).location("C1", "Demo cabinet")
    return fr.build(parts, design.draft(), *document_for(c1))


def test_a_document_with_no_schematic_page_builds_with_no_layout_record():
    """The SYSTEM preset lists SCHEMATIC but yields it when no set is left to print (R2368): a design with none has no layout."""
    parts = fransys_parts.load("demo_parts")
    design = Design(parts)
    design.project(title="Demo", number="D-1", customer="Demo Co", revision=1, author="demo")
    design.revision(1, date="2026-09-22", text="First issue", created="XX")
    result = fr.build(parts, design.draft(), system_document())
    assert not result.model.tables.get("layout.page")
    assert not result.model.tables.get("layout.symbol_placement")
    assert not [f for f in fr.check(result) if f.severity is Severity.ERROR]


def test_a_document_that_keeps_a_schematic_page_gets_the_layout():
    for document_for in (lambda c1: (layout_trigger_document(), cabinet_document(c1)), lambda c1: (cabinet_document(c1),)):
        result = _build(document_for)
        assert dict(result.model.tables["layout.page"])
        assert any(d.symbols for d in result.drawings.values())


# INK_WITHOUT_CONDUCTOR: a falling stock of this file's builds on KI-974 (docs/KNOWN-ISSUES.toml, el-0130).
