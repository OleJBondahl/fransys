"""Determinism: the authored date, never the clock (spec P3)."""

from _build import document, location, model, project, revision_entry
from fransys_pdf._geometry import document_metadata

from fransys_model.vocab import DocumentPreset, documents


def _metadata(*records):
    """`document_metadata` of a location document about `C1`, in the model of `records`."""
    c1 = location("C1", "Demo cabinet")
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=c1, cover="# Cover")
    m = model(c1, doc, *records)
    return document_metadata(m, documents(m)[doc.id])


def test_date_is_the_authored_revision_date_not_auto():
    entry = revision_entry("r1", unit=None, revision=1, date="2026-09-22")
    text = _metadata(project(title="T", author="A"), entry)
    assert "date: datetime(year: 2026, month: 9, day: 22)" in text
    assert "auto" not in text


def test_title_and_author_come_from_the_project():
    text = _metadata(project(title="Demo cabinet", author="demo"))
    assert 'title: "Demo cabinet"' in text
    assert 'author: "demo"' in text


def test_no_project_gives_date_none_and_empty_title_and_author():
    text = _metadata()
    assert "date: none" in text
    assert 'title: ""' in text
    assert 'author: ""' in text
