"""The cover's Typst measurement and the finding its panic becomes (pdf-0047)."""

import fransys_render
from _build import document, location, model, project, revision_entry
from fransys_pdf import cover_overflow_finding, source

from fransys_model.derive import document_sheets_of
from fransys_model.kernel import Severity
from fransys_model.vocab import DocumentPreset


def _document(cover: str = "x"):
    return document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=location("C1", "Demo cabinet"),
        cover=cover,
    )


def _source(*, revision: bool) -> str:
    c1 = location("C1", "Demo cabinet")
    p = project(title="Demo cabinet", number="DEMO-1", customer="Demo Co", revision=1, author="d")
    entries = [revision_entry("r1", unit=None, revision=1, date="2026-09-22")] if revision else []
    doc = _document("# Cover\n\nText.")
    m = model(c1, p, *entries, doc)
    return source(m, doc.id, {}, fransys_render.sheets(document_sheets_of(m)))


def test_a_panic_text_becomes_an_error_finding_with_the_heights():
    doc = _document()
    found = cover_overflow_finding(
        doc.id, "panicked with: COVER_OVERFLOW cover=240.5 table=30 available=257"
    )
    assert found is not None
    assert (found.code, found.severity, found.subjects) == (
        "COVER_OVERFLOW",
        Severity.ERROR,
        (doc.id,),
    )
    assert "240.5 mm" in found.message
    assert "30 mm" in found.message
    assert "257 mm" in found.message


def test_another_typst_error_is_not_a_cover_overflow():
    doc = _document()
    assert cover_overflow_finding(doc.id, "unknown variable: x") is None


def test_the_cover_source_measures_the_table_only_when_there_is_one():
    assert "measure(block(width: size.width, fr-table))" in _source(revision=True)
    without = _source(revision=False)
    assert "fr-table" not in without
    assert "let table = 0pt" in without
