"""`fr.build` lays out the schematic only when a document keeps a SCHEMATIC page (decision 0118)."""

from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import cabinet_document, layout_trigger_document, system_document
from demo_designs import cabinet_design
from fransys.pipeline import BuildResult

from fransys_layout import lay_out_schematic
from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from pathlib import Path


def _build(document_for):
    parts = fransys_parts.load("demo_parts")
    design = cabinet_design(parts)
    c1 = fransys_author.Design(parts).location("C1", "Demo cabinet")
    return fr.build(parts, design.draft(), document_for(c1))


def _written(result: BuildResult, out: Path) -> dict[str, bytes]:
    fr.write(result, out)
    return {
        p.relative_to(out).as_posix(): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()
    }


def test_a_document_with_no_schematic_page_builds_with_no_layout_record():
    result = _build(lambda _c1: system_document())
    assert not result.model.tables.get("layout.page")
    assert not result.model.tables.get("layout.symbol_placement")
    assert not [f for f in fr.check(result) if f.severity is Severity.ERROR]
    assert not [f for f in fr.check(result) if f.code == "LAYOUT_MISSING"]


def test_the_exports_of_that_document_equal_those_of_a_build_that_laid_out_anyway(tmp_path):
    lean = _build(lambda _c1: system_document())
    laid_out, _findings = lay_out_schematic(lean.model)
    assert dict(laid_out.tables["layout.page"])  # not vacuous: the forced layout drew pages
    assert _written(lean, tmp_path / "lean") == _written(
        BuildResult(model=laid_out, findings=lean.findings), tmp_path / "forced"
    )


def test_a_document_that_keeps_a_schematic_page_gets_the_layout():
    for document_for in (lambda _c1: layout_trigger_document(), cabinet_document):
        result = _build(document_for)
        assert dict(result.model.tables["layout.page"])
        assert dict(result.model.tables["layout.symbol_placement"])
