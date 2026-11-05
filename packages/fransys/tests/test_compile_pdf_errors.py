"""`_compile_pdf` turns only the cover measurement's panic into a finding (decision 0211)."""

import fransys as fr
import fransys_pdf
import pytest
import typst
from fransys import _exports, pipeline

from electrical_symbols import LIBRARY
from fransys_layout import DiagramLayout
from fransys_model.derive import documents
from fransys_model.kernel import Severity


def _compile(monkeypatch: pytest.MonkeyPatch, tmp_path, source_text: str):
    d = fr.design("demo_parts", place="C1")
    d.project(title="Cabinet", number="CAB-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-16", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    (tmp_path / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=tmp_path / "c.md")
    model = fr.build(d, doc).model
    (document_id,) = documents(model)
    monkeypatch.setattr(fransys_pdf, "source", lambda *_args, **_kwargs: source_text)
    return _exports._compile_pdf(pipeline._Drawn(model, {}, DiagramLayout(diagrams=()), LIBRARY, {}), document_id, fr.settings())


def test_another_typst_error_is_re_raised_untouched(monkeypatch, tmp_path):
    with pytest.raises(typst.TypstError, match="boom"):
        _compile(monkeypatch, tmp_path, '#panic("boom")')


def test_the_cover_panic_becomes_build_errors_naming_the_heights(monkeypatch, tmp_path):
    panic = '#panic("COVER_OVERFLOW cover=240.5 table=30 available=257")'
    with pytest.raises(pipeline.BuildFailedError) as raised:
        _compile(monkeypatch, tmp_path, panic)
    (finding,) = raised.value.findings
    assert (finding.code, finding.severity) == ("COVER_OVERFLOW", Severity.ERROR)
    assert "240.5 mm" in finding.message
